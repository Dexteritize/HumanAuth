#!/usr/bin/env python3
"""
HumanAuth Web Demo - Backend Server (app.py)

Flask REST API backend that:
- Starts auth sessions
- Accepts webcam frames as base64 (data URL or raw base64)
- Runs HumanAuth.update(frame)
- Returns AuthResult as JSON

Works best when you run with:
  FACE_MODEL_PATH=/abs/path/face_landmarker.task
  HAND_MODEL_PATH=/abs/path/hand_landmarker.task

Author: Jason Dank (2026)
"""

import os
import time
import uuid
import base64
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from functools import wraps

import cv2
import numpy as np
from flask import Blueprint, request, jsonify, g, Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("humanauth-backend")

# ------------------------------------------------------------------------------
# Paths / imports
# ------------------------------------------------------------------------------
# Assume this file is in backend/ and human_auth.py + .task files are also in backend/
BACKEND_DIR = Path(__file__).resolve().parent
import sys

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from human_auth import HumanAuth  # type: ignore
except Exception as e:
    logger.exception("Failed to import human_auth.py from backend directory.")
    raise

# ------------------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------------------
# Create a blueprint instead of a Flask app
app = Blueprint('api', __name__)

# Store configuration values that will be used by the main app
SECRET_KEY = os.environ.get("SECRET_KEY", "humanauth-web-demo-secret-key")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:4200")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", FRONTEND_URL)
API_KEY = os.environ.get("API_KEY", "dev-api-key-change-me-in-production")

# CORS and rate limiting will be set up in the main app
# These are placeholders for documentation purposes
limiter = None

# ------------------------------------------------------------------------------
# Authentication & Authorization
# ------------------------------------------------------------------------------
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get("X-API-Key")
        if provided_key and provided_key == API_KEY:
            return f(*args, **kwargs)
        return jsonify({
            "status": "error",
            "code": 401,
            "message": "Unauthorized. Valid API key required."
        }), 401
    return decorated_function

# Active sessions
auth_sessions: Dict[str, HumanAuth] = {}


def _resolve_model_path(env_key: str, default_filename: str) -> Optional[str]:
    """
    Resolve a model path using:
      1) env var (FACE_MODEL_PATH / HAND_MODEL_PATH)
      2) local file in backend dir (default_filename)
    """
    p = os.environ.get(env_key)
    if p:
        pp = Path(p).expanduser().resolve()
        return str(pp) if pp.exists() else str(pp)  # return string even if missing for debug

    local = (BACKEND_DIR / default_filename).resolve()
    return str(local) if local.exists() else None


def find_model_paths() -> Tuple[Optional[str], Optional[str]]:
    face = _resolve_model_path("FACE_MODEL_PATH", "face_landmarker.task")
    hand = _resolve_model_path("HAND_MODEL_PATH", "hand_landmarker.task")
    # If env var was set but file missing, _resolve_model_path returns string; keep it for debug,
    # but health endpoint will show exists False.
    return face, hand


FACE_MODEL_PATH, HAND_MODEL_PATH = find_model_paths()

logger.info(f"BACKEND_DIR = {BACKEND_DIR}")
logger.info(f"__file__ = {Path(__file__).resolve()}")
logger.info(f"FACE_MODEL_PATH = {FACE_MODEL_PATH}")
logger.info(f"HAND_MODEL_PATH = {HAND_MODEL_PATH}")


