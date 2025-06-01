from datetime import datetime, timedelta
from flask import jsonify, request, render_template, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from . import admin_bp
from ..models import Shop, User, Sale
from .. import db
from ..decorators import admin_required
import openai
import os
from backend.utils.analytics import (
    get_sales_trend,
    get_category_distribution,
    get_hourly_distribution,
    get_stock_levels,
    get_shop_performance,
    get_top_products,
    get_reorder_trend
)

# Initialize OpenAI client
openai.api_key = os.getenv('OPENAI_API_KEY')

@admin_bp.route('/shops/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_shop():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            location = request.form.get('location')
            contact = request.form.get('contact')
            email = request.form.get('email')
            
            # Validate required fields
            if not all([name, location, contact, email]):
                return jsonify({
                    'success': False,
                    'message': 'All fields are required'
                }), 400
            
            # Check if shop name already exists
            existing_shop = Shop.query.filter_by(name=name).first()
            if existing_shop:
                return jsonify({
                    'success': False,
                    'message': 'A shop with this name already exists'
                }), 400
            
            # Create new shop
            new_shop = Shop(
                name=name,
                location=location,
                contact=contact,
                email=email
            )
            
            db.session.add(new_shop)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Shop added successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error adding shop: {str(e)}'
            }), 500
    
    return render_template('admin/add_shop.html')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    shops = Shop.query.all()
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            role = request.form.get('role')
            shop_id = request.form.get('shop_id')
            
            # Validate required fields
            if not all([name, email, role]):
                return jsonify({
                    'success': False,
                    'message': 'Name, email, and role are required'
                }), 400
            
            # Validate email format
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                return jsonify({
                    'success': False,
                    'message': 'Invalid email format'
                }), 400
            
            # Validate role
            if role not in ['employee', 'admin']:
                return jsonify({
                    'success': False,
                    'message': 'Invalid role selected'
                }), 400
            
            # Check if email is already taken by another user
            existing_user = User.query.filter(User.email == email, User.id != user_id).first()
            if existing_user:
                return jsonify({
                    'success': False,
                    'message': 'Email is already taken by another user'
                }), 400
            
            # Update user
            user.name = name
            user.email = email
            user.role = role
            user.shop_id = shop_id if shop_id else None
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'User updated successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error updating user: {str(e)}'
            }), 500
    
    return render_template('admin/edit_user.html', user=user, shops=shops)

@admin_bp.route('/shops/<int:shop_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_shop(shop_id):
    try:
        shop = Shop.query.get_or_404(shop_id)
        
        # Check if shop has any users assigned
        users = User.query.filter_by(shop_id=shop_id).first()
        if users:
            return jsonify({
                'success': False,
                'message': 'Cannot delete shop: There are users assigned to this shop'
            }), 400
        
        # Delete the shop
        db.session.delete(shop)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Shop deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting shop: {str(e)}'
        }), 500

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deleting the last admin
        if user.role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                return jsonify({
                    'success': False,
                    'message': 'Cannot delete the last admin user'
                }), 400
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting user: {str(e)}'
        }), 500

