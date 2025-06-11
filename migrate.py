from flask import Flask
from flask_migrate import Migrate
from backend.database.models import db
from backend.config import Config
import os
from pathlib import Path

# Get the environment from environment variable, default to development
env = os.environ.get('FLASK_ENV', 'development')

# Create the app instance
app = Flask(__name__)
app.config.from_object(Config[env])

# Ensure instance folder exists
try:
    Path("backend/instance").mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"Error creating instance folder: {str(e)}")

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run() 