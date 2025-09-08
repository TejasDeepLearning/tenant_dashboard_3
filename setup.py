#!/usr/bin/env python3
"""
Setup script for Tenant Dashboard
Handles initial setup and environment preparation
"""

import os
import sys
import secrets
import subprocess
import json
from pathlib import Path

def create_env_file():
    """Create .env file from template if it doesn't exist."""
    env_file = Path('.env')
    env_example = Path('env.example')
    
    if not env_file.exists() and env_example.exists():
        with open(env_example, 'r') as src:
            content = src.read()
        
        # Generate a secure secret key
        secret_key = secrets.token_hex(32)
        content = content.replace('your_secret_key_here', secret_key)
        
        with open(env_file, 'w') as dst:
            dst.write(content)
        
        print("✓ Created .env file from template")
        print("⚠ Please edit .env file with your actual API keys and credentials")
        return True
    elif env_file.exists():
        print("✓ .env file already exists")
        return True
    else:
        print("✗ env.example file not found")
        return False

def create_directories():
    """Create required directories."""
    directories = ['uploads', 'static']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")

def install_dependencies():
    """Install Python dependencies."""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✓ Installed Python dependencies")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install dependencies")
        return False

def check_system_dependencies():
    """Check for required system dependencies."""
    dependencies = {
        'tesseract': 'tesseract --version',
        'poppler': 'pdftoppm -h'
    }
    
    missing = []
    for name, command in dependencies.items():
        try:
            subprocess.run(command.split(), capture_output=True, check=True)
            print(f"✓ {name} is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"✗ {name} is not installed or not in PATH")
            missing.append(name)
    
    if missing:
        print("\n⚠ Missing system dependencies:")
        if 'tesseract' in missing:
            print("  Install Tesseract OCR:")
            print("    Ubuntu/Debian: sudo apt install tesseract-ocr")
            print("    macOS: brew install tesseract")
            print("    Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        
        if 'poppler' in missing:
            print("  Install Poppler utilities:")
            print("    Ubuntu/Debian: sudo apt install poppler-utils")
            print("    macOS: brew install poppler")
            print("    Windows: Download from https://github.com/oschwartz10612/poppler-windows")
    
    return len(missing) == 0

def main():
    """Main setup function."""
    print("🚀 Setting up Tenant Dashboard...")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        sys.exit(1)
    else:
        print(f"✓ Python {sys.version.split()[0]} detected")
    
    # Create directories
    create_directories()
    
    # Create .env file
    env_created = create_env_file()
    
    # Install dependencies
    deps_installed = install_dependencies()
    
    # Check system dependencies
    system_deps_ok = check_system_dependencies()
    
    print("\n" + "=" * 50)
    print("📋 Setup Summary:")
    print(f"  Environment file: {'✓' if env_created else '✗'}")
    print(f"  Python dependencies: {'✓' if deps_installed else '✗'}")
    print(f"  System dependencies: {'✓' if system_deps_ok else '⚠'}")
    
    if env_created and deps_installed:
        print("\n🎉 Setup completed successfully!")
        print("\n📝 Next steps:")
        print("1. Edit .env file with your API keys and credentials")
        print("2. Set up Gmail App Password for email functionality")
        print("3. Run the application: python app.py")
        print("4. Access the dashboard at http://localhost:5000")
        print("5. Login with username 'admin' and your DEFAULT_ADMIN_PASSWORD")
        
        if not system_deps_ok:
            print("\n⚠ Note: Install missing system dependencies for full functionality")
    else:
        print("\n✗ Setup failed. Please resolve the issues above and try again.")

if __name__ == "__main__":
    main()
