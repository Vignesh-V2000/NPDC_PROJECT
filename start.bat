@echo off
setlocal

echo ==========================================
echo   NPDC - National Polar Data Center
echo   Starting up...
echo ==========================================
echo.

:: -------------------------------
:: [0/7] Check for .env file
:: -------------------------------
if not exist ".env" (
    echo ====== ERROR: MISSING CONFIGURATION ======
    echo The .env file is missing in this directory!
    echo This file is required to connect to the PostgreSQL database.
    echo Please copy .env.example to .env and fill in your credentials.
    echo ==========================================
    echo.
    pause
    exit /b 1
)
echo [0/7] Configuration .env file found.

:: -------------------------------
:: [1/7] Create virtual environment
:: -------------------------------
if not exist ".venv\Scripts\activate.bat" (
    echo [1/7] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo       Done.
) else (
    echo [1/7] Virtual environment found.
)
echo.

:: -------------------------------
:: [2/7] Activate virtual environment
:: -------------------------------
echo [2/7] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment.
    pause
    exit /b 1
)
echo       Done.
echo.

:: -------------------------------
:: [3/7] Install dependencies (only once)
:: -------------------------------
if not exist ".deps_installed" (
    echo [3/7] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
    echo. > .deps_installed
    echo       Done.
) else (
    echo [3/7] Dependencies already installed.
)
echo.

:: -------------------------------
:: [4/7] Run migrations + system check
:: -------------------------------
echo [4/7] Running migrations...
python manage.py migrate
if errorlevel 1 (
    echo ERROR: Migration failed.
    pause
    exit /b 1
)

python manage.py createcachetable 2>nul
python manage.py check
if errorlevel 1 (
    echo ERROR: Django system check failed.
    pause
    exit /b 1
)
echo       Done.
echo.

:: -------------------------------
:: [5/7] First-time setup (IMPORTANT)
:: -------------------------------
if exist ".setup_done" (
    echo [5/7] Setup already completed. Skipping import.
    echo       To re-run setup, delete .setup_done
) else (
    echo [5/7] Running first-time setup ^(user import + password reset^)
    python setup_complete.py
    if errorlevel 1 (
        echo ERROR: Setup failed.
        pause
        exit /b 1
    )
    echo. > .setup_done
    echo       Setup completed successfully.
)

:: -------------------------------
:: [6/7] Starting development server
:: -------------------------------
echo ==========================================
echo   Server starting...
echo   URL: http://localhost:10000
echo   First login: use ANY password
echo   Then reuse same password
echo ==========================================
echo.

python manage.py runserver 10000

endlocal