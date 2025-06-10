from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from backend.database.models import db, Shop, Product, Inventory, Sale, Service, ServiceSale, User, Resource, ShopResource, ResourceUpdate, Expense, ResourceAlert, ResourceHistory, ServiceCategory, FinancialRecord
from datetime import datetime, timedelta
import logging
from sqlalchemy import func, desc
import pandas as pd
from io import BytesIO
from werkzeug.utils import send_file
import json
from backend.config import Config
from decimal import Decimal
import xlsxwriter

employee_bp = Blueprint('employee', __name__)

# Configure logging
logger = logging.getLogger(__name__)


@employee_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get the shop
        shop = Shop.query.get(current_user.shop_id)

        # Get today's date
        today = datetime.now().date()

        # Get today's sales
        today_sales = Sale.query.filter(
            Sale.shop_id == current_user.shop_id,
            db.func.date(Sale.sale_date) == today
        ).all()

        # Get today's service income
        today_service_sales = ServiceSale.query.filter(
            ServiceSale.shop_id == current_user.shop_id,
            db.func.date(ServiceSale.sale_date) == today
        ).all()

        # Calculate today's totals
        today_sales_total = sum(sale.product.marked_price * sale.quantity for sale in today_sales)
        today_service_income = sum(sale.price for sale in today_service_sales)
        today_transactions = len(today_sales) + len(today_service_sales)

        # Get active services
        active_services = ServiceSale.query.filter(
            ServiceSale.shop_id == current_user.shop_id,
            ServiceSale.status == 'active'
        ).order_by(ServiceSale.sale_date.desc()).all()

        # Get recent sales (last 5)
        recent_sales = Sale.query.filter_by(shop_id=current_user.shop_id)\
            .order_by(Sale.sale_date.desc())\
            .limit(5)\
            .all()

        # Get low stock items
        low_stock_items = Inventory.query.filter_by(
            shop_id=current_user.shop_id) .filter(
            Inventory.quantity < 10) .all()

        return render_template('employee/dashboard.html',
                               shop=shop,
                               today_sales=today_sales_total,
                               today_service_income=today_service_income,
                               today_transactions=today_transactions,
                               active_services=active_services,
                               active_services_count=len(active_services),
                               recent_sales=recent_sales,
                               low_stock_items=low_stock_items,
                               low_stock_count=len(low_stock_items))

    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard. Please try again.', 'error')
        return redirect(url_for('employee.dashboard'))


@employee_bp.route('/products')
@login_required
def product_list():
    shop = Shop.query.get(current_user.shop_id)
    inventory_items = Inventory.query.filter_by(
        shop_id=current_user.shop_id).all()
    return render_template('employee/products.html',
                           shop=shop,
                           inventory_items=inventory_items)


@employee_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    """Add a new product to inventory."""
    if current_user.role != 'employee':
        flash('Access denied. Employee access only.', 'danger')
        return redirect(url_for('auth.select_role'))

    shop = Shop.query.get(current_user.shop_id)
    if not shop:
        flash('You are not assigned to any shop.', 'warning')
        return redirect(url_for('auth.select_role'))

    if request.method == 'POST':
        name = request.form.get('name')
        barcode = request.form.get('barcode')
        category = request.form.get('category')
        marked_price = request.form.get('marked_price', type=float)
        quantity = request.form.get('quantity', type=int)

        # Check if product with barcode already exists
        existing_product = Product.query.filter_by(barcode=barcode).first()

        if existing_product:
            # Update inventory for existing product
            inventory = Inventory.query.filter_by(
                shop_id=shop.id,
                product_id=existing_product.id
            ).first()

            if inventory:
                inventory.quantity += quantity
            else:
                inventory = Inventory(
                    shop_id=shop.id,
                    product_id=existing_product.id,
                    quantity=quantity
                )
                db.session.add(inventory)
        else:
            # Create new product
            product = Product(
                name=name,
                barcode=barcode,
                category=category,
                marked_price=marked_price
            )
            db.session.add(product)
            db.session.flush()  # Get the product ID

            # Create inventory entry
            inventory = Inventory(
                shop_id=shop.id,
                product_id=product.id,
                quantity=quantity
            )
            db.session.add(inventory)

        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('employee.product_list'))

    # Create a form object for GET request
    form = {
        'name': '',
        'barcode': '',
        'category': '',
        'marked_price': '',
        'quantity': ''
    }

    return render_template('employee/add_product.html', shop=shop, form=form)


@employee_bp.route('/products/<int:id>/update_stock', methods=['GET', 'POST'])
@login_required
def update_stock(id):
    try:
        # Get the product and inventory item
        product = Product.query.get_or_404(id)
        inventory_item = Inventory.query.filter_by(
            product_id=id,
            shop_id=current_user.shop_id
        ).first_or_404()

        if request.method == 'POST':
            # Get the new quantity from the form
            new_quantity = request.form.get('quantity', type=int)
            if new_quantity is None or new_quantity < 0:
                flash('Invalid quantity value', 'danger')
                return redirect(url_for('employee.product_list'))

            # Update the inventory
            inventory_item.quantity = new_quantity
            db.session.commit()

            flash('Stock updated successfully', 'success')
            return redirect(url_for('employee.product_list'))

        # GET request - show the update form
        return render_template('employee/update_stock.html',
                               product=product,
                               inventory_item=inventory_item)

    except Exception as e:
        db.session.rollback()
        flash('Error updating stock', 'danger')
        current_app.logger.error(f"Error updating stock: {str(e)}")
        return redirect(url_for('employee.product_list'))


