from flask import Flask
from database.models import db, Product
import sqlite3

def remove_price_range_column():
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/smartretail.db')
        cursor = conn.cursor()
        
        # Check if price_range column exists
        cursor.execute("PRAGMA table_info(product)")
        columns = cursor.fetchall()
        price_range_exists = any(col[1] == 'price_range' for col in columns)
        
        if price_range_exists:
            # Drop product_new table if it exists
            cursor.execute("DROP TABLE IF EXISTS product_new")
            
            # Create a new table without price_range
            cursor.execute("""
                CREATE TABLE product_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    barcode VARCHAR(50) NOT NULL UNIQUE,
                    category VARCHAR(50) NOT NULL,
                    marked_price FLOAT NOT NULL,
                    reorder_level INTEGER DEFAULT 10,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Copy data from old table to new table
            cursor.execute("""
                INSERT INTO product_new (id, name, barcode, category, marked_price, reorder_level, created_at)
                SELECT id, name, barcode, category, COALESCE(marked_price, 0.0), reorder_level, created_at
                FROM product
            """)
            
            # Drop the old table
            cursor.execute("DROP TABLE product")
            
            # Rename the new table to product
            cursor.execute("ALTER TABLE product_new RENAME TO product")
            
            # Commit the changes
            conn.commit()
            print("Successfully removed price_range column from product table")
        else:
            print("price_range column does not exist in product table")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    remove_price_range_column() 