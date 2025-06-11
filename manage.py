from flask_migrate import Migrate
from flask import Flask
from backend.app import create_app
from backend.database.models import db
from backend.config import Config
import os

# Get the environment from environment variable, default to development
env = os.environ.get('FLASK_ENV', 'development')

# Create the app instance
app = create_app(config[env])

# Initialize Flask-Migrate
migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run() 