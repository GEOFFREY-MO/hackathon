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

def remove_price_range():
    """Remove the price_range column from the product table."""
    with app.app_context():
        with db.engine.connect() as conn:
            try:
                # First, check if price_range column exists
                result = conn.execute(text("PRAGMA table_info(product);"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'price_range' in columns:
                    print("Removing price_range column...")
                    
                    # Create a new table without price_range
                    conn.execute(text('''
                        CREATE TABLE product_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name VARCHAR(100) NOT NULL,
                            barcode VARCHAR(50) NOT NULL UNIQUE,
                            category VARCHAR(50) NOT NULL,
                            marked_price FLOAT NOT NULL,
                            reorder_level INTEGER DEFAULT 10,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        );
                    '''))
                    
                    # Copy data from old table to new table
                    conn.execute(text('''
                        INSERT INTO product_new (id, name, barcode, category, marked_price, reorder_level, created_at)
                        SELECT id, name, barcode, category, 
                               COALESCE(marked_price, 
                                       CASE 
                                           WHEN price_range = 'Low' THEN 10.0
                                           WHEN price_range = 'Medium' THEN 30.0
                                           WHEN price_range = 'High' THEN 50.0
                                           ELSE 0.0
                                       END), 
                               reorder_level, created_at
                        FROM product;
                    '''))
                    
                    # Drop old table and rename new one
                    conn.execute(text('DROP TABLE product;'))
                    conn.execute(text('ALTER TABLE product_new RENAME TO product;'))
                    
                    print("Successfully removed price_range column!")
                else:
                    print("price_range column does not exist.")

            except Exception as e:
                print(f"An error occurred: {str(e)}")
                # If there's an error, try to clean up
                try:
                    conn.execute(text('DROP TABLE IF EXISTS product_new;'))
                except:
                    pass

if __name__ == '__main__':
    remove_price_range() 