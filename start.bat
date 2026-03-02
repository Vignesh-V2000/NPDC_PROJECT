@echo off
echo ==========================================
echo   NPDC - National Polar Data Center
echo   Starting up...
echo ==========================================
echo.

:: Create virtual environment if it doesn't exist
if not exist ".venv\Scripts\activate.bat" (
    echo [1/7] Creating virtual environment...
    python -m venv .venv
    echo       Done.
) else (
    echo [1/7] Virtual environment found.
)
echo.

:: Activate virtual environment
echo [2/7] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment.
    pause
    exit /b 1
)
echo       Done.
echo.

:: Install/update dependencies
echo [3/7] Installing dependencies...
pip install -r requirements.txt -q
echo       Done.
echo.

:: Load legacy database SQL
echo [4/7] Loading legacy database schema...
psql -U postgres -d npdc -f user_login_22_oct_2025.sql 2>nul
if errorlevel 1 (
    echo WARNING: Could not load SQL file. Make sure PostgreSQL is running and user_login table exists.
    echo          This is only needed on first setup.
) else (
    echo       Done.
)
echo.

:: Run migrations
echo [5/7] Running migrations...
python manage.py migrate
python manage.py createcachetable 2>nul
echo       Done.
echo.

:: Run complete setup ONLY on first run
if exist ".setup_done" (
    echo [6/7] Setup already completed. Skipping import.
    echo       To re-import, delete .setup_done and run start.bat again.
) else (
    echo [6/7] Running first-time setup (legacy data import^)...
    python setup_complete.py
    if not errorlevel 1 (
        echo. > .setup_done
        echo       Setup complete. Marker file created.
    )
)
echo.

:: Start server
echo ==========================================
echo [7/7] Starting development server...
echo       Open http://localhost:10000
echo       Press Ctrl+C to stop.
echo ==========================================
echo.
python manage.py runserver 10000
