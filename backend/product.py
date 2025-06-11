from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from backend.database import db, Product, Inventory, Shop, Sale
from sqlalchemy import or_
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

product_bp = Blueprint('product', __name__)

# View all products with inventory
@product_bp.route('/')
@login_required
def product_list():
    try:
        logger.info(f"User role: {current_user.role}")
        # Get search and filter parameters
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        
        # Base query
        query = Product.query
        
        # Apply search filter
        if search:
            query = query.filter(
                or_(
                    Product.name.ilike(f'%{search}%'),
                    Product.barcode.ilike(f'%{search}%')
                )
            )
        
        # Apply category filter
        if category:
            query = query.filter(Product.category == category)
        
        # Get all products
        products = query.all()
        logger.info(f"Found {len(products)} products")
        
        # Get inventory for each product
        product_inventory = {}
        for product in products:
            try:
                if current_user.role == 'admin':
                    # For admin, get total inventory across all shops
                    total_quantity = db.session.query(db.func.sum(Inventory.quantity))\
                        .filter(Inventory.product_id == product.id)\
                        .scalar() or 0
                    product_inventory[product.id] = total_quantity
                    logger.info(f"Admin view - Product {product.id}: {total_quantity} total quantity")
                else:
                    # For employees, get inventory for their shop only
                    inventory = Inventory.query.filter_by(
                        product_id=product.id,
                        shop_id=current_user.shop_id
                    ).first()
                    product_inventory[product.id] = inventory.quantity if inventory else 0
                    logger.info(f"Employee view - Product {product.id}: {product_inventory[product.id]} quantity")
            except Exception as e:
                logger.error(f"Error processing inventory for product {product.id}: {str(e)}")
                product_inventory[product.id] = 0
        
        # Get unique categories for filter dropdown
        categories = db.session.query(Product.category).distinct().all()
        categories = [cat[0] for cat in categories if cat[0]]
        
        return render_template('product/products.html', 
                             products=products,
                             inventory=product_inventory,
                             categories=categories,
                             search=search,
                             selected_category=category)
    except Exception as e:
        logger.error(f"Error in product_list: {str(e)}")
        flash('Error loading products.')
        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))

