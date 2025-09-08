# Tenant Dashboard - Production Ready Web Application

A secure, production-ready web application for managing rental agreements with OCR-powered document processing, automated email alerts, and comprehensive tenant management features.

##  Features

- **Secure Authentication**: User login system with bcrypt password hashing
- **OCR Document Processing**: Extract data from PDF rental agreements using Tesseract OCR
- **AI-Powered Data Extraction**: Uses OpenAI GPT-4o for intelligent text parsing
- **Email Notifications**: Automated alerts for agreement expiry dates
- **Rate Limiting**: Protection against abuse and DOS attacks
- **Responsive Design**: Mobile-friendly Bootstrap interface
- **Data Export**: CSV download functionality
- **Archive System**: Soft delete and restore capabilities
- **Production Security**: HTTPS support, secure headers, session management

##  Quick Start (Local Development)

### Prerequisites

- Python 3.8 or higher
- Git
- OpenAI API key
- Gmail account with App Password

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repository-url>
   cd tenant_dashboard_3
   ```

2. **Run the setup script**
   ```bash
   python setup.py
   ```

3. **Configure environment variables**
   - Edit the `.env` file created by the setup script
   - Add your OpenAI API key, Gmail credentials, and other settings

4. **Start the application**
   ```bash
   python app.py
   ```

5. **Access the dashboard**
   - Open http://localhost:5000 in your browser
   - Login with username `admin` and your configured password

##  Production Deployment

This application is ready for production deployment on various platforms:

### Supported Platforms
- **Render.com** (Recommended - Free tier available)
- **Heroku** (Popular platform with good documentation)
- **Railway** (Simple deployment process)
- **Your own VPS/Server** (Complete control)

### Quick Deploy to Render.com

1. Push your code to a GitHub repository
2. Sign up at [render.com](https://render.com)
3. Create a new Web Service connected to your repository
4. Configure environment variables in the Render dashboard
5. Deploy automatically!

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## 🔧 Configuration

### Required Environment Variables

```bash
FLASK_ENV=production                    # Set to 'production' for deployment
SECRET_KEY=your_random_secret_key       # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
OPENAI_API_KEY=your_openai_api_key      # From OpenAI dashboard
SENDER_PASSWORD=your_gmail_app_password # Gmail App Password (not regular password)
DEFAULT_ADMIN_PASSWORD=secure_password  # Initial admin password
```

### Optional Environment Variables

```bash
SMTP_SERVER=smtp.gmail.com              # SMTP server (default: Gmail)
SMTP_PORT=587                           # SMTP port (default: 587)
SENDER_EMAIL=your_gmail@gmail.com       # Only needed if not configured in Gmail Settings
SENDER_NAME=Tenant Dashboard            # Only needed if not configured in Gmail Settings
MAX_CONTENT_LENGTH=16777216             # Max file size in bytes (16MB)
```

##  Project Structure

```
tenant_dashboard_3/
├── app.py                 # Main Flask application
├── wsgi.py               # WSGI entry point for production
├── setup.py              # Setup and installation script
├── requirements.txt      # Python dependencies
├── Procfile             # Heroku deployment config
├── render.yaml          # Render.com deployment config
├── env.example          # Environment variables template
├── DEPLOYMENT.md        # Detailed deployment guide
├── templates/           # HTML templates
│   ├── dashboard.html   # Main dashboard interface
│   ├── login.html       # User authentication
│   ├── archive.html     # Archived agreements
│   ├── gmail_settings.html # Email configuration
│   └── error.html       # Error pages
├── uploads/             # PDF file storage (created automatically)
├── static/              # Static assets (created automatically)
├── agreements_data.json # Active agreements data
├── archived_agreements.json # Archived agreements
├── settings.json        # Application settings
└── users.json          # User accounts (created automatically)
```

## 🔒 Security Features

### Authentication & Authorization
- Secure user login system with Flask-Login
- Password hashing with bcrypt
- Session management with secure cookies
- Rate limiting on all endpoints

### Security Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security (in production)

### Input Validation
- File type validation (PDF only)
- File size limits (16MB max)
- Secure filename handling
- CSRF protection

##  Usage

### Adding Rental Agreements
1. Upload PDF rental agreement documents
2. The system automatically extracts key information:
   - Tenant name and contact details
   - Lease terms and dates
   - Rent amounts and escalations
   - Property details

### Managing Email Notifications
1. Configure tenant Gmail addresses in settings
2. System automatically sends alerts for:
   - Agreement expiry warnings (3, 2, 1 months)
   - Overdue notifications
3. Test email functionality before production use

### Data Export
- Download complete tenant data as CSV
- Include all agreement details and alert statuses
- Perfect for backup and external reporting

## 🛠 System Requirements

### For Local Development
- Python 3.8+
- Tesseract OCR
- Poppler utilities

### For Production Deployment
- All local requirements plus:
- WSGI server (Gunicorn included)
- HTTPS/SSL certificate
- Environment variable management
- Regular backup strategy

##  Troubleshooting

### Common Issues

**PDF Processing Fails**
- Ensure Tesseract OCR is installed and in PATH
- Verify OpenAI API key is valid and has credits
- Check PDF file is not corrupted or password-protected

**Email Sending Fails**
- Verify Gmail App Password (not regular password)
- Ensure 2-Factor Authentication is enabled on Gmail
- Check SMTP settings and network connectivity

**Login Issues**
- Verify DEFAULT_ADMIN_PASSWORD environment variable
- Check SECRET_KEY is set and not empty
- Clear browser cookies and try again

### Getting Help

1. Check application logs for detailed error messages
2. Verify all environment variables are correctly set
3. Test with simple PDF files first
4. Refer to [DEPLOYMENT.md](DEPLOYMENT.md) for platform-specific guidance
