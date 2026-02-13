# HumanAuth Deployment Guide for Render

This guide explains how to deploy the HumanAuth application on Render using the combined deployment approach.

## Overview

The combined deployment approach serves both the frontend and backend from a single web service, simplifying deployment and reducing costs. This is achieved by:

1. Building the Angular frontend during the Docker build process
2. Serving the static frontend files from the Flask application
3. Registering the backend API as a blueprint under the `/api` prefix

## Prerequisites

- A [Render](https://render.com) account
- A Git repository containing your HumanAuth code with the following files:
  - `Dockerfile` (in the repository root)
  - `serve.py` (in the repository root)
  - Modified `app.py` (in humanauth-web/backend)
  - Modified `auth-page.component.ts` (in humanauth-web/frontend)

## Deployment Steps

### 1. Create a New Web Service on Render

1. Log in to your Render dashboard
2. Click on "New" and select "Web Service"
3. Connect your Git repository
4. Give your service a name (e.g., "humanauth")

### 2. Configure the Web Service

Use the following settings:

- **Environment**: Docker
- **Region**: Choose the region closest to your users
- **Branch**: main (or your preferred branch)
- **Root Directory**: Leave empty (uses repository root)
- **Build Command**: Leave empty (handled by Dockerfile)
- **Start Command**: Leave empty (handled by Dockerfile)

### 3. Set Environment Variables

Add the following environment variables:

- `API_KEY`: A secure API key for backend authentication (generate a random string)
- `SECRET_KEY`: A secure secret key for Flask sessions (generate a random string)
- `FLASK_ENV`: Set to `production`
- `PORT`: Set to `10000` (or your preferred port)

Optional environment variables:

- `ALLOWED_ORIGINS`: Comma-separated list of allowed origins for CORS (if you need to access the API from other domains)
- `LOG_LEVEL`: Set to `INFO`, `DEBUG`, `WARNING`, or `ERROR` (default is `INFO`)

### 4. Deploy the Service

1. Click "Create Web Service"
2. Wait for the build and deployment to complete
3. Once deployed, your application will be available at the URL provided by Render (e.g., `https://humanauth.onrender.com`)

## Verification

After deployment, verify that:

1. The frontend is accessible at the root URL
2. The API is accessible at `/api`
3. The health check endpoint is accessible at `/health`

## Troubleshooting

If you encounter issues:

1. Check the Render logs for error messages
2. Verify that all environment variables are set correctly
3. Ensure that the model files (`face_landmarker.task` and `hand_landmarker.task`) are present in the repository

## Security Considerations

1. Always use HTTPS (Render provides this by default)
2. Use strong, randomly generated values for `API_KEY` and `SECRET_KEY`
3. Configure `ALLOWED_ORIGINS` to restrict API access to trusted domains
4. Consider implementing rate limiting for production use

## Scaling

If you need to scale the application:

1. Increase the number of instances in the Render dashboard
2. Adjust the number of workers and threads in the Dockerfile's CMD line:
   ```
   CMD gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 serve:app
   ```
   - For CPU-bound applications, increase the number of workers
   - For I/O-bound applications, increase the number of threads

## Monitoring

Render provides basic monitoring for your web service. For more advanced monitoring:

1. Set up logging to a third-party service
2. Implement health checks and alerts
3. Consider using a monitoring service like New Relic or Datadog

## Cost Optimization

The combined deployment approach already optimizes costs by using a single web service. Additional optimizations:

1. Use the appropriate instance size for your needs
2. Scale down during periods of low traffic
3. Implement caching for frequently accessed data