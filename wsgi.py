import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure 'backend' package is importable when running from project root
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import the Flask app
from backend.app import create_app

# Create the app instance with production config
app = create_app('production')

if __name__ == '__main__':
    app.run() 