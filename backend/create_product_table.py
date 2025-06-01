from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Create Flask app
app = Flask(__name__)

# Configure database
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smartretail.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    barcode = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    marked_price = db.Column(db.Float, nullable=False)
    reorder_level = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

def create_tables():
    try:
        with app.app_context():
            # Drop existing table if it exists
            db.drop_all()
            # Create all tables
            db.create_all()
            print(f"Product table created successfully in {db_path}")
            
            # Verify the table was created
            result = db.session.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product'")
            if result.scalar():
                print("Verified: Product table exists!")
            else:
                print("Error: Product table was not created!")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == '__main__':
    create_tables() 