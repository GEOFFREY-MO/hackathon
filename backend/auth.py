# backend/auth.py

from flask import Blueprint, render_template, redirect, request, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import re
from database.models import db, User, Shop
from datetime import datetime
import logging

auth_bp = Blueprint('auth', __name__)

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# -------------------------------
# ROLE SELECTION
# -------------------------------
@auth_bp.route('/select_role')
def select_role():
    return render_template('select_role.html')

# -------------------------------
# LOGIN
# -------------------------------
@auth_bp.route('/login')
def login():
    return render_template('select_role.html')

@auth_bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        try:
            email = request.form['email'].strip().lower()
            password = request.form['password']
            
            # Validate inputs
            if not email or not password:
                flash('Email and password are required.', 'danger')
                return redirect(url_for('auth.admin_login'))
            
            # Get user and verify role
            user = User.query.filter_by(email=email).first()
            if not user:
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('auth.admin_login'))
            
            if user.role != 'admin':
                flash('Access denied. Admin privileges required.', 'danger')
                return redirect(url_for('auth.admin_login'))
            
            # Verify password
            if not check_password_hash(user.password_hash, password):
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('auth.admin_login'))
            
            # Login successful
            login_user(user)
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            print(f"Login error: {str(e)}")  # Add logging
            flash('An error occurred during login. Please try again.', 'danger')
            return redirect(url_for('auth.admin_login'))

    return render_template('admin_login.html')

@auth_bp.route('/employee_login', methods=['GET', 'POST'])
def employee_login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email, role='employee').first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('auth.shop_select'))
        else:
            flash('Invalid employee credentials.')
            return redirect(url_for('auth.employee_login'))

    return render_template('employee_login.html')

# -------------------------------
# REGISTER
# -------------------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
            shop_id = request.form.get('shop_id')

            # Validate required fields
            if not all([name, email, password, role]):
                flash('All fields are required.', 'danger')
                return redirect(url_for('auth.register'))

            # Check if email already exists
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
                return redirect(url_for('auth.register'))

            if role == 'admin':
                # For new admin, create their first shop
                shop = Shop(
                    name=f"{name}'s Shop",
                    location="To be updated",
                    admin_id=None  # Will be set after user creation
                )
                db.session.add(shop)
                db.session.flush()  # Get the shop ID

                # Create admin user
                user = User(
                    name=name,
                    email=email,
                    password_hash=generate_password_hash(password),
                    role='admin',
                    shop_id=shop.id,
                    admin_id=None  # Admins don't have an admin
                )
                db.session.add(user)
                db.session.flush()  # Get the user ID

                # Update shop with admin_id
                shop.admin_id = user.id

            else:  # role == 'employee'
                # For employees, verify shop and admin
                if not shop_id:
                    flash('Shop selection is required for employees.', 'danger')
                    return redirect(url_for('auth.register'))

                # Verify shop exists and get its admin
                shop = Shop.query.get(shop_id)
                if not shop:
                    flash('Invalid shop selection.', 'danger')
                    return redirect(url_for('auth.register'))

                # Create employee user
                user = User(
                    name=name,
                    email=email,
                    password_hash=generate_password_hash(password),
                    role='employee',
                    shop_id=shop_id,
                    admin_id=shop.admin_id  # Set the shop's admin as this employee's admin
                )
                db.session.add(user)

            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            flash('Error during registration.', 'danger')
            return redirect(url_for('auth.register'))

    # For GET request, get shops for employee registration
    shops = Shop.query.all() if request.args.get('role') == 'employee' else []
    return render_template('register.html', shops=shops)

# -------------------------------
# LOGOUT
# -------------------------------
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()  # Clear active shop and other session variables
    return redirect(url_for('auth.login'))

# -------------------------------
# SHOP SELECTION (EMPLOYEE ONLY)
# -------------------------------
@auth_bp.route('/shop_select', methods=['GET', 'POST'])
@login_required
def shop_select():
    if current_user.role != 'employee':
        # Redirect admins back to their dashboard
        return redirect(url_for('admin.admin_dashboard'))

    try:
        # Check if user has a shop assigned
        if not current_user.shop_id:
            flash("No shop has been assigned to your account. Please contact an administrator.")
            return redirect(url_for('auth.logout'))

        # Get the shop
        employee_shop = Shop.query.get(current_user.shop_id)
        if not employee_shop:
            flash("Your assigned shop could not be found. Please contact an administrator.")
            return redirect(url_for('auth.logout'))

        if request.method == 'POST':
            selected_shop = request.form.get('shop_id')
            
            # Security: ensure they only select their assigned shop
            if not selected_shop or str(employee_shop.id) != selected_shop:
                flash("Invalid shop selection.")
                return redirect(url_for('auth.shop_select'))

            # Store the shop in session
            session['active_shop'] = selected_shop
            return redirect(url_for('employee.dashboard'))

        # For GET request, show the shop selection page
        return render_template('shop_select.html', shop=employee_shop)

    except Exception as e:
        print(f"Error in shop_select: {str(e)}")
        flash(f'An error occurred while selecting shop: {str(e)}')
        return redirect(url_for('auth.select_role'))
