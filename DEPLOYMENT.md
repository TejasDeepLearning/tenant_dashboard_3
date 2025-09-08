# Tenant Dashboard - Production Deployment Guide

This guide covers deploying the Tenant Dashboard application to various hosting platforms for public internet access.

## Prerequisites

Before deploying, ensure you have:

1. **OpenAI API Key**: Required for document processing
2. **Gmail Account**: For SMTP email notifications (with App Password)
3. **Git Repository**: Code should be in a public Git repository
4. **System Requirements**: 
   - Python 3.8+
   - Tesseract OCR (for PDF text extraction)
   - Poppler utilities (for PDF to image conversion)

## Environment Variables Setup

The application requires the following environment variables:

### Required Variables
```bash
FLASK_ENV=production
SECRET_KEY=your_random_secret_key_here
OPENAI_API_KEY=your_openai_api_key
SENDER_PASSWORD=your_gmail_app_password
DEFAULT_ADMIN_PASSWORD=your_secure_admin_password
```

### Optional Variables
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_gmail@gmail.com  # Only needed if not using Gmail Settings
SENDER_NAME=Tenant Dashboard       # Only needed if not using Gmail Settings
MAX_CONTENT_LENGTH=16777216
```

## Deployment Options

### Option 1: Deploy to Render.com (Recommended - Free Tier Available)

Render.com offers free hosting for web applications with the following benefits:
- Free SSL certificates
- Automatic deployments from Git
- Built-in environment variable management
- No credit card required for free tier

#### Steps:

1. **Prepare Your Repository**
   ```bash
   git add .
   git commit -m "Prepare for production deployment"
   git push origin main
   ```

2. **Create Render Account**
   - Go to [render.com](https://render.com)
   - Sign up with your GitHub account

3. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure the service:
     - **Name**: tenant-dashboard
     - **Region**: Choose closest to your users
     - **Branch**: main
     - **Runtime**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn wsgi:application`

4. **Set Environment Variables**
   In the Render dashboard, add these environment variables:
   - `FLASK_ENV`: production
   - `SECRET_KEY`: Generate using `python -c "import secrets; print(secrets.token_hex(32))"`
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `SENDER_EMAIL`: Your Gmail address
   - `SENDER_PASSWORD`: Your Gmail App Password
   - `DEFAULT_ADMIN_PASSWORD`: Secure password for admin user

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment to complete
   - Your app will be available at `https://your-app-name.onrender.com`

### Option 2: Deploy to Heroku

Heroku is another popular platform for web application deployment.

#### Steps:

