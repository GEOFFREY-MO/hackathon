# backend/database/__init__.py
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy
db = SQLAlchemy()

# Import models to make them available when importing from database
from .models import (
    User, Shop, Product, Inventory, Sale, Service, 
    ServiceSale, Resource, ShopResource, Expense, 
    ResourceHistory, ResourceAlert, ResourceCategory, 
    ServiceCategory, FinancialRecord, UnscannedSale,
    Notification, Report
)

__all__ = [
    'db', 'User', 'Shop', 'Product', 'Inventory', 
    'Sale', 'Service', 'ServiceSale', 'Resource', 
    'ShopResource', 'Expense', 'ResourceHistory', 
    'ResourceAlert', 'ResourceCategory', 'ServiceCategory', 
    'FinancialRecord', 'UnscannedSale', 'Notification',
    'Report'
]

def init_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_retail.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
