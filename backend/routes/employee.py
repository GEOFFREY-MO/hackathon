# routes/employee.py

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import get_shop_inventory, get_low_stock_items  # Your database functions

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/employee/dashboard')
@login_required
def employee_dashboard():
    shop = current_user.shop  # Assuming each employee is linked to a shop
    inventory = get_shop_inventory(shop.id)
    low_stock = get_low_stock_items(shop.id)

    return render_template('employee_dashboard.html', shop=shop, inventory=inventory, low_stock=low_stock)
