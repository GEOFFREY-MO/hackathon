from flask import Blueprint, render_template, flash, Response, redirect, url_for, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from database.models import Shop, Product, Inventory, User, db, Sale, Service, ServiceSale, Resource, ShopResource, Expense, ResourceHistory, ResourceAlert, ResourceCategory, ServiceCategory, FinancialRecord
from io import StringIO
import csv
from datetime import datetime, timedelta
import io
import logging
from sqlalchemy import text
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from functools import wraps
from decimal import Decimal
import json
from sqlalchemy import func
import xlsxwriter
from werkzeug.security import generate_password_hash

# Configure logging
logger = logging.getLogger(__name__)

# Define the admin blueprint
admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.admin_login'))
        if current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('auth.select_role'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/ai-assistant')
@login_required
@admin_required
def ai_assistant():
    """AI Assistant page for retail analytics"""
    return render_template('admin/ai_assistant.html')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    try:
        # Get shops owned by the current admin
        shops = Shop.query.filter_by(admin_id=current_user.id).all()
        
        # Initialize data structures
        shop_data = {}
        total_product_revenue = 0.0
        total_service_revenue = 0.0
        total_revenue = 0.0
        total_products = 0
        total_inventory = 0
        total_employees = 0
        total_sale_count = 0
        total_service_count = 0
        total_expenses = 0.0
        
        # Process each shop
        for shop in shops:
            try:
                # Get product sales data
                sales = Sale.query.filter_by(shop_id=shop.id).all()
                shop_product_revenue = sum(sale.total for sale in sales)
                total_sale_count += len(sales)

                # Get service sales data
                service_sales = ServiceSale.query.filter_by(shop_id=shop.id).all()
                shop_service_revenue = sum(ss.price for ss in service_sales)
                total_service_count += len(service_sales)
                
                # Get inventory data
                inventory_items = Inventory.query.filter_by(shop_id=shop.id).all()
                shop_inventory = sum(item.quantity for item in inventory_items)
                
                # Get employee count (only employees managed by this admin)
                employee_count = User.query.filter_by(
                    shop_id=shop.id, 
                    admin_id=current_user.id,
                    role='employee'
                ).count()
                
                # Expenses for this shop (all time)
                shop_expenses = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)).filter(Expense.shop_id == shop.id).scalar() or 0.0

                # Store shop data
                shop_data[shop.id] = {
                    'name': shop.name,
                    'product_revenue': float(shop_product_revenue),
                    'service_revenue': float(shop_service_revenue),
                    'revenue': float(shop_product_revenue + shop_service_revenue),
                    'inventory': shop_inventory,
                    'employees': employee_count,
                    'expenses': float(shop_expenses)
                }
                
                # Update totals
                total_product_revenue += float(shop_product_revenue)
                total_service_revenue += float(shop_service_revenue)
                total_revenue += float(shop_product_revenue + shop_service_revenue)
                total_inventory += shop_inventory
                total_employees += employee_count
                total_expenses += float(shop_expenses)
            except Exception as e:
                current_app.logger.error(f"Error processing shop {shop.id}: {str(e)}", exc_info=True)
                continue
        
        # Get total products across all shops
        shop_ids = [shop.id for shop in shops] or [-1]
        total_products = Product.query.filter(Product.shop_id.in_(shop_ids)).count()

        # Total shops/users (for header cards)
        total_shops = len(shops)
        active_shops = total_shops
        total_users = User.query.filter(User.admin_id == current_user.id).count()
        active_users = total_users

        # Low stock count across shops
        low_stock_count = (
            db.session.query(Inventory)
            .join(Product, Product.id == Inventory.product_id)
            .filter(Inventory.shop_id.in_(shop_ids))
            .filter(Inventory.quantity < Product.reorder_level)
            .count()
        )

        # Recent products with total stock
        recent_products = (
            Product.query.filter(Product.shop_id.in_(shop_ids))
            .order_by(Product.created_at.desc())
            .limit(5)
            .all()
        )
        for p in recent_products:
            qty = (
                db.session.query(func.coalesce(func.sum(Inventory.quantity), 0))
                .filter(Inventory.product_id == p.id)
                .filter(Inventory.shop_id.in_(shop_ids))
            ).scalar() or 0
            setattr(p, 'total_stock', int(qty))

        # Low stock products list
        low_stock_products = (
            db.session.query(Product)
            .join(Inventory, Inventory.product_id == Product.id)
            .filter(Product.shop_id.in_(shop_ids))
            .filter(Inventory.quantity < Product.reorder_level)
            .group_by(Product.id)
            .limit(10)
            .all()
        )
        for p in low_stock_products:
            qty = (
                db.session.query(func.coalesce(func.sum(Inventory.quantity), 0))
                .filter(Inventory.product_id == p.id)
                .filter(Inventory.shop_id.in_(shop_ids))
            ).scalar() or 0
            setattr(p, 'total_stock', int(qty))
        
        # Get recent product sales for all shops
        recent_sales = Sale.query.filter(
            Sale.shop_id.in_(shop_ids)
        ).order_by(Sale.sale_date.desc()).limit(5).all()

        # Get recent service sales for all shops
        recent_service_sales = ServiceSale.query.filter(
            ServiceSale.shop_id.in_(shop_ids)
        ).order_by(ServiceSale.sale_date.desc()).limit(5).all()

        # Active services and service categories summary
        active_services = Service.query.filter(Service.shop_id.in_(shop_ids), Service.is_active == True).all()
        service_categories = (
            db.session.query(ServiceCategory, func.count(Service.id))
            .join(Service, Service.category_id == ServiceCategory.id)
            .filter(Service.shop_id.in_(shop_ids))
            .group_by(ServiceCategory.id)
            .all()
        )

        # Augment shops with totals for the overview card
        for s in shops:
            s.total_products = Product.query.filter_by(shop_id=s.id).count()
            s.total_quantity = (
                db.session.query(func.coalesce(func.sum(Inventory.quantity), 0))
                .filter(Inventory.shop_id == s.id)
            ).scalar() or 0
            s.low_stock = (
                db.session.query(Inventory)
                .join(Product, Product.id == Inventory.product_id)
                .filter(Inventory.shop_id == s.id)
                .filter(Inventory.quantity < Product.reorder_level)
            ).all()
        
        # Derived metrics expected by template
        total_transactions = total_sale_count + total_service_count
        average_sale = float(total_revenue) / total_transactions if total_transactions > 0 else 0.0

        return render_template('admin/dashboard.html',
                             shops=shops,
                             shop_data=shop_data,
                             total_product_revenue=total_product_revenue,
                             total_service_revenue=total_service_revenue,
                             total_revenue=total_revenue,
                             total_sales=total_revenue,
                             total_products=total_products,
                             total_inventory=total_inventory,
                             total_employees=total_employees,
                             total_sale_count=total_sale_count,
                             total_service_count=total_service_count,
                             total_transactions=total_transactions,
                             average_sale=average_sale,
                             total_expenses=total_expenses,
                             recent_sales=recent_sales,
                             recent_service_sales=recent_service_sales,
                             total_shops=total_shops,
                             active_shops=active_shops,
                             total_users=total_users,
                             active_users=active_users,
                             low_stock_count=low_stock_count,
                             recent_products=recent_products,
                             low_stock_products=low_stock_products,
                             active_services=active_services,
                             service_categories=service_categories)
    except Exception as e:
        current_app.logger.error(f"Error in dashboard: {str(e)}", exc_info=True)
        flash('An error occurred while loading the dashboard.', 'error')
        return redirect(url_for('auth.select_role'))


@admin_bp.route('/api/my-shops')
@login_required
@admin_required
def api_my_shops():
    """Return shops owned by current admin as JSON for selectors."""
    try:
        shops = Shop.query.filter_by(admin_id=current_user.id).all()
        return jsonify([
            { 'id': s.id, 'name': s.name, 'location': s.location }
            for s in shops
        ])
    except Exception as e:
        current_app.logger.error(f"Error fetching admin shops: {str(e)}", exc_info=True)
        return jsonify({ 'error': 'Failed to load shops' }), 500


@admin_bp.route('/dashboard/recent-sales')
@login_required
@admin_required
def get_recent_sales():
    """Get recent sales data for the dashboard."""
    try:
        period = request.args.get('period', 'today')
        logger.info(f"Fetching recent sales for period: {period}")

        # Calculate date range based on period
        end_date = datetime.utcnow()
        if period == 'today':
            start_date = end_date.replace(
                hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = end_date.replace(
                hour=0, minute=0, second=0, microsecond=0)

        # Get recent sales with eager loading
        sales = (
            Sale.query
            .join(Shop)
            .join(Product)
            .filter(Sale.sale_date >= start_date)
            .filter(Sale.sale_date <= end_date)
            .order_by(Sale.sale_date.desc())
            .limit(20)
            .all()
        )

        # Format sales data for response
        sales_data = [{
            'sale_date': sale.sale_date.strftime('%Y-%m-%d %H:%M'),
            'shop_name': sale.shop.name,
            'product_name': sale.product.name,
            'quantity': sale.quantity,
            'total': float(sale.product.marked_price * sale.quantity)
        } for sale in sales]

        logger.info(f"Found {len(sales_data)} recent sales")

        return jsonify({
            'success': True,
            'sales': sales_data
        })

    except Exception as e:
        logger.error(f"Error fetching recent sales: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error loading recent sales data'
        }), 500


