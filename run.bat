@echo off
echo ========================================================
echo                 Starting Palopedix
echo ========================================================

REM 1. Activate Conda base if available
call conda activate base 2>nul

REM 2. Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ and re-run.
    pause
    exit /b 1
)

REM 3. Check Python packages
python -c "import fastapi, uvicorn, pydantic, click, tabulate" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] Installing required Python packages from requirements.txt...
    pip install -r requirements.txt
)

REM 4. Check UI dependencies
if not exist "ui\node_modules\" (
    echo [*] Installing UI packages with npm...
    cd ui
    call npm install
    cd ..
)

REM 5. Auto-extract assets if local zip is present and unextracted
if not exist "assets\palworld_assets.zip" goto launch
if exist "assets\palworld_assets\" goto launch
if exist "assets\pals\" goto launch

echo [*] Found assets\palworld_assets.zip. Extracting...
powershell -NoProfile -Command "Expand-Archive -Path 'assets\palworld_assets.zip' -DestinationPath 'assets' -Force"
echo [*] Assets extracted successfully.

:launch
REM 6. Launch Application
echo [*] Launching Palopedix web app...
cd ui
call npm run dev
pause
