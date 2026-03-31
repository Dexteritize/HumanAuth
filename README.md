# HumanAuth - Biometric Authentication System

A comprehensive full-stack human authentication system that uses advanced biometric verification through real-time face and hand landmark detection. This system provides secure, contactless authentication using computer vision and machine learning technologies.

## What is HumanAuth?

HumanAuth is a cutting-edge biometric authentication system that verifies human identity through:
- **Face Landmark Detection**: Analyzes facial features and expressions
- **Hand Landmark Detection**: Tracks hand movements and gestures
- **Real-time Processing**: Processes webcam frames in real-time for continuous verification
- **Multi-factor Biometric**: Combines multiple biometric factors for enhanced security
- **Session-based Authentication**: Maintains secure authentication sessions

The system is designed for applications requiring secure, contactless authentication such as access control, identity verification, and secure login systems.

## System Architecture

### Backend (Flask REST API)
- **Framework**: Flask with CORS support
- **Authentication**: API key-based authentication with rate limiting
- **Biometric Processing**: MediaPipe-based face and hand landmark detection
- **Session Management**: Real-time session handling for continuous authentication
- **Model Files**: Pre-trained MediaPipe models for landmark detection

### Frontend (Angular Application)
- **Framework**: Angular with TypeScript
- **Camera Integration**: WebRTC-based camera access
- **Real-time Visualization**: Live landmark visualization and authentication feedback
- **Responsive UI**: Modern, responsive interface with real-time status updates
- **Session Management**: Client-side session handling and state management

### Key Components
```
HumanAuth-FullStack/
├── backend/                    # Flask REST API server
│   ├── app.py                 # Main Flask application
│   ├── human_auth.py          # Core biometric authentication logic
│   ├── face_landmarker.task   # MediaPipe face detection model
│   ├── hand_landmarker.task   # MediaPipe hand detection model
│   └── requirements.txt       # Python dependencies
├── frontend/                   # Angular web application
│   ├── src/app/
│   │   ├── auth-page/         # Main authentication component
│   │   ├── services/          # Angular services (camera, auth)
│   │   └── environments/      # Environment configurations
│   └── package.json           # Node.js dependencies
├── tests/                      # Comprehensive test suite
│   ├── backend/               # Backend unit tests
│   ├── frontend/              # Frontend component tests
│   ├── integration/           # Integration tests
│   ├── security/              # Security vulnerability tests
│   └── performance/           # Load and performance tests
└── start.sh                   # Automated startup script
```

## How Biometric Authentication Works

### 1. Face Landmark Detection
- **68-point facial landmark detection** using MediaPipe
- **Real-time face tracking** with position, orientation, and expression analysis
- **Liveness detection** to prevent spoofing attacks
- **Facial feature analysis** including eye movement, mouth movement, and head pose

### 2. Hand Landmark Detection
- **21-point hand landmark detection** per hand
- **Gesture recognition** and hand movement tracking
- **Multi-hand support** for enhanced security
- **Hand pose analysis** including finger positions and palm orientation

### 3. Authentication Process
1. **Session Initialization**: Create secure authentication session
2. **Camera Activation**: Access user's webcam with permission
3. **Real-time Processing**: Continuously process video frames
4. **Biometric Analysis**: Extract and analyze face/hand landmarks
5. **Confidence Scoring**: Calculate authentication confidence scores
6. **Decision Making**: Authenticate based on configurable thresholds
7. **Session Management**: Maintain authentication state throughout session

### 4. Security Features
- **Anti-spoofing**: Liveness detection prevents photo/video attacks
- **Multi-factor**: Combines face and hand biometrics for enhanced security
- **Rate limiting**: Prevents brute force attacks
- **Session timeout**: Automatic session expiration for security
- **Encrypted communication**: HTTPS/WSS for secure data transmission

## Quick Start Guide

### Prerequisites
- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **Webcam** (built-in or external)
- **Modern web browser** (Chrome, Firefox, Safari, Edge)

### Option 1: Using start.sh (Recommended)

The easiest way to run HumanAuth is using the provided startup script:

```bash
# Clone and navigate to the project
cd HumanAuth-FullStack

# Make the script executable (Linux/macOS)
chmod +x start.sh

# Run in development mode (default)
./start.sh

# Or explicitly specify development mode
./start.sh --dev

# Run in production mode
./start.sh --prod

# Get help
./start.sh --help
```

