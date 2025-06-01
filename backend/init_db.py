from app import create_app
from database.models import db, Shop, User, Sale, Product, Service, ServiceSale, Expense
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import random

def init_db():
    app = create_app()
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Create test shop
        shop = Shop(
            name="Test Shop",
            location="123 Test Street"
        )
        db.session.add(shop)
        db.session.commit()
        
        # Create test admin
        admin = User(
            name="Test Admin",
            email="admin@test.com",
            password_hash=generate_password_hash("admin123"),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        
        # Create test products
        products = [
            Product(name="Product 1", barcode="123456", category="Category 1", marked_price=100),
            Product(name="Product 2", barcode="234567", category="Category 2", marked_price=200),
            Product(name="Product 3", barcode="345678", category="Category 1", marked_price=150)
        ]
        for product in products:
            db.session.add(product)
        db.session.commit()
        
        # Create test services
        services = [
            Service(name="Service 1", description="Test Service 1", price=300, shop_id=shop.id),
            Service(name="Service 2", description="Test Service 2", price=400, shop_id=shop.id)
        ]
        for service in services:
            db.session.add(service)
        db.session.commit()
        
        # Create test sales
        payment_methods = ['cash', 'till', 'bank']
        for i in range(10):
            sale = Sale(
                shop_id=shop.id,
                product_id=random.choice(products).id,
                quantity=random.randint(1, 5),
                price=random.randint(50, 200),
                payment_method=random.choice(payment_methods),
                sale_date=datetime.utcnow() - timedelta(days=random.randint(0, 30))
            )
            db.session.add(sale)
        
        # Create test service sales
        for i in range(5):
            service_sale = ServiceSale(
                service_id=random.choice(services).id,
                shop_id=shop.id,
                employee_id=admin.id,
                price=random.randint(200, 500),
                payment_method=random.choice(payment_methods),
                sale_date=datetime.utcnow() - timedelta(days=random.randint(0, 30))
            )
            db.session.add(service_sale)
        
        # Create test expenses
        expense_categories = ['Rent', 'Utilities', 'Supplies', 'Other']
        for i in range(5):
            expense = Expense(
                shop_id=shop.id,
                amount=random.randint(100, 1000),
                description=f"Test Expense {i+1}",
                category=random.choice(expense_categories),
                date=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                created_by=admin.id
            )
            db.session.add(expense)
        
        db.session.commit()
        print("Database initialized with test data!")

if __name__ == "__main__":
    init_db() 