import os
import sys
import logging
from sqlalchemy import inspect

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app, db
from database.models import ResourceHistory, ResourceAlert, ResourceCategory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_resource_tables():
    """Create the new resource-related tables in the database if they don't exist."""
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Check and create each table if it doesn't exist
            if 'resource_history' not in existing_tables:
                ResourceHistory.__table__.create(db.engine)
                logger.info("✅ Created resource_history table")
            else:
                logger.info("ℹ️ resource_history table already exists")
                
            if 'resource_alerts' not in existing_tables:
                ResourceAlert.__table__.create(db.engine)
                logger.info("✅ Created resource_alerts table")
            else:
                logger.info("ℹ️ resource_alerts table already exists")
                
            if 'resource_categories' not in existing_tables:
                ResourceCategory.__table__.create(db.engine)
                logger.info("✅ Created resource_categories table")
            else:
                logger.info("ℹ️ resource_categories table already exists")
            
            logger.info("✅ All resource-related tables are ready!")
    except Exception as e:
        logger.error(f"❌ Error managing resource tables: {str(e)}")
        raise

if __name__ == '__main__':
    create_resource_tables() 