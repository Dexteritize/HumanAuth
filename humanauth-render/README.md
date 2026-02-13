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
5. Render will automatically detect the `render.yaml` file and configure the service
   - Note: The `render.yaml` file includes a `rootDir: humanauth-render` setting to ensure Render uses the correct directory
6. Click "Apply" to deploy the service

### Option 2: Manual Deployment

1. Create a new Web Service in Render
2. Connect your repository
3. Set the following configuration:
   - **Name**: humanauth
   - **Root Directory**: humanauth-render
   - **Environment**: Python
   - **Build Command**: 
     ```
     # Build frontend
     cd frontend && npm install && npm run build && cd ..
     # Build backend
     pip install -r backend/requirements.txt
     ```
   - **Start Command**: `cd backend && python app.py`
   - **Environment Variables**:
     - `PORT`: 8000
     - `FLASK_ENV`: production
     - `API_KEY`: (generate a secure random string)
     - `SECRET_KEY`: (generate a secure random string)
     - `NODE_VERSION`: 20.x (or your preferred version)

## Environment Variables

- `PORT`: The port on which the server will run (default: 8000)
- `FLASK_ENV`: Set to "production" for production deployment
- `API_KEY`: API key for authentication
- `SECRET_KEY`: Secret key for Flask session
- `ALLOWED_ORIGINS`: Comma-separated list of allowed origins for CORS (optional)
- `NODE_VERSION`: Node.js version to use for building the frontend (default: 20.x)

## Model Files

The backend requires two model files:
- `face_landmarker.task`: Face landmark detection model
- `hand_landmarker.task`: Hand landmark detection model

These files are included in the `backend/` directory.

## Local Development

For local development, you can run the backend and frontend separately:

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

Alternatively, you can build the frontend and have the backend serve it:

1. Build the frontend:
   ```
   cd humanauth-render/frontend
   npm install
   npm run build
   ```

2. Start the backend:
   ```
   cd humanauth-render/backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

3. Open your browser and navigate to http://localhost:8000