@employee_bp.route('/sales/new', methods=['GET', 'POST'])
@login_required
def new_sale():
    if request.method == 'POST':
        try:
            product_id = request.form.get('product_id', type=int)
            quantity = request.form.get('quantity', type=int)
            customer_name = request.form.get('customer_name')
            payment_method = request.form.get('payment_method', 'cash')

            if not all([product_id, quantity, payment_method]):
                flash('Please fill in all required fields', 'danger')
                return redirect(url_for('employee.new_sale'))

            # Validate payment method
            valid_payment_methods = ['cash', 'till', 'bank']
            if payment_method not in valid_payment_methods:
                flash('Invalid payment method', 'danger')
                return redirect(url_for('employee.new_sale'))

            # Get the product and inventory
            product = Product.query.get_or_404(product_id)
            inventory_item = Inventory.query.filter_by(
                product_id=product_id,
                shop_id=current_user.shop_id
            ).first_or_404()

            # Check if we have enough stock
            if inventory_item.quantity < quantity:
                flash('Not enough stock available', 'danger')
                return redirect(url_for('employee.new_sale'))

            # Calculate total amount
            total_amount = product.marked_price * quantity

            # Create the sale
            sale = Sale(
                product_id=product_id,
                shop_id=current_user.shop_id,
                quantity=quantity,
                customer_name=customer_name,
                payment_method=payment_method,
                sale_date=datetime.now()
            )

            # Create financial record
            financial_record = FinancialRecord(
                shop_id=current_user.shop_id,
                type=payment_method,
                amount=total_amount,
                description=f'Sale of {quantity} {product.name}',
                date=datetime.now(),
                created_by=current_user.id
            )

            # Update inventory
            inventory_item.quantity -= quantity

            # Add records to session
            db.session.add(sale)
            db.session.add(financial_record)
            db.session.commit()

            flash('Sale recorded successfully', 'success')
            return redirect(url_for('employee.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash('Error recording sale', 'danger')
            current_app.logger.error(f"Error recording sale: {str(e)}", exc_info=True)
            return redirect(url_for('employee.new_sale'))

    # GET request - show the form
    shop = Shop.query.get(current_user.shop_id)
    products = Product.query.join(Inventory)\
        .filter(Inventory.shop_id == current_user.shop_id)\
        .all()

    return render_template('employee/new_sale.html',
                           shop=shop,
                           products=products)


@employee_bp.route('/sales')
@login_required
def sales_list():
    shop = Shop.query.get(current_user.shop_id)
    sales = Sale.query.filter_by(shop_id=current_user.shop_id)\
        .order_by(Sale.sale_date.desc())\
        .all()

    # Calculate total sales and items
    total_sales = sum(sale.product.marked_price * sale.quantity for sale in sales)
    total_items = len(sales)

    return render_template('employee/sales.html',
                           shop=shop,
                           sales=sales,
                           total_sales=total_sales,
                           total_items=total_items)


@employee_bp.route('/ai-assistant', methods=['POST'])
@login_required
def ai_assistant():
    """Handle AI assistant chat interactions with RAG capabilities."""
    if current_user.role != 'employee':
        return jsonify({"error": "Unauthorized"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'response': 'No data provided'
            }), 400

        message = data.get('message', '').lower()

        # Get current analytics data for context
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)

        # Get sales data for different time periods
        today_sales = Sale.query.filter(
            Sale.shop_id == current_user.shop_id,
            func.date(Sale.sale_date) == today
        ).all()

        week_sales = Sale.query.filter(
            Sale.shop_id == current_user.shop_id,
            func.date(Sale.sale_date) >= start_of_week
        ).all()

        month_sales = Sale.query.filter(
            Sale.shop_id == current_user.shop_id,
            func.date(Sale.sale_date) >= start_of_month
        ).all()

        # Get service data
        today_services = ServiceSale.query.filter(
            ServiceSale.shop_id == current_user.shop_id,
            func.date(ServiceSale.sale_date) == today
        ).all()

        # Get stock status
        low_stock_items = Inventory.query.filter(
            Inventory.shop_id == current_user.shop_id,
            Inventory.quantity < 10
        ).all()

        # Calculate metrics
        def calculate_metrics(sales, services):
            total_sales = sum(sale.price * sale.quantity for sale in sales)
            total_services = sum(service.price for service in services)
            total_revenue = total_sales + total_services
            total_transactions = len(sales) + len(services)
            avg_transaction = total_revenue / \
                total_transactions if total_transactions > 0 else 0

            # Payment method distribution
            payment_methods = {
                'cash': sum(
                    sale.price *
                    sale.quantity for sale in sales if sale.payment_method == 'cash'),
                'till': sum(
                    sale.price *
                    sale.quantity for sale in sales if sale.payment_method == 'till'),
                'bank': sum(
                    sale.price *
                    sale.quantity for sale in sales if sale.payment_method == 'bank')}

            return {
                'total_revenue': total_revenue,
                'total_transactions': total_transactions,
                'avg_transaction': avg_transaction,
                'payment_methods': payment_methods
            }

        today_metrics = calculate_metrics(today_sales, today_services)
        week_metrics = calculate_metrics(week_sales, [])
        month_metrics = calculate_metrics(month_sales, [])

        # Get shop information
        shop = Shop.query.get(current_user.shop_id)

        # Prepare context for RAG
        context = {
            'shop_name': shop.name if shop else 'your shop',
            'today_metrics': today_metrics,
            'week_metrics': week_metrics,
            'month_metrics': month_metrics,
            'low_stock_count': len(low_stock_items),
            'low_stock_items': [item.product.name for item in low_stock_items],
            'current_date': today.strftime("%B %d, %Y")
        }

        # Process the message and generate response using RAG
        if 'sales' in message or 'revenue' in message:
            response = f"""Here's your sales analysis for {context['shop_name']}:

Today's Performance:
- Total Revenue: KES {context['today_metrics']['total_revenue']:.2f}
- Total Transactions: {context['today_metrics']['total_transactions']}
- Average Transaction: KES {context['today_metrics']['avg_transaction']:.2f}
- Payment Methods:
  * Cash: KES {context['today_metrics']['payment_methods']['cash']:.2f}
  * Till: KES {context['today_metrics']['payment_methods']['till']:.2f}
  * Bank: KES {context['today_metrics']['payment_methods']['bank']:.2f}

This Week's Performance:
- Total Revenue: KES {context['week_metrics']['total_revenue']:.2f}
- Total Transactions: {context['week_metrics']['total_transactions']}
- Average Transaction: KES {context['week_metrics']['avg_transaction']:.2f}

This Month's Performance:
- Total Revenue: KES {context['month_metrics']['total_revenue']:.2f}
- Total Transactions: {context['month_metrics']['total_transactions']}
- Average Transaction: KES {context['month_metrics']['avg_transaction']:.2f}

Would you like me to analyze any specific aspect of these metrics or compare them with previous periods?"""

        elif 'stock' in message or 'inventory' in message:
            if context['low_stock_count'] > 0:
                response = f"""Stock Status Alert:
- {context['low_stock_count']} items are running low on stock
- Items needing attention: {', '.join(context['low_stock_items'])}
- Recommended action: Consider restocking these items soon

Would you like me to provide more detailed stock analysis or help with reorder suggestions?"""
            else:
                response = "All items are well-stocked at the moment. Would you like to see detailed inventory levels?"

        elif 'help' in message:
            response = """I can help you with:
1. Sales Analysis
   - Daily, weekly, and monthly revenue
   - Transaction patterns
   - Payment method distribution
   - Performance trends

2. Stock Management
   - Current stock levels
   - Low stock alerts
   - Reorder suggestions
   - Inventory trends

3. Performance Insights
   - Sales comparisons
   - Growth analysis
   - Best-selling items
   - Service performance

4. Business Recommendations
   - Stock optimization
   - Sales opportunities
   - Resource allocation
   - Performance improvements

Just ask me about any of these topics in natural language!"""

        else:
            response = """I can help you analyze your business performance, manage inventory, and provide insights. Try asking about:
- Today's sales performance
- Stock levels and alerts
- Payment method distribution
- Service performance
- Business recommendations

Or type 'help' for a complete list of topics I can assist with."""

        return jsonify({
            'success': True,
            'response': response,
            'context': context  # Include context for potential follow-up questions
        })

    except Exception as e:
        current_app.logger.error(f"Error in AI assistant: {str(e)}")
        return jsonify({
            'success': False,
            'response': 'Sorry, I encountered an error. Please try again.'
        }), 500


@employee_bp.route('/ai-assistant/insights')
@login_required
def ai_assistant_insights():
    if not current_user.is_authenticated or current_user.role != 'employee':
        return jsonify(
            {'success': False, 'response': 'Unauthorized access'}), 403

    try:
        # Get stock status insights
        stock_status = get_stock_status_insights()

        # Get today's performance insights
        performance = get_today_performance_insights()

        return jsonify({
            'success': True,
            'insights': {
                'stock': stock_status,
                'performance': performance
            }
        })

    except Exception as e:
        current_app.logger.error(f"AI Assistant Insights Error: {str(e)}")
        return jsonify(
            {'success': False, 'response': 'Failed to fetch insights'}), 500


@employee_bp.route('/analytics')
@login_required
def analytics():
    """Show analytics dashboard with shop-specific data visualizations."""
    if current_user.role != 'employee':
        flash('Access denied. Employee access only.', 'danger')
        return redirect(url_for('auth.select_role'))

    try:
        # Get the shop
        shop = Shop.query.get(current_user.shop_id)
        if not shop:
            flash('Shop not found.', 'danger')
            return redirect(url_for('employee.dashboard'))

        # Get today's date
        today = datetime.now().date()

        # Get sales data
        sales = Sale.query.filter(
            Sale.shop_id == current_user.shop_id,
            func.date(Sale.sale_date) == today
        ).all()

        # Get service sales data
        service_sales = ServiceSale.query.filter(
            ServiceSale.shop_id == current_user.shop_id,
            func.date(ServiceSale.sale_date) == today
        ).all()

        # Calculate totals
        total_sales = sum(sale.price * sale.quantity for sale in sales)
        total_products_sold = sum(sale.quantity for sale in sales)
        total_services_rendered = len(service_sales)
        total_transactions = len(sales) + len(service_sales)
        average_transaction = total_sales / \
            total_transactions if total_transactions > 0 else 0

        # Get top products
        top_products = db.session.query(
            Product.name,
            func.sum(Sale.quantity).label('units_sold'),
            func.sum(Sale.price * Sale.quantity).label('revenue')
        ).join(Sale).filter(
            Sale.shop_id == current_user.shop_id,
            func.date(Sale.sale_date) == today
        ).group_by(Product.name).order_by(desc('revenue')).limit(5).all()

        # Get top services
        top_services = db.session.query(
            Service.name,
            func.count(ServiceSale.id).label('times_rendered'),
            func.sum(ServiceSale.price).label('revenue')
        ).join(ServiceSale).filter(
            ServiceSale.shop_id == current_user.shop_id,
            func.date(ServiceSale.sale_date) == today
        ).group_by(Service.name).order_by(desc('revenue')).limit(5).all()

        # Prepare sales trend data
        sales_trend = {
            'labels': [sale.sale_date.strftime('%H:%M') for sale in sales],
            'data': [sale.price * sale.quantity for sale in sales]
        }

        # Prepare payment methods data
        payment_methods = {
            'labels': ['Cash', 'M-Pesa', 'Card'],
            'data': [
                sum(sale.price * sale.quantity for sale in sales if sale.payment_method == 'cash'),
                sum(sale.price * sale.quantity for sale in sales if sale.payment_method == 'mpesa'),
                sum(sale.price * sale.quantity for sale in sales if sale.payment_method == 'card')
            ]
        }

        # Get AI assistant insights
        stock_status = get_stock_status_insights()
        performance = get_today_performance_insights()

        # Get resource status
        resources = Resource.query.order_by(Resource.name).all()
        shop_resources = {}
        for resource in resources:
            shop_resource = ShopResource.query.filter_by(
                shop_id=current_user.shop_id,
                resource_id=resource.id
            ).first()
            shop_resources[resource.id] = {
                'quantity': shop_resource.quantity if shop_resource else 0,
                'last_updated': shop_resource.last_updated if shop_resource else None
            }

        return render_template('employee/analytics.html',
                               shop=shop,
                               total_sales=total_sales,
                               total_products_sold=total_products_sold,
                               total_services_rendered=total_services_rendered,
                               average_transaction=average_transaction,
                               top_products=top_products,
                               top_services=top_services,
                               sales_trend=sales_trend,
                               payment_methods=payment_methods,
                               stock_status=stock_status,
                               performance=performance,
                               resources=resources,
                               shop_resources=shop_resources)

    except Exception as e:
        logger.error(f"Error loading analytics: {str(e)}")
        flash('Error loading analytics. Please try again.', 'error')
        return redirect(url_for('employee.dashboard'))


@employee_bp.route('/analytics/data')
@login_required
def analytics_data():
    """Provide analytics data for the employee's shop."""
    if current_user.role != 'employee':
        return jsonify({"error": "Unauthorized"}), 403

    try:
        period = request.args.get('period', 'today')

        # Calculate date range based on period
        end_date = datetime.now()
        if period == 'today':
            start_date = end_date.replace(
                hour=0, minute=0, second=0, microsecond=0)
            date_format = '%H:%M'
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
            date_format = '%Y-%m-%d'
        else:  # month
            start_date = end_date.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0)
            date_format = '%Y-%m-%d'

        # Get sales data for the period
        sales = Sale.query.filter(
            Sale.shop_id == current_user.shop_id,
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).all()

        # Get service sales data for the period
        service_sales = ServiceSale.query.filter(
            ServiceSale.shop_id == current_user.shop_id,
            ServiceSale.sale_date >= start_date,
            ServiceSale.sale_date <= end_date
        ).all()

        # Calculate totals
        total_sales = sum(sale.price * sale.quantity for sale in sales)
        total_products_sold = sum(sale.quantity for sale in sales)
        total_services_rendered = len(service_sales)
        total_transactions = len(sales) + len(service_sales)
        average_transaction = total_sales / \
            total_transactions if total_transactions > 0 else 0

        # Get top products
        top_products = db.session.query(
            Product.name,
            func.sum(Sale.quantity).label('units_sold'),
            func.sum(Sale.price * Sale.quantity).label('revenue')
        ).join(Sale).filter(
            Sale.shop_id == current_user.shop_id,
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).group_by(Product.name).order_by(desc('revenue')).limit(5).all()

        # Get top services
        top_services = db.session.query(
            Service.name,
            func.count(ServiceSale.id).label('times_rendered'),
            func.sum(ServiceSale.price).label('revenue')
        ).join(ServiceSale).filter(
            ServiceSale.shop_id == current_user.shop_id,
            ServiceSale.sale_date >= start_date,
            ServiceSale.sale_date <= end_date
        ).group_by(Service.name).order_by(desc('revenue')).limit(5).all()

        # Prepare sales trend data
        sales_trend = {
            'labels': [sale.sale_date.strftime(date_format) for sale in sales],
            'data': [sale.price * sale.quantity for sale in sales]
        }

        # Prepare payment methods data
        payment_methods = {
            'labels': ['Cash', 'M-Pesa', 'Card'],
            'data': [
                sum(sale.price * sale.quantity for sale in sales if sale.payment_method == 'cash'),
                sum(sale.price * sale.quantity for sale in sales if sale.payment_method == 'mpesa'),
                sum(sale.price * sale.quantity for sale in sales if sale.payment_method == 'card')
            ]
        }

        # Format the response data
        response_data = {
            'total_sales': total_sales,
            'total_products_sold': total_products_sold,
            'total_services_rendered': total_services_rendered,
            'average_transaction': average_transaction,
            'top_products': [
                {
                    'name': product.name,
                    'units_sold': int(product.units_sold),
                    'revenue': float(product.revenue)
                }
                for product in top_products
            ],
            'top_services': [
                {
                    'name': service.name,
                    'times_rendered': int(service.times_rendered),
                    'revenue': float(service.revenue)
                }
                for service in top_services
            ],
            'sales_trend': sales_trend,
            'payment_methods': payment_methods
        }

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Error generating analytics data: {str(e)}")
        return jsonify({
            "error": "Failed to generate analytics data",
            "details": str(e)
        }), 500


