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

def check_and_fix_schema():
    """Check the current schema and fix any issues with the product table."""
    try:
        # Get current schema
        conn = db.engine.connect()
        result = conn.execute(text("PRAGMA table_info(product)"))
        columns = result.fetchall()
        
        print("Current schema:")
        for col in columns:
            print(f"Column: {col[1]}, NOT NULL: {col[3]}")
        
        # Check if price_range column exists
        has_price_range = any(col[1] == 'price_range' for col in columns)
        
        if has_price_range:
            print("Found price_range column. Creating new table without it...")
            
            # Drop product_new if it exists
            try:
                conn.execute(text("DROP TABLE IF EXISTS product_new"))
            except Exception as e:
                print(f"Error dropping product_new: {e}")
            
            # Create new table without price_range
            conn.execute(text("""
                CREATE TABLE product_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    barcode VARCHAR(50) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    reorder_level INTEGER,
                    created_at TIMESTAMP,
                    marked_price FLOAT
                )
            """))
            
            # Copy data from old table to new table
            conn.execute(text("""
                INSERT INTO product_new (id, name, barcode, category, reorder_level, created_at, marked_price)
                SELECT id, name, barcode, category, reorder_level, created_at, marked_price
                FROM product
            """))
            
            # Drop old table and rename new one
            conn.execute(text("DROP TABLE product"))
            conn.execute(text("ALTER TABLE product_new RENAME TO product"))
            
            print("Successfully removed price_range column")
        else:
            print("No price_range column found. Schema is correct.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        # Try to clean up if something went wrong
        try:
            conn.execute(text("DROP TABLE IF EXISTS product_new"))
        except:
            pass
    finally:
        conn.close()

if __name__ == '__main__':
    with app.app_context():
        check_and_fix_schema() 