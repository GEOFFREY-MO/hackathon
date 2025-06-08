from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class Resource(db.Model):
    __tablename__ = 'resource'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    unit = db.Column(db.String(20))
    cost_per_unit = db.Column(db.Float, nullable=False, default=0.0)
    reorder_level = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    shop_resources = db.relationship('ShopResource', back_populates='resource', cascade='all, delete-orphan')
    history = db.relationship('ResourceHistory', back_populates='resource', cascade='all, delete-orphan')
    alerts = db.relationship('ResourceAlert', back_populates='resource', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Resource {self.name}>'

class ShopResource(db.Model):
    __tablename__ = 'shop_resources'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    shop = db.relationship('Shop', back_populates='resources')
    resource = db.relationship('Resource', back_populates='shop_resources')
    updater = db.relationship('User')
    
    def __repr__(self):
        return f'<ShopResource {self.shop_id}:{self.resource_id}>'

class ResourceHistory(db.Model):
    __tablename__ = 'resource_history'
    
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    previous_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    change_type = db.Column(db.String(20), nullable=False)  # 'add', 'remove', 'adjust'
    reason = db.Column(db.Text)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    resource = db.relationship('Resource', back_populates='history')
    shop = db.relationship('Shop')
    updater = db.relationship('User')
    
    def __repr__(self):
        return f'<ResourceHistory {self.resource_id}:{self.shop_id}>'

class ResourceAlert(db.Model):
    __tablename__ = 'resource_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)  # 'low_stock', 'reorder', 'expiry'
    message = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    resource = db.relationship('Resource', back_populates='alerts')
    shop = db.relationship('Shop')
    
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

class ServiceCategory(db.Model):
    __tablename__ = 'service_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    services = db.relationship('Service', back_populates='category')
    
    def __repr__(self):
        return f'<ServiceCategory {self.name}>'

class Service(db.Model):
    __tablename__ = 'services'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('service_categories.id'))
    price = db.Column(db.Float, nullable=False, default=0.0)
    duration = db.Column(db.Integer)  # Duration in minutes
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = db.relationship('ServiceCategory', back_populates='services')
    
    def __repr__(self):
        return f'<Service {self.name}>'

class FinancialRecord(db.Model):
    """Model for tracking financial transactions."""
    __tablename__ = 'financial_record'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # cash, till, bank
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    shop = db.relationship('Shop', backref=db.backref('financial_records', lazy=True))
    creator = db.relationship('User', backref=db.backref('created_financial_records', lazy=True))
    
    def __repr__(self):
        return f'<FinancialRecord {self.id}: {self.type} {self.amount}>'

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