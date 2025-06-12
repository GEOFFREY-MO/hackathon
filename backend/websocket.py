from flask import Blueprint
from flask_socketio import emit
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

websocket_bp = Blueprint('websocket', __name__)

@websocket_bp.route('/ws', methods=['GET'])
@jwt_required()
def handle_connect():
    try:
        current_user_id = get_jwt_identity()
        emit('connect', {'message': 'Connected to websocket'})
    except Exception as e:
        logging.error(f"Error handling websocket connect: {str(e)}")
        emit('error', {'error': 'Internal server error'})
