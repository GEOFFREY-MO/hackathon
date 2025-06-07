import os
import sys

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from backend.config import config

# Get the environment from environment variable, default to production
env = os.environ.get('FLASK_ENV', 'production')
app = create_app(config[env])

if __name__ == '__main__':
    app.run() 