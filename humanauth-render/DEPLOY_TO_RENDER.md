# Deploying HumanAuth to Render

This guide provides detailed instructions for deploying the HumanAuth application to [Render](https://render.com), a unified cloud platform for building and running applications and websites.

## Prerequisites

Before you begin, make sure you have:

1. A [Render account](https://dashboard.render.com/register)
2. Your HumanAuth code in a Git repository (GitHub, GitLab, or Bitbucket)
3. The required model files (`face_landmarker.task` and `hand_landmarker.task`) in the `backend/` directory

## Deployment Options

There are two ways to deploy HumanAuth to Render:

1. **Blueprint Deployment** (Recommended): Uses the `render.yaml` file to automatically configure and deploy both services
2. **Manual Deployment**: Configure and deploy each service separately

## Option 1: Blueprint Deployment (Recommended)

Blueprint deployment is the easiest way to deploy HumanAuth as it automatically sets up both the backend and frontend services based on the configuration in the `render.yaml` file.

### Steps:

1. **Fork or Clone the Repository**
   - Ensure your repository contains the `humanauth-render` directory with all necessary files

2. **Connect Your Repository to Render**
   - Log in to your Render dashboard
   - Go to the "Blueprints" section
   - Click "New Blueprint Instance"
   - Connect your GitHub/GitLab/Bitbucket account if you haven't already
   - Select the repository containing your HumanAuth code

3. **Configure the Blueprint**
   - Render will automatically detect the `render.yaml` file in the `humanauth-render` directory
   - Review the services that will be created:
     - `humanauth-backend`: Python web service for the Flask API
     - `humanauth-frontend`: Static site for the Angular frontend
   - You can modify environment variables if needed

4. **Deploy the Blueprint**
   - Click "Apply" to start the deployment process
   - Render will create and deploy both services according to the configuration in `render.yaml`
   - This process may take a few minutes to complete

5. **Verify the Deployment**
   - Once deployment is complete, you'll see both services in your Render dashboard
   - Click on each service to view its details and access the deployed URL
   - The frontend service URL is where you'll access the HumanAuth application

## Option 2: Manual Deployment

If you prefer more control over the deployment process, you can manually deploy each service.

### Backend Deployment:

1. **Create a New Web Service**
   - Log in to your Render dashboard
   - Click "New" and select "Web Service"
   - Connect your repository if you haven't already

2. **Configure the Web Service**
   - **Name**: `humanauth-backend` (or your preferred name)
   - **Root Directory**: `humanauth-render`
   - **Environment**: `Python`
   - **Region**: Choose the region closest to your users
   - **Branch**: Your main branch (e.g., `main` or `master`)
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && python app.py`

3. **Set Environment Variables**
   - Click "Advanced" and add the following environment variables:
     - `PORT`: `8000`
     - `FLASK_ENV`: `production`
     - `API_KEY`: Generate a secure random string or use Render's auto-generated secret
     - `SECRET_KEY`: Generate a secure random string or use Render's auto-generated secret
     - `PYTHON_VERSION`: `3.9.0` (or your preferred version)

4. **Create the Web Service**
   - Click "Create Web Service"
   - Render will start building and deploying your backend service

### Frontend Deployment:

1. **Create a New Static Site**
   - In your Render dashboard, click "New" and select "Static Site"
   - Connect your repository if you haven't already

2. **Configure the Static Site**
   - **Name**: `humanauth-frontend` (or your preferred name)
   - **Root Directory**: `humanauth-render`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/dist/frontend`
   - **Region**: Choose the same region as your backend service

3. **Set Environment Variables**
   - Click "Advanced" and add the following environment variables:
     - `BACKEND_URL`: The URL of your backend service (e.g., `https://humanauth-backend.onrender.com`)
     - `NODE_VERSION`: `18.x` (or your preferred version)

4. **Configure Redirects/Rewrites**
   - Add a redirect/rewrite rule:
     - **Source**: `/*`
     - **Destination**: `/index.html`
     - **Type**: `Rewrite`

5. **Create the Static Site**
   - Click "Create Static Site"
   - Render will start building and deploying your frontend service

## Connecting Frontend to Backend

For the frontend to communicate with the backend, you need to ensure:

1. The `BACKEND_URL` environment variable in the frontend service is set to the URL of your backend service
2. CORS is properly configured in the backend to allow requests from the frontend
   - The `render.yaml` file and backend code already include CORS configuration for Render deployments

## Troubleshooting

### Common Issues:

1. **Build Failures**
   - **Issue**: The build process fails during deployment
   - **Solution**: Check the build logs for specific errors. Common issues include:
     - Missing dependencies: Ensure all required packages are listed in `requirements.txt` or `package.json`
     - Node.js version: Try specifying a different Node.js version in the environment variables
     - Python version: Try specifying a different Python version in the environment variables

2. **CORS Errors**
   - **Issue**: Frontend cannot communicate with backend due to CORS restrictions
   - **Solution**: 
     - Ensure the `ALLOWED_ORIGINS` environment variable includes your frontend URL
     - Check that the backend CORS configuration is correct
     - Verify that the `BACKEND_URL` in the frontend environment variables is correct

3. **Missing Model Files**
   - **Issue**: The application fails because it cannot find the model files
   - **Solution**: Ensure the model files (`face_landmarker.task` and `hand_landmarker.task`) are in the `backend/` directory

4. **Environment Variable Issues**
   - **Issue**: The application cannot access environment variables
   - **Solution**: 
     - Check that all required environment variables are set in the Render dashboard
     - Verify that the application is correctly accessing the environment variables

## Monitoring and Logs

Render provides built-in monitoring and logging for your services:

1. **View Logs**
   - Go to your service in the Render dashboard
   - Click on the "Logs" tab to view real-time logs
   - Use these logs to diagnose issues with your application

2. **Monitor Performance**
   - Render provides basic metrics for your services
   - Monitor CPU and memory usage to ensure your application is running efficiently

## Scaling

If you need to scale your application:

1. **Upgrade Your Plan**
   - Render offers different plans with varying resources
   - Upgrade to a plan that meets your performance needs

2. **Adjust Instance Type**
   - For the backend service, you can select a different instance type with more CPU and memory

## Conclusion

You've successfully deployed HumanAuth to Render! Your application is now accessible via the URL provided by Render for your frontend service.

For more information about Render's features and capabilities, refer to the [Render documentation](https://render.com/docs).