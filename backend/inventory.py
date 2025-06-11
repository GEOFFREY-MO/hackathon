from flask import Blueprint, jsonify, request
from backend.database import db, Inventory, Product, Shop, User
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import logging

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/api/inventory', methods=['GET'])
@jwt_required()
def get_inventory():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
            
        inventory_items = Inventory.query.filter_by(shop_id=user.shop_id).all()
        
        return jsonify([{
            'id': item.id,
            'product_id': item.product_id,
            'product_name': item.product.name if item.product else None,
            'quantity': item.quantity,
            'last_updated': item.last_updated.isoformat() if item.last_updated else None
        } for item in inventory_items])
    except Exception as e:
        logging.error(f"Error getting inventory: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@inventory_bp.route('/api/inventory/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_inventory(product_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
            
        data = request.get_json()
        if not data or 'quantity' not in data:
            return jsonify({'error': 'Quantity is required'}), 400
            
        inventory_item = Inventory.query.filter_by(
            shop_id=user.shop_id,
            product_id=product_id
        ).first()
        
        if not inventory_item:
            return jsonify({'error': 'Inventory item not found'}), 404
            
        inventory_item.quantity = data['quantity']
        inventory_item.last_updated = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'id': inventory_item.id,
            'product_id': inventory_item.product_id,
            'quantity': inventory_item.quantity,
            'last_updated': inventory_item.last_updated.isoformat()
        })
    except Exception as e:
        logging.error(f"Error updating inventory: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 