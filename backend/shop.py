from flask import Blueprint, jsonify, request
from database import db, Shop, User, Product, Inventory, Sale, Service, ServiceSale, Resource, ShopResource, Expense, ResourceHistory, ResourceAlert, ResourceCategory, ServiceCategory, FinancialRecord, UnscannedSale
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import logging

shop_bp = Blueprint('shop', __name__)

@shop_bp.route('/api/shop/info', methods=['GET'])
@jwt_required()
def get_shop_info():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
            
        shop = Shop.query.get(user.shop_id)
        if not shop:
            return jsonify({'error': 'Shop not found'}), 404
            
        return jsonify({
            'id': shop.id,
            'name': shop.name,
            'location': shop.location,
            'contact': shop.contact,
            'email': shop.email,
            'created_at': shop.created_at.isoformat() if shop.created_at else None
        })
    except Exception as e:
        logging.error(f"Error getting shop info: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@shop_bp.route('/api/shop/stats', methods=['GET'])
@jwt_required()
def get_shop_stats():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
            
        shop = Shop.query.get(user.shop_id)
        if not shop:
            return jsonify({'error': 'Shop not found'}), 404
            
        # Get today's date
        today = datetime.utcnow().date()
        
        # Get sales for today
        today_sales = Sale.query.filter(
            Sale.shop_id == shop.id,
            db.func.date(Sale.created_at) == today
        ).all()
        
        # Get service sales for today
        today_service_sales = ServiceSale.query.filter(
            ServiceSale.shop_id == shop.id,
            db.func.date(ServiceSale.created_at) == today
        ).all()
        
        # Calculate total revenue
        total_revenue = sum(sale.total_amount for sale in today_sales) + \
                       sum(sale.total_amount for sale in today_service_sales)
        
        # Get total products
        total_products = Product.query.filter_by(shop_id=shop.id).count()
        
        # Get total services
        total_services = Service.query.filter_by(shop_id=shop.id).count()
        
        return jsonify({
            'total_revenue': total_revenue,
            'total_products': total_products,
            'total_services': total_services,
            'today_sales_count': len(today_sales) + len(today_service_sales)
        })
    except Exception as e:
        logging.error(f"Error getting shop stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 