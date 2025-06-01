import os
import sqlite3
from pathlib import Path

def check_and_fix_db():
    """Check if database exists and is properly initialized"""
    db_path = Path("instance/smartretail.db")
    
    # Check if database exists
    if not db_path.exists():
        print("Database file not found. Creating new database...")
        # Create instance directory if it doesn't exist
        db_path.parent.mkdir(exist_ok=True)
        # Create empty database file
        conn = sqlite3.connect(db_path)
        conn.close()
        print("Database file created.")
    else:
        print("Database file exists.")

    # Check if database is properly initialized
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in database.")
        else:
            print("Found tables:", [table[0] for table in tables])
            
        conn.close()
    except Exception as e:
        print(f"Error checking database: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    check_and_fix_db() 