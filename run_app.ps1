# PowerShell script to run SmartRetail AI Application
Write-Host "Starting SmartRetail AI Application..." -ForegroundColor Green
Write-Host ""

# Activate virtual environment
& ".\venv\Scripts\Activate.ps1"

# Set environment variables
$env:FLASK_APP = "backend.app"
$env:FLASK_ENV = "development"
$env:PYTHONPATH = $PWD

# Change to backend directory and run the app
Set-Location backend
python app.py