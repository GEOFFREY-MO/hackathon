import sqlite3
import os

def verify_and_fix_resource_table():
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'smartretail.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First, let's check the current table structure
        cursor.execute("PRAGMA table_info(resource);")
        columns = cursor.fetchall()
        print("Current columns in resource table:")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
        
        # Check if cost_per_unit exists
        cost_per_unit_exists = any(col[1] == 'cost_per_unit' for col in columns)
        
        if not cost_per_unit_exists:
            print("\nAdding cost_per_unit column...")
            cursor.execute('''
                ALTER TABLE resource 
                ADD COLUMN cost_per_unit FLOAT NOT NULL DEFAULT 0.0
            ''')
            print("Added cost_per_unit column")
        
        # Verify resource_categories table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resource_categories';")
        if not cursor.fetchone():
            print("\nCreating resource_categories table...")
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
            
            # Insert some default categories
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
        
        # Commit changes
        conn.commit()
        print("\nTable verification completed successfully")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    verify_and_fix_resource_table() 