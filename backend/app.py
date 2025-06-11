import os
import logging
from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager
from dotenv import load_dotenv
from pathlib import Path
from werkzeug.security import generate_password_hash
from datetime import datetime
from backend.database import db, User, Shop, Product, Inventory, UnscannedSale
from backend.commands import create_test_shop, verify_database, check_database, reset_database, create_default_resources
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from backend.config import config, Config
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from logging.handlers import RotatingFileHandler
from backend.admin import admin_bp
from backend.auth import auth_bp
from backend.shop import shop_bp
from backend.product import product_bp
from backend.inventory import inventory_bp
from backend.sale import sale_bp
from backend.service import service_bp
from backend.resource import resource_bp
from backend.expense import expense_bp
from backend.analytics import analytics_bp
from backend.notification import notification_bp
from backend.report import report_bp
from backend.settings import settings_bp
from backend.websocket import websocket_bp

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    # Initialize Flask app
    app = Flask(__name__)

    # Set configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Ensure instance folder exists
    try:
        Path("instance").mkdir(exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating instance folder: {str(e)}")

    # Initialize extensions
    CORS(app)
    JWTManager(app)
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    socketio = SocketIO(app, cors_allowed_origins="*")

    # Register commands
    app.cli.add_command(create_test_shop)
    app.cli.add_command(verify_database)
    app.cli.add_command(check_database)
    app.cli.add_command(reset_database)
    app.cli.add_command(create_default_resources)

    # Register blueprints
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp, url_prefix='/shop')
    app.register_blueprint(product_bp, url_prefix='/product')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(sale_bp, url_prefix='/sale')
    app.register_blueprint(service_bp, url_prefix='/service')
    app.register_blueprint(resource_bp, url_prefix='/resource')
    app.register_blueprint(expense_bp, url_prefix='/expense')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(notification_bp, url_prefix='/notification')
    app.register_blueprint(report_bp, url_prefix='/report')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(websocket_bp, url_prefix='/ws')

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

    # Setup logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/smartretail.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('SmartRetail startup')

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
