#!/bin/bash
# HumanAuth Web Demo Startup Script
# Starts backend + frontend and cleans up fully on exit

set -u  # safer vars, but NOT -e (so a noncritical command won't trigger EXIT cleanup)

echo "Starting HumanAuth Web Demo..."
echo "------------------------------"

# ---------- Dependency Checks ----------
command -v python3 >/dev/null || { echo "Error: Python 3 not found."; exit 1; }
command -v node >/dev/null || { echo "Error: Node.js not found."; exit 1; }
command -v npm  >/dev/null || { echo "Error: npm not found."; exit 1; }

# ---------- Directories ----------
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# ---------- Model Check ----------
if [[ ! -f "$BACKEND_DIR/face_landmarker.task" || ! -f "$BACKEND_DIR/hand_landmarker.task" ]]; then
  echo "Error: Required model files not found in $BACKEND_DIR"
  echo "Please ensure face_landmarker.task and hand_landmarker.task are in the backend directory."
  exit 1
fi

# ---------- Helpers ----------
kill_tree() {
  # Kills a process and all of its children (macOS/Linux)
  local pid="$1"
  [[ -z "${pid:-}" ]] && return 0

  # kill children first
  local kids
  kids="$(pgrep -P "$pid" 2>/dev/null || true)"
  if [[ -n "$kids" ]]; then
    for k in $kids; do
      kill_tree "$k"
    done
  fi

  # then kill parent
  kill "$pid" 2>/dev/null || true
}

STARTED=0
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  # only do real cleanup if we actually started something
  if [[ "$STARTED" -eq 1 ]]; then
    echo ""
    echo "🛑 Shutting down servers..."

    # Try graceful shutdown first
    kill_tree "$FRONTEND_PID"
    kill_tree "$BACKEND_PID"

    # Safety net: free ports if still bound (macOS/Linux)
    lsof -ti :8000 2>/dev/null | xargs kill -9 2>/dev/null || true
    lsof -ti :4200 2>/dev/null | xargs kill -9 2>/dev/null || true

    echo "✅ Servers stopped."
  fi
}

# Run cleanup on Ctrl+C, termination, or normal exit
trap cleanup SIGINT SIGTERM EXIT

# ---------- Backend Setup ----------
# Create virtual environment if it doesn't exist
if [[ ! -d "$BACKEND_DIR/venv" ]]; then
  echo "Setting up Python virtual environment for backend..."
  cd "$BACKEND_DIR" || exit 1
  python3 -m venv venv
  echo "Virtual environment created."
fi

# Always install/update dependencies to ensure all required packages are available
echo "Installing/updating backend dependencies..."
cd "$BACKEND_DIR" || exit 1
source venv/bin/activate
pip install -r requirements.txt
deactivate
echo "Backend dependencies installed."

# ---------- API Configuration ----------
# Generate a random API key if not provided
if [[ -z "${API_KEY:-}" ]]; then
  # Generate a random API key (32 characters)
  API_KEY=$(openssl rand -hex 16)
  echo "Generated API key for development: $API_KEY"
  echo "For production, set a secure API_KEY environment variable."
fi
export API_KEY

# ---------- Start Backend ----------
echo "Starting backend server..."
cd "$BACKEND_DIR" || exit 1
source venv/bin/activate
python app.py &
BACKEND_PID=$!
deactivate
echo "Backend server started with PID: $BACKEND_PID"

echo "Waiting for backend to initialize..."
sleep 3

# ---------- Start Frontend ----------
echo "Starting frontend server..."
cd "$FRONTEND_DIR" || exit 1
npm start &
FRONTEND_PID=$!
echo "Frontend server started with PID: $FRONTEND_PID"

STARTED=1

# ---------- Status ----------
echo ""
echo "------------------------------"
echo "HumanAuth Web Demo is running!"
echo "Backend : http://localhost:8000"
echo "Frontend: http://localhost:4200"
echo ""
echo "Open your browser and navigate to: http://localhost:4200"
echo "Press Ctrl+C to stop both servers."
echo ""

# Keep the script running until one of the background jobs exits
wait