1. **Install Heroku CLI**
   - Download from [heroku.com](https://devcenter.heroku.com/articles/heroku-cli)

2. **Login and Create App**
   ```bash
   heroku login
   heroku create your-app-name
   ```

3. **Add Buildpacks**
   ```bash
   heroku buildpacks:add --index 1 heroku-community/apt
   heroku buildpacks:add --index 2 heroku/python
   ```

4. **Create Aptfile** (for system dependencies)
   ```bash
   echo "tesseract-ocr" > Aptfile
   echo "poppler-utils" >> Aptfile
   ```

5. **Set Environment Variables**
   ```bash
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   heroku config:set OPENAI_API_KEY=your_openai_api_key
   heroku config:set SENDER_PASSWORD=your_gmail_app_password
   heroku config:set DEFAULT_ADMIN_PASSWORD=your_secure_password
   ```

6. **Deploy**
   ```bash
   git add .
   git commit -m "Deploy to Heroku"
   git push heroku main
   ```

### Option 3: Deploy to Railway

Railway offers simple deployment with good performance.

#### Steps:

1. **Connect Repository**
   - Go to [railway.app](https://railway.app)
   - Connect your GitHub repository

2. **Configure Environment Variables**
   Add all required environment variables in the Railway dashboard

3. **Deploy**
   Railway automatically deploys from your Git repository

### Option 4: Deploy to Your Own VPS/Server

For complete control, deploy to your own server.

#### Ubuntu/Debian Server Setup:

1. **Install System Dependencies**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv nginx
   sudo apt install tesseract-ocr poppler-utils
   ```

2. **Setup Application**
   ```bash
   git clone your-repository-url
   cd tenant_dashboard_3
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create Environment File**
   ```bash
   cp env.example .env
   # Edit .env with your actual values
   nano .env
   ```

4. **Create Systemd Service**
   ```bash
   sudo nano /etc/systemd/system/tenant-dashboard.service
   ```
   
   Add:
   ```ini
   [Unit]
   Description=Tenant Dashboard
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/path/to/your/app
   Environment=PATH=/path/to/your/app/venv/bin
   ExecStart=/path/to/your/app/venv/bin/gunicorn wsgi:application
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

5. **Configure Nginx**
   ```bash
   sudo nano /etc/nginx/sites-available/tenant-dashboard
   ```
   
   Add:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

6. **Enable and Start Services**
   ```bash
   sudo systemctl enable tenant-dashboard
   sudo systemctl start tenant-dashboard
   sudo systemctl enable nginx
   sudo systemctl start nginx
   ```

## Security Configuration

### SSL/HTTPS Setup

For production deployments, always use HTTPS:

1. **For Managed Platforms** (Render, Heroku, Railway):
   - SSL is automatically provided
   - Ensure `SESSION_COOKIE_SECURE=true` in environment variables

2. **For Self-Hosted**:
   - Use Let's Encrypt with Certbot:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

### Additional Security Measures

1. **Strong Admin Password**: Use a complex password for the admin account
2. **Regular Updates**: Keep dependencies updated
3. **Monitoring**: Set up application monitoring and logging
4. **Backups**: Regularly backup your data files

## Gmail App Password Setup

For email functionality, you need a Gmail App Password:

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a new app password for "Mail"
   - Use this password (not your regular Gmail password) for `SENDER_PASSWORD`

## First Time Setup

After deployment:

1. **Access Your Application**:
   - Navigate to your deployed URL
   - You'll see a login page

2. **Login as Admin**:
   - Username: `admin`
   - Password: The value you set for `DEFAULT_ADMIN_PASSWORD`

3. **Configure Gmail Settings**:
   - Go to Gmail Settings in the dashboard
   - Add tenant Gmail addresses for notifications

4. **Test Upload**:
   - Upload a sample PDF rental agreement
   - Verify the extraction and processing works

## Troubleshooting

### Common Issues:

1. **PDF Processing Fails**:
   - Ensure Tesseract and Poppler are installed
   - Check OpenAI API key is valid

2. **Email Sending Fails**:
   - Verify Gmail App Password is correct
   - Check that 2FA is enabled on Gmail account

3. **Login Issues**:
   - Check `DEFAULT_ADMIN_PASSWORD` environment variable
   - Verify `SECRET_KEY` is set

4. **File Upload Issues**:
   - Ensure uploads directory has write permissions
   - Check `MAX_CONTENT_LENGTH` setting

### Log Monitoring:

Most platforms provide log access:
- **Render**: View logs in dashboard
- **Heroku**: `heroku logs --tail`
- **Railway**: View logs in dashboard
- **Self-hosted**: `journalctl -u tenant-dashboard -f`

## Scaling Considerations

For high-traffic deployments:

1. **Database Migration**: Consider moving from JSON files to PostgreSQL
2. **File Storage**: Use cloud storage (AWS S3, Google Cloud Storage)
3. **Load Balancing**: Use multiple application instances
4. **Caching**: Implement Redis for session storage
5. **CDN**: Use a CDN for static assets

## Support and Maintenance

### Regular Maintenance Tasks:

1. **Update Dependencies**: Monthly security updates
2. **Monitor Disk Space**: PDF uploads can accumulate
3. **Backup Data**: Regular backups of JSON data files
4. **Monitor Performance**: Track response times and errors

### Getting Help:

- Check application logs for error details
- Verify all environment variables are set correctly
- Ensure system dependencies are installed
- Test with a simple PDF file first

This deployment guide should help you successfully deploy the Tenant Dashboard to any major hosting platform. Choose the option that best fits your technical requirements and budget.
