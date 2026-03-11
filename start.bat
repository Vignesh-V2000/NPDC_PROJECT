@echo off
setlocal

echo ==========================================
echo   NPDC - National Polar Data Center
echo   Starting up...
echo ==========================================
echo.

:: -------------------------------
:: [0/9] Check for .env file
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
echo [0/9] Configuration .env file found.

:: -------------------------------
:: [1/9] Create virtual environment
:: -------------------------------
if not exist ".venv\Scripts\activate.bat" (
    echo [1/9] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo       Done.
) else (
    echo [1/9] Virtual environment found.
)
echo.

:: -------------------------------
:: [2/9] Activate virtual environment
:: -------------------------------
echo [2/9] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment.
    pause
    exit /b 1
)
echo       Done.
echo.

:: -------------------------------
:: [3/9] Install dependencies (only once)
:: -------------------------------
if not exist ".deps_installed" (
    echo [3/9] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
    echo. > .deps_installed
    echo       Done.
) else (
    echo [3/9] Dependencies already installed.
)
echo.

:: -------------------------------
:: [4/9] Run migrations + system check
:: -------------------------------
echo [4/9] Running migrations...
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
:: [5/9] First-time setup (IMPORTANT)
:: -------------------------------
if exist ".setup_done" (
    echo [5/9] Setup already completed. Skipping import.
    echo       To re-run setup, delete .setup_done
) else (
    echo [5/9] Running first-time setup ^(user import + password reset^)
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
:: [6/9] Setup Ollama (local AI fallback)
:: -------------------------------
echo [6/9] Checking Ollama ^(local AI fallback^)...

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
:: [7/9] Setup Squid Proxy (dataset caching)
:: -------------------------------
echo [7/9] Checking Squid Proxy ^(dataset caching^)...

set "SQUID_DIR=C:\Squid"
set "SQUID_CONF=%SQUID_DIR%\etc\squid\squid.conf"
set "SQUID_BIN=%SQUID_DIR%\bin\squid.exe"

:: Check for Administrator privileges (required for Squid service management)
net session >nul 2>&1
if errorlevel 1 (
    echo       WARNING: Not running as Administrator.
    echo       Squid proxy requires admin rights for first-time setup.
    echo       Right-click start.bat and select "Run as administrator".
    if not exist "%SQUID_BIN%" (
        echo       Skipping Squid setup ^(not installed and no admin rights^).
        goto :skip_squid
    )
    :: If already running from a previous admin session, let it be
    netstat -an 2>nul | findstr ":3128" >nul 2>&1
    if errorlevel 1 (
        echo       Squid is installed but not running. Need admin rights to start.
        goto :skip_squid
    ) else (
        echo       Squid proxy already running on port 3128 ^(from previous session^).
        goto :skip_squid
    )
)

:: ---- From here on, we HAVE admin rights ----

:: Step 1: Install Squid if not present
if not exist "%SQUID_BIN%" (
    echo       Squid not found. Downloading installer...
    curl -fsSL --max-time 120 -o "%TEMP%\squid.msi" "https://www.diladele.com/pkg/squid/4.14/squid.msi"
    if errorlevel 1 (
        echo       WARNING: Could not download Squid. Dataset caching will be unavailable.
        goto :skip_squid
    )
    echo       Installing Squid...
    msiexec /i "%TEMP%\squid.msi" /passive /norestart
    timeout /t 15 /nobreak >nul
    if not exist "%SQUID_BIN%" (
        echo       WARNING: Squid install did not complete. Dataset caching may not work.
        goto :skip_squid
    )
    echo       Squid installed successfully.
) else (
    echo       Squid already installed.
)

:: Step 2: Stop Squid service (so we can safely apply config + init cache)
net stop squidsrv >nul 2>&1
timeout /t 2 /nobreak >nul

:: Step 3: Copy our reverse-proxy squid.conf over the default/old one
if exist "%~dp0squid\squid.conf" (
    echo       Applying NPDC reverse-proxy configuration...
    copy /Y "%~dp0squid\squid.conf" "%SQUID_CONF%" >nul 2>&1
    if errorlevel 1 (
        echo       WARNING: Could not copy squid.conf. Check file permissions.
    ) else (
        echo       Configuration applied.
    )
)

:: Step 4: Initialize/rebuild cache directories (always run after config change)
echo       Initializing Squid cache directories...
if not exist "%SQUID_DIR%\var\cache\squid" (
    mkdir "%SQUID_DIR%\var\cache\squid" >nul 2>&1
)
if not exist "%SQUID_DIR%\var\log\squid" (
    mkdir "%SQUID_DIR%\var\log\squid" >nul 2>&1
)
"%SQUID_BIN%" -z >nul 2>&1
timeout /t 5 /nobreak >nul
if not exist "%SQUID_DIR%\var\cache\squid\00" (
    echo       WARNING: Cache directory init may have failed. Check cache.log.
) else (
    echo       Cache directories ready.
)

:: Step 5: Start Squid service
echo       Starting Squid proxy service...
net start squidsrv >nul 2>&1
if errorlevel 1 (
    echo       Service start failed. Trying direct launch...
    start /B "" "%SQUID_BIN%" >nul 2>&1
)
timeout /t 3 /nobreak >nul

:: Step 6: Verify Squid is listening
netstat -an 2>nul | findstr ":3128" >nul 2>&1
if errorlevel 1 (
    echo       WARNING: Squid is not listening on port 3128. Dataset caching unavailable.
    echo       Check C:\Squid\var\log\squid\cache.log for details.
) else (
    echo       Squid reverse proxy running on port 3128.
)

:skip_squid
echo.

:: -------------------------------
:: [8/9] Starting development server
:: -------------------------------
echo ==========================================
echo   Server starting...
echo   Django:  http://localhost:10000
echo   Squid:   http://localhost:3128 ^(reverse proxy cache^)
echo   First login: use ANY password
echo   Then reuse same password
echo ==========================================
echo.

python manage.py runserver 10000

endlocal