FROM node:18 AS frontend-build

WORKDIR /app/frontend
COPY humanauth-web/frontend/package*.json ./
RUN npm install
COPY humanauth-web/frontend/ ./
RUN npm run build

FROM python:3.9-slim

WORKDIR /app

# Copy frontend build from previous stage
COPY --from=frontend-build /app/frontend/dist/frontend /app/static

# Copy backend code and model files
COPY humanauth-web/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for the combined server
RUN pip install --no-cache-dir gunicorn flask-cors flask-limiter

# Copy model files
COPY humanauth-web/backend/face_landmarker.task .
COPY humanauth-web/backend/hand_landmarker.task .

# Copy backend Python files
COPY humanauth-web/backend/*.py .

# Copy the combined server file
COPY serve.py .

# Set environment variables
ENV FLASK_ENV=production
ENV PORT=10000

# Expose the port
EXPOSE ${PORT}

# Start the application with gunicorn
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 serve:app