from flask import Flask
from flask_migrate import Migrate
from database.models import db
from backend.config import Config

def init_db():
    app = Flask(__name__)
    app.config.from_object(config['production'])
    
    # Initialize database
    db.init_app(app)
    migrate = Migrate(app, db)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Run migrations
        from flask_migrate import upgrade
        upgrade()
        
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db() 