from flask import Blueprint, jsonify, request
from database import db, Expense, Shop, User
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_login import current_user
from datetime import datetime
import logging

expense_bp = Blueprint('expense', __name__)

@expense_bp.route('/api/expenses', methods=['GET'])
@jwt_required()
def get_expenses():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        expenses = Expense.query.filter_by(shop_id=user.shop_id).all()
        return jsonify([{
            'id': expense.id,
            'amount': float(expense.amount),
            'description': expense.description,
            'category': expense.category,
            'date': expense.date.isoformat(),
            'created_by': expense.created_by
        } for expense in expenses])
    except Exception as e:
        logging.error(f"Error getting expenses: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@expense_bp.route('/api/expenses', methods=['POST'])
@jwt_required()
def create_expense():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        # Admin-only creation
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        if not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        data = request.get_json()
        if not data or 'amount' not in data or 'category' not in data or 'description' not in data:
            return jsonify({'error': 'Amount, category, and description are required'}), 400
        
        expense = Expense(
            shop_id=user.shop_id,
            amount=data['amount'],
            description=data['description'],
            category=data['category'],
            date=datetime.strptime(data.get('date', datetime.utcnow().isoformat()), '%Y-%m-%dT%H:%M:%S.%fZ'),
            created_by=current_user_id
        )
        db.session.add(expense)
        db.session.commit()
        return jsonify({
            'id': expense.id,
            'amount': float(expense.amount),
            'description': expense.description,
            'category': expense.category,
            'date': expense.date.isoformat(),
            'created_by': expense.created_by
        }), 201
    except Exception as e:
        logging.error(f"Error creating expense: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@expense_bp.route('/api/expenses/<int:expense_id>', methods=['PUT'])
@jwt_required()
def update_expense(expense_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        if not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        expense = Expense.query.filter_by(
            id=expense_id,
            shop_id=user.shop_id
        ).first()
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        if 'amount' in data:
            expense.amount = data['amount']
        if 'description' in data:
            expense.description = data['description']
        if 'category' in data:
            expense.category = data['category']
        if 'date' in data:
            expense.date = datetime.strptime(data['date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        db.session.commit()
        return jsonify({
            'id': expense.id,
            'amount': float(expense.amount),
            'description': expense.description,
            'category': expense.category,
            'date': expense.date.isoformat(),
            'created_by': expense.created_by
        })
    except Exception as e:
        logging.error(f"Error updating expense: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@expense_bp.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@jwt_required()
def delete_expense(expense_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        if not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        expense = Expense.query.filter_by(
            id=expense_id,
            shop_id=user.shop_id
        ).first()
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
        db.session.delete(expense)
        db.session.commit()
        return jsonify({'message': 'Expense deleted successfully'})
    except Exception as e:
        logging.error(f"Error deleting expense: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
