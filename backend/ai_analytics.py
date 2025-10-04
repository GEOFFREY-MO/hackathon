"""
AI Analytics Blueprint
Provides OCR and AI-powered analytics endpoints for admin dashboard
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
import logging
from datetime import datetime
from ai_agent import ai_agent
from ocr_service import ocr_analyzer
from database import db, Shop, User

logger = logging.getLogger(__name__)

ai_analytics_bp = Blueprint('ai_analytics', __name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads/charts'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@ai_analytics_bp.route('/api/ai/chat', methods=['POST'])
@login_required
def chat_with_ai():
    """Chat with AI agent for retail insights"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        shop_id = data.get('shop_id', current_user.shop_id)
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        if not shop_id:
            return jsonify({'error': 'Shop ID is required'}), 400
        
        # Get AI response
        response = ai_agent.chat_with_agent(message, shop_id)
        
        return jsonify({
            'response': response,
            'timestamp': datetime.utcnow().isoformat(),
            'shop_id': shop_id
        })
        
    except Exception as e:
        logger.error(f"Error in AI chat: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_analytics_bp.route('/api/ai/performance', methods=['GET'])
@login_required
def get_shop_performance():
    """Get AI-analyzed shop performance"""
    try:
        shop_id = request.args.get('shop_id', current_user.shop_id)
        time_period = request.args.get('time_period', '30d')
        
        if not shop_id:
            return jsonify({'error': 'Shop ID is required'}), 400
        
        # Get performance analysis
        analysis = ai_agent.analyze_shop_performance(int(shop_id), time_period)
        insights = ai_agent.generate_insights(analysis)
        
        return jsonify({
            'analysis': analysis,
            'insights': insights,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting shop performance: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_analytics_bp.route('/api/ai/upload-chart', methods=['POST'])
@login_required
def upload_chart():
    """Upload and analyze chart/graph image"""
    try:
        # Accept hybrid-only payloads (no file) for DOM/Chart extraction
        has_file = 'file' in request.files and request.files['file'].filename != ''
        file = request.files['file'] if has_file else None
        if has_file and not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Create upload directory if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save file when provided
        filename = None
        filepath = None
        if has_file:
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
        
        # Analyze chart
        shop_id = request.form.get('shop_id', current_user.shop_id)
        # Hybrid extraction JSON from frontend (DOM / chart API)
        hybrid_json = None
        try:
            if 'hybrid_json' in request.form:
                hybrid_json = json.loads(request.form.get('hybrid_json'))
        except Exception:
            hybrid_json = None
        # If frontend provided chart metadata (Chart.js), pass via temp hint
        chart_meta = None
        try:
            if 'chart_meta' in request.form:
                chart_meta = json.loads(request.form.get('chart_meta'))
        except Exception:
            chart_meta = None
        # If we have a file, run OCR pipeline; otherwise start with empty analysis and rely on hybrid/chart meta
        analysis_result = ai_agent.analyze_uploaded_chart(filepath, int(shop_id)) if filepath else {'chart_data': {}, 'insights': []}
        if chart_meta and isinstance(analysis_result, dict):
            # Attach meta so assistant can leverage labels/series even if OCR is weak
            analysis_result['chart_meta'] = chart_meta
            try:
                cd = analysis_result.get('chart_data') or {}
                pts = cd.get('data_points') or []
                labels = chart_meta.get('labels') or []
                datasets = chart_meta.get('datasets') or []
                # Backfill datapoints if OCR missed them
                if (not pts) and labels and datasets:
                    # Sum values across datasets per label index
                    sums = []
                    for i, _ in enumerate(labels):
                        total = 0.0
                        for ds in datasets:
                            try:
                                total += float(ds.get('data', [0])[i] or 0)
                            except Exception:
                                pass
                        sums.append(total)
                    new_pts = [{ 'label': str(labels[i]), 'value': float(sums[i]), 'type': 'numerical' } for i in range(len(labels))]
                    cd['data_points'] = new_pts
                    # Map chart type
                    ctype = (chart_meta.get('chart_type') or '').lower()
                    mapped = 'unknown'
                    if 'bar' in ctype: mapped = 'bar_chart'
                    elif 'line' in ctype: mapped = 'line_chart'
                    elif 'pie' in ctype or 'doughnut' in ctype: mapped = 'pie_chart'
                    cd['chart_type'] = cd.get('chart_type') or mapped
                    # Simple trend
                    if mapped == 'line_chart' and len(sums) > 1:
                        if sums[-1] > sums[0] * 1.1:
                            cd['trends'] = list(set((cd.get('trends') or []) + ['increasing']))
                        elif sums[-1] < sums[0] * 0.9:
                            cd['trends'] = list(set((cd.get('trends') or []) + ['decreasing']))
                        else:
                            cd['trends'] = list(set((cd.get('trends') or []) + ['stable']))
                    analysis_result['chart_data'] = cd
                # Rebuild formatted text to include new data points
                lines = []
                if cd.get('title'):
                    lines.append(f"**Title**: {cd.get('title')}")
                if cd.get('chart_type'):
                    lines.append(f"**Type**: {cd.get('chart_type')}")
                if cd.get('data_points'):
                    lines.append('**Data Points**:')
                    for p in cd['data_points'][:20]:
                        lines.append(f"- {p.get('label','?')}: {p.get('value','?')}")
                if analysis_result.get('insights'):
                    lines.append('**OCR Insights**:')
                    for s in analysis_result['insights']:
                        lines.append(f"- {s}")
                analysis_result['formatted'] = "\n".join(lines)
            except Exception:
                pass

        # If hybrid_json provided, normalize to unified schema and merge
        try:
            if hybrid_json and isinstance(analysis_result, dict):
                schema = {
                    'chart_type': hybrid_json.get('chart_type'),
                    'title': hybrid_json.get('title') or '',
                    'labels': hybrid_json.get('labels') or [],
                    'values': [float(v) if v is not None else 0.0 for v in (hybrid_json.get('values') or [])],
                    'time_period': hybrid_json.get('time_period') or '',
                    'trends': hybrid_json.get('trends') or {},
                    'confidence': hybrid_json.get('confidence') or 'medium'
                }
                cd = analysis_result.get('chart_data') or {}
                # Prefer hybrid over OCR when high-confidence
                if schema['chart_type']:
                    cd['chart_type'] = schema['chart_type']
                if schema['title'] and not cd.get('title'):
                    cd['title'] = schema['title']
                if schema['labels'] and schema['values'] and not cd.get('data_points'):
                    cd['data_points'] = [
                        {'label': str(schema['labels'][i] if i < len(schema['labels']) else f'Item {i+1}'), 'value': float(schema['values'][i] if i < len(schema['values']) else 0.0), 'type': 'numerical'}
                        for i in range(max(len(schema['labels']), len(schema['values'])))
                    ]
                if schema['trends']:
                    cd['trends'] = list(set((cd.get('trends') or []) + list(schema['trends'].values())))
                analysis_result['chart_data'] = cd
                # Build natural summary with bullet points and follow-up
                lines = []
                const_type = cd.get('chart_type')
                if cd.get('title'):
                    lines.append(f"**Here are the results** for: {cd.get('title')}")
                else:
                    lines.append("**Here are the results** in point form:")
                if const_type:
                    lines.append(f"- **Type**: {const_type}")
                if cd.get('data_points'):
                    for p in cd['data_points'][:20]:
                        lines.append(f"- {p.get('label','?')}: {p.get('value','?')}")
                # Brief explanation
                if cd.get('data_points') and len(cd['data_points']) >= 2:
                    try:
                        first = float(cd['data_points'][0].get('value', 0) or 0)
                        last = float(cd['data_points'][-1].get('value', 0) or 0)
                        if last > first:
                            lines.append("- **Brief**: Values trend upward across the selected range.")
                        elif last < first:
                            lines.append("- **Brief**: Values trend downward across the selected range.")
                        else:
                            lines.append("- **Brief**: Values are relatively stable across the selected range.")
                    except Exception:
                        pass
                # Follow-up question
                lines.append("Would you like suggested next steps (e.g., restock alerts, promo ideas), or do you have a different question?")
                analysis_result['formatted'] = "\n".join(lines)
        except Exception:
            pass

        # If OCR succeeded, stream a formatted message payload
        try:
            if isinstance(analysis_result, dict):
                cd = analysis_result.get('chart_data', {}) or {}
                pts = cd.get('data_points', []) or []
                lines = []
                const_type2 = cd.get('chart_type')
                if cd.get('title'):
                    lines.append(f"**Here are the results** for: {cd.get('title')}")
                else:
                    lines.append("**Here are the results** in point form:")
                if const_type2:
                    lines.append(f"- **Type**: {const_type2}")
                if pts:
                    for p in pts[:20]:
                        lines.append(f"- {p.get('label','?')}: {p.get('value','?')}")
                    try:
                        first = float(pts[0].get('value', 0) or 0)
                        last = float(pts[-1].get('value', 0) or 0)
                        if last > first:
                            lines.append("- **Brief**: Values trend upward across the selected range.")
                        elif last < first:
                            lines.append("- **Brief**: Values trend downward across the selected range.")
                        else:
                            lines.append("- **Brief**: Values are relatively stable across the selected range.")
                    except Exception:
                        pass
                if analysis_result.get('insights'):
                    for s in analysis_result['insights']:
                        lines.append(f"- {s}")
                lines.append("Would you like suggested next steps (e.g., restock alerts, promo ideas), or do you have a different question?")
                # Do not show DB vs OCR comparison explicitly in chat; keep internal
                analysis_result['formatted'] = "\n".join(lines)
        except Exception:
            pass
        
        # Clean up file
        if filepath:
            try:
                os.remove(filepath)
            except:
                pass
        
        return jsonify({
            'analysis': analysis_result,
            'filename': filename,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error uploading chart: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_analytics_bp.route('/api/ai/visualization', methods=['GET'])
@login_required
def generate_visualization():
    """Generate visualization for shop data"""
    try:
        shop_id = request.args.get('shop_id', current_user.shop_id)
        chart_type = request.args.get('chart_type', 'revenue_trend')
        
        if not shop_id:
            return jsonify({'error': 'Shop ID is required'}), 400
        
        # Generate visualization
        chart_json = ai_agent.generate_visualization(int(shop_id), chart_type)
        
        return jsonify({
            'chart': json.loads(chart_json),
            'chart_type': chart_type,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating visualization: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_analytics_bp.route('/api/ai/insights', methods=['GET'])
@login_required
def get_ai_insights():
    """Get AI-generated insights for shop"""
    try:
        shop_id = request.args.get('shop_id', current_user.shop_id)
        time_period = request.args.get('time_period', '30d')
        
        if not shop_id:
            return jsonify({'error': 'Shop ID is required'}), 400
        
        # Get performance analysis
        analysis = ai_agent.analyze_shop_performance(int(shop_id), time_period)
        insights = ai_agent.generate_insights(analysis)
        
        # Get AI recommendations
        recommendations = ai_agent.chat_with_agent(
            "Based on the current performance data, what specific recommendations do you have for improving this shop's performance?",
            int(shop_id)
        )
        
        return jsonify({
            'insights': insights,
            'recommendations': recommendations,
            'analysis': analysis,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting AI insights: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_analytics_bp.route('/api/ai/conversation-history', methods=['GET'])
@login_required
def get_conversation_history():
    """Get conversation history with AI agent"""
    try:
        history = ai_agent.get_conversation_history()
        return jsonify({
            'history': history,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_analytics_bp.route('/api/ai/clear-history', methods=['POST'])
@login_required
def clear_conversation_history():
    """Clear conversation history with AI agent"""
    try:
        ai_agent.clear_conversation_history()
        return jsonify({
            'message': 'Conversation history cleared',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error clearing conversation history: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_analytics_bp.route('/api/ai/trend-analysis', methods=['GET'])
@login_required
def get_trend_analysis():
    """Get detailed trend analysis"""
    try:
        shop_id = request.args.get('shop_id', current_user.shop_id)
        time_period = request.args.get('time_period', '30d')
        
        if not shop_id:
            return jsonify({'error': 'Shop ID is required'}), 400
        
        # Get performance analysis
        analysis = ai_agent.analyze_shop_performance(int(shop_id), time_period)
        
        # Get trend analysis from AI
        trend_analysis = ai_agent.chat_with_agent(
            f"Provide a detailed trend analysis for this shop's performance over the last {time_period}. Include specific patterns, anomalies, and predictions.",
            int(shop_id)
        )
        
        return jsonify({
            'trend_analysis': trend_analysis,
            'performance_data': analysis,
            'time_period': time_period,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting trend analysis: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ai_analytics_bp.route('/api/ai/compare-shops', methods=['GET'])
@login_required
def compare_shops():
    """Compare performance between multiple shops"""
    try:
        shop_ids = request.args.getlist('shop_ids')
        time_period = request.args.get('time_period', '30d')
        
        if not shop_ids:
            return jsonify({'error': 'Shop IDs are required'}), 400
        
        if len(shop_ids) < 2:
            return jsonify({'error': 'At least 2 shops required for comparison'}), 400
        
        # Get performance data for each shop
        shop_comparisons = []
        for shop_id in shop_ids:
            analysis = ai_agent.analyze_shop_performance(int(shop_id), time_period)
            shop_comparisons.append({
                'shop_id': int(shop_id),
                'analysis': analysis
            })
        
        # Get AI comparison analysis
        comparison_data = {
            'shops': shop_comparisons,
            'time_period': time_period
        }
        
        comparison_analysis = ai_agent.chat_with_agent(
            f"Compare the performance of these shops over the last {time_period}. Provide insights on which shops are performing better and why.",
            int(shop_ids[0])  # Use first shop as context
        )
        
        return jsonify({
            'comparison': comparison_data,
            'analysis': comparison_analysis,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error comparing shops: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
