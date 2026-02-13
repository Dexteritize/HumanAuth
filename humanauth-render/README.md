# HumanAuth for Render

This directory contains a version of HumanAuth optimized for deployment on Render.

## Structure

- `backend/`: Flask backend API
- `frontend/`: Angular frontend application
- `Procfile`: Defines how to run the application on Render
- `render.yaml`: Configuration file for Render deployment

## Deployment Instructions

### Option 1: Deploy using render.yaml (Recommended)

1. Fork or clone this repository
2. Connect your GitHub account to Render
3. Click "New Blueprint Instance" in Render dashboard
4. Select your repository
5. Render will automatically detect the `render.yaml` file and configure the services
6. Click "Apply" to deploy both the backend and frontend services

### Option 2: Manual Deployment

#### Backend Deployment

1. Create a new Web Service in Render
2. Connect your repository
3. Set the following configuration:
   - **Name**: humanauth-backend
   - **Root Directory**: humanauth-render
   - **Environment**: Python
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && python app.py`
   - **Environment Variables**:
     - `PORT`: 8000
     - `FLASK_ENV`: production
     - `API_KEY`: (generate a secure random string)
     - `SECRET_KEY`: (generate a secure random string)

#### Frontend Deployment

1. Create a new Static Site in Render
2. Connect your repository
3. Set the following configuration:
   - **Name**: humanauth-frontend
   - **Root Directory**: humanauth-render
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/dist/frontend`
   - **Environment Variables**:
     - `BACKEND_URL`: (URL of your backend service, e.g., https://humanauth-backend.onrender.com)

## Environment Variables

### Backend

- `PORT`: The port on which the backend server will run (default: 8000)
- `FLASK_ENV`: Set to "production" for production deployment
- `API_KEY`: API key for authentication
- `SECRET_KEY`: Secret key for Flask session
- `ALLOWED_ORIGINS`: Comma-separated list of allowed origins for CORS (default: frontend URL)

### Frontend

- `BACKEND_URL`: URL of the backend service

## Model Files

The backend requires two model files:
- `face_landmarker.task`: Face landmark detection model
- `hand_landmarker.task`: Hand landmark detection model

These files are included in the `backend/` directory.

## Local Development

To run the application locally:

1. Start the backend:
   ```
   cd humanauth-render/backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

2. Start the frontend:
   ```
   cd humanauth-render/frontend
   npm install
   npm start
   ```

3. Open your browser and navigate to http://localhost:4200