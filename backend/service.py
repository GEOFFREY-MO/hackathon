from flask import Blueprint, jsonify, request
from database import db, Service, ServiceSale, Shop, User, ServiceCategory
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import logging

service_bp = Blueprint('service', __name__)

@service_bp.route('/api/services', methods=['GET'])
@jwt_required()
def get_services():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
            
        services = Service.query.filter_by(shop_id=user.shop_id).all()
        
        return jsonify([{
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'price': service.price,
            'duration': service.duration,
            'category_id': service.category_id,
            'category_name': service.category.name if service.category else None,
            'created_at': service.created_at.isoformat() if service.created_at else None
        } for service in services])
    except Exception as e:
        logging.error(f"Error getting services: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@service_bp.route('/api/services', methods=['POST'])
@jwt_required()
def create_service():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
            
        data = request.get_json()
        if not data or 'name' not in data or 'price' not in data:
            return jsonify({'error': 'Name and price are required'}), 400
            
        # Check if category exists and belongs to the shop
        category = None
        if 'category_id' in data:
            category = ServiceCategory.query.filter_by(
                id=data['category_id'],
                shop_id=user.shop_id
            ).first()
            
            if not category:
                return jsonify({'error': 'Category not found'}), 404
        
        # Create service
        service = Service(
            shop_id=user.shop_id,
            name=data['name'],
            description=data.get('description'),
            price=data['price'],
            duration=data.get('duration'),
            category_id=category.id if category else None,
            created_at=datetime.utcnow()
        )
        
        db.session.add(service)
        db.session.commit()
        
        return jsonify({
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'price': service.price,
            'duration': service.duration,
            'category_id': service.category_id,
            'category_name': category.name if category else None,
            'created_at': service.created_at.isoformat()
        }), 201
    except Exception as e:
        logging.error(f"Error creating service: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@service_bp.route('/api/services/<int:service_id>', methods=['PUT'])
@jwt_required()
def update_service(service_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
            
        service = Service.query.filter_by(
            id=service_id,
            shop_id=user.shop_id
        ).first()
        
        if not service:
            return jsonify({'error': 'Service not found'}), 404
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Update service fields
        if 'name' in data:
            service.name = data['name']
        if 'description' in data:
            service.description = data['description']
        if 'price' in data:
            service.price = data['price']
        if 'duration' in data:
            service.duration = data['duration']
            
        # Update category if provided
        if 'category_id' in data:
            if data['category_id'] is None:
                service.category_id = None
            else:
                category = ServiceCategory.query.filter_by(
                    id=data['category_id'],
                    shop_id=user.shop_id
                ).first()
                
                if not category:
                    return jsonify({'error': 'Category not found'}), 404
                    
                service.category_id = category.id
        
        db.session.commit()
        
        return jsonify({
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'price': service.price,
            'duration': service.duration,
            'category_id': service.category_id,
            'category_name': service.category.name if service.category else None,
            'created_at': service.created_at.isoformat()
        })
    except Exception as e:
        logging.error(f"Error updating service: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