@admin_bp.route('/ai-assistant', methods=['POST'])
@login_required
@admin_required
def ai_assistant():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'response': 'No message provided'
            }), 400
            
        message = data.get('message', '').strip()
        if not message:
            return jsonify({
                'success': False,
                'response': 'Message cannot be empty'
            }), 400
        
        # Get sales data for analysis
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)
        
        # Get sales data for different time periods
        today_sales = Sale.query.filter(
            Sale.shop_id.in_([shop.id for shop in current_user.shops]),
            func.date(Sale.timestamp) == today
        ).all()
        
        week_sales = Sale.query.filter(
            Sale.shop_id.in_([shop.id for shop in current_user.shops]),
            func.date(Sale.timestamp) >= start_of_week
        ).all()
        
        month_sales = Sale.query.filter(
            Sale.shop_id.in_([shop.id for shop in current_user.shops]),
            func.date(Sale.timestamp) >= start_of_month
        ).all()
        
        year_sales = Sale.query.filter(
            Sale.shop_id.in_([shop.id for shop in current_user.shops]),
            func.date(Sale.timestamp) >= start_of_year
        ).all()
        
        # Calculate metrics
        def calculate_metrics(sales):
            total_sales = sum(sale.total_amount for sale in sales)
            total_transactions = len(sales)
            avg_transaction = total_sales / total_transactions if total_transactions > 0 else 0
            return {
                'total_sales': total_sales,
                'total_transactions': total_transactions,
                'avg_transaction': avg_transaction
            }
        
        today_metrics = calculate_metrics(today_sales)
        week_metrics = calculate_metrics(week_sales)
        month_metrics = calculate_metrics(month_sales)
        year_metrics = calculate_metrics(year_sales)
        
        # Prepare context for the LLM
        context = {
            'today_metrics': today_metrics,
            'week_metrics': week_metrics,
            'month_metrics': month_metrics,
            'year_metrics': year_metrics,
            'shops': [shop.name for shop in current_user.shops]
        }
        
        # Create system message with context
        system_message = f"""You are a helpful AI assistant for a retail management system. You have access to the following sales data:

Today's Sales:
- Total Sales: KES {context['today_metrics']['total_sales']:,.2f}
- Total Transactions: {context['today_metrics']['total_transactions']}
- Average Transaction: KES {context['today_metrics']['avg_transaction']:,.2f}

This Week's Sales:
- Total Sales: KES {context['week_metrics']['total_sales']:,.2f}
- Total Transactions: {context['week_metrics']['total_transactions']}
- Average Transaction: KES {context['week_metrics']['avg_transaction']:,.2f}

This Month's Sales:
- Total Sales: KES {context['month_metrics']['total_sales']:,.2f}
- Total Transactions: {context['month_metrics']['total_transactions']}
- Average Transaction: KES {context['month_metrics']['avg_transaction']:,.2f}

This Year's Sales:
- Total Sales: KES {context['year_metrics']['total_sales']:,.2f}
- Total Transactions: {context['year_metrics']['total_transactions']}
- Average Transaction: KES {context['year_metrics']['avg_transaction']:,.2f}

Available Shops: {', '.join(context['shops'])}

You can help with:
1. Sales analysis and comparisons
2. Performance reports
3. Shop comparisons
4. Time-based analytics
5. General business insights

Provide clear, concise, and helpful responses based on the available data. Always format currency values with the KES symbol and use proper number formatting."""
        
        try:
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content
            
        except Exception as e:
            current_app.logger.error(f"OpenAI API Error: {str(e)}")
            # Fallback to basic responses if API call fails
            if 'sales report' in message.lower():
                ai_response = f"""Here's your sales report:
                
Today's Sales:
- Total Sales: KES {today_metrics['total_sales']:,.2f}
- Total Transactions: {today_metrics['total_transactions']}
- Average Transaction: KES {today_metrics['avg_transaction']:,.2f}

This Week's Sales:
- Total Sales: KES {week_metrics['total_sales']:,.2f}
- Total Transactions: {week_metrics['total_transactions']}
- Average Transaction: KES {week_metrics['avg_transaction']:,.2f}

This Month's Sales:
- Total Sales: KES {month_metrics['total_sales']:,.2f}
- Total Transactions: {month_metrics['total_transactions']}
- Average Transaction: KES {month_metrics['avg_transaction']:,.2f}

This Year's Sales:
- Total Sales: KES {year_metrics['total_sales']:,.2f}
- Total Transactions: {year_metrics['total_transactions']}
- Average Transaction: KES {year_metrics['avg_transaction']:,.2f}"""
            elif 'help' in message.lower():
                ai_response = """I can help you with:
1. Sales Report - Get detailed sales metrics for today, week, month, and year
2. Sales Analysis - Compare sales performance across different shops
3. Performance Reports - Get detailed performance metrics
4. Time-based Analytics - Analyze sales trends over different time periods
5. General Business Insights - Get recommendations and insights

Just ask me about any of these topics!"""
            else:
                ai_response = "I'm not sure I understand. Try asking for a 'sales report', 'sales analysis', or type 'help' for available commands."
        
        return jsonify({
            'success': True,
            'response': ai_response
        })
        
    except Exception as e:
        current_app.logger.error(f"AI Assistant Error: {str(e)}")
        return jsonify({
            'success': False,
            'response': 'Sorry, I encountered an error. Please try again.'
        }), 500

@admin_bp.route('/dashboard/recent-sales')
@login_required
@admin_required
def get_recent_sales():
    try:
        period = request.args.get('period', 'today')
        today = datetime.now().date()
        
        # Define time periods
        if period == 'today':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday())
        elif period == 'month':
            start_date = today.replace(day=1)
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid period specified'
            }), 400

        # Query recent sales
        recent_sales = Sale.query.filter(
            Sale.sale_date >= start_date
        ).order_by(Sale.sale_date.desc()).limit(50).all()

        # Format sales data
        sales_data = [{
            'sale_date': sale.sale_date.strftime('%Y-%m-%d %H:%M'),
            'shop_name': sale.shop.name,
            'product_name': sale.product.name,
            'quantity': sale.quantity,
            'total': float(sale.price * sale.quantity)
        } for sale in recent_sales]

        return jsonify({
            'success': True,
            'sales': sales_data
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching recent sales: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error fetching recent sales data'
        }), 500

@admin_bp.route('/analytics/data')
@login_required
def analytics_data():
    """Provide analytics data for the dashboard charts."""
    if current_user.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    try:
        period = request.args.get('period', 'week')
        quick = request.args.get('quick', 'false').lower() == 'true'

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
            'category_distribution': get_category_distribution(sales),
            'hourly_distribution': get_hourly_distribution(sales),
            'stock_levels': get_stock_levels()
        }

        # Add additional data for full analytics view
        if not quick:
            data.update({
                'shop_performance': get_shop_performance(sales),
                'top_products': get_top_products(sales),
                'reorder_trend': get_reorder_trend(
                    start_date,
                    end_date,
                    date_format)
            })

        return jsonify(data)
    except Exception as e:
        logger.error(f"Error generating analytics data: {str(e)}")
        return jsonify({"error": "Failed to generate analytics data"}), 500 