# Add a new product
@product_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        try:
            name = request.form['name'].strip()
            barcode = request.form['barcode'].strip()
            category = request.form['category'].strip()
            marked_price = float(request.form['marked_price'])
            initial_quantity = int(request.form.get('initial_quantity', 0))

            # Validate inputs
            if not name or not barcode:
                flash('Name and barcode are required.')
                return redirect(url_for('product.add_product'))

            # Check if barcode already exists
            if Product.query.filter_by(barcode=barcode).first():
                flash('A product with this barcode already exists.')
                return redirect(url_for('product.add_product'))

            # Create new product
            new_product = Product(
                name=name,
                barcode=barcode,
                category=category,
                marked_price=marked_price
            )
            db.session.add(new_product)
            db.session.flush()

            # Add initial inventory if quantity provided
            if initial_quantity > 0:
                if current_user.role == 'admin':
                    # For admin, add inventory to all shops
                    shops = Shop.query.all()
                    for shop in shops:
                        inventory = Inventory(
                            shop_id=shop.id,
                            product_id=new_product.id,
                            quantity=initial_quantity
                        )
                        db.session.add(inventory)
                else:
                    # For employees, add inventory to their shop only
                    inventory = Inventory(
                        shop_id=current_user.shop_id,
                        product_id=new_product.id,
                        quantity=initial_quantity
                    )
                    db.session.add(inventory)

            db.session.commit()
            flash('Product added successfully!')
            return redirect(url_for('product.product_list'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding product.')
            return redirect(url_for('product.add_product'))

    return render_template('add_product.html')

# Edit product
@product_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    try:
        product = Product.query.get_or_404(id)
        
        if request.method == 'POST':
            name = request.form['name'].strip()
            barcode = request.form['barcode'].strip()
            category = request.form['category'].strip()
            marked_price = float(request.form['marked_price'])

            # Validate inputs
            if not name or not barcode:
                flash('Name and barcode are required.')
                return redirect(url_for('product.edit_product', id=id))

            # Check if barcode already exists for another product
            existing = Product.query.filter_by(barcode=barcode).first()
            if existing and existing.id != id:
                flash('A product with this barcode already exists.')
                return redirect(url_for('product.edit_product', id=id))

            # Update product
            product.name = name
            product.barcode = barcode
            product.category = category
            product.marked_price = marked_price

            db.session.commit()
            flash('Product updated successfully!')
            return redirect(url_for('product.product_list'))

        return render_template('edit_product.html', product=product)
    except Exception as e:
        flash('Error editing product.')
        return redirect(url_for('product.product_list'))

# Update inventory
@product_bp.route('/inventory/<int:id>', methods=['POST'])
@login_required
def update_inventory(id):
    try:
        product = Product.query.get_or_404(id)
        quantity = int(request.form.get('quantity', 0))
        action = request.form.get('action', 'set')  # 'set' or 'adjust'

        inventory = Inventory.query.filter_by(
            product_id=id,
            shop_id=current_user.shop_id
        ).first()

        if not inventory:
            inventory = Inventory(
                product_id=id,
                shop_id=current_user.shop_id,
                quantity=0
            )
            db.session.add(inventory)

        if action == 'set':
            inventory.quantity = quantity
        else:  # adjust
            inventory.quantity += quantity

        db.session.commit()
        flash('Inventory updated successfully!')
        return redirect(url_for('product.product_list'))
    except Exception as e:
        db.session.rollback()
        flash('Error updating inventory.')
        return redirect(url_for('product.product_list'))

# Barcode scan endpoint
@product_bp.route('/scan', methods=['POST'])
@login_required
def scan_barcode():
    try:
        barcode = request.json.get('barcode')
        if not barcode:
            return jsonify({'error': 'No barcode provided'}), 400

        product = Product.query.filter_by(barcode=barcode).first()
        if not product:
            return jsonify({'error': 'Product not found'}), 404

        inventory = Inventory.query.filter_by(
            product_id=product.id,
            shop_id=current_user.shop_id
        ).first()

        return jsonify({
            'id': product.id,
            'name': product.name,
            'barcode': product.barcode,
            'category': product.category,
            'marked_price': product.marked_price,
            'quantity': inventory.quantity if inventory else 0
        })
    except Exception as e:
        return jsonify({'error': 'Error processing barcode'}), 500

@product_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_product(id):
    """Delete a product."""
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.select_role'))
    
    try:
        product = Product.query.get_or_404(id)
        
        # Check if product has any inventory
        if Inventory.query.filter_by(product_id=id).first():
            flash('Cannot delete product with inventory items.', 'danger')
            return redirect(url_for('product.product_list'))
        
        db.session.delete(product)
        db.session.commit()
        
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting product.', 'danger')
    
    return redirect(url_for('product.product_list'))

@product_bp.route('/<int:id>/sell', methods=['POST'])
@login_required
def sell_product(id):
    """Handle product sales."""
    try:
        product = Product.query.get_or_404(id)
        quantity = int(request.form.get('quantity', 0))
        price = float(request.form.get('price', 0))
        customer_name = request.form.get('customer_name')
        
        # Get current inventory
        inventory = Inventory.query.filter_by(
            product_id=id,
            shop_id=current_user.shop_id
        ).first()
        
        if not inventory or inventory.quantity < quantity:
            flash('Not enough stock available.', 'danger')
            return redirect(url_for('employee.inventory'))
        
        # Create sale record
        sale = Sale(
            product_id=id,
            shop_id=current_user.shop_id,
            employee_id=current_user.id,
            quantity=quantity,
            price=price,
            customer_name=customer_name
        )
        
        # Update inventory
        inventory.quantity -= quantity
        
        db.session.add(sale)
        db.session.commit()
        
        flash(f'Successfully sold {quantity} {product.name}(s)!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error processing sale.', 'danger')
    
    return redirect(url_for('employee.inventory'))

@product_bp.route('/<int:id>/get', methods=['GET'])
@login_required
def get_product(id):
    product = Product.query.get_or_404(id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'barcode': product.barcode,
        'category': product.category,
        'marked_price': product.marked_price,
        'reorder_level': product.reorder_level
    })