@admin_bp.route('/export')
@login_required
def export_data():
    """Export inventory data to CSV."""
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.select_role'))

    try:
        # Create a StringIO object to store the CSV data
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Shop', 'Product', 'Barcode', 'Category',
                        'Marked Price', 'Quantity', 'Last Updated'])

        # Get all inventory data
        inventory_data = (
            db.session.query(Shop, Product, Inventory)
            .join(Product, Inventory.product_id == Product.id)
            .join(Shop, Inventory.shop_id == Shop.id)
            .all()
        )

        # Write data rows
        for shop, product, inventory in inventory_data:
            writer.writerow([
                shop.name,
                product.name,
                product.barcode,
                product.category,
                product.marked_price,
                inventory.quantity,
                inventory.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            ])

        # Create the response
        output.seek(0)
        return send_file(
            io.BytesIO(
                output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'inventory_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    except Exception as e:
        flash('Error exporting data.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/shops')
@login_required
@admin_required
def manage_shops():
    """Manage shops - view, add, edit, delete shops."""
    # Get only shops owned by the current admin
    shops = Shop.query.filter_by(admin_id=current_user.id).all()
    return render_template('admin/shops.html', shops=shops)


@admin_bp.route('/shops/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_shop():
    """Add a new shop."""
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            location = request.form.get('location')
            contact = request.form.get('contact')
            email = request.form.get('email')

            if not name or not location:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Name and location are required.'}), 400
                flash('Name and location are required.', 'danger')
                return redirect(url_for('admin.manage_shops'))

            # Check if shop name already exists for this admin
            if Shop.query.filter_by(name=name, admin_id=current_user.id).first():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'A shop with this name already exists.'}), 400
                flash('A shop with this name already exists.', 'danger')
                return redirect(url_for('admin.manage_shops'))

            shop = Shop(
                name=name,
                location=location,
                contact=contact,
                email=email,
                admin_id=current_user.id
            )
            db.session.add(shop)
            db.session.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Shop added successfully!'})

            flash('Shop added successfully!', 'success')
            return redirect(url_for('admin.manage_shops'))
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Error adding shop.'}), 500
            flash('Error adding shop.', 'danger')

    return render_template('admin/add_shop.html')


@admin_bp.route('/shops/<int:shop_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_shop(shop_id):
    """Edit an existing shop."""
    # Get shop and verify ownership
    shop = Shop.query.filter_by(id=shop_id, admin_id=current_user.id).first_or_404()

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            location = request.form.get('location')
            contact = request.form.get('contact')
            email = request.form.get('email')

            if not name or not location:
                flash('Name and location are required.', 'danger')
                return redirect(url_for('admin.edit_shop', shop_id=shop_id))

            # Check if shop name already exists for this admin (excluding current shop)
            existing_shop = Shop.query.filter(
                Shop.name == name,
                Shop.admin_id == current_user.id,
                Shop.id != shop_id
            ).first()
            if existing_shop:
                flash('A shop with this name already exists.', 'danger')
                return redirect(url_for('admin.edit_shop', shop_id=shop_id))

            shop.name = name
            shop.location = location
            shop.contact = contact
            shop.email = email
            db.session.commit()

            flash('Shop updated successfully!', 'success')
            return redirect(url_for('admin.manage_shops'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating shop.', 'danger')

    return render_template('admin/edit_shop.html', shop=shop)


@admin_bp.route('/shops/<int:shop_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_shop(shop_id):
    """Delete a shop."""
    # Get shop and verify ownership
    shop = Shop.query.filter_by(id=shop_id, admin_id=current_user.id).first_or_404()

    try:
        # Check if shop has any employees
        if User.query.filter_by(shop_id=shop_id).first():
            flash('Cannot delete shop with associated employees.', 'danger')
            return redirect(url_for('admin.manage_shops'))

        # Check if shop has any inventory
        if Inventory.query.filter_by(shop_id=shop_id).first():
            flash('Cannot delete shop with inventory items.', 'danger')
            return redirect(url_for('admin.manage_shops'))

        db.session.delete(shop)
        db.session.commit()

        flash('Shop deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting shop.', 'danger')

    return redirect(url_for('admin.manage_shops'))


@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """Manage users - view, add, edit, delete users."""
    # Get only employees managed by this admin
    users = User.query.filter_by(admin_id=current_user.id).all()
    # Get only shops owned by this admin
    shops = Shop.query.filter_by(admin_id=current_user.id).all()
    return render_template('admin/users.html', users=users, shops=shops)


@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    """Add a new user (employee)."""
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            shop_id = request.form.get('shop_id')

            # Validate required fields
            if not all([name, email, password, shop_id]):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'All fields are required.'}), 400
                flash('All fields are required.', 'danger')
                return redirect(url_for('admin.add_user'))

            # Check if email already exists
            if User.query.filter_by(email=email).first():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Email already registered.'}), 400
                flash('Email already registered.', 'danger')
                return redirect(url_for('admin.add_user'))

            # Verify shop belongs to this admin
            shop = Shop.query.filter_by(id=shop_id, admin_id=current_user.id).first()
            if not shop:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Invalid shop selection.'}), 400
                flash('Invalid shop selection.', 'danger')
                return redirect(url_for('admin.add_user'))

            # Create new employee
            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role='employee',
                shop_id=shop_id,
                admin_id=current_user.id
            )
            db.session.add(user)
            db.session.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Employee added successfully!'})

            flash('Employee added successfully!', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Error adding employee.'}), 500
            flash('Error adding employee.', 'danger')

    # Get only shops owned by this admin
    shops = Shop.query.filter_by(admin_id=current_user.id).all()
    return render_template('admin/add_user.html', shops=shops)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit an existing user."""
    # Get user and verify they are managed by this admin
    user = User.query.filter_by(id=user_id, admin_id=current_user.id).first_or_404()
    # Get only shops owned by this admin
    shops = Shop.query.filter_by(admin_id=current_user.id).all()
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            shop_id = request.form.get('shop_id')
            is_active = request.form.get('is_active') == 'true'
            
            # Validate required fields
            if not all([name, email, shop_id]):
                return jsonify({
                    'success': False,
                    'message': 'Name, email, and shop are required'
                }), 400
            
            # Check if email is already taken by another user
            existing_user = User.query.filter(
                User.email == email,
                User.id != user_id,
                User.admin_id == current_user.id
            ).first()
            if existing_user:
                return jsonify({
                    'success': False,
                    'message': 'Email is already taken by another employee'
                }), 400
            
            # Verify shop belongs to this admin
            shop = Shop.query.filter_by(id=shop_id, admin_id=current_user.id).first()
            if not shop:
                return jsonify({
                    'success': False,
                    'message': 'Invalid shop selection'
                }), 400
            
            # Update user
            user.name = name
            user.email = email
            user.shop_id = shop_id
            user.is_active = is_active
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Employee updated successfully'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error updating employee: {str(e)}'
            }), 500

    return render_template('admin/edit_user.html', user=user, shops=shops)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    # Get user and verify they are managed by this admin
    user = User.query.filter_by(id=user_id, admin_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting user.', 'danger')
    
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/sales-report')
@login_required
def sales_report():
    """Show sales report for all shops."""
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.select_role'))

    try:
        # Get period filter and shop selection
        period = request.args.get('period', 'today')
        selected_shop_id = request.args.get('shop_id', type=int)

        # Get all shops for the filter dropdown
        shops = Shop.query.all()

        # Calculate date range based on period
        end_date = datetime.now()
        if period == 'today':
            start_date = end_date.replace(
                hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Base query with eager loading
        query = Sale.query.join(Shop).join(Product).options(
            db.joinedload(Sale.shop),
            db.joinedload(Sale.product)
        )

        # Apply date filter
        query = query.filter(
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date)

        # Apply shop filter
        if selected_shop_id:
            query = query.filter(Sale.shop_id == selected_shop_id)

        # Get sales data
        sales = query.order_by(Sale.sale_date.desc()).all()

        # Calculate summary statistics
        total_sales = sum(sale.quantity * sale.price for sale in sales)
        total_items = sum(sale.quantity for sale in sales)
        total_transactions = len(sales)
        average_sale = total_sales / total_transactions if total_transactions > 0 else 0

        # Get recent sales (last 20)
        recent_sales = query.order_by(Sale.sale_date.desc()).limit(20).all()

        return render_template('admin/sales_report.html',
                               sales=sales,
                               recent_sales=recent_sales,
                               total_sales=total_sales,
                               total_items=total_items,
                               total_transactions=total_transactions,
                               average_sale=average_sale,
                               shops=shops,
                               period=period,
                               selected_shop_id=selected_shop_id)
    except Exception as e:
        logger.error(f"Error in sales report: {str(e)}")
        flash('Error loading sales report.', 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/sales-report/filter')
@login_required
def filter_sales():
    """Filter sales data based on provided parameters."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        shop_id = request.args.get('shop_id', type=int)
        period = request.args.get('period', 'all')
        sort_by = request.args.get('sort_by', 'date_desc')

        logger.info(
            f"Filtering sales with params: start_date={start_date}, end_date={end_date}, shop_id={shop_id}, period={period}, sort_by={sort_by}")

        # Base query with eager loading
        query = Sale.query.join(Shop).join(Product).options(
            db.joinedload(Sale.shop),
            db.joinedload(Sale.product)
        )

        # Apply date filters
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(
                    end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Sale.sale_date.between(start, end))
            except ValueError as e:
                logger.error(f"Invalid date format: {str(e)}")
                return jsonify(
                    {'success': False, 'message': 'Invalid date format'}), 400
        elif period != 'all':
            now = datetime.utcnow()
            if period == 'today':
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(Sale.sale_date >= start)
            elif period == 'week':
                start = now - timedelta(days=7)
                query = query.filter(Sale.sale_date >= start)
            elif period == 'month':
                start = now - timedelta(days=30)
                query = query.filter(Sale.sale_date >= start)
            elif period == 'year':
                start = now.replace(
                    month=1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0)
                query = query.filter(Sale.sale_date >= start)

        # Apply shop filter
        if shop_id:
            shop = Shop.query.get(shop_id)
            if not shop:
                return jsonify(
                    {'success': False, 'message': 'Invalid shop ID'}), 400
            query = query.filter(Sale.shop_id == shop_id)

        # Apply sorting
        if sort_by == 'date_desc':
            query = query.order_by(Sale.sale_date.desc())
        elif sort_by == 'date_asc':
            query = query.order_by(Sale.sale_date.asc())
        elif sort_by == 'amount_desc':
            query = query.order_by((Sale.price * Sale.quantity).desc())
        elif sort_by == 'amount_asc':
            query = query.order_by((Sale.price * Sale.quantity).asc())

        # Get filtered sales
        try:
            sales = query.all()
        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            return jsonify(
                {'success': False, 'message': 'Error retrieving sales data'}), 500

        # Calculate summary statistics
        total_sales = sum(sale.quantity * sale.price for sale in sales)
        total_items = sum(sale.quantity for sale in sales)
        total_transactions = len(sales)
        average_sale = total_sales / total_transactions if total_transactions > 0 else 0

        # Prepare sales data for response
        sales_data = [{
            'id': sale.id,
            'sale_date': sale.sale_date.strftime('%Y-%m-%d %H:%M'),
            'shop_name': sale.shop.name,
            'product_name': sale.product.name,
            'quantity': sale.quantity,
            'price': float(sale.price),
            'total': float(sale.price * sale.quantity)
        } for sale in sales]

        logger.info(f"Filtered {len(sales_data)} sales records")

        return jsonify({
            'success': True,
            'sales': sales_data,
            'summary': {
                'total_sales': float(total_sales),
                'total_items': total_items,
                'total_transactions': total_transactions,
                'average_sale': float(average_sale)
            }
        })
    except Exception as e:
        logger.error(f"Error in filter_sales: {str(e)}")
        return jsonify(
            {'success': False, 'message': 'An error occurred while filtering sales'}), 500


@admin_bp.route('/sales-report/export/<format>')
@login_required
@admin_required
def export_sales(format):
    """Export sales data in the specified format."""
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        shop_id = request.args.get('shop_id', type=int)
        period = request.args.get('period', 'all')
        sort_by = request.args.get('sort_by', 'date_desc')

        logger.info(
            f"Exporting sales with params: format={format}, start_date={start_date}, end_date={end_date}, shop_id={shop_id}, period={period}")

        # Base query with eager loading
        query = Sale.query.join(Shop).join(Product).options(
            db.joinedload(Sale.shop),
            db.joinedload(Sale.product)
        )

        # Apply date filters
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(
                    end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Sale.sale_date.between(start, end))
            except ValueError as e:
                logger.error(f"Invalid date format: {str(e)}")
                return jsonify(
                    {'success': False, 'message': 'Invalid date format'}), 400
        elif period != 'all':
            now = datetime.utcnow()
            if period == 'today':
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(Sale.sale_date >= start)
            elif period == 'week':
                start = now - timedelta(days=7)
                query = query.filter(Sale.sale_date >= start)
            elif period == 'month':
                start = now - timedelta(days=30)
                query = query.filter(Sale.sale_date >= start)
            elif period == 'year':
                start = now.replace(
                    month=1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0)
                query = query.filter(Sale.sale_date >= start)

        # Apply shop filter
        if shop_id:
            shop = Shop.query.get(shop_id)
            if not shop:
                return jsonify(
                    {'success': False, 'message': 'Invalid shop ID'}), 400
            query = query.filter(Sale.shop_id == shop_id)

        # Apply sorting
        if sort_by == 'date_desc':
            query = query.order_by(Sale.sale_date.desc())
        elif sort_by == 'date_asc':
            query = query.order_by(Sale.sale_date.asc())
        elif sort_by == 'amount_desc':
            query = query.order_by((Sale.price * Sale.quantity).desc())
        elif sort_by == 'amount_asc':
            query = query.order_by((Sale.price * Sale.quantity).asc())

        # Get filtered sales
        sales = query.all()

        if not sales:
            return jsonify(
                {'success': False, 'message': 'No data to export'}), 404

        # Prepare data for export
        data = [{
            'Date': sale.sale_date.strftime('%Y-%m-%d %H:%M'),
            'Shop': sale.shop.name,
            'Product': sale.product.name,
            'Quantity': sale.quantity,
            'Price': float(sale.price),
            'Total': float(sale.price * sale.quantity)
        } for sale in sales]

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'sales_report_{timestamp}'

        # Export based on format
        if format == 'csv':
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}.csv',
                    'Content-Type': 'text/csv'})
        elif format == 'excel':
            df = pd.DataFrame(data)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Sales Report', index=False)
                worksheet = writer.sheets['Sales Report']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(), len(col)) + 2
                    worksheet.set_column(idx, idx, max_length)

            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}.xlsx',
                    'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                }
            )
        elif format == 'pdf':
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
            elements = []

            styles = getSampleStyleSheet()
            elements.append(Paragraph('Sales Report', styles['Title']))

            date_text = f"Period: {start_date} to {end_date}" if start_date and end_date else f"Period: {period}"
            elements.append(Paragraph(date_text, styles['Normal']))
            elements.append(Spacer(1, 20))

            table_data = [list(data[0].keys())]
            table_data.extend([list(row.values()) for row in data])
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [colors.white, colors.lightgrey])
            ]))
            elements.append(table)

            elements.append(Spacer(1, 20))
            total_sales = sum(row['Total'] for row in data)
            total_items = sum(row['Quantity'] for row in data)
            elements.append(
                Paragraph(
                    f"Total Sales: KES {total_sales:.2f}",
                    styles['Normal']))
            elements.append(
                Paragraph(
                    f"Total Items: {total_items}",
                    styles['Normal']))

            doc.build(elements)
            buffer.seek(0)

            return Response(
                buffer.getvalue(),
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}.pdf',
                    'Content-Type': 'application/pdf'})
        else:
            return jsonify(
                {'success': False, 'message': 'Invalid export format'}), 400

    except Exception as e:
        logger.error(f"Error exporting sales: {str(e)}")
        return jsonify(
            {'success': False, 'message': 'Error exporting sales data'}), 500


