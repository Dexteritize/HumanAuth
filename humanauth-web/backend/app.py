#!/usr/bin/env python3
"""
HumanAuth Web Demo - Backend Server (app.py)

Flask + Socket.IO backend that:
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

import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

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
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "humanauth-web-demo-secret-key")
CORS(app)

# Threading mode is the least painful in dev. If you install eventlet/gevent, you can change this.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

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
                "health": "/api/health",
                "auth": {
                    "start": "/api/auth/start",
                    "reset": "/api/auth/reset",
                    "process": "/api/auth/process",
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
# Socket.IO events
# ------------------------------------------------------------------------------
@socketio.on("connect")
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit("connected", {"status": "connected"})


@socketio.on("disconnect")
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on("start_auth")
def handle_start_auth():
    session_id = f"session_{uuid.uuid4().hex}"

    mx = models_exist()
    if not (mx["face"] or mx["hand"]):
        emit(
            "auth_started",
            {
                "status": "error",
                "message": "Model files not found. Put .task files in backend/ or set env vars.",
                "debug": mx,
            },
        )
        return

    try:
        auth_sessions[session_id] = HumanAuth(FACE_MODEL_PATH, HAND_MODEL_PATH)
        emit("auth_started", {"status": "success", "session_id": session_id, "message": "Authentication session started"})
    except Exception as e:
        logger.exception("Error starting authentication session (socket)")
        emit("auth_started", {"status": "error", "message": f"Failed to start authentication session: {str(e)}"})


@socketio.on("reset_auth")
def handle_reset_auth(data):
    session_id = (data or {}).get("session_id")
    if not session_id or session_id not in auth_sessions:
        emit("auth_reset", {"status": "error", "message": "Invalid session ID"})
        return

    try:
        auth_sessions[session_id] = HumanAuth(FACE_MODEL_PATH, HAND_MODEL_PATH)
        emit("auth_reset", {"status": "success", "message": "Authentication session reset"})
    except Exception as e:
        logger.exception("Error resetting authentication session (socket)")
        emit("auth_reset", {"status": "error", "message": f"Failed to reset authentication session: {str(e)}"})


@socketio.on("process_frame")
def handle_process_frame(data):
    session_id = (data or {}).get("session_id")
    frame_data = (data or {}).get("frame")

    if not session_id or session_id not in auth_sessions:
        emit("frame_processed", {"status": "error", "message": "Invalid session ID"})
        return

    if not frame_data:
        emit("frame_processed", {"status": "error", "message": "No frame data provided"})
        return

    frame = decode_frame(frame_data)
    if frame is None:
        emit("frame_processed", {"status": "error", "message": "Frame decode failed (bad base64 or invalid image)."})
        return

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
        emit("frame_processed", {"status": "success", "result": result_dict})
    except Exception as e:
        logger.exception("Error processing frame (socket)")
        emit("frame_processed", {"status": "error", "message": f"Failed to process frame: {str(e)}"})


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)
