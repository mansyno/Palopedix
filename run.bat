@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo                 Starting Palopedix
echo ========================================================

REM 1. Activate Conda environment if available
where conda >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [*] Activating Conda base environment...
    call conda activate base 2>nul
)

REM 2. Verify Python installation
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ and re-run.
    pause
    exit /b 1
)

REM 3. Check and install Python dependencies if missing
python -c "import fastapi, uvicorn, pydantic, click, tabulate" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] Installing required Python packages from requirements.txt...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install Python dependencies.
        pause
        exit /b 1
    )
)

REM 4. Check and install UI dependencies if missing
if not exist "ui\node_modules\" (
    echo [*] Installing UI packages (npm install)...
    cd ui
    call npm install
    cd ..
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install npm packages.
        pause
        exit /b 1
    )
)

REM 5. Auto-extract assets if local zip is present and unextracted
if exist "assets\palworld_assets.zip" (
    if not exist "assets\palworld_assets\" (
        if not exist "assets\pals\" (
            echo [*] Found assets\palworld_assets.zip. Auto-extracting into assets/...
            python -c "import zipfile; z = zipfile.ZipFile('assets/palworld_assets.zip'); z.extractall('assets'); print('[*] Assets extracted successfully.')"
        )
    )
)

REM 6. Launch Application (FastAPI backend + Vite frontend)
echo [*] Launching Palopedix web app...
cd ui
call npm run dev
pause
