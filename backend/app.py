import os
import logging
from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager
from dotenv import load_dotenv
from pathlib import Path
from werkzeug.security import generate_password_hash
from datetime import datetime
from database.models import db
from commands import create_test_shop, verify_database, check_database, reset_database, create_default_resources
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from auth import auth_bp
from admin import admin_bp
from employee import employee_bp
from backend.database.models import User

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_class=None):
    # Initialize Flask app
    app = Flask(__name__)

    # Set configuration
    if config_class:
        app.config.from_object(config_class)
    else:
        # Default configuration if none provided
        app.config.from_object(Config)

    # Ensure instance folder exists
    try:
        Path("instance").mkdir(exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating instance folder: {str(e)}")

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'

    # Import models
    from backend.database.models import Shop, Product, Inventory, UnscannedSale

    # Register commands
    app.cli.add_command(create_test_shop)
    app.cli.add_command(verify_database)
    app.cli.add_command(check_database)
    app.cli.add_command(reset_database)
    app.cli.add_command(create_default_resources)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp, url_prefix='/employee')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(product_bp, url_prefix='/products')
    app.register_blueprint(service_bp, url_prefix='/services')
    app.register_blueprint(resource_bp, url_prefix='/resources')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')

    # Initialize database
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            logger.info("Database tables created successfully.")

            # Check if default shop exists
            default_shop = Shop.query.filter_by(name="Main Store").first()
            if not default_shop:
                default_shop = Shop(
                    name="Main Store",
                    location="123 Main Street, City Center",
                    created_at=datetime.utcnow()
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

            logger.info("✅ Database initialized successfully with default data.")
        except Exception as e:
            logger.error(f"❌ Error during database initialization: {str(e)}")
            raise

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            logger.error(f"Error loading user: {str(e)}")
            return None

    # Landing page (role selector)
    @app.route('/')
    def index():
        return redirect(url_for('auth.select_role'))

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f"Internal server error: {str(error)}")
        return render_template('errors/500.html'), 500

    return app

# Create the application instance
app = create_app()

# Run
if __name__ == '__main__':
    try:
        logger.info("Starting SmartRetail AI application...")
        app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
