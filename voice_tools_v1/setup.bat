@echo off
echo ===========================================
echo      Voice AI Pro - Setup Environment
echo ===========================================

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.10+ and add to PATH.
    pause
    exit /b
)

:: Create Virtual Environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
) else (
    echo [INFO] Virtual environment already exists.
)

:: Activate & Install
echo [INFO] Installing dependencies...
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ===========================================
echo      Setup Complete! 
echo      Run 'server.bat' to start the app.
echo ===========================================
pause