def process_employee_message(message):
    """Process employee messages and generate appropriate responses."""
    message = message.lower()

    # Stock related queries
    if any(word in message for word in ['stock', 'inventory', 'available']):
        return handle_stock_query(message)

    # Sales related queries
    elif any(word in message for word in ['sales', 'revenue', 'earnings']):
        return handle_sales_query(message)

    # Product related queries
    elif any(word in message for word in ['product', 'item', 'goods']):
        return handle_product_query(message)

    # Time related queries
    elif any(word in message for word in ['today', 'yesterday', 'week', 'month']):
        return handle_time_query(message)

    # Default response
    return "I can help you with stock levels, sales information, product details, and time-based reports. What would you like to know?"


def handle_stock_query(message):
    """Handle stock-related queries."""
    try:
        # Get low stock items
        low_stock_items = Product.query.filter(
            Product.stock_quantity <= Product.reorder_level).all()

        if 'low' in message or 'running' in message:
            if low_stock_items:
                response = "Here are items running low on stock:\n"
                for item in low_stock_items:
                    response += f"- {item.name}: {item.stock_quantity} units remaining\n"
                return response
            return "All items are well-stocked at the moment."

        # Get specific product stock
        for item in Product.query.all():
            if item.name.lower() in message:
                inventory = Inventory.query.filter_by(
                    shop_id=current_user.shop_id,
                    product_id=item.id
                ).first()
                return f"{item.name}:\n- Price: KES {item.marked_price:.2f}\n- Stock: {inventory.quantity} units\n- Category: {item.category}"

        return "I can help you check stock levels. Would you like to know about low stock items or check a specific product?"

    except Exception as e:
        current_app.logger.error(f"Stock Query Error: {str(e)}")
        return "I encountered an error while checking stock levels. Please try again."


