from flask import Blueprint, jsonify, request
from database import db, Resource, ShopResource, Shop, User, ResourceCategory, ResourceHistory, ResourceAlert
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import logging

resource_bp = Blueprint('resource', __name__)

@resource_bp.route('/api/resources', methods=['GET'])
@jwt_required()
def get_resources():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        shop_resources = ShopResource.query.filter_by(shop_id=user.shop_id).all()
        return jsonify([{
            'id': sr.id,
            'resource_id': sr.resource_id,
            'name': sr.resource.name,
            'description': sr.resource.description,
            'category_id': sr.resource.category_id,
            'category_name': sr.resource.category.name if sr.resource.category else None,
            'quantity': sr.quantity,
            'unit': sr.resource.unit,
            'min_quantity': sr.min_quantity,
            'max_quantity': sr.max_quantity,
            'last_restock_date': sr.last_restock_date.isoformat() if sr.last_restock_date else None,
            'last_restock_quantity': sr.last_restock_quantity,
            'created_at': sr.created_at.isoformat() if sr.created_at else None
        } for sr in shop_resources])
    except Exception as e:
        logging.error(f"Error getting resources: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@resource_bp.route('/api/resources', methods=['POST'])
@jwt_required()
def create_resource():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Name is required'}), 400
        category = None
        if 'category_id' in data:
            category = ResourceCategory.query.filter_by(
                id=data['category_id'],
                shop_id=user.shop_id
            ).first()
            if not category:
                return jsonify({'error': 'Category not found'}), 404
        resource = Resource(
            name=data['name'],
            description=data.get('description'),
            category_id=category.id if category else None,
            unit=data.get('unit', 'piece'),
            created_at=datetime.utcnow()
        )
        db.session.add(resource)
        db.session.flush()
        shop_resource = ShopResource(
            shop_id=user.shop_id,
            resource_id=resource.id,
            quantity=data.get('quantity', 0),
            min_quantity=data.get('min_quantity', 0),
            max_quantity=data.get('max_quantity', 0),
            created_at=datetime.utcnow()
        )
        db.session.add(shop_resource)
        db.session.commit()
        return jsonify({
            'id': shop_resource.id,
            'resource_id': resource.id,
            'name': resource.name,
            'description': resource.description,
            'category_id': resource.category_id,
            'category_name': category.name if category else None,
            'quantity': shop_resource.quantity,
            'unit': resource.unit,
            'min_quantity': shop_resource.min_quantity,
            'max_quantity': shop_resource.max_quantity,
            'created_at': shop_resource.created_at.isoformat()
        }), 201
    except Exception as e:
        logging.error(f"Error creating resource: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@resource_bp.route('/api/resources/<int:resource_id>', methods=['PUT'])
@jwt_required()
def update_resource(resource_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        shop_resource = ShopResource.query.filter_by(
            id=resource_id,
            shop_id=user.shop_id
        ).first()
        if not shop_resource:
            return jsonify({'error': 'Resource not found'}), 404
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        if 'name' in data:
            shop_resource.resource.name = data['name']
        if 'description' in data:
            shop_resource.resource.description = data['description']
        if 'unit' in data:
            shop_resource.resource.unit = data['unit']
        if 'quantity' in data:
            shop_resource.quantity = data['quantity']
        if 'min_quantity' in data:
            shop_resource.min_quantity = data['min_quantity']
        if 'max_quantity' in data:
            shop_resource.max_quantity = data['max_quantity']
        if 'category_id' in data:
            if data['category_id'] is None:
                shop_resource.resource.category_id = None
            else:
                category = ResourceCategory.query.filter_by(
                    id=data['category_id'],
                    shop_id=user.shop_id
                ).first()
                if not category:
                    return jsonify({'error': 'Category not found'}), 404
                shop_resource.resource.category_id = category.id
        db.session.commit()
        return jsonify({
            'id': shop_resource.id,
            'resource_id': shop_resource.resource_id,
            'name': shop_resource.resource.name,
            'description': shop_resource.resource.description,
            'category_id': shop_resource.resource.category_id,
            'category_name': shop_resource.resource.category.name if shop_resource.resource.category else None,
            'quantity': shop_resource.quantity,
            'unit': shop_resource.resource.unit,
            'min_quantity': shop_resource.min_quantity,
            'max_quantity': shop_resource.max_quantity,
            'last_restock_date': shop_resource.last_restock_date.isoformat() if shop_resource.last_restock_date else None,
            'last_restock_quantity': shop_resource.last_restock_quantity,
            'created_at': shop_resource.created_at.isoformat()
        })
    except Exception as e:
        logging.error(f"Error updating resource: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@resource_bp.route('/api/resources/<int:resource_id>/restock', methods=['POST'])
@jwt_required()
def restock_resource(resource_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        shop_resource = ShopResource.query.filter_by(
            id=resource_id,
            shop_id=user.shop_id
        ).first()
        if not shop_resource:
            return jsonify({'error': 'Resource not found'}), 404
        data = request.get_json()
        if not data or 'quantity' not in data:
            return jsonify({'error': 'Quantity is required'}), 400
        quantity = data['quantity']
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be greater than 0'}), 400
        shop_resource.quantity += quantity
        shop_resource.last_restock_date = datetime.utcnow()
        shop_resource.last_restock_quantity = quantity
        history = ResourceHistory(
            shop_resource_id=shop_resource.id,
            quantity=quantity,
            type='restock',
            notes=data.get('notes'),
            created_at=datetime.utcnow()
        )
        db.session.add(history)
        db.session.commit()
        return jsonify({
            'id': shop_resource.id,
            'resource_id': shop_resource.resource_id,
            'name': shop_resource.resource.name,
            'quantity': shop_resource.quantity,
            'last_restock_date': shop_resource.last_restock_date.isoformat(),
            'last_restock_quantity': shop_resource.last_restock_quantity
        })
    except Exception as e:
        logging.error(f"Error restocking resource: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
