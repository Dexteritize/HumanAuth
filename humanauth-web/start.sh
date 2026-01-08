#!/bin/bash

# HumanAuth Web Demo Startup Script
# This script starts both the backend and frontend servers

echo "Starting HumanAuth Web Demo..."
echo "------------------------------"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is required but not found."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is required but not found."
    exit 1
fi

# Define directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Check if model files exist
if [ ! -f "$BACKEND_DIR/face_landmarker.task" ] || [ ! -f "$BACKEND_DIR/hand_landmarker.task" ]; then
    echo "Error: Model files not found in $BACKEND_DIR"
    echo "Please ensure face_landmarker.task and hand_landmarker.task are in the backend directory."
    exit 1
fi

# Check if requirements are installed for backend
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "Setting up Python virtual environment for backend..."
    cd "$BACKEND_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
    echo "Backend dependencies installed."
fi

# Start backend server in background
echo "Starting backend server..."
cd "$BACKEND_DIR"
source venv/bin/activate
python app.py &
BACKEND_PID=$!
echo "Backend server started with PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 3

# Start frontend server
echo "Starting frontend server..."
cd "$FRONTEND_DIR"
npm start &
FRONTEND_PID=$!
echo "Frontend server started with PID: $FRONTEND_PID"

# Function to handle script termination
cleanup() {
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Servers stopped."
    exit 0
}

# Register the cleanup function for script termination
trap cleanup SIGINT SIGTERM

echo ""
echo "HumanAuth Web Demo is running!"
echo "------------------------------"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:4200"
echo ""
echo "Open your browser and navigate to: http://localhost:4200"
echo "Press Ctrl+C to stop both servers."
echo ""

# Keep the script running
wait