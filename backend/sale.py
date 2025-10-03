from flask import Blueprint, jsonify, request
from database import db, Sale, Product, Shop, User, Inventory
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import logging

sale_bp = Blueprint('sale', __name__)

@sale_bp.route('/api/sales', methods=['GET'])
@jwt_required()
def get_sales():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
            
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Sale.query.filter_by(shop_id=user.shop_id)
        
        if start_date:
            query = query.filter(Sale.created_at >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(Sale.created_at <= datetime.fromisoformat(end_date))
            
        sales = query.order_by(Sale.created_at.desc()).all()
        
        return jsonify([{
            'id': sale.id,
            'product_id': sale.product_id,
            'product_name': sale.product.name if sale.product else None,
            'quantity': sale.quantity,
            'total_amount': sale.total_amount,
            'created_at': sale.created_at.isoformat() if sale.created_at else None
        } for sale in sales])
    except Exception as e:
        logging.error(f"Error getting sales: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@sale_bp.route('/api/sales', methods=['POST'])
@jwt_required()
def create_sale():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
            
        data = request.get_json()
        if not data or 'product_id' not in data or 'quantity' not in data:
            return jsonify({'error': 'Product ID and quantity are required'}), 400
            
        # Check if product exists and belongs to the shop
        product = Product.query.filter_by(
            id=data['product_id'],
            shop_id=user.shop_id
        ).first()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
            
        # Check inventory
        inventory = Inventory.query.filter_by(
            product_id=product.id,
            shop_id=user.shop_id
        ).first()
        
        if not inventory or inventory.quantity < data['quantity']:
            return jsonify({'error': 'Insufficient inventory'}), 400
            
        # Calculate total amount
        total_amount = product.price * data['quantity']
        
        # Create sale
        sale = Sale(
            shop_id=user.shop_id,
            product_id=product.id,
            quantity=data['quantity'],
            total_amount=total_amount,
            created_at=datetime.utcnow()
        )
        
        # Update inventory
        inventory.quantity -= data['quantity']
        inventory.last_updated = datetime.utcnow()
        
        db.session.add(sale)
        db.session.commit()
        
        return jsonify({
            'id': sale.id,
            'product_id': sale.product_id,
            'product_name': product.name,
            'quantity': sale.quantity,
            'total_amount': sale.total_amount,
            'created_at': sale.created_at.isoformat()
        }), 201
    except Exception as e:
        logging.error(f"Error creating sale: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 