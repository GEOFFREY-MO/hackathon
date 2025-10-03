import click
from flask.cli import with_appcontext
from database import db, Shop, User, Resource
from datetime import datetime
from werkzeug.security import generate_password_hash
import logging

logger = logging.getLogger(__name__)

@click.command()
@with_appcontext
def create_test_shop():
    """Create a test shop with default data."""
    try:
        # Create test shop
        shop = Shop(
            name="Test Shop",
            location="123 Test Street",
            contact="1234567890",
            email="test@shop.com",
            created_at=datetime.utcnow()
        )
        db.session.add(shop)
        db.session.commit()
        logger.info("Test shop created successfully.")

        # Create test admin
        admin = User(
            name="Test Admin",
            email="admin@test.com",
            password_hash=generate_password_hash("admin123"),
            role="admin",
            shop_id=shop.id,
            created_at=datetime.utcnow()
        )
        db.session.add(admin)
        db.session.commit()
        logger.info("Test admin created successfully.")

        # Create test employee
        employee = User(
            name="Test Employee",
            email="employee@test.com",
            password_hash=generate_password_hash("employee123"),
            role="employee",
            shop_id=shop.id,
            admin_id=admin.id,
            created_at=datetime.utcnow()
        )
        db.session.add(employee)
        db.session.commit()
        logger.info("Test employee created successfully.")

        click.echo("Test data created successfully!")
    except Exception as e:
        logger.error(f"Error creating test data: {str(e)}")
        db.session.rollback()
        raise click.ClickException(str(e))

@click.command()
@with_appcontext
def verify_database():
    """Verify database structure and connections."""
    try:
        # Test database connection
        db.session.execute("SELECT 1")
        click.echo("Database connection successful!")

        # Check tables
        tables = db.engine.table_names()
        click.echo(f"Found tables: {', '.join(tables)}")

        # Check Shop table
        shop_count = Shop.query.count()
        click.echo(f"Found {shop_count} shops")

        # Check User table
        user_count = User.query.count()
        click.echo(f"Found {user_count} users")

        click.echo("Database verification completed successfully!")
    except Exception as e:
        logger.error(f"Error verifying database: {str(e)}")
        raise click.ClickException(str(e))

@click.command()
@with_appcontext
def check_database():
    """Check database for common issues."""
    try:
        # Check for shops without admins
        shops = Shop.query.all()
        for shop in shops:
            admin = User.query.filter_by(shop_id=shop.id, role="admin").first()
            if not admin:
                click.echo(f"Warning: Shop '{shop.name}' has no admin user")

        # Check for employees without admin
        employees = User.query.filter_by(role="employee").all()
        for employee in employees:
            if not employee.admin_id:
                click.echo(f"Warning: Employee '{employee.name}' has no admin assigned")

        # Check for resources without categories
        resources = Resource.query.all()
        for resource in resources:
            if not resource.category:
                click.echo(f"Warning: Resource '{resource.name}' has no category")

        click.echo("Database check completed!")
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
        raise click.ClickException(str(e))

@click.command()
@with_appcontext
def reset_database():
    """Reset database to initial state."""
    if click.confirm("Are you sure you want to reset the database? This will delete all data!"):
        try:
            # Drop all tables
            db.drop_all()
            click.echo("All tables dropped successfully.")

            # Recreate tables
            db.create_all()
            click.echo("Tables recreated successfully.")

            # Create default shop
            shop = Shop(
                name="Main Store",
                location="123 Main Street",
                created_at=datetime.utcnow()
            )
            db.session.add(shop)
            db.session.commit()
            click.echo("Default shop created successfully.")

            # Create default admin
            admin = User(
                name="Admin User",
                email="admin@smartretail.com",
                password_hash=generate_password_hash("admin123"),
                role="admin",
                shop_id=shop.id,
                created_at=datetime.utcnow()
            )
            db.session.add(admin)
            db.session.commit()
            click.echo("Default admin created successfully.")

            click.echo("Database reset completed successfully!")
        except Exception as e:
            logger.error(f"Error resetting database: {str(e)}")
            db.session.rollback()
            raise click.ClickException(str(e))

@click.command()
@with_appcontext
def create_default_resources():
    """Create default resources for the system."""
    try:
        # Create default resource categories
        categories = [
            "Office Supplies",
            "Cleaning Supplies",
            "Maintenance",
            "IT Equipment",
            "Miscellaneous"
        ]

        for category in categories:
            resource = Resource(
                name=category,
                description=f"Default {category.lower()} category",
                category=category,
                unit="pieces",
                cost_per_unit=0.0,
                created_at=datetime.utcnow()
            )
            db.session.add(resource)

        db.session.commit()
        click.echo("Default resources created successfully!")
    except Exception as e:
        logger.error(f"Error creating default resources: {str(e)}")
        db.session.rollback()
        raise click.ClickException(str(e)) 