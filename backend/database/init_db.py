from database.models import Shop, User, db
from werkzeug.security import generate_password_hash
import logging
from .migrations.add_location_to_shop import migrate as migrate_location
from .migrations.add_reorder_level import migrate as migrate_reorder_level

logger = logging.getLogger(__name__)

def init_db(app, db):
    """Initialize the database with default data"""
    with app.app_context():
        try:
            # Create tables
            db.create_all()
            logger.info("Database tables created successfully.")

            # Run migrations
            if migrate_location():
                logger.info("Location migration completed successfully.")
            else:
                logger.error("Error during location migration.")
                return False

            if migrate_reorder_level():
                logger.info("Reorder level migration completed successfully.")
            else:
                logger.error("Error during reorder level migration.")
                return False

            # Check if default shop exists
            default_shop = Shop.query.filter_by(name="Main Store").first()
            if not default_shop:
                default_shop = Shop(
                    name="Main Store",
                    location="123 Main Street, City Center"
                )
                db.session.add(default_shop)
                db.session.commit()
                logger.info("Default shop created successfully.")

            # Check if admin user exists
            admin = User.query.filter_by(email="admin@smartretail.com").first()
            if not admin:
                admin = User(
                    name="Admin User",
                    email="admin@smartretail.com",
                    password_hash=generate_password_hash("admin123"),  # Change this in production
                    role="admin"
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("Default admin user created successfully.")

            logger.info("Database initialization completed successfully.")
            return True

        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    init_db() 