# backend/database/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .models import db

# Initialize SQLAlchemy
db = SQLAlchemy()

# Import models to make them available when importing from database
from backend.database.models import User, Shop, Product, Inventory, Sale, Service, ServiceSale, Resource, ShopResource, Expense, ResourceHistory, ResourceAlert, ResourceCategory, ServiceCategory, FinancialRecord

def init_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_retail.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