@admin_bp.route('/analytics')
@login_required
def analytics():
    """Show analytics dashboard with advanced data visualizations."""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('auth.select_role'))

    return render_template('admin/analytics.html')


@admin_bp.route('/analytics/data')
@login_required
def analytics_data():
    """Provide analytics data for the dashboard charts."""
    if current_user.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    try:
        period = request.args.get('period', 'week')

        # Calculate date range based on period
        end_date = datetime.utcnow()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
            date_format = '%Y-%m-%d'
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
            date_format = '%Y-%m-%d'
        else:  # year
            start_date = end_date.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            date_format = '%Y-%m'

        # Get sales data for the period
        sales = Sale.query.filter(
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).all()

        # Prepare data for charts
        data = {
            'sales_trend': get_sales_trend(
                sales,
                start_date,
                end_date,
                date_format),
            'shop_performance': get_shop_performance(sales),
            'top_products': get_top_products(sales),
            'category_distribution': get_category_distribution(sales),
            'hourly_distribution': get_hourly_distribution(sales),
            'stock_levels': get_stock_levels(),
            'reorder_trend': get_reorder_trend(
                start_date,
                end_date,
                date_format)}

        return jsonify(data)
    except Exception as e:
        logger.error(f"Error generating analytics data: {str(e)}")
        return jsonify({"error": "Failed to generate analytics data"}), 500


def get_sales_trend(sales, start_date, end_date, date_format):
    """Generate sales trend data for the line chart."""
    # Group sales by date
    sales_by_date = {}
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime(date_format)
        sales_by_date[date_str] = 0
        if date_format == '%Y-%m-%d':
            current_date += timedelta(days=1)
        else:
            current_date = (
                current_date.replace(
                    day=1) +
                timedelta(
                    days=32)).replace(
                day=1)

    # Calculate daily sales
    for sale in sales:
        date_str = sale.sale_date.strftime(date_format)
        sales_by_date[date_str] += sale.quantity * sale.price

    return {
        'labels': list(sales_by_date.keys()),
        'data': list(sales_by_date.values())
    }


def get_shop_performance(sales):
    """Generate shop performance data for the bar chart."""
    # Group sales by shop
    sales_by_shop = {}
    for sale in sales:
        shop_name = sale.shop.name
        if shop_name not in sales_by_shop:
            sales_by_shop[shop_name] = 0
        sales_by_shop[shop_name] += sale.quantity * sale.price

    return {
        'labels': list(sales_by_shop.keys()),
        'data': list(sales_by_shop.values())
    }


def get_top_products(sales):
    """Generate top products data for the doughnut chart."""
    # Group sales by product
    sales_by_product = {}
    for sale in sales:
        product_name = sale.product.name
        if product_name not in sales_by_product:
            sales_by_product[product_name] = 0
        sales_by_product[product_name] += sale.quantity * sale.price

    # Sort by sales and get top 5
    top_products = sorted(
        sales_by_product.items(),
        key=lambda x: x[1],
        reverse=True)[
        :5]

    return {
        'labels': [p[0] for p in top_products],
        'data': [p[1] for p in top_products]
    }


def get_category_distribution(sales):
    """Generate category distribution data for the pie chart."""
    # Group sales by category
    sales_by_category = {}
    for sale in sales:
        category = sale.product.category
        if category not in sales_by_category:
            sales_by_category[category] = 0
        sales_by_category[category] += sale.quantity * sale.price

    return {
        'labels': list(sales_by_category.keys()),
        'data': list(sales_by_category.values())
    }


def get_hourly_distribution(sales):
    """Generate hourly sales distribution data for the bar chart."""
    # Initialize hourly sales
    hourly_sales = {hour: 0 for hour in range(24)}

    # Calculate sales for each hour
    for sale in sales:
        hour = sale.sale_date.hour
        hourly_sales[hour] += sale.quantity * sale.price

    return {
        'labels': [f"{hour:02d}:00" for hour in range(24)],
        'data': [hourly_sales[hour] for hour in range(24)]
    }


def get_stock_levels():
    """Generate stock level data for the bar chart."""
    # Get all products with their current stock levels
    products = Product.query.all()

    return {
        'labels': [p.name for p in products],
        'current': [p.inventory[0].quantity if p.inventory else 0 for p in products],
        # Assuming reorder level is 5 for all products
        'reorder': [5 for _ in products]
    }


def get_reorder_trend(start_date, end_date, date_format):
    """Generate reorder trend data for the line chart."""
    # Get all inventory updates for the period
    inventory_updates = (
        db.session.query(Inventory)
        .filter(Inventory.updated_at >= start_date)
        .filter(Inventory.updated_at <= end_date)
        .order_by(Inventory.updated_at)
        .all()
    )

    # Group updates by date
    updates_by_date = {}
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime(date_format)
        updates_by_date[date_str] = 0
        if date_format == '%Y-%m-%d':
            current_date += timedelta(days=1)
        else:
            current_date = (
                current_date.replace(
                    day=1) +
                timedelta(
                    days=32)).replace(
                day=1)

    # Count updates per date
    for update in inventory_updates:
        date_str = update.updated_at.strftime(date_format)
        updates_by_date[date_str] += 1

    return {
        'labels': list(updates_by_date.keys()),
        'data': list(updates_by_date.values())
    }


@admin_bp.route('/services')
@login_required
@admin_required
def manage_services():
    """Manage services - view, add, edit, delete services."""
    if current_user.role != 'admin':
        return redirect(url_for('auth.select_role'))

    # Get services with their categories and shops
    services = db.session.query(
        Service.id,
        Service.name,
        Service.description,
        Service.price,
        Service.duration,
        Service.is_active,
        Service.shop_id,
        ServiceCategory.name.label('category_name'),
        Shop.name.label('shop_name')
    ).join(
        ServiceCategory,
        Service.category_id == ServiceCategory.id
    ).join(
        Shop,
        Service.shop_id == Shop.id
    ).all()

    # Get service sales history
    service_sales = ServiceSale.query.order_by(
        ServiceSale.sale_date.desc()).all()

    # Get all service categories
    categories = ServiceCategory.query.all()

    shops = Shop.query.all()
    return render_template(
        'admin/services.html',
        services=services,
        shops=shops,
        service_sales=service_sales,
        categories=categories)

