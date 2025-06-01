import os
from backend.app import create_app

# Get the environment from environment variable, default to production
env = os.environ.get('FLASK_ENV', 'production')
app = create_app()

if __name__ == '__main__':
    app.run() 