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

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Set up database
echo "Setting up database..."
export FLASK_APP=app.py
export FLASK_ENV=production

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Start the application
echo "Starting application..."
gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120 