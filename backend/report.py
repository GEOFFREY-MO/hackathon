from flask import Blueprint, jsonify, request
from database import db, Report, Shop, User
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
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

        # Get query parameters
        report_type = request.args.get('type')
        schedule = request.args.get('schedule')

        # Build query
        query = Report.query.filter_by(shop_id=user.shop_id)
        
        if report_type:
            query = query.filter_by(type=report_type)
        if schedule:
            query = query.filter_by(schedule=schedule)
            
        reports = query.order_by(Report.created_at.desc()).all()

        return jsonify([{
            'id': report.id,
            'title': report.title,
            'type': report.type,
            'parameters': report.parameters,
            'created_at': report.created_at.isoformat(),
            'last_generated': report.last_generated.isoformat() if report.last_generated else None,
            'schedule': report.schedule
        } for report in reports])

    except Exception as e:
        logging.error(f"Error getting reports: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@report_bp.route('/api/reports', methods=['POST'])
@jwt_required()
def create_report():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404

        data = request.get_json()
        if not data or 'title' not in data or 'type' not in data:
            return jsonify({'error': 'Title and type are required'}), 400

        report = Report(
            shop_id=user.shop_id,
            user_id=current_user_id,
            title=data['title'],
            type=data['type'],
            parameters=data.get('parameters', {}),
            schedule=data.get('schedule', 'none')
        )
        db.session.add(report)
        db.session.commit()

        return jsonify({
            'id': report.id,
            'title': report.title,
            'type': report.type,
            'parameters': report.parameters,
            'created_at': report.created_at.isoformat(),
            'last_generated': report.last_generated.isoformat() if report.last_generated else None,
            'schedule': report.schedule
        }), 201

    except Exception as e:
        logging.error(f"Error creating report: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@report_bp.route('/api/reports/<int:report_id>', methods=['PUT'])
@jwt_required()
def update_report(report_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404

        report = Report.query.filter_by(
            id=report_id,
            shop_id=user.shop_id
        ).first()
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        if 'title' in data:
            report.title = data['title']
        if 'type' in data:
            report.type = data['type']
        if 'parameters' in data:
            report.parameters = data['parameters']
        if 'schedule' in data:
            report.schedule = data['schedule']

        db.session.commit()

        return jsonify({
            'id': report.id,
            'title': report.title,
            'type': report.type,
            'parameters': report.parameters,
            'created_at': report.created_at.isoformat(),
            'last_generated': report.last_generated.isoformat() if report.last_generated else None,
            'schedule': report.schedule
        })

    except Exception as e:
        logging.error(f"Error updating report: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@report_bp.route('/api/reports/<int:report_id>', methods=['DELETE'])
@jwt_required()
def delete_report(report_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404

        report = Report.query.filter_by(
            id=report_id,
            shop_id=user.shop_id
        ).first()
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404

        db.session.delete(report)
        db.session.commit()

        return jsonify({'message': 'Report deleted successfully'})

    except Exception as e:
        logging.error(f"Error deleting report: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@report_bp.route('/api/reports/<int:report_id>/generate', methods=['POST'])
@jwt_required()
def generate_report(report_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.shop_id:
            return jsonify({'error': 'Shop not found'}), 404

        report = Report.query.filter_by(
            id=report_id,
            shop_id=user.shop_id
        ).first()
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404

        # Update last generated timestamp
        report.last_generated = datetime.utcnow()
        db.session.commit()

        # Here you would implement the actual report generation logic
        # based on the report type and parameters
        # For now, we'll just return a success message
        return jsonify({
            'message': 'Report generation started',
            'report_id': report.id,
            'type': report.type
        })

    except Exception as e:
        logging.error(f"Error generating report: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 