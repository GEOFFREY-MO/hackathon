import sqlite3
import os

def check_tables():
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'smartretail.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("Tables in the database:")
        for table in tables:
            print(f"- {table[0]}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    check_tables() 