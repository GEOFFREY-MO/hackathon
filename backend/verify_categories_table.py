import sqlite3
import os

def verify_categories_table():
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'smartretail.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if resource_categories table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resource_categories';")
        if not cursor.fetchone():
            print("Creating resource_categories table...")
            cursor.execute('''
                CREATE TABLE resource_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("Created resource_categories table")
            
            # Insert default categories
            default_categories = [
                ('Office Supplies', 'General office supplies like paper, pens, etc.'),
                ('Printing Materials', 'Ink, toner, and other printing supplies'),
                ('Cleaning Supplies', 'Cleaning and maintenance materials'),
                ('IT Equipment', 'Computer and technology related resources'),
                ('Packaging Materials', 'Boxes, bags, and other packaging supplies')
            ]
            
            cursor.executemany('''
                INSERT INTO resource_categories (name, description)
                VALUES (?, ?)
            ''', default_categories)
            print("Added default resource categories")
        
        # Verify existing categories
        cursor.execute("SELECT * FROM resource_categories;")
        categories = cursor.fetchall()
        print("\nExisting categories:")
        for category in categories:
            print(f"- {category[1]}: {category[2]}")
        
        # Commit changes
        conn.commit()
        print("\nCategories table verification completed successfully")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    verify_categories_table() 