import os
from backend import create_app

# Get the environment from environment variable, default to production
env = os.environ.get('FLASK_ENV', 'production')
app = create_app(env)

if __name__ == '__main__':
    app.run() 