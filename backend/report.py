from flask import Blueprint, jsonify
from backend.database import db, Report, Shop, User
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

report_bp = Blueprint('report', __name__)

@report_bp.route('/api/reports', methods=['GET'])
@jwt_required()
def get_reports():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        reports = Report.query.filter_by(shop_id=user.shop_id).all()
        return jsonify([{
            'id': report.id,
            'title': report.title,
            'content': report.content,
            'created_at': report.created_at.isoformat()
        } for report in reports])
    except Exception as e:
        logging.error(f"Error getting reports: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 