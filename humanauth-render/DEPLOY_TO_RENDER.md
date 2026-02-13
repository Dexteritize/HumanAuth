# Deploying HumanAuth to Render

This guide provides detailed instructions for deploying the HumanAuth application to [Render](https://render.com), a unified cloud platform for building and running applications and websites.

## Prerequisites

Before you begin, make sure you have:

1. A [Render account](https://dashboard.render.com/register)
2. Your HumanAuth code in a Git repository (GitHub, GitLab, or Bitbucket)
3. The required model files (`face_landmarker.task` and `hand_landmarker.task`) in the `backend/` directory

## Deployment Options

There are two ways to deploy HumanAuth to Render:

1. **Blueprint Deployment** (Recommended): Uses the `render.yaml` file to automatically configure and deploy the service
2. **Manual Deployment**: Configure and deploy the service manually

## Option 1: Blueprint Deployment (Recommended)

Blueprint deployment is the easiest way to deploy HumanAuth as it automatically sets up the service based on the configuration in the `render.yaml` file.

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
   - Review the service that will be created:
     - `humanauth`: A combined web service that includes both the Flask API backend and Angular frontend
   - You can modify environment variables if needed

4. **Deploy the Blueprint**
   - Click "Apply" to start the deployment process
   - Render will create and deploy the service according to the configuration in `render.yaml`
   - This process may take a few minutes to complete

5. **Verify the Deployment**
   - Once deployment is complete, you'll see the service in your Render dashboard
   - Click on the service to view its details and access the deployed URL
   - The service URL is where you'll access the HumanAuth application

## Option 2: Manual Deployment

If you prefer more control over the deployment process, you can manually deploy the service.

### Combined Service Deployment:

1. **Create a New Web Service**
   - Log in to your Render dashboard
   - Click "New" and select "Web Service"
   - Connect your repository if you haven't already

2. **Configure the Web Service**
   - **Name**: `humanauth` (or your preferred name)
   - **Root Directory**: `humanauth-render`
   - **Environment**: `Python`
   - **Region**: Choose the region closest to your users
   - **Branch**: Your main branch (e.g., `main` or `master`)
   - **Build Command**: 
     ```
     # Build frontend
     cd frontend && npm install && npm run build && cd ..
     # Build backend
     pip install -r backend/requirements.txt
     ```
   - **Start Command**: `cd backend && python app.py`

3. **Set Environment Variables**
   - Click "Advanced" and add the following environment variables:
     - `PORT`: `8000`
     - `FLASK_ENV`: `production`
     - `API_KEY`: Generate a secure random string or use Render's auto-generated secret
     - `SECRET_KEY`: Generate a secure random string or use Render's auto-generated secret
     - `PYTHON_VERSION`: `3.9.0` (or your preferred version)
     - `NODE_VERSION`: `20.x` (or your preferred version)

4. **Create the Web Service**
   - Click "Create Web Service"
   - Render will start building and deploying your service

## Troubleshooting

### Common Issues:

1. **Build Failures**
   - **Issue**: The build process fails during deployment
   - **Solution**: Check the build logs for specific errors. Common issues include:
     - Missing dependencies: Ensure all required packages are listed in `requirements.txt` or `package.json`
     - Node.js version: Try specifying a different Node.js version in the environment variables
     - Python version: Try specifying a different Python version in the environment variables

2. **Frontend Not Loading**
   - **Issue**: The frontend doesn't load or shows a blank page
   - **Solution**: 
     - Check that the frontend build completed successfully in the build logs
     - Verify that the frontend files were correctly built in the `frontend/dist/frontend` directory
     - Ensure the Flask app is correctly serving the static files

3. **Missing Model Files**
   - **Issue**: The application fails because it cannot find the model files
   - **Solution**: Ensure the model files (`face_landmarker.task` and `hand_landmarker.task`) are in the `backend/` directory

4. **Environment Variable Issues**
   - **Issue**: The application cannot access environment variables
   - **Solution**: 
     - Check that all required environment variables are set in the Render dashboard
     - Verify that the application is correctly accessing the environment variables

## Monitoring and Logs

Render provides built-in monitoring and logging for your service:

1. **View Logs**
   - Go to your service in the Render dashboard
   - Click on the "Logs" tab to view real-time logs
   - Use these logs to diagnose issues with your application

2. **Monitor Performance**
   - Render provides basic metrics for your service
   - Monitor CPU and memory usage to ensure your application is running efficiently

## Scaling

If you need to scale your application:

1. **Upgrade Your Plan**
   - Render offers different plans with varying resources
   - Upgrade to a plan that meets your performance needs

2. **Adjust Instance Type**
   - You can select a different instance type with more CPU and memory to handle increased load

## Conclusion

You've successfully deployed HumanAuth to Render! Your application is now accessible via the URL provided by Render for your service.

For more information about Render's features and capabilities, refer to the [Render documentation](https://render.com/docs).