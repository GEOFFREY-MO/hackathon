#!/bin/bash

# Exit on error
set -e

echo "Starting deployment process..."

# Install system dependencies
echo "Installing system dependencies..."
apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libpq-dev

# Upgrade pip to latest version
python -m pip install --upgrade pip==25.1.1

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Set up environment
echo "Setting up environment..."
export FLASK_APP=backend/app.py
export FLASK_ENV=production
export PYTHONPATH=/opt/render/project/src

# Run database migrations
echo "Running database migrations..."
cd backend
flask db upgrade
cd ..

# Start the application
echo "Starting application..."
gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120 