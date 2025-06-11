from flask import Blueprint, jsonify
from backend.database import db, Notification, Shop, User
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

notification_bp = Blueprint('notification', __name__)

@notification_bp.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        notifications = Notification.query.filter_by(shop_id=user.shop_id).all()
        return jsonify([{
            'id': notification.id,
            'message': notification.message,
            'type': notification.type,
            'created_at': notification.created_at.isoformat()
        } for notification in notifications])
    except Exception as e:
        logging.error(f"Error getting notifications: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 