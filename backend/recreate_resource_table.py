import sqlite3
import os

def recreate_resource_table():
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'smartretail.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Drop existing resource table if it exists
        cursor.execute("DROP TABLE IF EXISTS resource;")
        
        # Create the resource table with all necessary columns
        cursor.execute('''
            CREATE TABLE resource (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                category VARCHAR(50),
                unit VARCHAR(20),
                cost_per_unit FLOAT NOT NULL DEFAULT 0.0,
                reorder_level INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create resource_categories table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resource_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default categories if they don't exist
        default_categories = [
            ('Office Supplies', 'General office supplies like paper, pens, etc.'),
            ('Printing Materials', 'Ink, toner, and other printing supplies'),
            ('Cleaning Supplies', 'Cleaning and maintenance materials'),
            ('IT Equipment', 'Computer and technology related resources'),
            ('Packaging Materials', 'Boxes, bags, and other packaging supplies')
        ]
        
        for category in default_categories:
            cursor.execute('''
                INSERT OR IGNORE INTO resource_categories (name, description)
                VALUES (?, ?)
            ''', category)
        
        # Insert some sample resources
        sample_resources = [
            ('Printer Paper', 'A4 size printer paper', 'Office Supplies', 'sheets', 0.05, 100),
            ('Black Ink Cartridge', 'HP compatible black ink cartridge', 'Printing Materials', 'units', 25.99, 5),
            ('Cleaning Spray', 'Multi-surface cleaning spray', 'Cleaning Supplies', 'bottles', 5.99, 10),
            ('USB Drive', '32GB USB flash drive', 'IT Equipment', 'units', 12.99, 5),
            ('Shipping Boxes', 'Medium size shipping boxes', 'Packaging Materials', 'boxes', 2.99, 20)
        ]
        
        cursor.executemany('''
            INSERT INTO resource (name, description, category, unit, cost_per_unit, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_resources)
        
        # Commit changes
        conn.commit()
        print("Successfully recreated resource table with sample data")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    recreate_resource_table() 