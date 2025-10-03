from flask import Blueprint, jsonify, request
from database import db, Shop, Sale, ServiceSale, Expense, Product, Service
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import logging

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/analytics/sales', methods=['GET'])
@jwt_required()
def get_sales_analytics():
    try:
        current_user_id = get_jwt_identity()
        user = Shop.query.filter_by(admin_id=current_user_id).first()
        if not user:
            return jsonify({'error': 'Shop not found'}), 404

        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            start_date = datetime.utcnow() - timedelta(days=30)
            
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end_date = datetime.utcnow()

        # Get total sales
        total_sales = db.session.query(
            func.sum(Sale.amount).label('total_amount'),
            func.count(Sale.id).label('total_count')
        ).filter(
            Sale.shop_id == user.id,
            Sale.date >= start_date,
            Sale.date <= end_date
        ).first()

        # Get service sales
        service_sales = db.session.query(
            func.sum(ServiceSale.amount).label('total_amount'),
            func.count(ServiceSale.id).label('total_count')
        ).filter(
            ServiceSale.shop_id == user.id,
            ServiceSale.date >= start_date,
            ServiceSale.date <= end_date
        ).first()

        # Get top selling products
        top_products = db.session.query(
            Product.name,
            func.sum(Sale.amount).label('total_amount'),
            func.count(Sale.id).label('total_count')
        ).join(
            Sale, Sale.product_id == Product.id
        ).filter(
            Sale.shop_id == user.id,
            Sale.date >= start_date,
            Sale.date <= end_date
        ).group_by(Product.id).order_by(func.sum(Sale.amount).desc()).limit(5).all()

        # Get top selling services
        top_services = db.session.query(
            Service.name,
            func.sum(ServiceSale.amount).label('total_amount'),
            func.count(ServiceSale.id).label('total_count')
        ).join(
            ServiceSale, ServiceSale.service_id == Service.id
        ).filter(
            ServiceSale.shop_id == user.id,
            ServiceSale.date >= start_date,
            ServiceSale.date <= end_date
        ).group_by(Service.id).order_by(func.sum(ServiceSale.amount).desc()).limit(5).all()

        # Get daily sales for the period
        daily_sales = db.session.query(
            func.date(Sale.date).label('date'),
            func.sum(Sale.amount).label('amount')
        ).filter(
            Sale.shop_id == user.id,
            Sale.date >= start_date,
            Sale.date <= end_date
        ).group_by(func.date(Sale.date)).all()

        # Get daily service sales for the period
        daily_service_sales = db.session.query(
            func.date(ServiceSale.date).label('date'),
            func.sum(ServiceSale.amount).label('amount')
        ).filter(
            ServiceSale.shop_id == user.id,
            ServiceSale.date >= start_date,
            ServiceSale.date <= end_date
        ).group_by(func.date(ServiceSale.date)).all()

        # Get expenses for the period
        expenses = db.session.query(
            func.sum(Expense.amount).label('total_amount')
        ).filter(
            Expense.shop_id == user.id,
            Expense.date >= start_date,
            Expense.date <= end_date
        ).first()

        return jsonify({
            'sales_summary': {
                'total_amount': float(total_sales.total_amount or 0),
                'total_count': total_sales.total_count or 0
            },
            'service_sales_summary': {
                'total_amount': float(service_sales.total_amount or 0),
                'total_count': service_sales.total_count or 0
            },
            'top_products': [{
                'name': product.name,
                'total_amount': float(product.total_amount or 0),
                'total_count': product.total_count or 0
            } for product in top_products],
            'top_services': [{
                'name': service.name,
                'total_amount': float(service.total_amount or 0),
                'total_count': service.total_count or 0
            } for service in top_services],
            'daily_sales': [{
                'date': sale.date.strftime('%Y-%m-%d'),
                'amount': float(sale.amount or 0)
            } for sale in daily_sales],
            'daily_service_sales': [{
                'date': sale.date.strftime('%Y-%m-%d'),
                'amount': float(sale.amount or 0)
            } for sale in daily_service_sales],
            'expenses': float(expenses.total_amount or 0),
            'net_profit': float((total_sales.total_amount or 0) + (service_sales.total_amount or 0) - (expenses.total_amount or 0))
        })

    except Exception as e:
        logging.error(f"Error getting sales analytics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@analytics_bp.route('/api/analytics/inventory', methods=['GET'])
@jwt_required()
def get_inventory_analytics():
    try:
        current_user_id = get_jwt_identity()
        user = Shop.query.filter_by(admin_id=current_user_id).first()
        if not user:
            return jsonify({'error': 'Shop not found'}), 404

        # Get low stock products
        low_stock_products = db.session.query(
            Product.name,
            Product.quantity,
            Product.reorder_level
        ).filter(
            Product.shop_id == user.id,
            Product.quantity <= Product.reorder_level
        ).all()

        # Get out of stock products
        out_of_stock_products = db.session.query(
            Product.name
        ).filter(
            Product.shop_id == user.id,
            Product.quantity == 0
        ).all()

        # Get inventory value
        inventory_value = db.session.query(
            func.sum(Product.quantity * Product.price).label('total_value')
        ).filter(
            Product.shop_id == user.id
        ).first()

        return jsonify({
            'low_stock_products': [{
                'name': product.name,
                'quantity': product.quantity,
                'reorder_level': product.reorder_level
            } for product in low_stock_products],
            'out_of_stock_products': [product.name for product in out_of_stock_products],
            'inventory_value': float(inventory_value.total_value or 0)
        })

    except Exception as e:
        logging.error(f"Error getting inventory analytics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@analytics_bp.route('/api/analytics/expenses', methods=['GET'])
@jwt_required()
def get_expense_analytics():
    try:
        current_user_id = get_jwt_identity()
        user = Shop.query.filter_by(admin_id=current_user_id).first()
        if not user:
            return jsonify({'error': 'Shop not found'}), 404

        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            start_date = datetime.utcnow() - timedelta(days=30)
            
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end_date = datetime.utcnow()

        # Get expenses by category
        expenses_by_category = db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total_amount')
        ).filter(
            Expense.shop_id == user.id,
            Expense.date >= start_date,
            Expense.date <= end_date
        ).group_by(Expense.category).all()

        # Get daily expenses
        daily_expenses = db.session.query(
            func.date(Expense.date).label('date'),
            func.sum(Expense.amount).label('amount')
        ).filter(
            Expense.shop_id == user.id,
            Expense.date >= start_date,
            Expense.date <= end_date
        ).group_by(func.date(Expense.date)).all()

        return jsonify({
            'expenses_by_category': [{
                'category': category,
                'total_amount': float(total_amount or 0)
            } for category, total_amount in expenses_by_category],
            'daily_expenses': [{
                'date': expense.date.strftime('%Y-%m-%d'),
                'amount': float(expense.amount or 0)
            } for expense in daily_expenses]
        })

    except Exception as e:
        logging.error(f"Error getting expense analytics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
