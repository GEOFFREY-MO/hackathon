from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Create Flask app
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smartretail.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

def update_existing_products():
    """Update existing products with marked prices based on their previous price ranges."""
    with app.app_context():
        with db.engine.connect() as conn:
            try:
                # First, check if price_range column exists
                result = conn.execute(text("PRAGMA table_info(product);"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'price_range' in columns:
                    print("Updating existing products with marked prices...")
                    # Update marked_price based on price_range
                    conn.execute(text("""
                        UPDATE product 
                        SET marked_price = CASE 
                            WHEN price_range = 'Low' THEN 10.0
                            WHEN price_range = 'Medium' THEN 30.0
                            WHEN price_range = 'High' THEN 50.0
                            ELSE 0.0
                        END
                        WHERE marked_price IS NULL OR marked_price = 0;
                    """))
                    print("Existing products updated successfully!")
                else:
                    print("No price_range column found. Setting default marked prices...")
                    # Set a default marked price for all products
                    conn.execute(text("""
                        UPDATE product 
                        SET marked_price = 0.0
                        WHERE marked_price IS NULL OR marked_price = 0;
                    """))
                    print("Default marked prices set successfully!")

            except Exception as e:
                print(f"An error occurred: {str(e)}")

if __name__ == '__main__':
    update_existing_products() 