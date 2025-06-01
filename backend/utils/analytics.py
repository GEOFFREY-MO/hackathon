from datetime import datetime, timedelta
from backend.models import Sale, Product, InventoryUpdate

def get_sales_trend(sales, start_date, end_date, date_format):
    """Generate sales trend data for line chart."""
    sales_by_date = {}
    current_date = start_date
    while current_date <= end_date:
        key = current_date.strftime(date_format)
        sales_by_date[key] = 0
        if date_format == '%Y-%m':
            current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
        else:
            current_date += timedelta(days=1)

    for sale in sales:
        key = sale.sale_date.strftime(date_format)
        if key in sales_by_date:
            sales_by_date[key] += sale.price * sale.quantity

    return {
        'labels': list(sales_by_date.keys()),
        'data': list(sales_by_date.values())
    }

def get_category_distribution(sales):
    """Generate category distribution data for doughnut chart."""
    category_sales = {}
    for sale in sales:
        category = sale.product.category
        if category not in category_sales:
            category_sales[category] = 0
        category_sales[category] += sale.price * sale.quantity

    # Sort categories by sales amount
    sorted_categories = sorted(category_sales.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'labels': [cat for cat, _ in sorted_categories],
        'data': [amount for _, amount in sorted_categories]
    }

def get_hourly_distribution(sales):
    """Generate hourly distribution data for bar chart."""
    hourly_sales = {hour: 0 for hour in range(24)}
    
    for sale in sales:
        hour = sale.sale_date.hour
        hourly_sales[hour] += sale.price * sale.quantity

    return {
        'labels': [f"{hour:02d}:00" for hour in range(24)],
        'data': [hourly_sales[hour] for hour in range(24)]
    }

def get_stock_levels():
    """Generate stock levels data for bar chart."""
    products = Product.query.all()
    return {
        'labels': [product.name for product in products],
        'current': [product.current_stock for product in products],
        'reorder': [product.reorder_level for product in products]
    }

def get_shop_performance(sales):
    """Generate shop performance data for bar chart."""
    shop_sales = {}
    for sale in sales:
        shop_name = sale.shop.name
        if shop_name not in shop_sales:
            shop_sales[shop_name] = 0
        shop_sales[shop_name] += sale.price * sale.quantity

    # Sort shops by sales amount
    sorted_shops = sorted(shop_sales.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'labels': [shop for shop, _ in sorted_shops],
        'data': [amount for _, amount in sorted_shops]
    }

def get_top_products(sales):
    """Generate top products data for bar chart."""
    product_sales = {}
    for sale in sales:
        product_name = sale.product.name
        if product_name not in product_sales:
            product_sales[product_name] = 0
        product_sales[product_name] += sale.price * sale.quantity

    # Sort products by sales amount and get top 10
    sorted_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'labels': [product for product, _ in sorted_products],
        'data': [amount for _, amount in sorted_products]
    }

def get_reorder_trend(start_date, end_date, date_format):
    """Generate reorder trend data for line chart."""
    reorders = InventoryUpdate.query.filter(
        InventoryUpdate.update_type == 'reorder',
        InventoryUpdate.timestamp >= start_date,
        InventoryUpdate.timestamp <= end_date
    ).all()

    reorders_by_date = {}
    current_date = start_date
    while current_date <= end_date:
        key = current_date.strftime(date_format)
        reorders_by_date[key] = 0
        if date_format == '%Y-%m':
            current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
        else:
            current_date += timedelta(days=1)

    for reorder in reorders:
        key = reorder.timestamp.strftime(date_format)
        if key in reorders_by_date:
            reorders_by_date[key] += reorder.quantity

    return {
        'labels': list(reorders_by_date.keys()),
        'data': list(reorders_by_date.values())
    } 