#!/usr/bin/env python3
"""
Setup script for AI features in SmartRetail AI
Installs required dependencies and sets up environment
"""

import subprocess
import sys
import os
from pathlib import Path

def install_dependencies():
    """Install required Python packages"""
    print("Installing AI dependencies...")
    
    packages = [
        "opencv-python==4.8.1.78",
        "pytesseract==0.3.10",
        "Pillow==10.0.1",
        "openai==1.3.0",
        "matplotlib==3.7.2",
        "seaborn==0.12.2",
        "plotly==5.17.0"
    ]
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ Installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            return False
    
    return True

def create_env_file():
    """Create .env file with required environment variables"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("Creating .env file...")
        env_content = """# SmartRetail AI Environment Variables
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///smartretail.db
"""
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("✅ Created .env file")
        print("⚠️  Please update the .env file with your actual API keys")
    else:
        print("✅ .env file already exists")

def create_upload_directories():
    """Create necessary upload directories"""
    print("Creating upload directories...")
    
    directories = [
        "uploads",
        "uploads/charts",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

def check_tesseract():
    """Check if Tesseract OCR is installed"""
    print("Checking Tesseract OCR installation...")
    
    try:
        import pytesseract
        # Try to get version
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract OCR found (version: {version})")
        return True
    except Exception as e:
        print(f"❌ Tesseract OCR not found: {e}")
        print("Please install Tesseract OCR:")
        print("  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        print("  macOS: brew install tesseract")
        print("  Ubuntu: sudo apt-get install tesseract-ocr")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up AI features for SmartRetail AI...")
    print("=" * 50)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        return False
    
    # Create .env file
    create_env_file()
    
    # Create upload directories
    create_upload_directories()
    
    # Check Tesseract
    tesseract_ok = check_tesseract()
    
    print("=" * 50)
    if tesseract_ok:
        print("✅ AI features setup completed successfully!")
        print("\nNext steps:")
        print("1. Update .env file with your OpenAI API key")
        print("2. Run: python backend/app.py")
        print("3. Visit: http://localhost:5000/admin/ai-assistant")
    else:
        print("⚠️  Setup completed with warnings")
        print("Please install Tesseract OCR to enable chart analysis features")
    
    return True

if __name__ == "__main__":
    main()











