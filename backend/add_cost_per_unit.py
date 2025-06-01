import sqlite3
import os

def add_cost_per_unit_column():
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'smartretail.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add the cost_per_unit column with a default value of 0.0
        cursor.execute('''
            ALTER TABLE resource 
            ADD COLUMN cost_per_unit FLOAT NOT NULL DEFAULT 0.0
        ''')
        
        # Commit the changes
        conn.commit()
        print("Successfully added cost_per_unit column to Resource table")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column cost_per_unit already exists")
        else:
            print(f"Error: {str(e)}")
            conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_cost_per_unit_column() 