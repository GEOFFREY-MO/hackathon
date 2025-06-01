import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask
from backend.database.models import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    try:
        logger.info("Starting expenses table migration...")
        
        # Create Flask app
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smartretail.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database with app
        db.init_app(app)
        
        with app.app_context():
            # Create expense table if it doesn't exist
            with db.engine.connect() as conn:
                # Check if table exists
                result = conn.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='expense'"))
                table_exists = result.scalar() is not None
                
                if not table_exists:
                    logger.info("Creating expense table...")
                    conn.execute(db.text('''
                        CREATE TABLE expense (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            shop_id INTEGER NOT NULL,
                            category VARCHAR(50) NOT NULL,
                            description TEXT NOT NULL,
                            amount DECIMAL(10,2) NOT NULL,
                            date DATETIME NOT NULL,
                            created_by INTEGER,
                            FOREIGN KEY (shop_id) REFERENCES shop(id),
                            FOREIGN KEY (created_by) REFERENCES user(id)
                        )
                    '''))
                    logger.info("Expense table created successfully")
                else:
                    logger.info("Expense table already exists")
                    
                    # Check if created_by column exists
                    result = conn.execute(db.text("PRAGMA table_info(expense)"))
                    columns = [row[1] for row in result.fetchall()]
                    
                    if 'created_by' not in columns:
                        logger.info("Adding created_by column to expense table...")
                        conn.execute(db.text('ALTER TABLE expense ADD COLUMN created_by INTEGER REFERENCES user(id)'))
                        logger.info("created_by column added successfully")
                    else:
                        logger.info("created_by column already exists")
                
                conn.commit()
                logger.info("Expenses table migration completed successfully!")
                
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    run_migration() 