def handle_sales_query(message):
    """Handle sales-related queries."""
    try:
        today = datetime.now().date()

        if 'today' in message:
            sales = Sale.query.filter(
                Sale.shop_id == current_user.shop_id,
                db.func.date(Sale.sale_date) == today
            ).all()
            total = sum(sale.price * sale.quantity for sale in sales)
            count = len(sales)
            return f"Today's sales: {count} transactions totaling KES {total:.2f}"

        elif 'yesterday' in message:
            yesterday = today - timedelta(days=1)
            sales = Sale.query.filter(
                Sale.shop_id == current_user.shop_id,
                db.func.date(Sale.sale_date) == yesterday
            ).all()
            total = sum(sale.price * sale.quantity for sale in sales)
            count = len(sales)
            return f"Yesterday's sales: {count} transactions totaling KES {total:.2f}"

        return "I can provide sales information for today or yesterday. Which would you like to know about?"

    except Exception as e:
        current_app.logger.error(f"Sales Query Error: {str(e)}")
        return "I encountered an error while checking sales data. Please try again."


def handle_product_query(message):
    """Handle product-related queries."""
    try:
        # Search for specific product
        for item in Product.query.join(Inventory).filter(
                Inventory.shop_id == current_user.shop_id).all():
            if item.name.lower() in message:
                inventory = Inventory.query.filter_by(
                    shop_id=current_user.shop_id,
                    product_id=item.id
                ).first()
                return f"{item.name}:\n- Price: KES {item.marked_price:.2f}\n- Stock: {inventory.quantity} units\n- Category: {item.category}"

        # Get top selling products
        if 'top' in message or 'best' in message:
            top_products = db.session.query(
                Product,
                db.func.count(
                    Sale.id).label('sale_count')).join(Sale).filter(
                Sale.shop_id == current_user.shop_id).group_by(
                Product.id).order_by(
                    db.desc('sale_count')).limit(5).all()

            if top_products:
                response = "Top selling products:\n"
                for product, count in top_products:
                    response += f"- {product.name}: {count} sales\n"
                return response

        return "I can help you find product information or show you top-selling items. What would you like to know?"

    except Exception as e:
        current_app.logger.error(f"Product Query Error: {str(e)}")
        return "I encountered an error while checking product information. Please try again."


