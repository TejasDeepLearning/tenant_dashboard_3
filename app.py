import os
import re
import json
import logging
import csv
import io
import smtplib
import secrets
import bcrypt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, Response, flash, session, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import openai

# Load environment variables
load_dotenv()

# Configure logging based on environment
log_level = logging.INFO if os.getenv('FLASK_ENV') == 'production' else logging.DEBUG
logging.basicConfig(level=log_level)

app = Flask(__name__)

# Security Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = "uploads"
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Constants
UPLOAD_FOLDER = "uploads"
DATA_FILE = "agreements_data.json"
ARCHIVE_FILE = "archived_agreements.json"
SETTINGS_FILE = "settings.json"
USERS_FILE = "users.json"
ALLOWED_EXTENSIONS = {"pdf"}

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access the dashboard.'
login_manager.login_message_category = 'info'

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Security headers
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if os.getenv('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# User management class
class User(UserMixin):
    def __init__(self, id, username, password_hash, is_admin=False):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

@login_manager.user_loader
def load_user(user_id):
    users = load_users()
    for user_data in users:
        if user_data['id'] == user_id:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                password_hash=user_data['password_hash'],
                is_admin=user_data.get('is_admin', False)
            )
    return None

def load_users():
    """Load users from JSON file."""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Create default admin user if no users file exists
            default_users = create_default_admin()
            save_users(default_users)
            return default_users
    except Exception as e:
        logging.error(f"Error loading users: {e}")
        return []

def save_users(users):
    """Save users to JSON file."""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        logging.debug(f"Saved {len(users)} users")
    except Exception as e:
        logging.error(f"Error saving users: {e}")

def create_default_admin():
    """Create default admin user."""
    default_password = os.getenv('DEFAULT_ADMIN_PASSWORD', 'admin123')
    password_hash = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    return [{
        'id': 'admin_' + secrets.token_hex(8),
        'username': 'admin',
        'password_hash': password_hash,
        'is_admin': True,
        'created_at': datetime.now().isoformat()
    }]

openai.api_key = os.getenv("OPENAI_API_KEY")

def load_agreements():
    """Load existing agreements from JSON file."""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                agreements = json.load(f)
                logging.debug(f"Loaded {len(agreements)} existing agreements")
                return agreements
        else:
            logging.debug("No existing data file found, starting fresh")
            return []
    except Exception as e:
        logging.error(f"Error loading agreements: {e}")
        return []

def save_agreements(agreements):
    """Save agreements to JSON file."""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(agreements, f, indent=2, ensure_ascii=False)
            logging.debug(f"Saved {len(agreements)} agreements to {DATA_FILE}")
    except Exception as e:
        logging.error(f"Error saving agreements: {e}")

def load_archived_agreements():
    """Load archived agreements from JSON file."""
    try:
        if os.path.exists(ARCHIVE_FILE):
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                archived = json.load(f)
                logging.debug(f"Loaded {len(archived)} archived agreements")
                return archived
        else:
            logging.debug("No archived data file found")
            return []
    except Exception as e:
        logging.error(f"Error loading archived agreements: {e}")
        return []

def save_archived_agreements(archived):
    """Save archived agreements to JSON file."""
    try:
        with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(archived, f, indent=2, ensure_ascii=False)
            logging.debug(f"Saved {len(archived)} archived agreements to {ARCHIVE_FILE}")
    except Exception as e:
        logging.error(f"Error saving archived agreements: {e}")

