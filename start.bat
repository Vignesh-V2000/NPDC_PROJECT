@echo off
setlocal

echo ==========================================
echo   NPDC - National Polar Data Center
echo   Starting up...
echo ==========================================
echo.

:: -------------------------------
:: [0/8] Check for .env file
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
echo [0/8] Configuration .env file found.

:: -------------------------------
:: [1/8] Create virtual environment
:: -------------------------------
if not exist ".venv\Scripts\activate.bat" (
    echo [1/8] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo       Done.
) else (
    echo [1/8] Virtual environment found.
)
echo.

:: -------------------------------
:: [2/8] Activate virtual environment
:: -------------------------------
echo [2/8] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment.
    pause
    exit /b 1
)
echo       Done.
echo.

:: -------------------------------
:: [3/8] Install dependencies (only once)
:: -------------------------------
if not exist ".deps_installed" (
    echo [3/8] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
    echo. > .deps_installed
    echo       Done.
) else (
    echo [3/8] Dependencies already installed.
)
echo.

:: -------------------------------
:: [4/8] Run migrations + system check
:: -------------------------------
echo [4/8] Running migrations...
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
:: [5/8] First-time setup (IMPORTANT)
:: -------------------------------
if exist ".setup_done" (
    echo [5/8] Setup already completed. Skipping import.
    echo       To re-run setup, delete .setup_done
) else (
    echo [5/8] Running first-time setup ^(user import + password reset^)
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
:: [6/8] Setup Ollama (local AI fallback)
:: -------------------------------
echo [6/8] Checking Ollama ^(local AI fallback^)...

set "OLLAMA_INSTALL_DIR=%LOCALAPPDATA%\Programs\Ollama"
set "PATH=%PATH%;%OLLAMA_INSTALL_DIR%"

where ollama >nul 2>&1
if errorlevel 1 (
    echo       Ollama not found. Downloading installer ^(requires internet^)...
    curl -fsSL --max-time 120 -o "%TEMP%\OllamaSetup.exe" "https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
    if errorlevel 1 (
        echo       WARNING: Could not download Ollama. Local AI fallback will be unavailable.
        goto :skip_ollama
    )
    echo       Installing Ollama silently...
    "%TEMP%\OllamaSetup.exe" /S
    timeout /t 5 /nobreak >nul
    where ollama >nul 2>&1
    if errorlevel 1 (
        echo       WARNING: Ollama install did not complete. Local AI fallback may not work.
        goto :skip_ollama
    )
    echo       Ollama installed successfully.
) else (
    echo       Ollama already installed.
)

:: Start Ollama service if not already running
curl -s --max-time 2 http://localhost:11434 >nul 2>&1
if errorlevel 1 (
    echo       Starting Ollama service in background...
    start /B "" ollama serve
    timeout /t 4 /nobreak >nul
) else (
    echo       Ollama service already running.
)

:: Pull llama3.2 model if not already present
ollama list 2>nul | findstr /I "llama3.2" >nul
if errorlevel 1 (
    echo       Pulling llama3.2 model ^(first-time only - may take several minutes^)...
    ollama pull llama3.2
    if errorlevel 1 (
        echo       WARNING: Could not pull llama3.2. Local AI fallback will not work.
    ) else (
        echo       llama3.2 model ready.
    )
) else (
    echo       llama3.2 model already present.
)

:skip_ollama
echo.

:: -------------------------------
:: [7/8] Starting development server
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