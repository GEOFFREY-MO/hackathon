import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the Flask app
from backend.app import create_app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run() 