def load_settings():
    """Load settings from JSON file."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                logging.debug(f"Loaded settings: {settings}")
                
                # Handle migration from old single gmail_address to gmail_addresses list
                if "gmail_address" in settings and "gmail_addresses" not in settings:
                    old_gmail = settings.get("gmail_address", "").strip()
                    settings["gmail_addresses"] = [old_gmail] if old_gmail else []
                    if "gmail_address" in settings:
                        del settings["gmail_address"]
                    save_settings(settings)  # Save the migrated format
                
                # Handle migration from simple gmail_addresses list to tenant_gmail_pairs
                if "gmail_addresses" in settings and "tenant_gmail_pairs" not in settings:
                    old_gmail_list = settings.get("gmail_addresses", [])
                    # Convert old list to new format with empty tenant names
                    settings["tenant_gmail_pairs"] = []
                    for gmail in old_gmail_list:
                        if gmail and gmail.strip():
                            settings["tenant_gmail_pairs"].append({
                                "tenant_name": "",
                                "gmail_address": gmail.strip()
                            })
                    if "gmail_addresses" in settings:
                        del settings["gmail_addresses"]
                    save_settings(settings)  # Save the migrated format
                
                return settings
        else:
            logging.debug("No settings file found, using defaults")
            return {"tenant_gmail_pairs": []}
    except Exception as e:
        logging.error(f"Error loading settings: {e}")
        return {"tenant_gmail_pairs": []}

def save_settings(settings):
    """Save settings to JSON file."""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            logging.debug(f"Saved settings: {settings}")
    except Exception as e:
        logging.error(f"Error saving settings: {e}")

def get_email_config():
    """Get email configuration from environment variables and saved settings."""
    # Load saved tenant-Gmail pairs to get sender information
    settings = load_settings()
    tenant_gmail_pairs = settings.get("tenant_gmail_pairs", [])
    
    # Use the first available Gmail address as sender, or fallback to environment variable
    sender_email = None
    sender_name = "Tenant Dashboard"  # Default name
    
    if tenant_gmail_pairs:
        # Use the first Gmail address from saved pairs
        first_pair = tenant_gmail_pairs[0]
        sender_email = first_pair.get('gmail_address', '')
        sender_name = first_pair.get('tenant_name', 'Tenant Dashboard')
        if not sender_name or sender_name.strip() == '':
            sender_name = "Tenant Dashboard"
    
    # If no saved addresses, fall back to environment variable
    if not sender_email:
        sender_email = os.getenv('SENDER_EMAIL')
        sender_name = os.getenv('SENDER_NAME', 'Tenant Dashboard')
    
    config = {
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'sender_email': sender_email,
        'sender_password': os.getenv('SENDER_PASSWORD'),
        'sender_name': sender_name
    }
    
    # Debug logging for configuration
    logging.debug(f"Email config - Server: {config['smtp_server']}, Port: {config['smtp_port']}")
    logging.debug(f"Sender email: {config['sender_email']} (from {'saved addresses' if tenant_gmail_pairs else 'environment variable'})")
    logging.debug(f"Sender name: {config['sender_name']}")
    logging.debug(f"Sender password configured: {'Yes' if config['sender_password'] else 'No'}")
    
    return config

def create_alert_email_content(tenant_name, agreement_data, alert_type):
    """Create email content based on alert type."""
    
    alert_messages = {
        'three_months': {
            'subject': f'Agreement Expiry Notice - 3 Months Remaining ({tenant_name})',
            'urgency': 'Notice',
            'color': 'amber yellow',
            'action': 'Please start planning for renewal discussions.'
        },
        'two_months': {
            'subject': f'Agreement Expiry Alert - 2 Months Remaining ({tenant_name})',
            'urgency': 'Alert',
            'color': 'light red',
            'action': 'Please begin renewal negotiations immediately.'
        },
        'one_month': {
            'subject': f'URGENT: Agreement Expiry - 1 Month Remaining ({tenant_name})',
            'urgency': 'URGENT',
            'color': 'red',
            'action': 'Immediate action required for renewal or termination.'
        },
        'expired': {
            'subject': f'CRITICAL: Agreement Expired ({tenant_name})',
            'urgency': 'CRITICAL',
            'color': 'dark red',
            'action': 'Agreement has expired. Please contact management immediately.'
        }
    }
    
    alert_info = alert_messages.get(alert_type, alert_messages['three_months'])
    
    # Create HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
            .alert-{alert_type} {{ 
                padding: 15px; 
                border-radius: 5px; 
                margin: 15px 0;
                font-weight: bold;
            }}
            .alert-three_months {{ background-color: #fff3cd; color: #856404; }}
            .alert-two_months {{ background-color: #f8d7da; color: #721c24; }}
            .alert-one_month {{ background-color: #dc3545; color: #ffffff; }}
            .alert-expired {{ background-color: #dc3545; color: #ffffff; }}
            .details {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 0.9em; color: #6c757d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Tenant Agreement Alert</h2>
                <p><strong>Tenant:</strong> {tenant_name}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            
            <div class="alert-{alert_type}">
                <h3>{alert_info['urgency']}: Agreement Expiry {alert_info['urgency']}</h3>
                <p>{alert_info['action']}</p>
            </div>
            
            <div class="details">
                <h4>Agreement Details:</h4>
                <p><strong>Area:</strong> {agreement_data.get('area_sqft', 'N/A')} sqft</p>
                <p><strong>Floor:</strong> {agreement_data.get('floor', 'N/A')}</p>
                <p><strong>Building:</strong> {agreement_data.get('building', 'N/A')}</p>
                <p><strong>Agreement Start Date:</strong> {agreement_data.get('agreement_start_date', 'N/A')}</p>
                <p><strong>Agreement Expiry Date:</strong> {agreement_data.get('agreement_expiry_date', 'N/A')}</p>
                <p><strong>Rent Amount:</strong> Rs {agreement_data.get('rent_amount', 'N/A')}/sqft/month</p>
                <p><strong>Lock-in Period End:</strong> {agreement_data.get('lock_in_period_end_date', 'N/A')}</p>
            </div>
            
            <p>This is an automated notification from your Tenant Dashboard system. Please contact the property management team if you have any questions or need to discuss renewal options.</p>
            
            <div class="footer">
                <p>This email was sent from the Tenant Dashboard System.<br>
                Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return alert_info['subject'], html_content

def find_tenant_gmail(tenant_name, tenant_gmail_pairs):
    """Find Gmail address for a tenant by matching names."""
    for pair in tenant_gmail_pairs:
        if pair.get('tenant_name', '').strip().lower() == tenant_name.strip().lower():
            return pair.get('gmail_address', '')
    return None

def send_email_notification(recipient_email, subject, html_content):
    """Send email notification using SMTP."""
    try:
        config = get_email_config()
        
        # Check configuration
        if not config['sender_email']:
            logging.error("No sender email found. Please add at least one Gmail address in the Gmail settings or set SENDER_EMAIL environment variable.")
            return False, "No sender email configured"
            
        if not config['sender_password']:
            logging.error("SENDER_PASSWORD environment variable not set.")
            return False, "Missing sender password configuration"
        
        logging.debug(f"Attempting to send email to {recipient_email}")
        logging.debug(f"Using sender email: {config['sender_email']}")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{config['sender_name']} <{config['sender_email']}>"
        msg['To'] = recipient_email
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email with detailed error handling
        server = None
        try:
            logging.debug(f"Connecting to SMTP server: {config['smtp_server']}:{config['smtp_port']}")
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            
            logging.debug("Starting TLS encryption")
            server.starttls()
            
            logging.debug("Attempting login")
            server.login(config['sender_email'], config['sender_password'])
            
            logging.debug("Sending email")
            text = msg.as_string()
            server.sendmail(config['sender_email'], recipient_email, text)
            
            logging.info(f"Email sent successfully to {recipient_email}")
            return True, "Success"
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP Authentication failed: {e}. Check your Gmail credentials and app password."
            logging.error(error_msg)
            return False, error_msg
            
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipient {recipient_email} refused: {e}"
            logging.error(error_msg)
            return False, error_msg
            
        except smtplib.SMTPServerDisconnected as e:
            error_msg = f"SMTP server disconnected: {e}"
            logging.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"SMTP error: {e}"
            logging.error(error_msg)
            return False, error_msg
            
        finally:
            if server:
                try:
                    server.quit()
                except:
                    pass
        
    except Exception as e:
        error_msg = f"General error sending email to {recipient_email}: {e}"
        logging.error(error_msg)
        return False, error_msg

def archive_agreement(agreement):
    """Move an agreement to the archive."""
    archived = load_archived_agreements()
    # Add deletion timestamp
    agreement["archived_timestamp"] = datetime.now().isoformat()
    archived.append(agreement)
    save_archived_agreements(archived)

def normalize_period_of_rent(period_value):
    """Convert period of rent to standardized months format."""
    if not period_value or period_value.strip() == "":
        return ""
    
    period_str = str(period_value).lower().strip()
    
    # Extract numbers from the string
    import re
    numbers = re.findall(r'\d+', period_str)
    
    if not numbers:
        return ""
    
    num = int(numbers[0])
    
    # Convert based on units mentioned
    if 'year' in period_str:
        months = num * 12
    elif 'month' in period_str:
        months = num
    elif 'quarter' in period_str:
        months = num * 3
    else:
        # Default assumption: if only a number, assume months
        months = num
    
    return str(months)

def normalize_rent_amount(rent_value):
    """Extract numeric rent amount per sqft per month."""
    if not rent_value or str(rent_value).strip() == "":
        return ""
    
    rent_str = str(rent_value).strip()
    
    # Extract numbers (including decimals) from the string
    import re
    # Look for decimal numbers first, then integers
    numbers = re.findall(r'\d+\.?\d*', rent_str)
    
    if not numbers:
        return ""
    
    # Return the first number found (should be the rent amount)
    return numbers[0]

def normalize_maintenance_amount(maintenance_value):
    """Extract total numeric maintenance amount per sqft per month."""
    if not maintenance_value or str(maintenance_value).strip() == "":
        return ""
    
    maintenance_str = str(maintenance_value).strip()
    
    # Extract all numbers (including decimals) from the string
    import re
    numbers = re.findall(r'\d+\.?\d*', maintenance_str)
    
    if not numbers:
        return ""
    
    # Sum all numbers found (to handle cases like "Rs.11 + Rs. 2")
    total = 0
    for num_str in numbers:
        try:
            total += float(num_str)
        except ValueError:
            continue
    
    # Return as string, removing unnecessary decimal places
    if total == int(total):
        return str(int(total))
    else:
        return str(total)

def normalize_rent_escalation(escalation_value):
    """Extract percentage value from rent escalation."""
    if not escalation_value or str(escalation_value).strip() == "":
        return ""
    
    escalation_str = str(escalation_value).strip()
    
    # Extract percentage value
    import re
    # Look for number followed by % or number by itself
    percentage_match = re.search(r'(\d+\.?\d*)%?', escalation_str)
    
    if percentage_match:
        number = percentage_match.group(1)
        # Always return with % sign
        return f"{number}%"
    
    return ""

def normalize_area_sqft(area_value):
    """Extract numeric square footage value."""
    if not area_value or str(area_value).strip() == "":
        return ""
    
    area_str = str(area_value).strip()
    
    # Extract numeric value
    import re
    numbers = re.findall(r'\d+', area_str)
    
    if numbers:
        return numbers[0]  # Return the first number found
    
    return ""

def normalize_floor(floor_value):
    """Standardize floor information."""
    if not floor_value or str(floor_value).strip() == "":
        return ""
    
    floor_str = str(floor_value).strip().lower()
    
    # Standardize common floor formats
    if 'ground' in floor_str or 'g.f' in floor_str or floor_str in ['gf', '0']:
        return "Ground Floor"
    elif '1st' in floor_str or 'first' in floor_str or floor_str in ['1', 'f1']:
        return "1st Floor"
    elif '2nd' in floor_str or 'second' in floor_str or floor_str in ['2', 'f2']:
        return "2nd Floor"
    elif '3rd' in floor_str or 'third' in floor_str or floor_str in ['3', 'f3']:
        return "3rd Floor"
    elif '4th' in floor_str or 'fourth' in floor_str or floor_str in ['4', 'f4']:
        return "4th Floor"
    elif '5th' in floor_str or 'fifth' in floor_str or floor_str in ['5', 'f5']:
        return "5th Floor"
    else:
        # Return as is if no standard format matches
        return str(floor_value).strip()

def normalize_building(building_value):
    """Standardize building names."""
    if not building_value or str(building_value).strip() == "":
        return ""
    
    building_str = str(building_value).strip().lower()
    
    # Standardize building names
    if 'jp classic' in building_str or 'jp-classic' in building_str:
        return "JP Classic"
    elif 'silver software' in building_str or 'silver-software' in building_str:
        return "Silver Software"
    else:
        # Return as is if no standard building matches
        return str(building_value).strip()

def add_unique_id(agreement):
    """Add a unique ID to an agreement based on timestamp."""
    agreement["id"] = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
    agreement["upload_timestamp"] = datetime.now().isoformat()
    return agreement

def extract_text_from_pdf(pdf_path):
    logging.debug(f"Extracting text from: {pdf_path}")
    images = convert_from_path(pdf_path)
    extracted_text = ""
    for image in images:
        text = pytesseract.image_to_string(image)
        extracted_text += text + "\n"
    logging.debug(f"Extracted text: {extracted_text}")
    return extracted_text

def calculate_alert_status(agreement_expiry_date):
    """Calculate alert status based on agreement expiry date."""
    if not agreement_expiry_date or agreement_expiry_date.strip() == "":
        logging.debug("No agreement expiry date provided")
        return ""
    
    try:
        # Clean the date string
        date_str = agreement_expiry_date.strip()
        logging.debug(f"Trying to parse date: '{date_str}'")
        
        # Try different date formats
        date_formats = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
            "%Y/%m/%d", "%m-%d-%Y", "%d.%m.%Y", "%Y.%m.%d",
            "%B %d, %Y", "%d %B %Y", "%b %d, %Y", "%d %b %Y"
        ]
        expiry_date = None
        
        for fmt in date_formats:
            try:
                expiry_date = datetime.strptime(date_str, fmt).date()
                logging.debug(f"Successfully parsed date with format {fmt}: {expiry_date}")
                break
            except ValueError:
                continue
        
        if not expiry_date:
            logging.debug(f"Could not parse date: {date_str}")
            return ""
        
        today = datetime.today().date()
        three_months_before = expiry_date - timedelta(days=90)
        two_months_before = expiry_date - timedelta(days=60)
        one_month_before = expiry_date - timedelta(days=30)
        
        logging.debug(f"Today: {today}")
        logging.debug(f"Agreement expiry date: {expiry_date}")
        logging.debug(f"Three months before: {three_months_before}")
        logging.debug(f"Two months before: {two_months_before}")
        logging.debug(f"One month before: {one_month_before}")
        
        if today < three_months_before:
            logging.debug("Status: No alert (more than 3 months away)")
            return ""  # No alert if more than 3 months away
        elif three_months_before <= today < two_months_before:
            logging.debug("Status: three_months (amber yellow)")
            return "three_months"  # Amber yellow: 3 months before
        elif two_months_before <= today < one_month_before:
            logging.debug("Status: two_months (light red)")
            return "two_months"  # Light red: 2 months before
        elif one_month_before <= today < expiry_date:
            logging.debug("Status: one_month (dark red)")
            return "one_month"  # Dark red: 1 month before
        elif today >= expiry_date:
            logging.debug("Status: expired (dark red)")
            return "expired"  # Dark red: After deadline
        else:
            return ""
    except Exception as e:
        logging.error(f"Error calculating alert status: {e}")
        return ""

def extract_information_with_gpt4o(text):
    prompt = (
        "Extract the following details from this rental agreement and return them as a single JSON object with these keys: "
        '"tenant_name", "area_sqft", "floor", "building", "period_of_rent", "rent_amount", "maintenance", "rent_escalation", '
        '"agreement_start_date", "agreement_expiry_date", "lock_in_period", "lock_in_period_end_date", '
        '"rental_period_greater_than_lock_in_period", "next_rent_escalation". '
        "For dates, use YYYY-MM-DD format. "
        "For 'period_of_rent', convert to months as a number only (e.g., '12' for 1 year, '24' for 2 years, '6' for 6 months). "
        "For 'rent_amount', extract only the numeric rent per sqft per month value (e.g., '72' from 'Rs 72 per sqft per month', '90.50' from 'Rs. 90.50 per square foot per month'). "
        "For 'maintenance', extract only the total numeric maintenance per sqft per month value (e.g., '13' from 'Rs.11 per square foot per month + Rs. 2 per square foot per month for canteen', '10' from 'Rs 10 per sqft per month'). "
        "For 'rent_escalation', extract only the percentage value (e.g., '7%' from '7%', '5%' from '5% annually'). "
        "For 'lock_in_period', convert to months as a number only (e.g., '24' for 24 months, '36' for 3 years, '6' for 6 months). "
        "For 'area_sqft', extract only the numeric square footage value (e.g., '3200' from 'ad measuring 3200 sqft', '1500' from '1500 square feet'). "
        "For 'floor', extract the floor information (e.g., 'Ground Floor', '1st Floor', '2nd Floor'). "
        "For 'building', extract the building name - should be either 'JP Classic' or 'Silver Software' (e.g., 'JP Classic' from '1st Floor of JP Classic', 'Silver Software' if mentioned). "
        "For 'rental_period_greater_than_lock_in_period', return ONLY 'True' or 'False' (not Yes/No or true/false). "
        "If a value is not found, use an empty string. Only return the JSON object, nothing else.\n\n"
        f"{text}"
    )
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an OCR and information extraction assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1024,
    )
    content = response.choices[0].message.content
    logging.debug(f"GPT-4o raw response: {content}")
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        json_str = json_match.group(0)
        try:
            data = json.loads(json_str)
        except Exception as e:
            logging.error(f"JSON decode error: {e}")
            data = {}
    else:
        data = {}
    keys = [
        "tenant_name", "area_sqft", "floor", "building", "period_of_rent", "rent_amount", "maintenance", "rent_escalation",
        "agreement_start_date", "agreement_expiry_date", "lock_in_period", "lock_in_period_end_date",
        "rental_period_greater_than_lock_in_period", "next_rent_escalation"
    ]
    for key in keys:
        if key not in data:
            data[key] = ""
    
    # Normalize area_sqft to numeric value
    area_value = data.get("area_sqft", "")
    data["area_sqft"] = normalize_area_sqft(area_value)
    
    # Normalize floor to standard format
    floor_value = data.get("floor", "")
    data["floor"] = normalize_floor(floor_value)
    
    # Normalize building to standard names
    building_value = data.get("building", "")
    data["building"] = normalize_building(building_value)
    
    # Normalize period_of_rent to months
    period_value = data.get("period_of_rent", "")
    data["period_of_rent"] = normalize_period_of_rent(period_value)
    
    # Normalize rent_amount to numeric value
    rent_value = data.get("rent_amount", "")
    data["rent_amount"] = normalize_rent_amount(rent_value)
    
    # Normalize maintenance to numeric value
    maintenance_value = data.get("maintenance", "")
    data["maintenance"] = normalize_maintenance_amount(maintenance_value)
    
    # Normalize rent_escalation to percentage value
    escalation_value = data.get("rent_escalation", "")
    data["rent_escalation"] = normalize_rent_escalation(escalation_value)
    
    # Normalize lock_in_period to months (using same logic as period_of_rent)
    lock_in_value = data.get("lock_in_period", "")
    data["lock_in_period"] = normalize_period_of_rent(lock_in_value)
    
    # Normalize rental_period_greater_than_lock_in_period to True/False
    rental_period_value = data.get("rental_period_greater_than_lock_in_period", "")
    
    # Handle different data types (string, boolean, etc.)
    if isinstance(rental_period_value, bool):
        data["rental_period_greater_than_lock_in_period"] = "True" if rental_period_value else "False"
    elif isinstance(rental_period_value, str):
        rental_period_value = rental_period_value.strip()
        if rental_period_value.lower() in ["yes", "true", "1"]:
            data["rental_period_greater_than_lock_in_period"] = "True"
        elif rental_period_value.lower() in ["no", "false", "0"]:
            data["rental_period_greater_than_lock_in_period"] = "False"
        else:
            data["rental_period_greater_than_lock_in_period"] = "False"  # Default to False if unclear
    else:
        data["rental_period_greater_than_lock_in_period"] = "False"  # Default to False if unclear
    
    # Add alert status based on agreement expiry date
    expiry_date = data.get("agreement_expiry_date", "")
    alert_status = calculate_alert_status(expiry_date)
    data["alert_status"] = alert_status
    
    # Debug logging
    logging.debug(f"Agreement expiry date: {expiry_date}")
    logging.debug(f"Calculated alert status: {alert_status}")
    
    return data

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    """User login route."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("login.html")
        
        users = load_users()
        user = None
        for user_data in users:
            if user_data['username'] == username:
                user = User(
                    id=user_data['id'],
                    username=user_data['username'],
                    password_hash=user_data['password_hash'],
                    is_admin=user_data.get('is_admin', False)
                )
                break
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password.", "error")
    
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    """User logout route."""
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))