def get_json() -> Dict[str, Any]:
    """Safely parse JSON body even if Content-Type is wrong."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def decode_frame(frame_data: str) -> Optional[np.ndarray]:
    """
    Decode a frame from either:
      - Data URL:  'data:image/jpeg;base64,....'
      - Raw base64: '....'
    Returns BGR OpenCV image or None.
    """
    if not isinstance(frame_data, str) or not frame_data:
        return None

    # Accept both data URL and raw base64
    if "," in frame_data:
        frame_data = frame_data.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(frame_data, validate=False)
    except Exception:
        return None

    arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    
    # Downsample large images for better performance
    # Only resize if the image is larger than 640x480
    if frame is not None and (frame.shape[1] > 640 or frame.shape[0] > 480):
        scale_factor = min(640 / frame.shape[1], 480 / frame.shape[0])
        new_width = int(frame.shape[1] * scale_factor)
        new_height = int(frame.shape[0] * scale_factor)
        frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    return frame


def models_exist() -> Dict[str, Any]:
    face_exists = bool(FACE_MODEL_PATH and Path(FACE_MODEL_PATH).expanduser().exists())
    hand_exists = bool(HAND_MODEL_PATH and Path(HAND_MODEL_PATH).expanduser().exists())
    return {
        "face": face_exists,
        "hand": hand_exists,
        "face_path": FACE_MODEL_PATH,
        "hand_path": HAND_MODEL_PATH,
    }


# ------------------------------------------------------------------------------
# Helper Functions for API
# ------------------------------------------------------------------------------
def error_response(message, code=400, details=None):
    """Generate a standardized error response"""
    response = {
        "status": "error",
        "code": code,
        "message": message
    }
    if details:
        response["details"] = details
    return jsonify(response), code

def success_response(data):
    """Generate a standardized success response"""
    return jsonify({
        "status": "success",
        "data": data
    })

def validate_request_json(required_fields=None):
    """Validate that the request has JSON data and required fields"""
    if not request.is_json:
        return error_response("Request must be JSON", 400)
    
    data = request.get_json()
    if required_fields:
        missing = [field for field in required_fields if field not in data]
        if missing:
            return error_response(f"Missing required fields: {', '.join(missing)}", 400)
    
    return None

# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:4200")
    return jsonify(
        {
            "name": "HumanAuth Web Demo API",
            "version": "1.0.0",
            "description": "Backend API for the HumanAuth Web Demo",
            "endpoints": {
                "v1": "/api/v1",
                "legacy": {
                    "health": "/api/health",
                    "auth": {
                        "start": "/api/auth/start",
                        "reset": "/api/auth/reset",
                        "process": "/api/auth/process",
                    },
                },
            },
            "frontend_url": frontend_url,
            "message": f"Please visit the frontend application at {frontend_url}",
        }
    )


@app.route("/api/health", methods=["GET"])
def health_check():
    mx = models_exist()
    return jsonify(
        {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "models": {"face": bool(mx["face"]), "hand": bool(mx["hand"])},
            "debug": {
                "__file__": str(Path(__file__).resolve()),
                "backend_dir": str(BACKEND_DIR),
                "face_model_path": mx["face_path"],
                "hand_model_path": mx["hand_path"],
                "face_exists": mx["face"],
                "hand_exists": mx["hand"],
            },
        }
    )

@app.route("/api/config", methods=["GET"])
def get_frontend_config():
    """
    Provides configuration for the frontend, including a development API key.
    In production, this should be restricted or removed.
    """
    # For development only - in production, API keys should be managed securely
    # and not exposed directly to the frontend
    return jsonify({
        "apiKey": API_KEY,
        "apiUrl": request.url_root + "api/v1"
    })

# ------------------------------------------------------------------------------
# API v1 Routes
# ------------------------------------------------------------------------------
@app.route("/api/v1/health", methods=["GET"])
@require_api_key
@limiter.limit("60 per minute")
def api_v1_health():
    """Health check endpoint for API v1"""
    mx = models_exist()
    return success_response({
        "timestamp": datetime.now().isoformat(),
        "models": {"face": bool(mx["face"]), "hand": bool(mx["hand"])}
    })

@app.route("/api/v1/verify", methods=["POST"])
@require_api_key
@limiter.limit("30 per minute")
def api_v1_verify():
    """Verify if the provided image contains a human"""
    # Validate request
    error = validate_request_json(["image"])
    if error:
        return error
    
    data = request.get_json()
    image_data = data.get("image")
    
    # Decode the image
    frame = decode_frame(image_data)
    if frame is None:
        return error_response("Invalid image data. Expected base64 encoded image.", 400)
    
    try:
        # Create a temporary HumanAuth instance for this verification
        auth = HumanAuth(FACE_MODEL_PATH, HAND_MODEL_PATH)
        result = auth.update(frame)
        
        # Return the result
        return success_response({
            "verified": bool(result.authenticated),
            "confidence": float(result.confidence),
            "message": result.message,
            "details": {
                k: (float(v) if isinstance(v, (int, float, np.number)) else v)
                for k, v in (result.details or {}).items()
            }
        })
    except Exception as e:
        logger.exception("Error in verify endpoint")
        return error_response(f"Verification failed: {str(e)}", 500)

@app.route("/api/v1/sessions", methods=["POST"])
@require_api_key
@limiter.limit("60 per minute")
def api_v1_create_session():
    """Start a new verification session"""
    session_id = f"session_{uuid.uuid4().hex}"
    
    mx = models_exist()
    if not (mx["face"] or mx["hand"]):
        return error_response(
            "Model files not found. Put face_landmarker.task and hand_landmarker.task in backend/, "
            "or set FACE_MODEL_PATH / HAND_MODEL_PATH env vars.",
            500,
            mx
        )
    
    try:
        auth_sessions[session_id] = HumanAuth(FACE_MODEL_PATH, HAND_MODEL_PATH)
        return success_response({
            "session_id": session_id,
            "message": "Authentication session started"
        })
    except Exception as e:
        logger.exception("Error starting authentication session")
        return error_response(f"Failed to start authentication session: {str(e)}", 500)

@app.route("/api/v1/sessions/<session_id>/reset", methods=["POST"])
@require_api_key
@limiter.limit("60 per minute")
def api_v1_reset_session(session_id):
    """Reset an existing verification session"""
    if not session_id or session_id not in auth_sessions:
        return error_response("Invalid session ID", 400)
    
    try:
        auth_sessions[session_id] = HumanAuth(FACE_MODEL_PATH, HAND_MODEL_PATH)
        return success_response({
            "message": "Authentication session reset"
        })
    except Exception as e:
        logger.exception("Error resetting authentication session")
        return error_response(f"Failed to reset authentication session: {str(e)}", 500)

@app.route("/api/v1/sessions/<session_id>/process", methods=["POST"])
@require_api_key
@limiter.limit("600 per minute")  # Increased from 120 to 600 for demo purposes (10 fps)
def api_v1_process_frame(session_id):
    """Process a frame in an existing session"""
    if not session_id or session_id not in auth_sessions:
        return error_response("Invalid session ID", 400)
    
    # Validate request
    error = validate_request_json(["frame"])
    if error:
        return error
    
    data = request.get_json()
    frame_data = data.get("frame")
    
    frame = decode_frame(frame_data)
    if frame is None:
        return error_response("Frame decode failed (bad base64 or invalid image).", 400)
    
    try:
        auth = auth_sessions[session_id]
        result = auth.update(frame)
        
        result_dict = {
            "authenticated": bool(result.authenticated),
            "confidence": float(result.confidence),
            "message": result.message,
            "details": {
                k: (float(v) if isinstance(v, (int, float, np.number)) else v)
                for k, v in (result.details or {}).items()
            }
        }
        return success_response(result_dict)
    except Exception as e:
        logger.exception("Error processing frame")
        return error_response(f"Failed to process frame: {str(e)}", 500)


@app.route("/api/auth/start", methods=["POST"])
def start_auth():
    session_id = f"session_{uuid.uuid4().hex}"

    mx = models_exist()
    if not (mx["face"] or mx["hand"]):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Model files not found. Put face_landmarker.task and hand_landmarker.task in backend/, "
                    "or set FACE_MODEL_PATH / HAND_MODEL_PATH env vars.",
                    "debug": mx,
                }
            ),
            500,
        )

    try:
        auth_sessions[session_id] = HumanAuth(FACE_MODEL_PATH, HAND_MODEL_PATH)
        return jsonify({"status": "success", "session_id": session_id, "message": "Authentication session started"})
    except Exception as e:
        logger.exception("Error starting authentication session")
        return jsonify({"status": "error", "message": f"Failed to start authentication session: {str(e)}"}), 500


@app.route("/api/auth/reset", methods=["POST"])
def reset_auth():
    data = get_json()
    session_id = data.get("session_id")

    if not session_id or session_id not in auth_sessions:
        return jsonify({"status": "error", "message": "Invalid session ID"}), 400

    try:
        auth_sessions[session_id] = HumanAuth(FACE_MODEL_PATH, HAND_MODEL_PATH)
        return jsonify({"status": "success", "message": "Authentication session reset"})
    except Exception as e:
        logger.exception("Error resetting authentication session")
        return jsonify({"status": "error", "message": f"Failed to reset authentication session: {str(e)}"}), 500


@app.route("/api/auth/process", methods=["POST"])
def process_frame():
    data = get_json()
    session_id = data.get("session_id")
    frame_data = data.get("frame")

    if not session_id or session_id not in auth_sessions:
        return jsonify({"status": "error", "message": "Invalid session ID"}), 400

    if not frame_data:
        return jsonify({"status": "error", "message": "No frame data provided"}), 400

    frame = decode_frame(frame_data)
    if frame is None:
        return jsonify({"status": "error", "message": "Frame decode failed (bad base64 or invalid image)."}), 400

    try:
        auth = auth_sessions[session_id]
        result = auth.update(frame)

        result_dict = {
            "authenticated": bool(result.authenticated),
            "confidence": float(result.confidence),
            "message": result.message,
            "details": {
                k: (float(v) if isinstance(v, (int, float, np.number)) else v)
                for k, v in (result.details or {}).items()
            },
        }
        return jsonify({"status": "success", "result": result_dict})
    except Exception as e:
        logger.exception("Error processing frame")
        return jsonify({"status": "error", "message": f"Failed to process frame: {str(e)}"}), 500


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # When running this file directly, create a Flask app and register the blueprint
    # This is for development/testing only
    flask_app = Flask(__name__)
    flask_app.config["SECRET_KEY"] = SECRET_KEY
    
    # Set up CORS
    if os.environ.get("FLASK_ENV") == "production":
        allowed_origins = [origin.strip() for origin in ALLOWED_ORIGINS.split(",")]
        logger.info(f"CORS: Allowing specific origins: {allowed_origins}")
        CORS(flask_app, resources={
            r"/api/*": {"origins": allowed_origins, "supports_credentials": False}
        })
    else:
        logger.info("CORS: Development mode - allowing all origins")
        CORS(flask_app)
    
    # Set up rate limiting
    limiter = Limiter(
        get_remote_address,
        app=flask_app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )
    
    # Register the blueprint
    flask_app.register_blueprint(app, url_prefix='/api')
    
    # Run the app
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host="0.0.0.0", port=port, debug=True)