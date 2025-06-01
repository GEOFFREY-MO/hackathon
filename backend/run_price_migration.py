from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import sqlite3

# Create Flask app
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smartretail.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

def column_exists(conn, table, column):
    result = conn.execute(text(f"PRAGMA table_info({table});"))
    return any(row[1] == column for row in result.fetchall())

def run_migration():
    """Run the migration to update the product price field."""
    with app.app_context():
        with db.engine.connect() as conn:
            # 1. Add marked_price if missing
            if not column_exists(conn, 'product', 'marked_price'):
                print('Adding marked_price column...')
                conn.execute(text('ALTER TABLE product ADD COLUMN marked_price FLOAT;'))
            else:
                print('marked_price column already exists.')

            # 2. Update marked_price values if price_range exists
            if column_exists(conn, 'product', 'price_range'):
                print('Copying price_range to marked_price...')
                conn.execute(text("""
                    UPDATE product 
                    SET marked_price = CASE 
                        WHEN price_range = 'Low' THEN 10.0
                        WHEN price_range = 'Medium' THEN 30.0
                        WHEN price_range = 'High' THEN 50.0
                        ELSE 0.0
                    END
                """))
            else:
                print('price_range column does not exist, skipping value copy.')

            # 3. Remove price_range if it exists (SQLite doesn't support DROP COLUMN directly)
            if column_exists(conn, 'product', 'price_range'):
                print('Rebuilding table to drop price_range column...')
                # Create new table without price_range
                conn.execute(text('''
                    CREATE TABLE product_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) NOT NULL,
                        barcode VARCHAR(50) NOT NULL UNIQUE,
                        category VARCHAR(50) NOT NULL,
                        marked_price FLOAT NOT NULL DEFAULT 0.0,
                        reorder_level INTEGER DEFAULT 10,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                '''))
                conn.execute(text('''
                    INSERT INTO product_new (id, name, barcode, category, marked_price, reorder_level, created_at)
                    SELECT id, name, barcode, category, COALESCE(marked_price, 0.0), reorder_level, created_at FROM product;
                '''))
                conn.execute(text('DROP TABLE product;'))
                conn.execute(text('ALTER TABLE product_new RENAME TO product;'))
                print('Dropped price_range column.')
            else:
                print('price_range column already dropped.')

            print("Product price field migration completed successfully!")

if __name__ == '__main__':
    run_migration() 