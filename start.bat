@echo off
echo ==========================================
echo   NPDC - National Polar Data Center
echo   Starting up...
echo ==========================================
echo.

:: Create virtual environment if it doesn't exist
if not exist ".venv\Scripts\activate.bat" (
    echo [1/5] Creating virtual environment...
    python -m venv .venv
    echo       Done.
) else (
    echo [1/5] Virtual environment found.
)
echo.

:: Activate virtual environment
echo [2/5] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment.
    pause
    exit /b 1
)
echo       Done.
echo.

:: Install/update dependencies
echo [3/6] Installing dependencies...
pip install -r requirements.txt -q
echo       Done.
echo.

:: Run migrations
echo [4/6] Running migrations...
python manage.py migrate
python manage.py createcachetable 2>nul
echo       Done.
echo.

:: Run complete setup (import users, datasets, link submitters)
echo [5/6] Running complete setup (legacy data import)...
python setup_complete.py
echo       Done.
echo.

:: Start server
echo ==========================================
echo [6/6] Starting development server...
echo       Open http://localhost:8000
echo       Press Ctrl+C to stop.
echo ==========================================
echo.
python manage.py runserver 8000
