#!/usr/bin/env python3
"""
Simple Flask Hello World Application
"""

from flask import Flask, jsonify
import logging
from werkzeug.exceptions import HTTPException

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.route('/')
def hello_world():
    """Root route that returns Hello, World!"""
    logger.info('Hello World endpoint accessed')
    return 'Hello, World!'


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Application is running'})


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f'404 error: {error}')
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f'Internal server error: {error}')
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(HTTPException)
def handle_exception(e):
    """Handle HTTP exceptions"""
    logger.error(f'HTTP exception occurred: {e}')
    return jsonify({
        'error': e.name,
        'message': e.description
    }), e.code


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Handle unexpected errors"""
    logger.error(f'Unexpected error: {error}', exc_info=True)
    return jsonify({'error': 'An unexpected error occurred'}), 500


if __name__ == '__main__':
    logger.info('Starting Flask application on http://localhost:5000')
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )