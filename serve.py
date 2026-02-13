#!/usr/bin/env python3
"""
HumanAuth Combined Server (serve.py)

This script serves both the backend API and frontend static files from a single server.
It registers the backend Flask app as a blueprint under the /api prefix.

For production deployment on Render.com
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask, send_from_directory, jsonify

# Configure logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("humanauth-server")

# Add the backend directory to the Python path
BACKEND_DIR = Path(__file__).parent / "humanauth-web" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Create the main app
app = Flask(__name__, static_folder='static')

# Import the backend app (which is now a blueprint)
# This import must happen after adding the backend directory to sys.path
try:
    from app import app as api_blueprint, API_KEY, SECRET_KEY, ALLOWED_ORIGINS
except ImportError as e:
    logger.error(f"Failed to import backend app: {e}")
    raise

# Register the API blueprint under /api
app.register_blueprint(api_blueprint, url_prefix='/api')

# Set up CORS
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:4200")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", ALLOWED_ORIGINS)
allowed_origins = [origin.strip() for origin in ALLOWED_ORIGINS.split(",")]

# In production, only allow specific origins
if os.environ.get("FLASK_ENV") == "production":
    logger.info(f"CORS: Allowing specific origins: {allowed_origins}")
    CORS(app, resources={
        r"/api/*": {"origins": allowed_origins, "supports_credentials": False}
    })
else:
    # In development, allow all origins for easier testing
    logger.info("CORS: Development mode - allowing all origins")
    CORS(app)

# Set up rate limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Health check endpoint
@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

# API configuration endpoint that returns the correct API URL
@app.route('/api/config')
def api_config():
    # For development only - in production, API keys should be managed securely
    # and not exposed directly to the frontend
    api_key = os.environ.get("API_KEY", API_KEY)
    return jsonify({
        "apiKey": api_key,
        "apiUrl": "/api"  # Use relative URL for the API
    })

# Serve static files for any other route
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)