def handle_time_query(message):
    """Handle time-based queries."""
    try:
        today = datetime.now().date()

        if 'today' in message:
            return "Today's date is " + today.strftime("%B %d, %Y")

        elif 'yesterday' in message:
            yesterday = today - timedelta(days=1)
            return "Yesterday was " + yesterday.strftime("%B %d, %Y")

        elif 'week' in message:
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            return f"This week is from {week_start.strftime('%B %d')} to {week_end.strftime('%B %d, %Y')}"

        elif 'month' in message:
            return "Current month is " + today.strftime("%B %Y")

        return "I can tell you about today, yesterday, this week, or this month. What would you like to know?"

    except Exception as e:
        current_app.logger.error(f"Time Query Error: {str(e)}")
        return "I encountered an error while processing the time query. Please try again."


def get_stock_status_insights():
    """Generate stock status insights."""
    try:
        low_stock_items = Inventory.query.filter(
            Inventory.shop_id == current_user.shop_id,
            Inventory.quantity < 10
        ).all()
        total_items = Inventory.query.filter_by(
            shop_id=current_user.shop_id).count()

        if low_stock_items:
            return f"{len(low_stock_items)} out of {total_items} items need restocking"
        return f"All {total_items} items are well-stocked"

    except Exception as e:
        current_app.logger.error(f"Stock Status Insights Error: {str(e)}")
        return "Unable to fetch stock status"


def get_today_performance_insights():
    """Generate today's performance insights."""
    try:
        today = datetime.now().date()
        sales = Sale.query.filter(
            Sale.shop_id == current_user.shop_id,
            db.func.date(Sale.sale_date) == today
        ).all()

        if sales:
            total = sum(sale.price * sale.quantity for sale in sales)
            count = len(sales)
            return f"{count} sales today totaling KES {total:.2f}"
        return "No sales recorded today"

    except Exception as e:
        current_app.logger.error(f"Performance Insights Error: {str(e)}")
        return "Unable to fetch performance data"


@employee_bp.route('/services')
@login_required
def services():
    try:
        # Get all active services for the current shop
        services = Service.query.filter_by(shop_id=current_user.shop_id, is_active=True).all()
        
        # Get all service categories
        categories = ServiceCategory.query.all()
        
        # Get all service sales for the current shop
        service_sales = ServiceSale.query.filter_by(shop_id=current_user.shop_id).order_by(ServiceSale.sale_date.desc()).all()
        
        # Get all employees for the current shop
        employees = User.query.filter_by(shop_id=current_user.shop_id, role='employee').all()
        
        return render_template('employee/services.html',
                             services=services,
                             categories=categories,
                             service_sales=service_sales,
                             employees=employees)
    except Exception as e:
        current_app.logger.error(f"Error in services route: {str(e)}")
        flash('An error occurred while loading services.', 'error')
        return redirect(url_for('employee.dashboard'))


@employee_bp.route('/services/record', methods=['POST'])
@login_required
def record_service_sale():
    try:
        # Get form data
        service_id = request.form.get('service_id')
        customer_name = request.form.get('customer_name')
        employee_id = request.form.get('employee_id')
        price = request.form.get('price', type=float)
        notes = request.form.get('notes')
        status = request.form.get('status', 'pending')
        payment_method = request.form.get('payment_method', 'cash')

        # Validate required fields
        if not all([service_id, customer_name, employee_id, price, payment_method]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('employee.services'))

        # Validate payment method
        valid_payment_methods = ['cash', 'till', 'bank']
        if payment_method not in valid_payment_methods:
            flash('Invalid payment method', 'error')
            return redirect(url_for('employee.services'))

        # Get service and validate it belongs to the shop
        service = Service.query.get_or_404(service_id)
        if service.shop_id != current_user.shop_id:
            flash('Invalid service selected.', 'error')
            return redirect(url_for('employee.services'))

        # Get employee and validate they belong to the shop
        employee = User.query.get_or_404(employee_id)
        if employee.shop_id != current_user.shop_id:
            flash('Invalid employee selected.', 'error')
            return redirect(url_for('employee.services'))

        # Create new service sale record
        service_sale = ServiceSale(
            service_id=service_id,
            customer_name=customer_name,
            price=price,
            notes=notes,
            employee_id=employee_id,
            shop_id=current_user.shop_id,
            sale_date=datetime.utcnow(),
            status=status,
            payment_method=payment_method
        )

        # Create financial record for the sale
        financial_record = FinancialRecord(
            shop_id=current_user.shop_id,
            type=payment_method,
            amount=price,
            description=f"Service sale: {service.name} for {customer_name}",
            created_by=current_user.id
        )

        db.session.add(service_sale)
        db.session.add(financial_record)
        db.session.commit()

        flash('Service sale recorded successfully!', 'success')
        return redirect(url_for('employee.services'))

    except Exception as e:
        current_app.logger.error(f"Error recording service sale: {str(e)}")
        db.session.rollback()
        flash('Error recording service sale. Please try again.', 'error')
        return redirect(url_for('employee.services'))


