# HumanAuth Web Demo

A web-based human authentication system using face and hand recognition.

## Overview

HumanAuth Web Demo is a complete web application that demonstrates human authentication using face and hand recognition. The system uses MediaPipe for face and hand landmark detection and implements various liveness detection techniques to distinguish between real humans and spoofing attempts.

## Features

- Real-time face and hand landmark detection
- Interactive challenge-response authentication
- Visual feedback with face and hand mesh visualization
- Progress tracking for authentication challenges
- REST API for integration with external applications
- API key authentication for secure access

## Requirements

- Python 3.8 or higher
- Node.js 18 or higher
- npm 8 or higher
- Web camera

## Quick Start

The easiest way to run the HumanAuth Web Demo is to use the provided start script:

```bash
# Navigate to the humanauth-web directory
cd /path/to/humanauth-web

# Make the start script executable (if not already)
chmod +x start.sh

# Run the start script
./start.sh
```

This script will:
1. Check for required dependencies
2. Verify model files are present
3. Set up a Python virtual environment for the backend (if needed)
4. Start the backend server
5. Start the frontend server
6. Provide URLs to access the application

Once both servers are running, open your browser and navigate to:
http://localhost:4200

## Manual Setup

If you prefer to start the servers manually:

### Backend Setup

```bash
# Navigate to the backend directory
cd /path/to/humanauth-web/backend

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the backend server
python app.py
```

### Frontend Setup

```bash
# Navigate to the frontend directory
cd /path/to/humanauth-web/frontend

# Install dependencies
npm install

# Start the development server
npm start
```

## Troubleshooting

### Nothing happens when I run npm start

If you only run `npm start` in the frontend directory, the application won't work properly because it needs the backend server running as well. Use the `start.sh` script to start both servers together.

### Model files not found

Make sure the model files (`face_landmarker.task` and `hand_landmarker.task`) are present in the backend directory. These files are required for face and hand detection.

### Connection issues

If the frontend can't connect to the backend:
1. Ensure the backend server is running on port 8000
2. Check if there are any firewall or network issues
3. Verify that the `backendUrl` in `auth-page.component.ts` is set to `http://localhost:8000`

## How It Works

1. The frontend captures frames from your webcam
2. Frames are sent to the backend via REST API
3. The backend processes frames using MediaPipe for face and hand detection
4. Authentication results are sent back to the frontend
5. The frontend visualizes the results and displays authentication status

## Architecture

The application is structured with a clean separation of concerns:

1. **Backend**:
   - `app.py`: Main Flask application with REST API endpoints
   - `human_auth.py`: Core authentication logic using MediaPipe
   - `auth_types.py`: Shared data types (AuthResult) to avoid circular dependencies
   - `visualization.py`: Visualization utilities for debugging

2. **Frontend**:
   - Angular-based SPA with TypeScript
   - Components for authentication UI and visualization
   - Services for camera access and backend communication

## Performance and Display Settings

The application is configured for optimal performance and display:

- **Video Display**: 900px width (max-width: 90% for responsiveness), centered on the page
- **Camera Resolution**: 1280x720 (720p HD)
- **Framerate**: ~60fps (using requestAnimationFrame for smooth rendering)
- **Image Quality**: 0.7 (balanced for quality and performance)
- **Rendering Optimizations**: Hardware acceleration and stabilization techniques

### Performance Optimizations

The application includes several optimizations to ensure smooth rendering and prevent visual artifacts:

- **Hardware Acceleration**: CSS transform: translate3d(0,0,0) is applied to video and canvas elements
- **Rendering Hints**: will-change property is used to optimize browser rendering
- **Stable Layout**: Fixed aspect ratio and explicit dimensions prevent layout shifts
- **Efficient Animation**: requestAnimationFrame is used instead of setTimeout for smoother rendering
- **Canvas Optimization**: Separate canvases for capture and visualization prevent dimension conflicts
- **Composite Operations**: Efficient canvas clearing and drawing techniques reduce flickering

### Customization Options

You can adjust these settings if needed:

- To change the video size or position, modify `video-container` in `frontend/src/app/auth-page/auth-page.component.scss`
- To change the camera resolution, modify the `getUserMedia` parameters in `frontend/src/app/services/camera.service.ts`
- To adjust rendering performance, modify the optimization settings in `frontend/src/app/auth-page/auth-page.component.ts`
- To change the image quality, modify the quality parameter in the `capture` call in `frontend/src/app/services/camera.service.ts`

## License

This project is licensed under the MIT License - see the LICENSE file for details.