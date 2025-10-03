@echo off
echo Starting SmartRetail AI Application...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set environment variables
set FLASK_APP=backend.app
set FLASK_ENV=development
set PYTHONPATH=%CD%

REM Change to backend directory and run the app
cd backend
python app.py

pause











