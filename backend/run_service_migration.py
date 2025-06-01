from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from database.models import db
import os

def run_migration():
    app = Flask(__name__)
    
    # Configure the database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smartretail.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize the database with the app
    db.init_app(app)
    
    with app.app_context():
        # Add payment_method column to service_sale table
        with db.engine.connect() as conn:
            conn.execute(db.text('ALTER TABLE service_sale ADD COLUMN payment_method VARCHAR(20) NOT NULL DEFAULT "cash"'))
            conn.commit()
        print("Service sale payment method migration completed successfully!")

if __name__ == '__main__':
    run_migration() 