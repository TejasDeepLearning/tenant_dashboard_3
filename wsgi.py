#!/usr/bin/env python3
"""
WSGI Configuration for Tenant Dashboard
Production-ready WSGI entry point for deployment
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask application
from app import app

# Configure for production
if os.getenv('FLASK_ENV') == 'production':
    # Disable debug mode in production
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Set secure session cookies for production
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Additional production security headers
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static files

# Create required directories if they don't exist
required_dirs = ['uploads', 'static']
for directory in required_dirs:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

# Ensure proper file permissions for uploads directory
uploads_dir = app.config.get('UPLOAD_FOLDER', 'uploads')
if os.path.exists(uploads_dir):
    try:
        os.chmod(uploads_dir, 0o755)
    except OSError:
        pass  # Ignore permission errors

# WSGI application entry point
application = app

if __name__ == "__main__":
    # For local development
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
