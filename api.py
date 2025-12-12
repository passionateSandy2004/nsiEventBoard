"""
NSE Data API
============

Flask API to serve latest data from all 4 monitors.

Endpoints:
    GET /event-calendar     - Event calendar data
    GET /announcements      - Announcements data
    GET /crd                - CRD credit rating data
    GET /credit-rating      - Credit rating reg.30 data
    GET /health             - API health check

Query Parameters:
    page      - Page number (default: 1)
    per_page  - Records per page (default: 50, max: 1000)
    market    - Market type for announcements/credit-rating (default: equity)

Usage:
    python api.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


def load_json_file(filepath):
    """Load JSON data from file"""
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None


def paginate_data(data, page=1, per_page=50):
    """Paginate data"""
    if not data:
        return [], 0, 0
    
    total = len(data)
    total_pages = (total + per_page - 1) // per_page
    
    start = (page - 1) * per_page
    end = start + per_page
    
    return data[start:end], total, total_pages


def create_response(data, metadata, page, per_page, total, total_pages):
    """Create standardized API response"""
    return {
        'success': True,
        'metadata': {
            'scrape_timestamp': metadata.get('scrape_timestamp'),
            'total_records': metadata.get('total_records'),
            'total_pages_scraped': metadata.get('total_pages'),
            'source_url': metadata.get('source_url'),
            'market_type': metadata.get('market_type', 'N/A')
        },
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_records': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        },
        'data': data
    }


def error_response(message, code=404):
    """Create error response"""
    return jsonify({
        'success': False,
        'error': message
    }), code


@app.route('/')
def index():
    """API documentation"""
    return jsonify({
        'name': 'NSE Data API',
        'version': '1.0',
        'endpoints': {
            'GET /event-calendar': 'Get event calendar data',
            'GET /announcements': 'Get announcements data (supports market parameter)',
            'GET /crd': 'Get CRD credit rating data',
            'GET /credit-rating': 'Get credit rating reg.30 data (supports market parameter)',
            'GET /health': 'Health check'
        },
        'query_parameters': {
            'page': 'Page number (default: 1)',
            'per_page': 'Records per page (default: 50, max: 1000)',
            'market': 'Market type for announcements/credit-rating (default: equity, options: equity, sme, debt, mf)'
        },
        'examples': [
            '/event-calendar?page=1&per_page=50',
            '/announcements?market=equity&page=1&per_page=50',
            '/crd?page=2&per_page=100',
            '/credit-rating?market=sme&page=1'
        ]
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    # Check if data files exist
    files = {
        'event_calendar': os.path.exists('event_calendar_data/latest.json'),
        'announcements_equity': os.path.exists('announcements_data/latest_equity.json'),
        'crd': os.path.exists('crd_data/latest.json'),
        'credit_rating_equity': os.path.exists('credit_rating_data/latest_equity.json')
    }
    
    # Count how many monitors have data
    ready_count = sum(files.values())
    all_healthy = all(files.values())
    
    # Always return 200 for Railway health check, but indicate status
    return jsonify({
        'status': 'healthy' if all_healthy else 'starting' if ready_count > 0 else 'initializing',
        'timestamp': datetime.now().isoformat(),
        'monitors': files,
        'ready': f"{ready_count}/4"
    }), 200


@app.route('/event-calendar')
def get_event_calendar():
    """Get event calendar data"""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 1000)
    
    # Load data
    filepath = 'event_calendar_data/latest.json'
    json_data = load_json_file(filepath)
    
    if not json_data:
        return error_response('Event calendar data not found. Please ensure the monitor is running.')
    
    # Paginate
    paginated_data, total, total_pages = paginate_data(
        json_data.get('data', []), 
        page, 
        per_page
    )
    
    # Create response
    response = create_response(
        paginated_data,
        json_data.get('metadata', {}),
        page,
        per_page,
        total,
        total_pages
    )
    
    return jsonify(response)


@app.route('/announcements')
def get_announcements():
    """Get announcements data"""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 1000)
    market = request.args.get('market', 'equity', type=str).lower()
    
    # Load data
    filepath = f'announcements_data/latest_{market}.json'
    json_data = load_json_file(filepath)
    
    if not json_data:
        return error_response(
            f'Announcements data not found for market: {market}. '
            f'Available markets: equity, sme, debt, mf. '
            f'Please ensure the monitor is running for this market type.'
        )
    
    # Paginate
    paginated_data, total, total_pages = paginate_data(
        json_data.get('data', []), 
        page, 
        per_page
    )
    
    # Create response
    response = create_response(
        paginated_data,
        json_data.get('metadata', {}),
        page,
        per_page,
        total,
        total_pages
    )
    
    return jsonify(response)


@app.route('/crd')
def get_crd():
    """Get CRD credit rating data"""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 1000)
    
    # Load data
    filepath = 'crd_data/latest.json'
    json_data = load_json_file(filepath)
    
    if not json_data:
        return error_response('CRD data not found. Please ensure the monitor is running.')
    
    # Paginate
    paginated_data, total, total_pages = paginate_data(
        json_data.get('data', []), 
        page, 
        per_page
    )
    
    # Create response
    response = create_response(
        paginated_data,
        json_data.get('metadata', {}),
        page,
        per_page,
        total,
        total_pages
    )
    
    return jsonify(response)


@app.route('/credit-rating')
def get_credit_rating():
    """Get credit rating regulation 30 data"""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 1000)
    market = request.args.get('market', 'equity', type=str).lower()
    
    # Load data
    filepath = f'credit_rating_data/latest_{market}.json'
    json_data = load_json_file(filepath)
    
    if not json_data:
        return error_response(
            f'Credit rating data not found for market: {market}. '
            f'Available markets: equity, sme. '
            f'Please ensure the monitor is running for this market type.'
        )
    
    # Paginate
    paginated_data, total, total_pages = paginate_data(
        json_data.get('data', []), 
        page, 
        per_page
    )
    
    # Create response
    response = create_response(
        paginated_data,
        json_data.get('metadata', {}),
        page,
        per_page,
        total,
        total_pages
    )
    
    return jsonify(response)


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found. Visit / for API documentation.'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    import os
    
    port = int(os.environ.get('PORT', 5000))
    
    print("\n" + "=" * 80)
    print("NSE DATA API")
    print("=" * 80)
    print(f"\nStarting API server on port {port}")
    print("Press Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)