@employee_bp.route('/services/<int:sale_id>/update-status', methods=['POST'])
@login_required
def update_service_status(sale_id):
    try:
        data = request.get_json()
        new_status = data.get('status')

        if not new_status:
            return jsonify(
                {'success': False, 'message': 'Status is required'}), 400

        # Get the service sale
        service_sale = ServiceSale.query.get_or_404(sale_id)

        # Verify the service belongs to the employee's shop
        if service_sale.shop_id != current_user.shop_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        # Update the status
        service_sale.status = new_status
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Service status updated to {new_status}'
        })

    except Exception as e:
        logger.error(f"Error updating service status: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Error updating service status'
        }), 500


@employee_bp.route('/resources')
@login_required
def resources():
    try:
        # Get the shop associated with the current user
        shop = Shop.query.get(current_user.shop_id)
        if not shop:
            flash('No shop found for this user.', 'error')
            return redirect(url_for('employee.dashboard'))

        # Load all resources
        resources = Resource.query.all()
        if not resources:
            flash('No resources found.', 'warning')
            return render_template('employee/resources.html', 
                                resources=[], 
                                shop_resources={}, 
                                low_stock_resources=[])

        # Load shop resources with updater relationship
        shop_resources = {}
        for resource in resources:
            try:
                shop_resource = ShopResource.query.filter_by(
                    shop_id=shop.id,
                    resource_id=resource.id
                ).first()

                if shop_resource:
                    # Ensure updater relationship is loaded
                    if shop_resource.updated_by:
                        shop_resource.updater = User.query.get(shop_resource.updated_by)
                    shop_resources[resource.id] = shop_resource
                else:
                    # Create new shop resource entry
                    new_shop_resource = ShopResource(
                        shop_id=shop.id,
                        resource_id=resource.id,
                        quantity=0,
                        last_updated=datetime.utcnow(),
                        updated_by=current_user.id
                    )
                    new_shop_resource.updater = current_user
                    db.session.add(new_shop_resource)
                    shop_resources[resource.id] = new_shop_resource

            except Exception as e:
                current_app.logger.error(f"Error loading resource {resource.id}: {str(e)}")
                continue

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error committing shop resources: {str(e)}")
            flash('Error saving resource data. Please try again.', 'error')
            return redirect(url_for('employee.dashboard'))

        # Get low stock resources
        low_stock_resources = []
        for resource in resources:
            if resource.id in shop_resources:
                shop_resource = shop_resources[resource.id]
                if shop_resource.quantity <= resource.reorder_level:
                    low_stock_resources.append(resource)

        return render_template('employee/resources.html',
                            resources=resources,
                            shop_resources=shop_resources,
                            low_stock_resources=low_stock_resources)

    except Exception as e:
        current_app.logger.error(f"Error in resources route: {str(e)}")
        flash('An error occurred while loading resources.', 'error')
        return redirect(url_for('employee.dashboard'))


