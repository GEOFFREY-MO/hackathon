from flask import Blueprint, jsonify
from backend.database import db, Settings, Shop, User
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/api/settings', methods=['GET'])
@jwt_required()
def get_settings():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        settings = Settings.query.filter_by(shop_id=user.shop_id).first()
        if not settings:
            return jsonify({'error': 'Settings not found'}), 404
        return jsonify({
            'id': settings.id,
            'shop_id': settings.shop_id,
            'setting_key': settings.setting_key,
            'setting_value': settings.setting_value,
            'created_at': settings.created_at.isoformat()
        })
    except Exception as e:
        logging.error(f"Error getting settings: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 