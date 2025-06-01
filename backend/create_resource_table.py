import sqlite3
import os
from datetime import datetime

def create_resource_table():
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'smartretail.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create the Resource table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resource (
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
        
        # Create the ShopResource table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shop_resource (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                resource_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER NOT NULL,
                FOREIGN KEY (shop_id) REFERENCES shop (id),
                FOREIGN KEY (resource_id) REFERENCES resource (id),
                FOREIGN KEY (updated_by) REFERENCES user (id)
            )
        ''')
        
        # Create the ResourceHistory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resource_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                shop_id INTEGER NOT NULL,
                previous_quantity INTEGER NOT NULL,
                new_quantity INTEGER NOT NULL,
                change_type VARCHAR(20) NOT NULL,
                reason TEXT,
                updated_by INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resource_id) REFERENCES resource (id),
                FOREIGN KEY (shop_id) REFERENCES shop (id),
                FOREIGN KEY (updated_by) REFERENCES user (id)
            )
        ''')
        
        # Create the ResourceAlert table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resource_alert (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                shop_id INTEGER NOT NULL,
                alert_type VARCHAR(20) NOT NULL,
                message TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (resource_id) REFERENCES resource (id),
                FOREIGN KEY (shop_id) REFERENCES shop (id)
            )
        ''')
        
        # Commit the changes
        conn.commit()
        print("Successfully created Resource tables")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    create_resource_table() 