@employee_bp.route('/resources/update', methods=['POST'])
@login_required
def update_resource():
    try:
        resource_id = request.form.get('resource_id')
        new_quantity = float(request.form.get('quantity'))
        reason = request.form.get('reason')
        other_reason = request.form.get('other_reason')

        if not resource_id or new_quantity is None:
            return jsonify({'success': False, 'message': 'Missing required fields'})

        # Get the shop associated with the current user
        shop = Shop.query.get(current_user.shop_id)
        if not shop:
            return jsonify({'success': False, 'message': 'No shop found for this user'})

        # Get the resource
        resource = Resource.query.get(resource_id)
        if not resource:
            return jsonify({'success': False, 'message': 'Resource not found'})

        # Get or create shop resource
        shop_resource = ShopResource.query.filter_by(
            shop_id=shop.id,
            resource_id=resource.id
        ).first()

        if not shop_resource:
            shop_resource = ShopResource(
                shop_id=shop.id,
                resource_id=resource.id,
                quantity=0,
                last_updated=datetime.utcnow(),
                updated_by=current_user.id
            )
            db.session.add(shop_resource)

        # Store the old quantity for history
        old_quantity = shop_resource.quantity

        # Update the quantity
        shop_resource.quantity = new_quantity
        shop_resource.last_updated = datetime.utcnow()
        shop_resource.updated_by = current_user.id

        # Create history record
        history = ResourceHistory(
            shop_id=shop.id,
            resource_id=resource.id,
            previous_quantity=old_quantity,
            new_quantity=new_quantity,
            change_type='adjust',
            reason=other_reason if reason == 'other' else reason,
            updated_by=current_user.id
        )
        db.session.add(history)

        db.session.commit()
        current_app.logger.info(f"Successfully updated resource {resource_id}")

        return jsonify({
            'success': True,
            'message': 'Resource updated successfully',
            'resource': {
                'id': resource.id,
                'name': resource.name,
                'quantity': new_quantity,
                'last_updated': shop_resource.last_updated.strftime('%Y-%m-%d %H:%M'),
                'updated_by': current_user.name
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating resource: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@employee_bp.route('/resources/<int:resource_id>/history')
@login_required
def resource_history(resource_id):
    """View resource history."""
    try:
        current_app.logger.info(f"Loading history for resource {resource_id}")
        
        # Get the shop associated with the current user
        shop = Shop.query.get(current_user.shop_id)
        if not shop:
            current_app.logger.error(f"No shop found for user {current_user.id}")
            return jsonify({
                'success': False,
                'message': 'No shop found for this user.'
            }), 404

        # Get resource history for this shop
        history = ResourceHistory.query.filter_by(
            resource_id=resource_id,
            shop_id=shop.id
        ).order_by(ResourceHistory.updated_at.desc()).all()

        # Format history data
        history_data = []
        for record in history:
            updated_by_user = User.query.get(record.updated_by)
            history_data.append({
                'date': record.updated_at.strftime('%Y-%m-%d %H:%M'),
                'previous_quantity': record.previous_quantity,
                'new_quantity': record.new_quantity,
                'change': record.new_quantity - record.previous_quantity,
                'updated_by': updated_by_user.name if updated_by_user else 'Unknown',
                'reason': record.reason
            })

        current_app.logger.info(f"Successfully loaded {len(history_data)} history records")
        
        return jsonify({
            'success': True,
            'history': history_data
        })

    except Exception as e:
        current_app.logger.error(f"Error loading resource history: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Error loading resource history.'
        }), 500


@employee_bp.route('/resources/export')
@login_required
def export_resources():
    """Export resources data to Excel."""
    try:
        current_app.logger.info("Starting resource export")
        
        # Get the shop associated with the current user
        shop = Shop.query.get(current_user.shop_id)
        if not shop:
            current_app.logger.error(f"No shop found for user {current_user.id}")
            flash('No shop found for this user.', 'error')
            return redirect(url_for('employee.resources'))

        # Get all resources
        resources = Resource.query.all()
        
        # Create DataFrame
        data = []
        for resource in resources:
            shop_resource = ShopResource.query.filter_by(
                shop_id=shop.id,
                resource_id=resource.id
            ).first()
            
            row = {
                'Resource ID': resource.id,
                'Name': resource.name,
                'Category': resource.category,
                'Unit': resource.unit,
                'Reorder Level': resource.reorder_level,
                'Current Quantity': shop_resource.quantity if shop_resource else 0,
                'Last Updated': shop_resource.updated_at.strftime('%Y-%m-%d %H:%M') if shop_resource and shop_resource.updated_at else 'Never',
                'Updated By': User.query.get(shop_resource.updated_by).name if shop_resource and shop_resource.updated_by else 'N/A'
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Resources', index=False)
            
            # Auto-adjust columns width
            worksheet = writer.sheets['Resources']
            for i, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_length)
        
        output.seek(0)
        current_app.logger.info("Successfully exported resources data")
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'resources_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting resources: {str(e)}", exc_info=True)
        flash('Error exporting resources', 'error')
        return redirect(url_for('employee.resources'))


@employee_bp.route('/accounts')
@login_required
def accounts():
    try:
        # Get shop for the current user
        shop = Shop.query.get(current_user.shop_id)
        if not shop:
            flash('Shop not found', 'error')
            return redirect(url_for('employee.dashboard'))

        # Get today's date
        today = datetime.now().date()

        # Get today's financial records
        today_records = FinancialRecord.query.filter(
            FinancialRecord.shop_id == shop.id,
            func.date(FinancialRecord.date) == today
        ).all()

        # Get today's expenses
        today_expenses = Expense.query.filter(
            Expense.shop_id == shop.id,
            func.date(Expense.date) == today
        ).order_by(Expense.date.desc()).all()

        # Calculate today's totals
        totals = {
            'cash': 0,
            'till': 0,
            'bank': 0,
            'expenses': 0
        }

        # Process today's records
        for record in today_records:
            totals[record.type] += float(record.amount or 0)

        # Process today's expenses
        for expense in today_expenses:
            totals['expenses'] += float(expense.amount or 0)

        # Calculate grand total
        totals['grand_total'] = totals['cash'] + totals['till'] + totals['bank'] - totals['expenses']

        # Get historical data (last 30 days)
        start_date = today - timedelta(days=30)
        historical_records = FinancialRecord.query.filter(
            FinancialRecord.shop_id == shop.id,
            FinancialRecord.date >= start_date,
            FinancialRecord.date < today + timedelta(days=1)
        ).all()

        # Get historical expenses
        historical_expenses = Expense.query.filter(
            Expense.shop_id == shop.id,
            Expense.date >= start_date,
            Expense.date < today + timedelta(days=1)
        ).all()

        # Process historical data
        daily_data = {}
        for record in historical_records:
            record_date = record.date.date()
            if record_date not in daily_data:
                daily_data[record_date] = {
                    'date': record_date,
                    'cash': 0,
                    'till': 0,
                    'bank': 0,
                    'expenses': 0
                }
            daily_data[record_date][record.type] += float(record.amount or 0)

        # Process historical expenses
        for expense in historical_expenses:
            expense_date = expense.date.date()
            if expense_date in daily_data:
                daily_data[expense_date]['expenses'] += float(expense.amount or 0)

        # Calculate grand totals and convert to list
        historical_data = []
        for date in sorted(daily_data.keys(), reverse=True):
            data = daily_data[date]
            data['grand_total'] = data['cash'] + data['till'] + data['bank'] - data['expenses']
            data['date'] = date.strftime('%Y-%m-%d')  # Convert date to string
            historical_data.append(data)

        return render_template('employee/accounts.html',
                            totals=totals,
                            today_expenses=today_expenses,
                            historical_data=historical_data)

    except Exception as e:
        current_app.logger.error(f"Error in accounts page: {str(e)}", exc_info=True)
        flash('An error occurred while loading the accounts page', 'error')
        return redirect(url_for('employee.dashboard'))


@employee_bp.route('/accounts/data')
@login_required
def get_accounts_data():
    try:
        period = request.args.get('period', 'today')
        current_app.logger.info(f"Processing accounts data request for period: {period}")

        # Get shop for the current user
        shop = Shop.query.get(current_user.shop_id)
        if not shop:
            current_app.logger.error(f"No shop found for user {current_user.id}")
            return jsonify({
                'success': False,
                'message': 'Shop not found'
            }), 404

        # Get date range based on period
        today = datetime.now().date()
        try:
            if period == 'today':
                start_date = today
                end_date = today
            elif period == 'week':
                start_date = today - timedelta(days=today.weekday())
                end_date = today
            elif period == 'month':
                start_date = today.replace(day=1)
                end_date = today
            elif period == 'year':
                start_date = today.replace(month=1, day=1)
                end_date = today
            else:
                return jsonify({
                    'success': False,
                    'message': 'Invalid period'
                }), 400
        except Exception as e:
            current_app.logger.error(f"Error calculating date range: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Error calculating date range'
            }), 500

        current_app.logger.info(f"Date range: {start_date} to {end_date}")

        try:
            # Get sales data
            sales = Sale.query.filter(
                Sale.shop_id == shop.id,
                func.date(Sale.sale_date).between(start_date, end_date)
            ).all()
            current_app.logger.info(f"Found {len(sales)} sales records")

            # Get expenses data
            expenses = Expense.query.filter(
                Expense.shop_id == shop.id,
                func.date(Expense.date).between(start_date, end_date)
            ).order_by(Expense.date.desc()).all()
            current_app.logger.info(f"Found {len(expenses)} expense records")

            # Initialize summary
            summary = {
                'cash': 0.0,
                'till': 0.0,
                'bank': 0.0,
                'expenses': 0.0,
                'grand_total': 0.0
            }

            # Process sales
            for sale in sales:
                try:
                    sale_total = float(sale.price or 0) * \
                        float(sale.quantity or 0)
                    if sale.payment_method == 'cash':
                        summary['cash'] += sale_total
                    elif sale.payment_method == 'till':
                        summary['till'] += sale_total
                    elif sale.payment_method == 'bank':
                        summary['bank'] += sale_total
                except (ValueError, TypeError) as e:
                    current_app.logger.error(f"Error processing sale {sale.id}: {str(e)}")
                    continue

            # Process expenses
            for expense in expenses:
                try:
                    summary['expenses'] += float(expense.amount or 0)
                except (ValueError, TypeError) as e:
                    current_app.logger.error(f"Error processing expense {expense.id}: {str(e)}")
                    continue

            # Calculate grand total
            summary['grand_total'] = summary['cash'] + \
                summary['till'] + summary['bank'] - summary['expenses']
            current_app.logger.info(f"Calculated summary: {summary}")

            # Prepare accounts data
            accounts_data = []
            current_date = start_date
            while current_date <= end_date:
                try:
                    day_data = {
                        'date': current_date.strftime('%Y-%m-%d'),
                        'cash': 0.0,
                        'till': 0.0,
                        'bank': 0.0,
                        'expenses': 0.0,
                        'grand_total': 0.0
                    }

                    # Process day's sales
                    day_sales = [
                        s for s in sales if s.sale_date.date() == current_date]
                    for sale in day_sales:
                        try:
                            sale_total = float(
                                sale.price or 0) * float(sale.quantity or 0)
                            if sale.payment_method == 'cash':
                                day_data['cash'] += sale_total
                            elif sale.payment_method == 'till':
                                day_data['till'] += sale_total
                            elif sale.payment_method == 'bank':
                                day_data['bank'] += sale_total
                        except (ValueError, TypeError) as e:
                            current_app.logger.error(f"Error processing day sale {sale.id}: {str(e)}")
                            continue

                    # Process day's expenses
                    day_expenses = [
                        e for e in expenses if e.date.date() == current_date]
                    for expense in day_expenses:
                        try:
                            day_data['expenses'] += float(expense.amount or 0)
                        except (ValueError, TypeError) as e:
                            current_app.logger.error(f"Error processing day expense {expense.id}: {str(e)}")
                            continue

                    # Calculate day's grand total
                    day_data['grand_total'] = day_data['cash'] + \
                        day_data['till'] + day_data['bank'] - \
                        day_data['expenses']
                    accounts_data.append(day_data)
                except Exception as e:
                    current_app.logger.error(f"Error processing data for date {current_date}: {str(e)}")
                    continue

                current_date += timedelta(days=1)

            # Prepare expenses data
            expenses_data = []
            for expense in expenses:
                try:
                    expenses_data.append({
                        'id': expense.id,
                        'date': expense.date.strftime('%Y-%m-%d %H:%M'),
                        'category': expense.category,
                        'description': expense.description,
                        'amount': float(expense.amount or 0)
                    })
                except (ValueError, TypeError) as e:
                    current_app.logger.error(f"Error formatting expense {expense.id}: {str(e)}")
                    continue

            current_app.logger.info(f"Successfully processed {len(accounts_data)} days of data and {len(expenses_data)} expenses")

            return jsonify({
                'success': True,
                'summary': summary,
                'accounts': accounts_data,
                'expenses': expenses_data
            })

        except Exception as e:
            current_app.logger.error(f"Error processing financial data: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': f'Error processing financial data: {str(e)}'
            }), 500

    except Exception as e:
        current_app.logger.error(f"Error in get_accounts_data: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'An error occurred while fetching the data: {str(e)}'
        }), 500


