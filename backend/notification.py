from flask import Blueprint, jsonify, request
from backend.database import db, Notification, Shop, User
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
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

        # Get query parameters
        is_read = request.args.get('is_read')
        notification_type = request.args.get('type')
        limit = request.args.get('limit', default=50, type=int)

        # Build query
        query = Notification.query.filter_by(shop_id=user.shop_id)
        
        if is_read is not None:
            query = query.filter_by(is_read=is_read.lower() == 'true')
        if notification_type:
            query = query.filter_by(type=notification_type)
            
        # Order by created_at desc and limit results
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()

        return jsonify([{
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.type,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat()
        } for notification in notifications])

    except Exception as e:
        logging.error(f"Error getting notifications: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@notification_bp.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(notification_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404

        notification = Notification.query.filter_by(
            id=notification_id,
            shop_id=user.shop_id
        ).first()
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404

        notification.is_read = True
        db.session.commit()

        return jsonify({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.type,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat()
        })

    except Exception as e:
        logging.error(f"Error marking notification as read: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@notification_bp.route('/api/notifications/read-all', methods=['PUT'])
@jwt_required()
def mark_all_notifications_read():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404

        Notification.query.filter_by(
            shop_id=user.shop_id,
            is_read=False
        ).update({'is_read': True})
        
        db.session.commit()

        return jsonify({'message': 'All notifications marked as read'})

    except Exception as e:
        logging.error(f"Error marking all notifications as read: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@notification_bp.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404

        notification = Notification.query.filter_by(
            id=notification_id,
            shop_id=user.shop_id
        ).first()
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404

        db.session.delete(notification)
        db.session.commit()

        return jsonify({'message': 'Notification deleted successfully'})

    except Exception as e:
        logging.error(f"Error deleting notification: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 