# backend/database/models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import event

# Create SQLAlchemy instance without binding to app
db = SQLAlchemy()

class Shop(db.Model):
    __tablename__ = 'shop'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    users = db.relationship('User', backref='shop', lazy=True)
    inventory = db.relationship('Inventory', backref='shop', lazy=True)

    def __repr__(self):
        return f'<Shop {self.name}>'

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'employee'
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email}>'

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    barcode = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    marked_price = db.Column(db.Float, nullable=False)
    reorder_level = db.Column(db.Integer, default=10)  # Default reorder level of 10 units
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    inventory = db.relationship('Inventory', backref='product', lazy=True)

    def __repr__(self):
        return f'<Product {self.name}>'

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Inventory {self.shop_id}:{self.product_id}>'

class UnscannedSale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')
    shop = db.relationship('Shop')

class Sale(db.Model):
    __tablename__ = 'sale'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(100), nullable=True)
    payment_method = db.Column(db.String(20), nullable=False, default='cash')  # cash, till, bank
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)

    shop = db.relationship('Shop', backref=db.backref('sales', lazy=True))
    product = db.relationship('Product', backref=db.backref('sales', lazy=True))

    def __repr__(self):
        return f'<Sale {self.id}>'

class Service(db.Model):
    """Model for services provided by the shop."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Integer)  # Duration in minutes
    category = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    shop = db.relationship('Shop', backref=db.backref('services', lazy=True))

    def __repr__(self):
        return f'<Service {self.name}>'

class ServiceSale(db.Model):
    """Model for service sales."""
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    price = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='completed')  # completed, pending, cancelled
    payment_method = db.Column(db.String(20), nullable=False, default='cash')  # cash, till, bank
    
    service = db.relationship('Service', backref=db.backref('sales', lazy=True))
    shop = db.relationship('Shop', backref=db.backref('service_sales', lazy=True))
    employee = db.relationship('User', backref=db.backref('service_sales', lazy=True))

    def __repr__(self):
        return f'<ServiceSale {self.id}>'

class Resource(db.Model):
    """Model for business resources like printer ink, paper, etc."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    unit = db.Column(db.String(20))  # e.g., "sheets", "ml", "pieces"
    cost_per_unit = db.Column(db.Float, nullable=False, default=0.0)  # Cost per unit of the resource
    reorder_level = db.Column(db.Integer, default=10)  # When to reorder
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Resource {self.name}>'

class ShopResource(db.Model):
    """Model for tracking resources in each shop."""
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    shop = db.relationship('Shop', backref=db.backref('resources', lazy=True))
    resource = db.relationship('Resource', backref=db.backref('shop_quantities', lazy=True))
    updater = db.relationship('User', backref=db.backref('shop_resource_updates', lazy=True))

    def __repr__(self):
        return f'<ShopResource {self.resource.name} at {self.shop.name}>'

class ResourceUpdate(db.Model):
    """Model for tracking resource quantity updates."""
    __tablename__ = 'resource_updates'

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    previous_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    shop = db.relationship('Shop', backref='resource_updates')
    resource = db.relationship('Resource', backref='updates')
    updater = db.relationship('User', backref='resource_quantity_updates')

    def __repr__(self):
        return f'<ResourceUpdate {self.id}: {self.resource.name} at {self.shop.name}>'

class Expense(db.Model):
    """Model for tracking shop expenses."""
    __tablename__ = 'expense'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    shop = db.relationship('Shop', backref=db.backref('expenses', lazy=True))
    creator = db.relationship('User', backref=db.backref('created_expenses', lazy=True))

    def __repr__(self):
        return f'<Expense {self.id}: {self.description}>'

class ResourceHistory(db.Model):
    __tablename__ = 'resource_history'
    
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    previous_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    change_type = db.Column(db.String(20), nullable=False)  # 'add', 'remove', 'adjust'
    reason = db.Column(db.Text)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    resource = db.relationship('Resource', backref=db.backref('history', lazy=True))
    shop = db.relationship('Shop', backref=db.backref('resource_history', lazy=True))
    updater = db.relationship('User', backref=db.backref('resource_history_updates', lazy=True))
    
    def __repr__(self):
        return f'<ResourceHistory {self.resource_id}:{self.shop_id}>'

class ResourceAlert(db.Model):
    __tablename__ = 'resource_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)  # 'low_stock', 'reorder', 'expiry'
    message = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    resource = db.relationship('Resource', backref=db.backref('alerts', lazy=True))
    shop = db.relationship('Shop', backref=db.backref('resource_alerts', lazy=True))
    
    def __repr__(self):
        return f'<ResourceAlert {self.resource_id}:{self.alert_type}>'

class ResourceCategory(db.Model):
    __tablename__ = 'resource_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ResourceCategory {self.name}>'

# Event listeners for resource tracking
@event.listens_for(ShopResource, 'after_update')
def track_resource_changes(mapper, connection, target):
    """Track changes to resource quantities"""
    if db.inspect(target).attrs.quantity.history.has_changes():
        history = ResourceHistory(
            resource_id=target.resource_id,
            shop_id=target.shop_id,
            previous_quantity=db.inspect(target).attrs.quantity.history.deleted[0],
            new_quantity=target.quantity,
            change_type='adjust',
            updated_by=target.updated_by
        )
        db.session.add(history)
        
        # Check for low stock alerts
        resource = Resource.query.get(target.resource_id)
        if target.quantity <= resource.reorder_level:
            alert = ResourceAlert(
                resource_id=target.resource_id,
                shop_id=target.shop_id,
                alert_type='low_stock',
                message=f'Low stock alert: {resource.name} is below reorder level ({resource.reorder_level})'
            )
            db.session.add(alert)
