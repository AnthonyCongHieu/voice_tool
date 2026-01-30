@echo off
setlocal
echo ===========================================
echo      Building Voice AI Editor Pro EXE
echo ===========================================

:: 1. Check for Virtual Env
if exist "venv\Scripts\python.exe" (
    echo [INFO] Using Virtual Environment...
    set "PYTHON_CMD=venv\Scripts\python.exe"
    goto :RunBuild
)

:: 2. Check for Python 3.11 in Program Files (Verified Path)
if exist "C:\Program Files\Python311\python.exe" (
    echo [INFO] Using Python 3.11...
    set "PYTHON_CMD=C:\Program Files\Python311\python.exe"
    goto :RunBuild
)

:: 3. Fallback to system python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Using System Python...
    set "PYTHON_CMD=python"
    goto :RunBuild
)

echo [ERROR] Python not found! Please install Python.
pause
exit /b 1

:RunBuild
echo [INFO] Command: "%PYTHON_CMD%"

echo [INFO] Cleaning up previous builds to free space...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /f /q "*.spec"

:: Run Build (ONEDIR for fast startup)
"%PYTHON_CMD%" -m PyInstaller --noconsole --onedir --clean ^
    --name "Voice_AI_Editor_Pro" ^
    --icon=NONE ^
    --collect-all=faster_whisper ^
    --hidden-import=pydub ^
    --hidden-import=customtkinter ^
    --collect-all=customtkinter ^
    --log-level=WARN ^
    voice_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ===========================================
    echo      BUILD FAILED!
    echo ===========================================
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ===========================================
echo      Build Success! creating ZIP archive...
echo ===========================================

cd dist
powershell Compress-Archive -Path "Voice_AI_Editor_Pro" -DestinationPath "Voice_AI_Editor_Pro_v3.zip" -Force
cd ..

echo.
echo ===========================================
echo      DONE! 
echo      1. Run folder: dist\Voice_AI_Editor_Pro\Voice_AI_Editor_Pro.exe (Instant Start)
echo      2. Share file: dist\Voice_AI_Editor_Pro_v3.zip
echo ===========================================
dir dist
pause
