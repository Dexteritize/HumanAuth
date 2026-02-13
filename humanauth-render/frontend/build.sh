#!/bin/bash
# Frontend build script for Render deployment

set -e  # Exit on error

echo "Building HumanAuth frontend for production..."

# Install dependencies
npm install

# Build the application
npm run build

echo "Frontend build complete!"