@employee_bp.route('/expenses/add', methods=['POST'])
@login_required
def add_expense():
    try:
        data = request.get_json()
        current_app.logger.info(f"Adding new expense: {data}")

        # Validate input data
        if not all(key in data for key in ['category', 'description', 'amount']):
            current_app.logger.error("Missing required fields in request payload")
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400

        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                current_app.logger.error("Amount must be greater than 0")
                return jsonify({
                    'success': False,
                    'message': 'Amount must be greater than 0'
                }), 400
        except (ValueError, TypeError) as e:
            current_app.logger.error(f"Invalid amount value: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Invalid amount value'
            }), 400

        # Get shop for validation
        shop = Shop.query.get(current_user.shop_id)
        if not shop:
            current_app.logger.error(f"No shop found for user {current_user.id}")
            return jsonify({
                'success': False,
                'message': 'Shop not found'
            }), 404

        try:
            # Create new expense with proper data types
            new_expense = Expense(
                shop_id=current_user.shop_id,
                category=str(data['category']),
                description=str(data['description']),
                amount=amount,  # SQLAlchemy will handle the conversion to Numeric
                date=datetime.utcnow(),
                created_by=current_user.id
            )

            db.session.add(new_expense)
            db.session.commit()

            current_app.logger.info(f"Successfully added expense with ID {new_expense.id}")

            return jsonify({
                'success': True,
                'message': 'Expense added successfully',
                'expense': {
                    'id': new_expense.id,
                    'date': new_expense.date.strftime('%Y-%m-%d %H:%M'),
                    'category': new_expense.category,
                    'description': new_expense.description,
                    'amount': float(new_expense.amount)
                }
            })

        except Exception as e:
            current_app.logger.error(f"Database error while adding expense: {str(e)}", exc_info=True)
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Database error while adding expense: {str(e)}'
            }), 500

    except Exception as e:
        current_app.logger.error(f"Error adding expense: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'An error occurred while adding the expense: {str(e)}'
        }), 500


@employee_bp.route('/expenses/<int:id>/delete', methods=['DELETE'])
@login_required
def delete_expense(id):
    try:
        expense = Expense.query.get_or_404(id)

        # Verify the expense belongs to the current user's shop
        if expense.shop_id != current_user.shop_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403

        current_app.logger.info(f"Deleting expense {id}")

        db.session.delete(expense)
        db.session.commit()

        current_app.logger.info(f"Successfully deleted expense {id}")

        return jsonify({
            'success': True,
            'message': 'Expense deleted successfully'
        })

    except Exception as e:
        current_app.logger.error(f"Error deleting expense {id}: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred while deleting the expense'
        }), 500
