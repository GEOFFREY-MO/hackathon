from sqlalchemy import text
from database.models import db

def migrate():
    """Add reorder_level column to product table"""
    try:
        # Check if reorder_level column exists
        result = db.session.execute(text("PRAGMA table_info(product)"))
        columns = [column[1] for column in result.fetchall()]
        
        if 'reorder_level' not in columns:
            print("Adding reorder_level column to product table...")
            
            # Add reorder_level column with default value
            db.session.execute(text("""
                ALTER TABLE product 
                ADD COLUMN reorder_level INTEGER DEFAULT 10
            """))
            
            db.session.commit()
            print("Reorder level column added successfully.")
        else:
            print("Reorder level column already exists.")
            
        return True
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    migrate() 