@app.route("/", methods=["GET", "POST"])
@login_required
@limiter.limit("50 per hour")
def dashboard():
    # Load existing agreements and settings
    agreements = load_agreements()
    settings = load_settings()
    
    # Update alert status and normalize values for all existing agreements
    for agreement in agreements:
        agreement["alert_status"] = calculate_alert_status(agreement.get("agreement_expiry_date", ""))
        
        # Handle legacy data - convert place_occupied to new fields if needed
        if "place_occupied" in agreement and not agreement.get("area_sqft"):
            place = agreement.get("place_occupied", "")
            # Extract area, floor, and building from place_occupied
            agreement["area_sqft"] = normalize_area_sqft(place)
            agreement["floor"] = normalize_floor(place)
            agreement["building"] = normalize_building(place)
        
        # Normalize new fields for existing data
        area_value = agreement.get("area_sqft", "")
        agreement["area_sqft"] = normalize_area_sqft(area_value)
        
        floor_value = agreement.get("floor", "")
        agreement["floor"] = normalize_floor(floor_value)
        
        building_value = agreement.get("building", "")
        agreement["building"] = normalize_building(building_value)
        
        # Normalize period_of_rent for existing data
        period_value = agreement.get("period_of_rent", "")
        agreement["period_of_rent"] = normalize_period_of_rent(period_value)
        
        # Normalize rent_amount for existing data
        rent_value = agreement.get("rent_amount", "")
        agreement["rent_amount"] = normalize_rent_amount(rent_value)
        
        # Normalize maintenance for existing data
        maintenance_value = agreement.get("maintenance", "")
        agreement["maintenance"] = normalize_maintenance_amount(maintenance_value)
        
        # Normalize rent_escalation for existing data
        escalation_value = agreement.get("rent_escalation", "")
        agreement["rent_escalation"] = normalize_rent_escalation(escalation_value)
        
        # Normalize lock_in_period for existing data (using same logic as period_of_rent)
        lock_in_value = agreement.get("lock_in_period", "")
        agreement["lock_in_period"] = normalize_period_of_rent(lock_in_value)
        
        # Normalize rental_period_greater_than_lock_in_period for existing data
        rental_period_value = agreement.get("rental_period_greater_than_lock_in_period", "")
        
        # Handle different data types (string, boolean, etc.)
        if isinstance(rental_period_value, bool):
            agreement["rental_period_greater_than_lock_in_period"] = "True" if rental_period_value else "False"
        elif isinstance(rental_period_value, str):
            rental_period_value = rental_period_value.strip()
            if rental_period_value.lower() in ["yes", "true", "1"]:
                agreement["rental_period_greater_than_lock_in_period"] = "True"
            elif rental_period_value.lower() in ["no", "false", "0"]:
                agreement["rental_period_greater_than_lock_in_period"] = "False"
            else:
                agreement["rental_period_greater_than_lock_in_period"] = "False"
        else:
            agreement["rental_period_greater_than_lock_in_period"] = "False"
    
    if request.method == "POST":
        file = request.files["file"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            full_text = extract_text_from_pdf(filepath)
            data = extract_information_with_gpt4o(full_text)
            
            # Add unique ID and timestamp
            data = add_unique_id(data)
            
            # Debug: Print the final data being sent to template
            logging.debug(f"Final data being sent to template: {data}")
            
            # Add new agreement to the list
            agreements.append(data)
            
            # Save all agreements to file
            save_agreements(agreements)
            
    return render_template("dashboard.html", agreements=agreements, settings=settings)

@app.route("/test_alert")
@login_required
def test_alert():
    """Test route to verify alert functionality with test dates"""
    test_agreements = [
        {
            "tenant_name": "Test Tenant 1",
            "area_sqft": "3200",
            "floor": "Ground Floor",
            "building": "JP Classic",
            "period_of_rent": "24",
            "rent_amount": "72",
            "maintenance": "13",
            "rent_escalation": "7%",
            "agreement_start_date": "2024-01-01",
            "agreement_expiry_date": (datetime.today() + timedelta(days=75)).strftime("%Y-%m-%d"),  # ~2.5 months from now (should be amber)
            "lock_in_period": "18",
            "lock_in_period_end_date": (datetime.today() + timedelta(days=15)).strftime("%Y-%m-%d"),  # 15 days from now (should be green)
            "rental_period_greater_than_lock_in_period": "True",
            "next_rent_escalation": "2024-07-01",
            "alert_status": "approaching"
        },
        {
            "tenant_name": "Test Tenant 2",
            "area_sqft": "1500",
            "floor": "1st Floor",
            "building": "JP Classic",
            "period_of_rent": "36",
            "rent_amount": "90.50",
            "maintenance": "10",
            "rent_escalation": "5%",
            "agreement_start_date": "2023-06-01",
            "agreement_expiry_date": (datetime.today() + timedelta(days=45)).strftime("%Y-%m-%d"),  # ~1.5 months from now (should be light red)
            "lock_in_period": "24",
            "lock_in_period_end_date": (datetime.today() - timedelta(days=45)).strftime("%Y-%m-%d"),  # 45 days past (should be red)
            "rental_period_greater_than_lock_in_period": "False",
            "next_rent_escalation": "2024-06-01",
            "alert_status": "overdue"
        },
        {
            "tenant_name": "Test Tenant 3",
            "area_sqft": "2800",
            "floor": "2nd Floor",
            "building": "Silver Software",
            "period_of_rent": "18",
            "rent_amount": "65",
            "maintenance": "8.5",
            "rent_escalation": "6%",
            "agreement_start_date": "2023-12-01",
            "agreement_expiry_date": (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d"),  # 30 days ago (should be dark red - expired)
            "lock_in_period": "12",
            "lock_in_period_end_date": (datetime.today() - timedelta(days=10)).strftime("%Y-%m-%d"),  # 10 days past (should be gray)
            "rental_period_greater_than_lock_in_period": "True",
            "next_rent_escalation": "2024-12-01",
            "alert_status": "grace_period"
        },
        {
            "tenant_name": "Test Tenant 4",
            "area_sqft": "950",
            "floor": "Ground Floor",
            "building": "Silver Software",
            "period_of_rent": "12",
            "rent_amount": "85",
            "maintenance": "12",
            "rent_escalation": "4%",
            "agreement_start_date": "2023-11-01",
            "agreement_expiry_date": (datetime.today() + timedelta(days=20)).strftime("%Y-%m-%d"),  # 20 days from now (should be dark red - 1 month)
            "lock_in_period": "6",
            "lock_in_period_end_date": (datetime.today() + timedelta(days=5)).strftime("%Y-%m-%d"),
            "rental_period_greater_than_lock_in_period": "True",
            "next_rent_escalation": "2024-11-01",
            "alert_status": "one_month"
        }
    ]
    
    # Calculate alert status for test data and add IDs
    for i, agreement in enumerate(test_agreements):
        agreement["alert_status"] = calculate_alert_status(agreement["agreement_expiry_date"])
        agreement["id"] = f"test_{i+1}"  # Add test IDs
    
    return render_template("dashboard.html", agreements=test_agreements)

@app.route("/delete_agreement/<agreement_id>", methods=["POST"])
@login_required
@limiter.limit("20 per hour")
def delete_agreement(agreement_id):
    """Archive a specific agreement by ID."""
    try:
        agreements = load_agreements()
        # Find the agreement to archive
        agreement_to_archive = None
        for agreement in agreements:
            if agreement.get("id") == agreement_id:
                agreement_to_archive = agreement
                break
        
        if agreement_to_archive:
            # Archive the agreement
            archive_agreement(agreement_to_archive)
            # Remove from active agreements
            agreements = [a for a in agreements if a.get("id") != agreement_id]
            save_agreements(agreements)
            logging.debug(f"Archived agreement with ID: {agreement_id}")
        else:
            logging.warning(f"Agreement with ID {agreement_id} not found")
        
        return redirect("/")
    except Exception as e:
        logging.error(f"Error archiving agreement: {e}")
        return redirect("/")

@app.route("/archive")
@login_required
def archive():
    """Display archived agreements."""
    archived_agreements = load_archived_agreements()
    # Sort by archived timestamp (most recent first)
    archived_agreements.sort(key=lambda x: x.get("archived_timestamp", ""), reverse=True)
    return render_template("archive.html", agreements=archived_agreements)

@app.route("/restore_agreement/<agreement_id>", methods=["POST"])
@login_required
@limiter.limit("20 per hour")
def restore_agreement(agreement_id):
    """Restore an archived agreement back to active status."""
    try:
        archived_agreements = load_archived_agreements()
        active_agreements = load_agreements()
        
        # Find the agreement to restore
        agreement_to_restore = None
        for agreement in archived_agreements:
            if agreement.get("id") == agreement_id:
                agreement_to_restore = agreement
                break
        
        if agreement_to_restore:
            # Remove archived timestamp and add restore timestamp
            if "archived_timestamp" in agreement_to_restore:
                del agreement_to_restore["archived_timestamp"]
            agreement_to_restore["restored_timestamp"] = datetime.now().isoformat()
            
            # Add back to active agreements
            active_agreements.append(agreement_to_restore)
            save_agreements(active_agreements)
            
            # Remove from archived agreements
            archived_agreements = [a for a in archived_agreements if a.get("id") != agreement_id]
            save_archived_agreements(archived_agreements)
            
            logging.debug(f"Restored agreement with ID: {agreement_id}")
        else:
            logging.warning(f"Archived agreement with ID {agreement_id} not found")
        
        return redirect("/archive")
    except Exception as e:
        logging.error(f"Error restoring agreement: {e}")
        return redirect("/archive")

@app.route("/gmail_settings")
@login_required
def gmail_settings():
    """Display Gmail settings page with form and list of saved addresses."""
    settings = load_settings()
    return render_template("gmail_settings.html", settings=settings)

@app.route("/add_gmail", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def add_gmail():
    """Add a new tenant-Gmail pair to settings."""
    try:
        tenant_name = request.form.get("tenant_name", "").strip()
        gmail_address = request.form.get("gmail_address", "").strip()
        
        # Basic email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'
        if not gmail_address:
            logging.warning("Empty Gmail address provided")
            return redirect("/gmail_settings")
        
        if not re.match(email_pattern, gmail_address):
            logging.warning(f"Invalid Gmail address format: {gmail_address}")
            return redirect("/gmail_settings")
        
        # Load current settings
        settings = load_settings()
        tenant_gmail_pairs = settings.get("tenant_gmail_pairs", [])
        
        # Check if email already exists
        existing_gmail = any(pair.get("gmail_address") == gmail_address for pair in tenant_gmail_pairs)
        if existing_gmail:
            logging.warning(f"Gmail address already exists: {gmail_address}")
            return redirect("/gmail_settings")
        
        # Add new tenant-Gmail pair
        new_pair = {
            "tenant_name": tenant_name,
            "gmail_address": gmail_address
        }
        tenant_gmail_pairs.append(new_pair)
        settings["tenant_gmail_pairs"] = tenant_gmail_pairs
        save_settings(settings)
        
        logging.debug(f"Added tenant-Gmail pair: {tenant_name} - {gmail_address}")
        return redirect("/gmail_settings")
    except Exception as e:
        logging.error(f"Error adding tenant-Gmail pair: {e}")
        return redirect("/gmail_settings")

@app.route("/remove_gmail", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def remove_gmail():
    """Remove a tenant-Gmail pair from settings."""
    try:
        gmail_address = request.form.get("gmail_address", "").strip()
        
        if not gmail_address:
            logging.warning("Empty Gmail address provided for removal")
            return redirect("/gmail_settings")
        
        # Load current settings
        settings = load_settings()
        tenant_gmail_pairs = settings.get("tenant_gmail_pairs", [])
        
        # Remove Gmail pair if it exists
        updated_pairs = [pair for pair in tenant_gmail_pairs if pair.get("gmail_address") != gmail_address]
        
        if len(updated_pairs) < len(tenant_gmail_pairs):
            settings["tenant_gmail_pairs"] = updated_pairs
            save_settings(settings)
            logging.debug(f"Removed Gmail address: {gmail_address}")
        else:
            logging.warning(f"Gmail address not found for removal: {gmail_address}")
        
        return redirect("/gmail_settings")
    except Exception as e:
        logging.error(f"Error removing Gmail address: {e}")
        return redirect("/gmail_settings")

@app.route("/send_email_alerts", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def send_email_alerts():
    """Send email alerts to tenants with expiry warnings."""
    try:
        # Load agreements and settings
        agreements = load_agreements()
        settings = load_settings()
        tenant_gmail_pairs = settings.get("tenant_gmail_pairs", [])
        
        if not tenant_gmail_pairs:
            flash("No tenant Gmail addresses found. Please add tenant Gmail addresses first.", "warning")
            return redirect("/")
        
        sent_count = 0
        failed_count = 0
        no_email_count = 0
        
        # Process each agreement
        for agreement in agreements:
            # Update alert status
            alert_status = calculate_alert_status(agreement.get("agreement_expiry_date", ""))
            agreement["alert_status"] = alert_status
            
            # Only send emails for agreements with alerts
            if alert_status in ['three_months', 'two_months', 'one_month', 'expired']:
                tenant_name = agreement.get("tenant_name", "")
                
                if tenant_name:
                    # Find Gmail address for this tenant
                    gmail_address = find_tenant_gmail(tenant_name, tenant_gmail_pairs)
                    
                    if gmail_address:
                        # Create and send email
                        subject, html_content = create_alert_email_content(tenant_name, agreement, alert_status)
                        
                        success, error_msg = send_email_notification(gmail_address, subject, html_content)
                        if success:
                            sent_count += 1
                            logging.info(f"Alert email sent to {tenant_name} ({gmail_address}) - Alert: {alert_status}")
                        else:
                            failed_count += 1
                            logging.error(f"Failed to send email to {tenant_name} ({gmail_address}): {error_msg}")
                    else:
                        no_email_count += 1
                        logging.warning(f"No Gmail address found for tenant: {tenant_name}")
                else:
                    logging.warning(f"No tenant name found for agreement: {agreement.get('id', 'Unknown')}")
        
        # Provide feedback to user
        if sent_count > 0:
            flash(f"Successfully sent {sent_count} email alert(s).", "success")
        if failed_count > 0:
            flash(f"Failed to send {failed_count} email(s). Check logs for details.", "error")
        if no_email_count > 0:
            flash(f"{no_email_count} tenant(s) have alerts but no matching Gmail address found.", "warning")
        if sent_count == 0 and failed_count == 0 and no_email_count == 0:
            flash("No tenants currently have agreement expiry alerts requiring notifications.", "info")
        
        return redirect("/")
        
    except Exception as e:
        logging.error(f"Error sending email alerts: {e}")
        flash("An error occurred while sending email alerts. Check logs for details.", "error")
        return redirect("/")

@app.route("/test_email", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def test_email():
    """Test email configuration by sending a test email."""
    try:
        test_recipient = request.form.get("test_email", "").strip()
        
        if not test_recipient:
            flash("Please provide a test email address.", "error")
            return redirect("/")
        
        # Create test email content
        subject = "Test Email from Tenant Dashboard"
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #f8f9fa; padding: 20px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Test Email from Tenant Dashboard</h2>
                    <p>This is a test email to verify your email configuration is working correctly.</p>
                    <p><strong>Sent at:</strong> {}</p>
                </div>
                <p>If you received this email, your SMTP configuration is working properly!</p>
            </div>
        </body>
        </html>
        """.format(datetime.now().strftime('%B %d, %Y at %I:%M %p'))
        
        # Send test email
        success, error_msg = send_email_notification(test_recipient, subject, html_content)
        
        if success:
            flash(f"Test email sent successfully to {test_recipient}!", "success")
        else:
            flash(f"Failed to send test email: {error_msg}", "error")
        
        return redirect("/")
        
    except Exception as e:
        logging.error(f"Error sending test email: {e}")
        flash("An error occurred while sending test email. Check logs for details.", "error")
        return redirect("/")

@app.route("/download_csv")
@login_required
@limiter.limit("10 per hour")
def download_csv():
    """Download tenant agreements data as CSV file."""
    try:
        # Load agreements and update alert statuses
        agreements = load_agreements()
        
        # Update alert status and normalize values for all agreements
        for agreement in agreements:
            agreement["alert_status"] = calculate_alert_status(agreement.get("agreement_expiry_date", ""))
            
            # Handle legacy data - convert place_occupied to new fields if needed
            if "place_occupied" in agreement and not agreement.get("area_sqft"):
                place = agreement.get("place_occupied", "")
                agreement["area_sqft"] = normalize_area_sqft(place)
                agreement["floor"] = normalize_floor(place)
                agreement["building"] = normalize_building(place)
            
            # Normalize fields for existing data
            agreement["area_sqft"] = normalize_area_sqft(agreement.get("area_sqft", ""))
            agreement["floor"] = normalize_floor(agreement.get("floor", ""))
            agreement["building"] = normalize_building(agreement.get("building", ""))
            agreement["period_of_rent"] = normalize_period_of_rent(agreement.get("period_of_rent", ""))
            agreement["rent_amount"] = normalize_rent_amount(agreement.get("rent_amount", ""))
            agreement["maintenance"] = normalize_maintenance_amount(agreement.get("maintenance", ""))
            agreement["rent_escalation"] = normalize_rent_escalation(agreement.get("rent_escalation", ""))
            agreement["lock_in_period"] = normalize_period_of_rent(agreement.get("lock_in_period", ""))
            
            # Normalize rental_period_greater_than_lock_in_period
            rental_period_value = agreement.get("rental_period_greater_than_lock_in_period", "")
            if isinstance(rental_period_value, bool):
                agreement["rental_period_greater_than_lock_in_period"] = "True" if rental_period_value else "False"
            elif isinstance(rental_period_value, str):
                rental_period_value = rental_period_value.strip()
                if rental_period_value.lower() in ["yes", "true", "1"]:
                    agreement["rental_period_greater_than_lock_in_period"] = "True"
                elif rental_period_value.lower() in ["no", "false", "0"]:
                    agreement["rental_period_greater_than_lock_in_period"] = "False"
                else:
                    agreement["rental_period_greater_than_lock_in_period"] = "False"
            else:
                agreement["rental_period_greater_than_lock_in_period"] = "False"
        
        # Create CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write CSV headers (matching the table columns)
        headers = [
            "Tenant Name",
            "Area (sqft)",
            "Floor",
            "Building",
            "Period of Rent (Months)",
            "Rent Amount (₹/sqft/month)",
            "Maintenance (₹/sqft/month)",
            "Rent Escalation (% per year)",
            "Agreement Start Date",
            "Agreement Expiry Date",
            "Lock In Period (Months)",
            "Lock In Period End Date",
            "Rental Period > Lock In Period",
            "Next Rent Escalation",
            "Alert Status"
        ]
        writer.writerow(headers)
        
        # Write data rows
        for agreement in agreements:
            row = [
                agreement.get("tenant_name", ""),
                f"{agreement.get('area_sqft', '')} sqft" if agreement.get("area_sqft") else "",
                agreement.get("floor", ""),
                agreement.get("building", ""),
                f"{agreement.get('period_of_rent', '')} months" if agreement.get("period_of_rent") else "",
                f"Rs {agreement.get('rent_amount', '')}" if agreement.get("rent_amount") else "",
                f"Rs {agreement.get('maintenance', '')}" if agreement.get("maintenance") else "",
                agreement.get("rent_escalation", ""),
                agreement.get("agreement_start_date", ""),
                agreement.get("agreement_expiry_date", ""),
                f"{agreement.get('lock_in_period', '')} months" if agreement.get("lock_in_period") else "",
                agreement.get("lock_in_period_end_date", ""),
                agreement.get("rental_period_greater_than_lock_in_period", ""),
                agreement.get("next_rent_escalation", ""),
                agreement.get("alert_status", "")
            ]
            writer.writerow(row)
        
        # Create response with CSV data
        csv_data = output.getvalue()
        output.close()
        
        # Generate filename with current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tenant_agreements_{timestamp}.csv"
        
        # Create response
        response = Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
        logging.debug(f"Generated CSV download with {len(agreements)} agreements")
        return response
        
    except Exception as e:
        logging.error(f"Error generating CSV: {e}")
        return redirect("/")

# Error handlers for production
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal server error: {error}")
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500

@app.errorhandler(413)
def too_large(error):
    flash("File too large. Maximum file size is 16MB.", "error")
    return redirect(url_for('dashboard'))

@app.errorhandler(429)
def ratelimit_handler(e):
    flash("Too many requests. Please try again later.", "warning")
    return redirect(url_for('dashboard'))

if __name__ == "__main__":
    # Ensure required directories exist
    required_dirs = [UPLOAD_FOLDER, 'static']
    for directory in required_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    
    # Run application
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    port = int(os.environ.get('PORT', 5000))
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
