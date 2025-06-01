from sqlalchemy import text, create_engine
from database.models import db
import os

def migrate():
    """Add location column to shop table"""
    try:
        # Check if location column exists
        result = db.session.execute(text("PRAGMA table_info(shop)"))
        columns = [column[1] for column in result.fetchall()]
        
        if 'location' not in columns:
            print("Adding location column to shop table...")
            
            # Create a temporary table with the new schema
            db.session.execute(text("""
                CREATE TABLE shop_temp (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    location VARCHAR(200) NOT NULL DEFAULT 'Unknown Location',
                    created_at DATETIME
                )
            """))
            
            # Copy data from old table to new table
            db.session.execute(text("""
                INSERT INTO shop_temp (id, name, created_at)
                SELECT id, name, created_at FROM shop
            """))
            
            # Drop the old table
            db.session.execute(text("DROP TABLE shop"))
            
            # Rename the new table to the original name
            db.session.execute(text("ALTER TABLE shop_temp RENAME TO shop"))
            
            db.session.commit()
            print("Location column added successfully.")
        else:
            print("Location column already exists.")
            
        return True
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    migrate() 