@admin_bp.route('/services/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_service_categories():
    """Manage service categories."""
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            
            if not name:
                flash('Category name is required.', 'danger')
                return redirect(url_for('admin.manage_service_categories'))
            
            category = ServiceCategory(
                name=name,
                description=description
            )
            db.session.add(category)
            db.session.commit()
            
            flash('Category added successfully!', 'success')
            return redirect(url_for('admin.manage_service_categories'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding category.', 'danger')
    
    categories = ServiceCategory.query.all()
    return render_template('admin/service_categories.html', categories=categories)

@admin_bp.route('/services/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_service_category(category_id):
    """Delete a service category."""
    try:
        category = ServiceCategory.query.get_or_404(category_id)
        
        # Check if category is in use
        if Service.query.filter_by(category=category.name).first():
            return jsonify({
                'success': False,
                'message': 'Cannot delete category: It is being used by one or more services'
            }), 400
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting category: {str(e)}'
        }), 500

@admin_bp.route('/services/add', methods=['GET', 'POST'])
@login_required
def add_service():
    """Add a new service."""
    if current_user.role != 'admin':
        return redirect(url_for('auth.select_role'))

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            price = request.form.get('price')
            duration = request.form.get('duration')
            category_id = request.form.get('category_id')
            shop_id = request.form.get('shop_id')
            apply_to_all_shops = request.form.get('apply_to_all_shops') == 'on'

            if not all([name, price, category_id]):
                flash('Name, price, and category are required.', 'danger')
                return redirect(url_for('admin.manage_services'))

            if not apply_to_all_shops and not shop_id:
                flash('Please select a shop or apply to all shops.', 'danger')
                return redirect(url_for('admin.manage_services'))

            if apply_to_all_shops:
                # Get all shops
                shops = Shop.query.all()
                for shop in shops:
                    service = Service(
                        name=name,
                        description=description,
                        price=float(price),
                        duration=int(duration) if duration else None,
                        category_id=category_id,
                        shop_id=shop.id
                    )
                    db.session.add(service)
            else:
                service = Service(
                    name=name,
                    description=description,
                    price=float(price),
                    duration=int(duration) if duration else None,
                    category_id=category_id,
                    shop_id=shop_id
                )
                db.session.add(service)

            db.session.commit()

            flash('Service(s) added successfully!', 'success')
            return redirect(url_for('admin.manage_services'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding service.', 'danger')

    shops = Shop.query.all()
    categories = ServiceCategory.query.all()
    return render_template('admin/add_service.html', shops=shops, categories=categories)


@admin_bp.route('/services/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_service(service_id):
    """Edit an existing service."""
    if current_user.role != 'admin':
        return redirect(url_for('auth.select_role'))

    service = Service.query.get_or_404(service_id)

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            price = request.form.get('price')
            duration = request.form.get('duration')
            category_id = request.form.get('category_id')
            shop_id = request.form.get('shop_id')
            is_active = request.form.get('is_active') == 'on'

            if not all([name, price, category_id, shop_id]):
                flash('Name, price, category, and shop are required.', 'danger')
                return redirect(
                    url_for(
                        'admin.edit_service',
                        service_id=service_id))

            service.name = name
            service.description = description
            service.price = float(price)
            service.duration = int(duration) if duration else None
            service.category_id = category_id
            service.shop_id = shop_id
            service.is_active = is_active

            db.session.commit()

            flash('Service updated successfully!', 'success')
            return redirect(url_for('admin.manage_services'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating service.', 'danger')

    shops = Shop.query.all()
    categories = ServiceCategory.query.all()
    return render_template(
        'admin/edit_service.html',
        service=service,
        shops=shops,
        categories=categories)


@admin_bp.route('/services/<int:service_id>/delete', methods=['POST'])
@login_required
def delete_service(service_id):
    """Delete a service."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    try:
        service = Service.query.get_or_404(service_id)

        # Check if service has any sales
        if ServiceSale.query.filter_by(service_id=service_id).first():
            return jsonify({
                'success': False,
                'message': 'Cannot delete service: There are sales associated with this service'
            }), 400

        db.session.delete(service)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Service deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting service: {str(e)}'
        }), 500


@admin_bp.route('/resources')
@login_required
def manage_resources():
    """Resource management page with detailed error reporting"""
    resources = []
    shops = []
    shop_resources = {}
    low_stock_resources = []
    categories = []
    alerts = []
    errors = []
    try:
        current_app.logger.info("Starting resource management page load")
        # Get all resources with their categories
        try:
            resources = Resource.query.all()
            current_app.logger.info(f"Loaded {len(resources)} resources")
        except Exception as e:
            error_msg = f"Error loading resources: {str(e)}"
            current_app.logger.error(error_msg)
            errors.append(error_msg)
        
        # Get all shops
        try:
            shops = Shop.query.all()
            current_app.logger.info(f"Loaded {len(shops)} shops")
        except Exception as e:
            error_msg = f"Error loading shops: {str(e)}"
            current_app.logger.error(error_msg)
            errors.append(error_msg)
        
        # Get resource quantities for each shop
        for shop in shops:
            try:
                shop_resources[shop.id] = {
                    sr.resource_id: sr.quantity 
                    for sr in ShopResource.query.filter_by(shop_id=shop.id).all()
                }
            except Exception as e:
                error_msg = f"Error loading resources for shop {shop.id}: {str(e)}"
                current_app.logger.error(error_msg)
                errors.append(error_msg)
                shop_resources[shop.id] = {}
        
        # Get low stock resources
        for resource in resources:
            try:
                total_quantity = sum(
                    shop_resources.get(shop.id, {}).get(resource.id, 0)
                    for shop in shops
                )
                if total_quantity <= resource.reorder_level:
                    low_stock_resources.append({
                        'id': resource.id,
                        'name': resource.name,
                        'quantity': total_quantity,
                        'reorder_level': resource.reorder_level
                    })
            except Exception as e:
                error_msg = f"Error checking low stock for resource {resource.id}: {str(e)}"
                current_app.logger.error(error_msg)
                errors.append(error_msg)
        
        # Get resource categories
        try:
            categories = ResourceCategory.query.all()
            if not categories:
                # If no categories exist, create default ones
                default_categories = [
                    ('Office Supplies', 'General office supplies like paper, pens, etc.'),
                    ('Printing Materials', 'Ink, toner, and other printing supplies'),
                    ('Cleaning Supplies', 'Cleaning and maintenance materials'),
                    ('IT Equipment', 'Computer and technology related resources'),
                    ('Packaging Materials', 'Boxes, bags, and other packaging supplies')
                ]
                for name, description in default_categories:
                    category = ResourceCategory(name=name, description=description)
                    db.session.add(category)
                db.session.commit()
                categories = ResourceCategory.query.all()
            current_app.logger.info(f"Loaded {len(categories)} categories")
        except Exception as e:
            error_msg = f"Error loading categories: {str(e)}"
            current_app.logger.error(error_msg)
            errors.append(error_msg)
        
        # Get active alerts
        try:
            alerts = ResourceAlert.query.filter_by(is_active=True).all()
        except Exception as e:
            error_msg = f"Error loading alerts: {str(e)}"
            current_app.logger.error(error_msg)
            errors.append(error_msg)
        
        current_app.logger.info("Successfully loaded all resource management data")
        for error in errors:
            flash(error, 'danger')
        
        return render_template('admin/resources.html',
                             resources=resources,
                             shops=shops,
                             shop_resources=shop_resources,
                             low_stock_resources=low_stock_resources,
                             categories=categories,
                             alerts=alerts)
    except Exception as e:
        current_app.logger.error(f"Critical error in manage_resources: {str(e)}", exc_info=True)
        flash(f'Critical error loading resource management page: {str(e)}', 'danger')
        return render_template('admin/resources.html',
                             resources=resources,
                             shops=shops,
                             shop_resources=shop_resources,
                             low_stock_resources=low_stock_resources,
                             categories=categories,
                             alerts=alerts)

@admin_bp.route('/resources/add', methods=['POST'])
@login_required
def add_resource():
    """Add a new resource"""
    try:
        data = request.form
        
        # Create new resource
        resource = Resource(
            name=data['name'],
            description=data.get('description', ''),
            category=data['category'],
            unit=data['unit'],
            reorder_level=int(data['reorder_level'])
        )
        db.session.add(resource)
        
        # Initialize quantities for all shops
        shops = Shop.query.all()
        for shop in shops:
            shop_resource = ShopResource(
                shop_id=shop.id,
                resource_id=resource.id,
                quantity=0,
                updated_by=current_user.id
            )
            db.session.add(shop_resource)
        
        db.session.commit()
        flash('Resource added successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding resource: {str(e)}", exc_info=True)
        flash('Error adding resource', 'error')
    
    return redirect(url_for('admin.manage_resources'))

@admin_bp.route('/resources/<int:resource_id>/update', methods=['POST'])
@login_required
def update_resource(resource_id):
    """Update resource details"""
    try:
        resource = Resource.query.get_or_404(resource_id)
        data = request.form
        
        resource.name = data['name']
        resource.description = data.get('description', '')
        resource.category = data['category']
        resource.unit = data['unit']
        resource.reorder_level = int(data['reorder_level'])
        
        db.session.commit()
        flash('Resource updated successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating resource {resource_id}: {str(e)}", exc_info=True)
        flash('Error updating resource', 'error')
    
    return redirect(url_for('admin.manage_resources'))

@admin_bp.route('/resources/<int:resource_id>/delete', methods=['POST'])
@login_required
def delete_resource(resource_id):
    """Delete a resource"""
    try:
        resource = Resource.query.get_or_404(resource_id)
        db.session.delete(resource)
        db.session.commit()
        flash('Resource deleted successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting resource {resource_id}: {str(e)}", exc_info=True)
        flash('Error deleting resource', 'error')
    
    return redirect(url_for('admin.manage_resources'))

@admin_bp.route('/resources/bulk-update', methods=['POST'])
@login_required
def bulk_update_resources():
    """Bulk update resource quantities"""
    try:
        data = request.json
        shop_id = data['shop_id']
        updates = data['updates']
        
        for update in updates:
            shop_resource = ShopResource.query.filter_by(
                shop_id=shop_id,
                resource_id=update['resource_id']
            ).first()
            
            if shop_resource:
                previous_quantity = shop_resource.quantity
                shop_resource.quantity = update['quantity']
                shop_resource.updated_by = current_user.id
                
                # Create history entry
                history = ResourceHistory(
                    resource_id=update['resource_id'],
                    shop_id=shop_id,
                    previous_quantity=previous_quantity,
                    new_quantity=update['quantity'],
                    change_type='adjust',
                    reason=update.get('reason', ''),
                    updated_by=current_user.id
                )
                db.session.add(history)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Resources updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk update: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error updating resources'}), 500

@admin_bp.route('/resources/export')
@login_required
def export_resources():
    """Export resources data to Excel"""
    try:
        resources = Resource.query.all()
        shops = Shop.query.all()
        
        # Create DataFrame
        data = []
        for resource in resources:
            row = {
                'Resource ID': resource.id,
                'Name': resource.name,
                'Category': resource.category,
                'Unit': resource.unit,
                'Reorder Level': resource.reorder_level
            }
            
            # Add quantities for each shop
            for shop in shops:
                shop_resource = ShopResource.query.filter_by(
                    shop_id=shop.id,
                    resource_id=resource.id
                ).first()
                row[f'{shop.name} Quantity'] = shop_resource.quantity if shop_resource else 0
            
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
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'resources_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting resources: {str(e)}", exc_info=True)
        flash('Error exporting resources', 'error')
        return redirect(url_for('admin.manage_resources'))

@admin_bp.route('/resources/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    """Manage resource categories"""
    if request.method == 'POST':
        try:
            data = request.form
            if 'add' in data:
                category = ResourceCategory(
                    name=data['name'],
                    description=data.get('description', '')
                )
                db.session.add(category)
            elif 'edit' in data:
                category = ResourceCategory.query.get(data['category_id'])
                if category:
                    category.name = data['name']
                    category.description = data.get('description', '')
            
            db.session.commit()
            flash('Category updated successfully', 'success')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error managing categories: {str(e)}", exc_info=True)
            flash('Error updating category', 'error')
    
    categories = ResourceCategory.query.all()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/resources/<int:resource_id>/history')
@login_required
def resource_history(resource_id):
    """View resource history"""
    try:
        resource = Resource.query.get_or_404(resource_id)
        history = ResourceHistory.query.filter_by(resource_id=resource_id).order_by(ResourceHistory.updated_at.desc()).all()
        
        return render_template('admin/resource_history.html',
                             resource=resource,
                             history=history)
                             
    except Exception as e:
        current_app.logger.error(f"Error loading resource history: {str(e)}", exc_info=True)
        flash('Error loading resource history', 'error')
        return redirect(url_for('admin.manage_resources'))

@admin_bp.route('/resources/alerts')
@login_required
def resource_alerts():
    """View and manage resource alerts"""
    try:
        alerts = ResourceAlert.query.filter_by(is_active=True).order_by(ResourceAlert.created_at.desc()).all()
        return render_template('admin/alerts.html', alerts=alerts)
        
    except Exception as e:
        current_app.logger.error(f"Error loading alerts: {str(e)}", exc_info=True)
        flash('Error loading alerts', 'error')
        return redirect(url_for('admin.manage_resources'))

@admin_bp.route('/resources/alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    """Resolve a resource alert"""
    try:
        alert = ResourceAlert.query.get_or_404(alert_id)
        alert.is_active = False
        alert.resolved_at = datetime.utcnow()
        db.session.commit()
        flash('Alert resolved successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error resolving alert {alert_id}: {str(e)}", exc_info=True)
        flash('Error resolving alert', 'error')
    
    return redirect(url_for('admin.resource_alerts'))


@admin_bp.route('/accounts')
@login_required
@admin_required
def accounts():
    """Show admin accounts dashboard with financial data from all shops."""
    try:
        # Get period filter and shop selection
        period = request.args.get('period', 'today')
        selected_shop_id = request.args.get('shop_id', type=int)

        # Get all shops
        shops = Shop.query.all()

        # Calculate date range based on period
        end_date = datetime.now()
        if period == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Initialize shop breakdown list
        shop_breakdown = []

        # Process each shop
        for shop in shops:
            # Skip if shop is selected and this isn't it
            if selected_shop_id and shop.id != selected_shop_id:
                continue

            # Initialize shop totals
            shop_totals = {
                'cash': Decimal('0.00'),
                'till': Decimal('0.00'),
                'bank': Decimal('0.00'),
                'expenses': Decimal('0.00')
            }

            # Initialize daily breakdown
            daily_breakdown = []
            current_date = start_date

            # Process each day in the period
            while current_date <= end_date:
                # Get financial records for this day
                day_records = FinancialRecord.query.filter(
                    FinancialRecord.shop_id == shop.id,
                    db.func.date(FinancialRecord.date) == current_date.date()
                ).all()

                # Get expenses for this day
                shop_expenses = Expense.query.filter(
                    Expense.shop_id == shop.id,
                    db.func.date(Expense.date) == current_date.date()
                ).all()

                # Initialize day totals
                day_totals = {
                    'cash': Decimal('0.00'),
                    'till': Decimal('0.00'),
                    'bank': Decimal('0.00'),
                    'expenses': sum(Decimal(str(expense.amount)) for expense in shop_expenses)
                }

                # Calculate totals from financial records
                for record in day_records:
                    if record.type in day_totals:
                        day_totals[record.type] += Decimal(str(record.amount or 0))
                        shop_totals[record.type] += Decimal(str(record.amount or 0))

                # Add expenses to shop total
                shop_totals['expenses'] += day_totals['expenses']

                # Calculate day total
                day_total = sum(day_totals[method] for method in ['cash', 'till', 'bank']) - day_totals['expenses']

                # Add day data to breakdown
                daily_breakdown.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'cash': float(day_totals['cash']),
                    'till': float(day_totals['till']),
                    'bank': float(day_totals['bank']),
                    'expenses': float(day_totals['expenses']),
                    'total': float(day_total)
                })

                current_date += timedelta(days=1)

            # Calculate shop total
            shop_total = sum(shop_totals[method] for method in ['cash', 'till', 'bank']) - shop_totals['expenses']

            # Add shop data to breakdown
            shop_breakdown.append({
                'shop_id': shop.id,
                'shop_name': shop.name,
                'cash': float(shop_totals['cash']),
                'till': float(shop_totals['till']),
                'bank': float(shop_totals['bank']),
                'expenses': float(shop_totals['expenses']),
                'total': float(shop_total),
                'daily_breakdown': daily_breakdown
            })

        # Calculate overall totals
        overall_totals = {
            'cash': sum(shop['cash'] for shop in shop_breakdown),
            'till': sum(shop['till'] for shop in shop_breakdown),
            'bank': sum(shop['bank'] for shop in shop_breakdown),
            'expenses': sum(shop['expenses'] for shop in shop_breakdown)
        }
        overall_totals['total'] = overall_totals['cash'] + overall_totals['till'] + overall_totals['bank'] - overall_totals['expenses']

        return render_template('admin/accounts.html',
                            shops=shops,
                            period=period,
                            selected_shop_id=selected_shop_id,
                            shop_breakdown=shop_breakdown,
                            overall_totals=overall_totals)

    except Exception as e:
        logger.error(f"Error loading accounts page: {str(e)}", exc_info=True)
        flash('Error loading accounts page.', 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/api/accounts/summary')
@login_required
@admin_required
def get_accounts_summary():
    """Get financial summary data for all shops."""
    try:
        logger.info("Starting get_accounts_summary")

        # Get filter parameters
        date_range = request.args.get('date_range', 'today')
        shop_ids = request.args.getlist('shop_ids[]')
        logger.info(
            f"Received parameters - date_range: {date_range}, shop_ids: {shop_ids}")

        # Calculate date range
        end_date = datetime.now()
        if date_range == 'today':
            start_date = end_date.replace(
                hour=0, minute=0, second=0, microsecond=0)
        elif date_range == 'week':
            start_date = end_date - timedelta(days=7)
        elif date_range == 'month':
            start_date = end_date - timedelta(days=30)
        elif date_range == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            logger.error(f"Invalid date range: {date_range}")
            return jsonify({'error': 'Invalid date range'}), 400

        logger.info(f"Date range: {start_date} to {end_date}")

        # Get all shops
        shops = Shop.query.all()
        logger.info(f"Found {len(shops)} shops")

        if not shops:
            logger.warning("No shops found in database")
            return jsonify({
                'overall': {
                    'cash': 0,
                    'till': 0,
                    'bank': 0,
                    'expenses': 0,
                    'total': 0
                },
                'shop_breakdown': []
            })

        # Initialize totals
        totals = {
            'cash': 0,
            'till': 0,
            'bank': 0,
            'expenses': 0
        }

        # Get shop-wise breakdown
        shop_breakdown = []

        for shop in shops:
            if not shop_ids or str(shop.id) in shop_ids:
                logger.info(f"Processing shop: {shop.name} (ID: {shop.id})")

                try:
                    # Get product sales grouped by payment method
                    sales_by_payment = db.session.query(
                        Sale.payment_method,
                        db.func.sum(Sale.price * Sale.quantity).label('total')
                    ).filter(
                        Sale.shop_id == shop.id,
                        Sale.sale_date >= start_date,
                        Sale.sale_date <= end_date
                    ).group_by(Sale.payment_method).all()

                    logger.info(f"Found {len(sales_by_payment)} product sales records for shop {shop.name}")

                    # Get service sales grouped by payment method
                    service_sales_by_payment = db.session.query(
                        ServiceSale.payment_method,
                        db.func.sum(ServiceSale.price).label('total')
                    ).filter(
                        ServiceSale.shop_id == shop.id,
                        ServiceSale.sale_date >= start_date,
                        ServiceSale.sale_date <= end_date
                    ).group_by(ServiceSale.payment_method).all()

                    logger.info(f"Found {len(service_sales_by_payment)} service sales records for shop {shop.name}")

                    # Get expenses
                    shop_expenses = Expense.query.filter(
                        Expense.shop_id == shop.id,
                        Expense.date >= start_date,
                        Expense.date <= end_date
                    ).all()

                    logger.info(f"Found {len(shop_expenses)} expenses for shop {shop.name}")

                    # Initialize shop totals
                    shop_totals = {
                        'cash': 0, 'till': 0, 'bank': 0, 'expenses': sum(
                            expense.amount for expense in shop_expenses)}

                    # Calculate totals from product sales
                    for payment_method, total in sales_by_payment:
                        if payment_method in shop_totals:
                            shop_totals[payment_method] += float(total)
                            totals[payment_method] += float(total)

                    # Add service sales to totals
                    for payment_method, total in service_sales_by_payment:
                        if payment_method in shop_totals:
                            shop_totals[payment_method] += float(total)
                            totals[payment_method] += float(total)

                    # Add shop expenses to total expenses
                    totals['expenses'] += shop_totals['expenses']

                    # Calculate shop total
                    shop_total = sum(
                        shop_totals[method] for method in [
                            'cash', 'till', 'bank']) - shop_totals['expenses']

                    shop_breakdown.append({
                        'shop_id': shop.id,
                        'shop_name': shop.name,
                        'cash': shop_totals['cash'],
                        'till': shop_totals['till'],
                        'bank': shop_totals['bank'],
                        'expenses': shop_totals['expenses'],
                        'total': shop_total
                    })

                    logger.info(f"Processed shop {shop.name} totals: {shop_totals}")

                except Exception as e:
                    logger.error(
                        f"Error processing shop {shop.name}: {str(e)}")
                    continue

        # Calculate overall total
        overall_total = sum(
            totals[method] for method in [
                'cash',
                'till',
                'bank']) - totals['expenses']

        response_data = {
            'overall': {
                'cash': totals['cash'],
                'till': totals['till'],
                'bank': totals['bank'],
                'expenses': totals['expenses'],
                'total': overall_total
            },
            'shop_breakdown': shop_breakdown
        }

        logger.info(f"Final response data: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in get_accounts_summary: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/accounts/download')
@login_required
@admin_required
def download_accounts():
    """Download financial data as Excel file."""
    try:
        # Get filter parameters
        date_range = request.args.get('date_range', 'today')
        shop_ids = request.args.getlist('shop_ids[]')

        # Calculate date range
        end_date = datetime.now()
        if date_range == 'today':
            start_date = end_date.replace(
                hour=0, minute=0, second=0, microsecond=0)
        elif date_range == 'week':
            start_date = end_date - timedelta(days=7)
        elif date_range == 'month':
            start_date = end_date - timedelta(days=30)
        elif date_range == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            return jsonify({'error': 'Invalid date range'}), 400

        # Get product sales data
        sales_query = Sale.query.filter(
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date)
        if shop_ids:
            sales_query = sales_query.filter(Sale.shop_id.in_(shop_ids))
        sales = sales_query.options(
            db.joinedload(Sale.shop),
            db.joinedload(Sale.product)
        ).all()

        # Get service sales data
        service_sales_query = ServiceSale.query.filter(
            ServiceSale.sale_date >= start_date,
            ServiceSale.sale_date <= end_date)
        if shop_ids:
            service_sales_query = service_sales_query.filter(
                ServiceSale.shop_id.in_(shop_ids))
        service_sales = service_sales_query.options(
            db.joinedload(ServiceSale.shop),
            db.joinedload(ServiceSale.service)
        ).all()

        # Get expenses data
        expenses_query = Expense.query.filter(
            Expense.date >= start_date, Expense.date <= end_date)
        if shop_ids:
            expenses_query = expenses_query.filter(
                Expense.shop_id.in_(shop_ids))
        expenses = expenses_query.options(
            db.joinedload(Expense.shop)
        ).all()

        # Prepare product sales data for Excel
        sales_data = []
        for sale in sales:
            sales_data.append({
                'Date': sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
                'Shop': sale.shop.name,
                'Type': 'Product',
                'Item': sale.product.name,
                'Quantity': sale.quantity,
                'Price': sale.price,
                'Total': sale.price * sale.quantity,
                'Payment Method': sale.payment_method.title(),
                'Customer': sale.customer_name or 'N/A'
            })

        # Prepare service sales data for Excel
        for sale in service_sales:
            sales_data.append({
                'Date': sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
                'Shop': sale.shop.name,
                'Type': 'Service',
                'Item': sale.service.name,
                'Quantity': 1,
                'Price': sale.price,
                'Total': sale.price,
                'Payment Method': sale.payment_method.title(),
                'Customer': sale.customer_name or 'N/A'
            })

        # Sort sales data by date
        sales_data.sort(key=lambda x: x['Date'])

        # Prepare expenses data for Excel
        expenses_data = []
        for expense in expenses:
            expenses_data.append({
                'Date': expense.date.strftime('%Y-%m-%d %H:%M:%S'),
                'Shop': expense.shop.name,
                'Description': expense.description,
                'Amount': expense.amount,
                'Category': expense.category
            })

        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Sales sheet
            df_sales = pd.DataFrame(sales_data)
            df_sales.to_excel(writer, sheet_name='Sales', index=False)

            # Expenses sheet
            df_expenses = pd.DataFrame(expenses_data)
            df_expenses.to_excel(writer, sheet_name='Expenses', index=False)

            # Summary sheet
            total_cash = sum(
                sale.price *
                sale.quantity for sale in sales if sale.payment_method == 'cash')
            total_till = sum(
                sale.price *
                sale.quantity for sale in sales if sale.payment_method == 'till')
            total_bank = sum(
                sale.price *
                sale.quantity for sale in sales if sale.payment_method == 'bank')

            # Add service sales to totals
            total_cash += sum(
                sale.price for sale in service_sales if sale.payment_method == 'cash')
            total_till += sum(
                sale.price for sale in service_sales if sale.payment_method == 'till')
            total_bank += sum(
                sale.price for sale in service_sales if sale.payment_method == 'bank')

            total_sales = total_cash + total_till + total_bank
            total_expenses = sum(expense.amount for expense in expenses)

            summary_data = {
                'Category': [
                    'Total Cash Sales',
                    'Total Till Sales',
                    'Total Bank Sales',
                    'Total Sales',
                    'Total Expenses',
                    'Net Total'
                ],
                'Amount': [
                    total_cash,
                    total_till,
                    total_bank,
                    total_sales,
                    total_expenses,
                    total_sales - total_expenses
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)

        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'financial_report_{date_range}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')

    except Exception as e:
        logger.error(f"Error downloading accounts: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/download-shop-accounts')
@login_required
@admin_required
def download_shop_accounts():
    """Download shop accounts report with daily breakdown for the selected period."""
    try:
        logger.info("Starting download_shop_accounts")

        # Get period filter and shop selection
        period = request.args.get('period', 'today')
        selected_shop_id = request.args.get('shop_id', type=int)
        logger.info(f"Period selected: {period}, Shop ID: {selected_shop_id}")

        # Calculate date range based on period
        end_date = datetime.now()
        if period == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            days = 1
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
            days = 7
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
            days = 30
        elif period == 'year':
            start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            days = 365
        else:
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            days = 1

        logger.info(f"Date range: {start_date} to {end_date}")

        # Get shops based on selection
        if selected_shop_id:
            shops = Shop.query.filter_by(id=selected_shop_id).all()
            if not shops:
                logger.error(f"No shop found with ID: {selected_shop_id}")
                flash('Selected shop not found.', 'danger')
                return redirect(url_for('admin.accounts'))
        else:
            shops = Shop.query.all()
            if not shops:
                logger.error("No shops found in database")
                flash('No shops found.', 'danger')
                return redirect(url_for('admin.accounts'))

        # Create a list to store all data
        data = []

        # Process each shop
        for shop in shops:
            try:
                logger.info(f"Processing shop: {shop.name}")

                # Add shop header
                data.append({
                    'Date': shop.name,
                    'Cash': '',
                    'Till': '',
                    'Bank': '',
                    'Expenses': '',
                    'Total': ''
                })

                # Process each day in the period
                current_date = start_date
                while current_date <= end_date:
                    try:
                        logger.info(f"Processing date: {current_date.date()}")

                        # Get sales for this day
                        sales_by_payment = db.session.query(
                            Sale.payment_method,
                            db.func.sum(Sale.price * Sale.quantity).label('total')
                        ).filter(
                            Sale.shop_id == shop.id,
                            db.func.date(Sale.sale_date) == current_date.date()
                        ).group_by(Sale.payment_method).all()

                        # Get service sales for this day
                        service_sales_by_payment = db.session.query(
                            ServiceSale.payment_method,
                            db.func.sum(ServiceSale.price).label('total')
                        ).filter(
                            ServiceSale.shop_id == shop.id,
                            db.func.date(ServiceSale.sale_date) == current_date.date()
                        ).group_by(ServiceSale.payment_method).all()

                        # Get expenses for this day
                        shop_expenses = Expense.query.filter(
                            Expense.shop_id == shop.id,
                            db.func.date(Expense.date) == current_date.date()
                        ).all()

                        # Initialize day totals with Decimal
                        day_totals = {
                            'cash': Decimal('0.00'),
                            'till': Decimal('0.00'),
                            'bank': Decimal('0.00'),
                            'expenses': sum(Decimal(str(expense.amount)) for expense in shop_expenses)
                        }

                        # Calculate totals from product sales
                        for payment_method, total in sales_by_payment:
                            if payment_method in day_totals:
                                day_totals[payment_method] += Decimal(str(total))

                        # Add service sales to totals
                        for payment_method, total in service_sales_by_payment:
                            if payment_method in day_totals:
                                day_totals[payment_method] += Decimal(str(total))

                        # Calculate day total
                        day_total = sum(day_totals[method] for method in ['cash', 'till', 'bank']) - day_totals['expenses']

                        # Add day data to the list
                        data.append({
                            'Date': current_date.strftime('%Y-%m-%d'),
                            'Cash': float(day_totals['cash']),
                            'Till': float(day_totals['till']),
                            'Bank': float(day_totals['bank']),
                            'Expenses': float(day_totals['expenses']),
                            'Total': float(day_total)
                        })

                        current_date += timedelta(days=1)
                    except Exception as e:
                        logger.error(f"Error processing date {current_date.date()}: {str(e)}")
                        continue

                # Calculate shop totals
                shop_data = data[-days - 1:]
                shop_total = {
                    'cash': sum(Decimal(str(row['Cash'])) for row in shop_data if isinstance(row['Cash'], (int, float))),
                    'till': sum(Decimal(str(row['Till'])) for row in shop_data if isinstance(row['Till'], (int, float))),
                    'bank': sum(Decimal(str(row['Bank'])) for row in shop_data if isinstance(row['Bank'], (int, float))),
                    'expenses': sum(Decimal(str(row['Expenses'])) for row in shop_data if isinstance(row['Expenses'], (int, float)))
                }
                shop_total['total'] = shop_total['cash'] + shop_total['till'] + shop_total['bank'] - shop_total['expenses']

                # Add shop total
                data.append({
                    'Date': f'{shop.name} Total',
                    'Cash': float(shop_total['cash']),
                    'Till': float(shop_total['till']),
                    'Bank': float(shop_total['bank']),
                    'Expenses': float(shop_total['expenses']),
                    'Total': float(shop_total['total'])
                })

                # Add empty row for spacing
                data.append({
                    'Date': '',
                    'Cash': '',
                    'Till': '',
                    'Bank': '',
                    'Expenses': '',
                    'Total': ''
                })

            except Exception as e:
                logger.error(f"Error processing shop {shop.name}: {str(e)}")
                continue

        if not data:
            logger.error("No data generated for the report")
            flash('No data available for the selected period.', 'warning')
            return redirect(url_for('admin.accounts'))

        try:
            logger.info(f"Total rows in data: {len(data)}")

            # Create Excel file
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Convert data to DataFrame
                df = pd.DataFrame(data)
                logger.info(f"DataFrame shape: {df.shape}")

                # Write to Excel
                df.to_excel(writer, sheet_name='Shop Accounts', index=False)

                # Get workbook and worksheet objects
                workbook = writer.book
                worksheet = writer.sheets['Shop Accounts']

                # Add some formatting
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4CAF50',
                    'font_color': 'white',
                    'border': 1
                })

                shop_header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#E8F5E9',
                    'border': 1
                })

                shop_total_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#C8E6C9',
                    'border': 1
                })

                number_format = workbook.add_format({
                    'num_format': 'KES #,##0.00',
                    'border': 1
                })

                # Format headers
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)

                # Format data
                for row_num, row in enumerate(df.itertuples(), start=1):
                    for col_num, value in enumerate(row[1:], start=0):
                        if isinstance(value, (int, float)):
                            worksheet.write(row_num, col_num, value, number_format)
                        elif isinstance(value, str):
                            if value.endswith('Total'):
                                worksheet.write(row_num, col_num, value, shop_total_format)
                            elif value and not value.isdigit():
                                worksheet.write(row_num, col_num, value, shop_header_format)
                            else:
                                worksheet.write(row_num, col_num, value)

                # Adjust column widths
                worksheet.set_column('A:A', 20)  # Date column
                worksheet.set_column('B:F', 15)  # Other columns

                # Add period information
                worksheet.write(0, 6, f'Period: {period.capitalize()}', header_format)
                worksheet.write(1, 6, f'From: {start_date.strftime("%Y-%m-%d")}', header_format)
                worksheet.write(2, 6, f'To: {end_date.strftime("%Y-%m-%d")}', header_format)

            # Prepare the file for download
            output.seek(0)
            filename = f'shop_accounts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename)

        except Exception as e:
            logger.error(f"Error creating Excel file: {str(e)}")
            flash('Error creating the report file.', 'danger')
            return redirect(url_for('admin.accounts'))

    except Exception as e:
        logger.error(f"Error in download_shop_accounts: {str(e)}")
        flash('Error downloading shop accounts report.', 'danger')
        return redirect(url_for('admin.accounts'))


@admin_bp.route('/api/test-db')
@login_required
@admin_required
def test_db():
    """Test database connection and data."""
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))

        # Get counts
        shop_count = Shop.query.count()
        sale_count = Sale.query.count()
        service_sale_count = ServiceSale.query.count()
        expense_count = Expense.query.count()

        # Get sample data
        shops = Shop.query.all()
        shop_data = [{'id': shop.id, 'name': shop.name} for shop in shops]

        return jsonify({
            'status': 'success',
            'counts': {
                'shops': shop_count,
                'sales': sale_count,
                'service_sales': service_sale_count,
                'expenses': expense_count
            },
            'shops': shop_data
        })

    except Exception as e:
        logger.error(f"Database test error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@admin_bp.route('/api/sales/<int:sale_id>')
@login_required
def get_sale_details(sale_id):
    """Get details for a specific sale."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    try:
        sale = Sale.query.get_or_404(sale_id)
        return jsonify({
            'success': True,
            'sale': {
                'id': sale.id,
                'sale_date': sale.sale_date.strftime('%Y-%m-%d %H:%M'),
                'shop_name': sale.shop.name,
                'product_name': sale.product.name,
                'quantity': sale.quantity,
                'price': float(sale.product.marked_price),
                'total': float(sale.product.marked_price * sale.quantity)
            }
        })
    except Exception as e:
        logger.error(f"Error getting sale details: {str(e)}")
        return jsonify(
            {'success': False, 'message': 'Error getting sale details'}), 500


@admin_bp.route('/download-sales-report')
@login_required
@admin_required
def download_sales_report():
    try:
        logger.info("Starting download_sales_report")
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        selected_shop_id = request.args.get('shop_id', type=int)
        sort_by = request.args.get('sort_by', 'date_desc')
        period = request.args.get('period', 'today')

        # Set default dates based on period if not provided
        if not start_date or not end_date:
            end_date_dt = datetime.now()
            if period == 'today':
                start_date_dt = end_date_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'week':
                start_date_dt = end_date_dt - timedelta(days=7)
            elif period == 'month':
                start_date_dt = end_date_dt - timedelta(days=30)
            elif period == 'year':
                start_date_dt = end_date_dt - timedelta(days=365)
            else:
                start_date_dt = end_date_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            try:
                start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_date_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            except ValueError as e:
                logger.error(f"Invalid date format: {str(e)}")
                flash('Invalid date format. Please use YYYY-MM-DD format.', 'danger')
                return redirect(url_for('admin.sales_report'))

        logger.info(f"Date range: {start_date_dt} to {end_date_dt}")

        # Base query with eager loading
        query = Sale.query.join(Shop).join(Product).options(
            db.joinedload(Sale.shop),
            db.joinedload(Sale.product)
        )

        # Apply date filter
        query = query.filter(
            Sale.sale_date >= start_date_dt,
            Sale.sale_date <= end_date_dt
        )

        # Apply shop filter
        if selected_shop_id:
            query = query.filter(Sale.shop_id == selected_shop_id)

        # Apply sorting
        if sort_by == 'date_desc':
            query = query.order_by(Sale.sale_date.desc())
        elif sort_by == 'date_asc':
            query = query.order_by(Sale.sale_date.asc())
        elif sort_by == 'amount_desc':
            query = query.order_by((Sale.product.marked_price * Sale.quantity).desc())
        elif sort_by == 'amount_asc':
            query = query.order_by((Sale.product.marked_price * Sale.quantity).asc())

        # Get sales data
        sales = query.all()
        logger.info(f"Found {len(sales)} sales records")

        if not sales:
            flash('No sales data found for the selected period.', 'warning')
            return redirect(url_for('admin.sales_report'))

        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Prepare detailed sales data
            sales_data = []
            for sale in sales:
                sales_data.append({
                    'Date': sale.sale_date.strftime('%Y-%m-%d %H:%M'),
                    'Shop': sale.shop.name,
                    'Product': sale.product.name,
                    'Category': sale.product.category,
                    'Quantity': sale.quantity,
                    'Price': float(sale.product.marked_price),
                    'Total': float(sale.product.marked_price * sale.quantity),
                    'Payment Method': sale.payment_method.title(),
                    'Customer': sale.customer_name or 'N/A'
                })

            # Create detailed sales sheet
            df_sales = pd.DataFrame(sales_data)
            df_sales.to_excel(writer, sheet_name='Detailed Sales', index=False)

            # Create daily summary sheet
            daily_summary = df_sales.groupby([pd.to_datetime(df_sales['Date']).dt.date]).agg({
                'Total': 'sum',
                'Quantity': 'sum',
                'Date': 'count'
            }).rename(columns={'Date': 'Transactions'})
            daily_summary.index.name = 'Date'
            daily_summary.to_excel(writer, sheet_name='Daily Summary')

            # Create shop summary sheet
            shop_summary = df_sales.groupby('Shop').agg({
                'Total': 'sum',
                'Quantity': 'sum',
                'Date': 'count'
            }).rename(columns={'Date': 'Transactions'})
            shop_summary.to_excel(writer, sheet_name='Shop Summary')

            # Create category summary sheet
            category_summary = df_sales.groupby('Category').agg({
                'Total': 'sum',
                'Quantity': 'sum',
                'Date': 'count'
            }).rename(columns={'Date': 'Transactions'})
            category_summary.to_excel(writer, sheet_name='Category Summary')

            # Create payment method summary sheet
            payment_summary = df_sales.groupby('Payment Method').agg({
                'Total': 'sum',
                'Date': 'count'
            }).rename(columns={'Date': 'Transactions'})
            payment_summary.to_excel(writer, sheet_name='Payment Summary')

            # Create overall summary sheet
            total_sales = df_sales['Total'].sum()
            total_items = df_sales['Quantity'].sum()
            total_transactions = len(df_sales)
            average_sale = total_sales / total_transactions if total_transactions > 0 else 0

            summary_data = {
                'Metric': [
                    'Total Sales',
                    'Total Items Sold',
                    'Total Transactions',
                    'Average Sale Amount',
                    'Period',
                    'Start Date',
                    'End Date'
                ],
                'Value': [
                    f"KES {total_sales:.2f}",
                    total_items,
                    total_transactions,
                    f"KES {average_sale:.2f}",
                    period.capitalize(),
                    start_date_dt.strftime('%Y-%m-%d'),
                    end_date_dt.strftime('%Y-%m-%d')
                ]
            }

            if selected_shop_id:
                shop = Shop.query.get(selected_shop_id)
                if shop:
                    summary_data['Metric'].extend(['Shop Name', 'Shop Location'])
                    summary_data['Value'].extend([shop.name, shop.location])

            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)

            # Get workbook and worksheet objects
            workbook = writer.book

            # Add formatting to all sheets
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]

                # Add header format
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4CAF50',
                    'font_color': 'white',
                })

                # Add number format
                number_format = workbook.add_format({
                    'num_format': 'KES #,##0.00',
                    'border': 1
                })

                # Add date format
                date_format = workbook.add_format({
                    'num_format': 'yyyy-mm-dd',
                    'border': 1
                })

                # Format headers
                for col_num, value in enumerate(df_sales.columns.values):
                    worksheet.write(0, col_num, value, header_format)

                # Format data
                for row_num, row in enumerate(df_sales.itertuples(), start=1):
                    for col_num, value in enumerate(row[1:], start=0):
                        if isinstance(value, (int, float)):
                            worksheet.write(row_num, col_num, value, number_format)
                        elif isinstance(value, str) and value.replace('-', '').replace(':', '').isdigit():
                            worksheet.write(row_num, col_num, value, date_format)

        # Prepare the file for download
        output.seek(0)
        filename = f'sales_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Unexpected error in download_sales_report: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'danger')
        return redirect(url_for('admin.sales_report'))


@admin_bp.route('/api/sales/summary')
@login_required
@admin_required
def get_sales_summary():
    """Get summary of sales data for the frontend."""
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        shop_id = request.args.get('shop_id')

        # Base query
        query = db.session.query(
            Sale,
            Product,
            Shop
        ).join(
            Product, Sale.product_id == Product.id
        ).join(
            Shop, Sale.shop_id == Shop.id
        )

        # Apply filters
        if start_date:
            query = query.filter(
                Sale.sale_date >= datetime.strptime(
                    start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(
                Sale.sale_date <= datetime.strptime(
                    end_date, '%Y-%m-%d'))
        if shop_id:
            query = query.filter(Sale.shop_id == shop_id)

        # Execute query
        sales_data = query.all()

        # Process data
        summary = {
            'total_sales': 0,
            'total_items': 0,
            'total_transactions': len(sales_data),
            'sales_by_shop': {},
            'sales_by_category': {},
            'sales_by_date': {},
            'top_products': {},
            'payment_methods': {
                'cash': 0,
                'till': 0,
                'bank': 0
            }
        }

        for sale, product, shop in sales_data:
            sale_amount = sale.quantity * product.marked_price

            # Update totals
            summary['total_sales'] += sale_amount
            summary['total_items'] += sale.quantity

            # Update shop statistics
            if shop.name not in summary['sales_by_shop']:
                summary['sales_by_shop'][shop.name] = {
                    'total_sales': 0,
                    'total_items': 0,
                    'total_transactions': 0
                }
            summary['sales_by_shop'][shop.name]['total_sales'] += sale_amount
            summary['sales_by_shop'][shop.name]['total_items'] += sale.quantity
            summary['sales_by_shop'][shop.name]['total_transactions'] += 1

            # Update category statistics
            if product.category not in summary['sales_by_category']:
                summary['sales_by_category'][product.category] = {
                    'total_sales': 0,
                    'total_items': 0
                }
            summary['sales_by_category'][product.category]['total_sales'] += sale_amount
            summary['sales_by_category'][product.category]['total_items'] += sale.quantity

            # Update date statistics
            sale_date = sale.sale_date.strftime('%Y-%m-%d')
            if sale_date not in summary['sales_by_date']:
                summary['sales_by_date'][sale_date] = {
                    'total_sales': 0,
                    'total_items': 0,
                    'total_transactions': 0
                }
            summary['sales_by_date'][sale_date]['total_sales'] += sale_amount
            summary['sales_by_date'][sale_date]['total_items'] += sale.quantity
            summary['sales_by_date'][sale_date]['total_transactions'] += 1

            # Update top products
            if product.name not in summary['top_products']:
                summary['top_products'][product.name] = {
                    'total_sales': 0,
                    'total_items': 0,
                    'category': product.category
                }
            summary['top_products'][product.name]['total_sales'] += sale_amount
            summary['top_products'][product.name]['total_items'] += sale.quantity

            # Update payment methods
            summary['payment_methods'][sale.payment_method] += sale_amount

        # Sort top products by total sales
        summary['top_products'] = dict(sorted(
            summary['top_products'].items(),
            key=lambda x: x[1]['total_sales'],
            reverse=True
        )[:10])  # Keep only top 10

        return jsonify({
            'status': 'success',
            'data': summary
        })

    except Exception as e:
        logger.error(f"Error getting sales summary: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@admin_bp.route('/api/sales/detailed')
@login_required
@admin_required
def get_detailed_sales():
    """Get detailed sales data for the frontend."""
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        shop_id = request.args.get('shop_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        # Base query
        query = db.session.query(
            Sale,
            Product,
            Shop
        ).join(
            Product, Sale.product_id == Product.id
        ).join(
            Shop, Sale.shop_id == Shop.id
        )

        # Apply filters
        if start_date:
            query = query.filter(
                Sale.sale_date >= datetime.strptime(
                    start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(
                Sale.sale_date <= datetime.strptime(
                    end_date, '%Y-%m-%d'))
        if shop_id:
            query = query.filter(Sale.shop_id == shop_id)

        # Get total count
        total_count = query.count()

        # Apply pagination
        query = query.order_by(Sale.sale_date.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        # Execute query
        sales_data = query.all()

        # Process data
        detailed_sales = []
        for sale, product, shop in sales_data:
            detailed_sales.append({
                'id': sale.id,
                'date': sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
                'shop_name': shop.name,
                'product_name': product.name,
                'category': product.category,
                'quantity': sale.quantity,
                'price': product.marked_price,
                'total': sale.quantity * product.marked_price,
                'payment_method': sale.payment_method,
                'customer_name': sale.customer_name
            })

        return jsonify({
            'status': 'success',
            'data': {
                'sales': detailed_sales,
                'pagination': {
                    'total': total_count,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total_count + per_page - 1) // per_page
                }
            }
        })

    except Exception as e:
        logger.error(f"Error getting detailed sales: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/products')
@login_required
@admin_required
def manage_products():
    try:
        # Get all products with their inventory across shops
        products = []
        all_products = Product.query.all()
        shops = Shop.query.all()
        
        for product in all_products:
            try:
                shop_inventory = {}
                for shop in shops:
                    inventory = Inventory.query.filter_by(
                        product_id=product.id,
                        shop_id=shop.id
                    ).first()
                    shop_inventory[shop.id] = inventory.quantity if inventory else 0
                
                products.append({
                    'product': product,
                    'shop_inventory': shop_inventory
                })
            except Exception as e:
                app.logger.error(f"Error processing product {product.id}: {str(e)}")
                continue
        
        if not products:
            flash('No products found. Add your first product!', 'info')
        
        return render_template('admin/products.html', 
                             products=products,
                             shops=shops)
    except Exception as e:
        app.logger.error(f"Error loading products: {str(e)}")
        flash('Error loading products. Please try again.', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    """Add a new product to the system."""
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            barcode = request.form.get('barcode')
            category = request.form.get('category')
            marked_price = float(request.form.get('marked_price', 0))
            
            # Create new product
            product = Product(
                name=name,
                barcode=barcode,
                category=category,
                marked_price=marked_price
            )
            db.session.add(product)
            db.session.flush()  # Get the product ID
            
            # Add inventory for each shop
            shops = Shop.query.all()
            for shop in shops:
                quantity = int(request.form.get(f'quantity_{shop.id}', 0))
                if quantity > 0:
                    inventory = Inventory(
                        product_id=product.id,
                        shop_id=shop.id,
                        quantity=quantity
                    )
                    db.session.add(inventory)
            
            db.session.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin.manage_products'))
        except Exception as e:
            app.logger.error(f"Error in add_product: {str(e)}")
            flash('Error adding product. Please try again.', 'error')
            return redirect(url_for('admin.manage_products'))
    
    # GET request - show form
    shops = Shop.query.all()
    return render_template('admin/add_product.html', shops=shops)

@admin_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    """Edit an existing product."""
    try:
        product = Product.query.get_or_404(product_id)
        
        if request.method == 'POST':
            product.name = request.form.get('name')
            product.barcode = request.form.get('barcode')
            product.category = request.form.get('category')
            product.marked_price = float(request.form.get('marked_price', 0))
            
            # Update inventory for each shop
            shops = Shop.query.all()
            for shop in shops:
                quantity = int(request.form.get(f'quantity_{shop.id}', 0))
                inventory = Inventory.query.filter_by(
                    product_id=product.id,
                    shop_id=shop.id
                ).first()
                
                if inventory:
                    inventory.quantity = quantity
                else:
                    inventory = Inventory(
                        product_id=product.id,
                        shop_id=shop.id,
                        quantity=quantity
                    )
                    db.session.add(inventory)
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin.manage_products'))
            
        # GET request - show form
        shops = Shop.query.all()
        shop_inventory = {}
        for shop in shops:
            inventory = Inventory.query.filter_by(
                product_id=product.id,
                shop_id=shop.id
            ).first()
            shop_inventory[shop.id] = inventory.quantity if inventory else 0
            
        return render_template('admin/edit_product.html',
                             product=product,
                             shops=shops,
                             shop_inventory=shop_inventory)
    except Exception as e:
        app.logger.error(f"Error in edit_product: {str(e)}")
        flash('Error updating product. Please try again.', 'error')
        return redirect(url_for('admin.manage_products'))

@admin_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    """Delete a product from the system."""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Delete associated inventory first
        Inventory.query.filter_by(product_id=product.id).delete()
        
        # Delete the product
        db.session.delete(product)
        db.session.commit()
        
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting product: {str(e)}")
        flash('Error deleting product. Please try again.', 'danger')
    
    return redirect(url_for('admin.manage_products'))

@admin_bp.route('/services/<int:service_id>')
@login_required
@admin_required
def get_service(service_id):
    """Get service details for editing."""
    try:
        service = Service.query.get_or_404(service_id)
        return jsonify({
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'price': service.price,
            'duration': service.duration,
            'category': service.category,
            'shop_id': service.shop_id,
            'is_active': service.is_active
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@admin_bp.route('/services/categories/<int:category_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_service_category(category_id):
    """Edit a service category."""
    try:
        category = ServiceCategory.query.get_or_404(category_id)
        
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            return jsonify({
                'success': False,
                'message': 'Category name is required'
            }), 400
        
        # Check if name is already taken by another category
        existing = ServiceCategory.query.filter(
            ServiceCategory.name == name,
            ServiceCategory.id != category_id
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'message': 'A category with this name already exists'
            }), 400
        
        category.name = name
        category.description = description
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating category: {str(e)}'
        }), 500

@admin_bp.route('/services/categories/<int:category_id>')
@login_required
@admin_required
def get_service_category(category_id):
    """Get service category details for editing."""
    try:
        category = ServiceCategory.query.get_or_404(category_id)
        return jsonify({
            'id': category.id,
            'name': category.name,
            'description': category.description
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@admin_bp.route('/admin/download-report')
@login_required
@admin_required
def download_report():
    try:
        # Get date range from request
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'error': 'Start date and end date are required'}), 400
            
        # Convert dates to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Get all shops
        shops = Shop.query.all()
        
        # Create a BytesIO object to store the Excel file
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Add a worksheet for each shop
        for shop in shops:
            worksheet = workbook.add_worksheet(shop.name)
            
            # Add headers
            headers = [
                'Date', 'Total Sales', 'Cash', 'M-Pesa', 'Card', 'Other',
                'Products Sold', 'Services Rendered', 'New Customers',
                'Returning Customers', 'Average Transaction Value'
            ]
            for col, header in enumerate(headers):
                worksheet.write(0, col, header)
            
            # Process each date in the range
            current_date = start_date
            row = 1
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                logger.info(f"Processing date: {date_str}")
                
                try:
                    # Get sales for this date
                    sales = Sale.query.filter(
                        Sale.shop_id == shop.id,
                        func.date(Sale.sale_date) == date_str
                    ).all()
                    
                    # Calculate totals
                    total_sales = sum(sale.price * sale.quantity for sale in sales)
                    
                    # Calculate payment method totals
                    payment_totals = {}
                    for sale in sales:
                        method = sale.payment_method
                        if method not in payment_totals:
                            payment_totals[method] = 0
                        payment_totals[method] += sale.price * sale.quantity
                    
                    # Get product and service counts
                    product_count = sum(1 for sale in sales if sale.product_id is not None)
                    service_count = sum(1 for sale in sales if sale.service_id is not None)
                    
                    # Get customer counts
                    customer_ids = {sale.customer_id for sale in sales if sale.customer_id}
                    new_customers = sum(1 for cid in customer_ids if Customer.query.get(cid).created_at.date() == current_date.date())
                    returning_customers = len(customer_ids) - new_customers
                    
                    # Calculate average transaction value
                    avg_transaction = total_sales / len(sales) if sales else 0
                    
                    # Write data to worksheet
                    worksheet.write(row, 0, date_str)
                    worksheet.write(row, 1, total_sales)
                    worksheet.write(row, 2, payment_totals.get('cash', 0))
                    worksheet.write(row, 3, payment_totals.get('mpesa', 0))
                    worksheet.write(row, 4, payment_totals.get('card', 0))
                    worksheet.write(row, 5, payment_totals.get('other', 0))
                    worksheet.write(row, 6, product_count)
                    worksheet.write(row, 7, service_count)
                    worksheet.write(row, 8, new_customers)
                    worksheet.write(row, 9, returning_customers)
                    worksheet.write(row, 10, avg_transaction)
                    
                except Exception as e:
                    logger.error(f"Error processing date {date_str}: {str(e)}")
                    # Write error message to worksheet
                    worksheet.write(row, 0, date_str)
                    worksheet.write(row, 1, f"Error: {str(e)}")
                
                current_date += timedelta(days=1)
                row += 1
            
            # Add summary section
            summary_row = row + 2
            worksheet.write(summary_row, 0, 'Summary')
            worksheet.write(summary_row + 1, 0, 'Total Sales')
            worksheet.write(summary_row + 1, 1, f'=SUM(B2:B{row})')
            worksheet.write(summary_row + 2, 0, 'Average Daily Sales')
            worksheet.write(summary_row + 2, 1, f'=AVERAGE(B2:B{row})')
            worksheet.write(summary_row + 3, 0, 'Total Products Sold')
            worksheet.write(summary_row + 3, 1, f'=SUM(G2:G{row})')
            worksheet.write(summary_row + 4, 0, 'Total Services Rendered')
            worksheet.write(summary_row + 4, 1, f'=SUM(H2:H{row})')
            worksheet.write(summary_row + 5, 0, 'Total New Customers')
            worksheet.write(summary_row + 5, 1, f'=SUM(I2:I{row})')
            worksheet.write(summary_row + 6, 0, 'Total Returning Customers')
            worksheet.write(summary_row + 6, 1, f'=SUM(J2:J{row})')
            
            # Add charts
            chart_sheet = workbook.add_worksheet(f'{shop.name} Charts')
            
            # Sales trend chart
            sales_chart = workbook.add_chart({'type': 'line'})
            sales_chart.add_series({
                'name': 'Daily Sales',
                'categories': f'={shop.name}!$A$2:$A${row}',
                'values': f'={shop.name}!$B$2:$B${row}',
            })
            sales_chart.set_title({'name': 'Daily Sales Trend'})
            sales_chart.set_x_axis({'name': 'Date'})
            sales_chart.set_y_axis({'name': 'Amount (KES)'})
            chart_sheet.insert_chart('A1', sales_chart)
            
            # Payment methods pie chart
            payment_chart = workbook.add_chart({'type': 'pie'})
            payment_chart.add_series({
                'name': 'Payment Methods',
                'categories': ['Cash', 'M-Pesa', 'Card', 'Other'],
                'values': [
                    f'=SUM({shop.name}!$C$2:$C${row})',
                    f'=SUM({shop.name}!$D$2:$D${row})',
                    f'=SUM({shop.name}!$E$2:$E${row})',
                    f'=SUM({shop.name}!$F$2:$F${row})'
                ],
            })
            payment_chart.set_title({'name': 'Payment Methods Distribution'})
            chart_sheet.insert_chart('A17', payment_chart)
            
            # Customer type pie chart
            customer_chart = workbook.add_chart({'type': 'pie'})
            customer_chart.add_series({
                'name': 'Customer Types',
                'categories': ['New Customers', 'Returning Customers'],
                'values': [
                    f'=SUM({shop.name}!$I$2:$I${row})',
                    f'=SUM({shop.name}!$J$2:$J${row})'
                ],
            })
            customer_chart.set_title({'name': 'Customer Distribution'})
            chart_sheet.insert_chart('I1', customer_chart)
        
        # Save the workbook
        workbook.close()
        output.seek(0)
        
        # Create the response
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'sales_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.xlsx'
        )
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return jsonify({'error': str(e)}), 500