The `start.sh` script will:
- ✅ Check for required dependencies (Python, Node.js, npm)
- ✅ Verify model files are present
- ✅ Create Python virtual environment if needed
- ✅ Install/update all dependencies automatically
- ✅ Generate API keys for development
- ✅ Configure environment settings
- ✅ Start both backend and frontend servers
- ✅ Provide cleanup on exit (Ctrl+C)

### Option 2: Manual Setup

If you prefer manual setup or need custom configuration:

#### Backend Setup
```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify model files exist
ls -la face_landmarker.task hand_landmarker.task

# Start backend server
python app.py
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Or build for production
npm run build
```

## Usage Instructions

### 1. Starting the System
```bash
# Start in development mode (default)
./start.sh

# The system will display:
# Backend : http://localhost:8000
# Frontend: http://localhost:4200
```

### 2. Accessing the Application
1. Open your web browser
2. Navigate to `http://localhost:4200`
3. Allow camera permissions when prompted
4. Click "Start Authentication" to begin

### 3. Authentication Process
1. **Position yourself** in front of the camera
2. **Look directly** at the camera for face detection
3. **Show your hands** in the camera view for hand detection
4. **Wait for authentication** - the system will display confidence scores
5. **Authentication complete** when thresholds are met

## API Documentation

### Authentication
All API endpoints require an API key in the header:
```
X-API-Key: your-api-key-here
```

### Endpoints

#### Health Check
```http
GET /api/v1/health
```
**Response:**
```json
{
  "success": true,
  "data": {
    "timestamp": "2026-03-31T11:07:00.000Z",
    "models": {
      "face": true,
      "hand": true
    }
  }
}
```

#### Create Authentication Session
```http
POST /api/v1/sessions
```
**Response:**
```json
{
  "success": true,
  "data": {
    "session_id": "session_abc123...",
    "message": "Authentication session started"
  }
}
```

#### Process Frame
```http
POST /api/v1/sessions/{session_id}/process
Content-Type: application/json

{
  "frame": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "authenticated": false,
    "confidence": 0.75,
    "message": "Face detected, analyzing...",
    "details": {
      "face_confidence": 0.85,
      "hand_confidence": 0.65,
      "landmarks_detected": true
    }
  }
}
```

#### Single Image Verification
```http
POST /api/v1/verify
Content-Type: application/json

{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
}
```

#### Reset Session
```http
POST /api/v1/sessions/{session_id}/reset
```

### Rate Limits
- **Health checks**: 60 requests per minute
- **Session creation**: 60 requests per minute
- **Frame processing**: 600 requests per minute (10 FPS)
- **Verification**: 30 requests per minute

## Testing

The system includes comprehensive testing across multiple categories:

### Running All Tests
```bash
# Run the complete test suite
python tests/run_all_tests.py

# Run specific test categories
python -m pytest tests/backend/          # Backend tests
python -m pytest tests/frontend/         # Frontend tests
python -m pytest tests/integration/      # Integration tests
python -m pytest tests/security/         # Security tests
python -m pytest tests/performance/      # Performance tests
```

### Test Categories

#### Backend Tests
- **Unit tests**: Core authentication logic
- **API tests**: REST endpoint functionality
- **Model tests**: Biometric processing accuracy
- **Visualization tests**: Landmark rendering

#### Frontend Tests
- **Component tests**: Angular component functionality
- **Service tests**: Camera and authentication services
- **Integration tests**: Frontend-backend communication

#### Security Tests
- **Vulnerability scanning**: Common security issues
- **Authentication bypass**: Security mechanism testing
- **Rate limiting**: DoS protection verification

#### Performance Tests
- **Load testing**: High-concurrency scenarios
- **Latency testing**: Response time measurement
- **Memory usage**: Resource consumption analysis

### Test Results Interpretation
- **✅ PASS**: Test successful
- **❌ FAIL**: Test failed - requires attention
- **⚠️ SKIP**: Test skipped (missing dependencies/conditions)

## Configuration

### Environment Variables

