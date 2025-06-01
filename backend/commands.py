from flask.cli import with_appcontext
import click
from backend.database.models import db, Shop, User, Resource
from werkzeug.security import generate_password_hash
from datetime import datetime

@click.command('create-test-shop')
@with_appcontext
def create_test_shop():
    """Create a test shop with default data."""
    try:
        # Create test shop
        shop = Shop(
            name="Test Shop",
            location="123 Test Street",
            created_at=datetime.utcnow()
        )
        db.session.add(shop)
        db.session.flush()

        # Create test admin user
        admin = User(
            name="Test Admin",
            email="admin@test.com",
            password_hash=generate_password_hash("admin123"),
            role="admin",
            shop_id=shop.id
        )
        db.session.add(admin)

        # Create test employee user
        employee = User(
            name="Test Employee",
            email="employee@test.com",
            password_hash=generate_password_hash("employee123"),
            role="employee",
            shop_id=shop.id
        )
        db.session.add(employee)

        db.session.commit()
        click.echo('Test shop and users created successfully!')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating test shop: {str(e)}')

@click.command('create-default-resources')
@with_appcontext
def create_default_resources():
    """Create default resources for the shop."""
    try:
        # Define default resources
        default_resources = [
            {
                'name': 'Printer Paper',
                'description': 'A4 size printer paper',
                'category': 'Office Supplies',
                'unit': 'ream',
                'cost_per_unit': 5.0,
                'reorder_level': 5
            },
            {
                'name': 'Printer Ink',
                'description': 'Black printer ink cartridge',
                'category': 'Office Supplies',
                'unit': 'cartridge',
                'cost_per_unit': 25.0,
                'reorder_level': 2
            },
            {
                'name': 'Cleaning Supplies',
                'description': 'General cleaning supplies',
                'category': 'Maintenance',
                'unit': 'set',
                'cost_per_unit': 15.0,
                'reorder_level': 3
            },
            {
                'name': 'Coffee',
                'description': 'Coffee beans for break room',
                'category': 'Break Room',
                'unit': 'kg',
                'cost_per_unit': 12.0,
                'reorder_level': 2
            }
        ]

        # Add resources to database
        for resource_data in default_resources:
            resource = Resource(**resource_data)
            db.session.add(resource)

        db.session.commit()
        click.echo('Default resources created successfully!')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating default resources: {str(e)}')

@click.command('verify-database')
@with_appcontext
def verify_database():
    """Verify database connection and tables."""
    try:
        # Try to query each model
        Shop.query.first()
        User.query.first()
        Resource.query.first()
        click.echo('Database connection and tables verified successfully!')
    except Exception as e:
        click.echo(f'Error verifying database: {str(e)}')

@click.command('check-database')
@with_appcontext
def check_database():
    """Check database contents."""
    try:
        shops = Shop.query.all()
        users = User.query.all()
        resources = Resource.query.all()

        click.echo(f'\nShops ({len(shops)}):')
        for shop in shops:
            click.echo(f'- {shop.name} ({shop.location})')

        click.echo(f'\nUsers ({len(users)}):')
        for user in users:
            click.echo(f'- {user.name} ({user.email}, {user.role})')

        click.echo(f'\nResources ({len(resources)}):')
        for resource in resources:
            click.echo(f'- {resource.name} ({resource.category}, {resource.unit})')

    except Exception as e:
        click.echo(f'Error checking database: {str(e)}')

@click.command('reset-database')
@with_appcontext
def reset_database():
    """Reset database by dropping all tables and recreating them."""
    try:
        # Drop all tables
        db.drop_all()
        click.echo('All tables dropped successfully.')

        # Create all tables
        db.create_all()
        click.echo('All tables recreated successfully.')

        # Create test data
        create_test_shop()
        create_default_resources()
        click.echo('Database reset and test data created successfully!')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error resetting database: {str(e)}') 