#### Backend Configuration
```bash
# Server Configuration
PORT=8000                    # Server port (default: 8000)
FLASK_ENV=development        # Environment mode
SECRET_KEY=your-secret-key   # Flask session secret

# Authentication
API_KEY=your-api-key         # API authentication key

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:4200,https://yourdomain.com

# Model Paths (optional - defaults to backend/ directory)
FACE_MODEL_PATH=/path/to/face_landmarker.task
HAND_MODEL_PATH=/path/to/hand_landmarker.task

# Logging
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR
```

#### Frontend Configuration
Edit `frontend/src/environments/environment.ts`:
```typescript
export const environment = {
  production: false,
  backendUrl: 'http://localhost:8000'
};
```

### Model Files
The system requires two MediaPipe model files:
- **face_landmarker.task**: Face landmark detection model (~2.6MB)
- **hand_landmarker.task**: Hand landmark detection model (~2.3MB)

These files should be placed in the `backend/` directory and are included with the project.

## 🛠️ Development

### Development Mode vs Production Mode

#### Development Mode (Default)
- **Frontend**: Runs on `http://localhost:4200` with hot reload
- **Backend**: Runs on `http://localhost:8000` with debug mode
- **CORS**: Allows all origins for easier testing
- **Logging**: Verbose logging enabled
- **API Keys**: Auto-generated development keys

#### Production Mode
- **Frontend**: Built and served by backend
- **Backend**: Optimized for production with security hardening
- **CORS**: Restricted to specified origins only
- **Logging**: Production-level logging
- **API Keys**: Must be explicitly configured

### Building for Production
```bash
# Build frontend
cd frontend
npm run build

# The built files will be in dist/frontend/browser/
# Backend will automatically serve these files
```

### Custom Development Setup
```bash
# Backend with custom configuration
cd backend
export FLASK_ENV=development
export API_KEY=my-dev-key
export LOG_LEVEL=DEBUG
python app.py

# Frontend with custom backend URL
cd frontend
# Edit src/environments/environment.ts
npm start
```



## 📊 System Requirements

### Minimum Requirements
- **CPU**: Dual-core 2.0GHz processor
- **RAM**: 4GB system memory
- **Storage**: 1GB free space
- **Camera**: 720p webcam
- **Browser**: Chrome, Firefox, Safari, Edge

### Recommended Requirements
- **CPU**: Quad-core 2.5GHz processor or better
- **RAM**: 8GB system memory
- **Storage**: 2GB free space
- **Camera**: 1080p webcam with good low-light performance
- **Browser**: Latest version of supported browsers

### Network Requirements
- **Local development**: No internet required after initial setup
- **Production deployment**: HTTPS required for camera access
- **Bandwidth**: Minimal - all processing is local

## Security Considerations

### Data Privacy
- **No data storage**: Biometric data is processed in real-time and not stored
- **Local processing**: All biometric analysis happens locally
- **Session-based**: Authentication state is temporary and session-scoped

### Security Features
- **API key authentication**: Prevents unauthorized access
- **Rate limiting**: Protects against DoS attacks
- **CORS protection**: Restricts cross-origin requests
- **Input validation**: Sanitizes all user inputs
- **Session timeout**: Automatic session expiration

### Production Security
- **Use HTTPS**: Required for camera access and secure communication
- **Strong API keys**: Generate cryptographically secure API keys
- **Regular updates**: Keep dependencies updated for security patches
- **Access logging**: Monitor and log authentication attempts

## Performance Optimization

### Backend Optimization
- **Model caching**: Models are loaded once and reused
- **Session pooling**: Efficient session management
- **Memory management**: Automatic cleanup of expired sessions
- **Rate limiting**: Prevents resource exhaustion

### Frontend Optimization
- **Frame rate control**: Configurable processing frequency
- **Canvas optimization**: Efficient rendering and drawing
- **Memory management**: Proper cleanup of video streams
- **Lazy loading**: Components loaded on demand

### System Optimization
- **Hardware acceleration**: Utilizes GPU when available
- **Multi-threading**: Parallel processing where possible
- **Caching strategies**: Efficient resource utilization
- **Connection pooling**: Optimized network communication

## 📝 License

This project is developed for educational purposes. Please refer to the LICENSE file for detailed licensing information.

---

**Author**: Jason Dank | Jack Denholm
**Last Updated**: March 31, 2026

