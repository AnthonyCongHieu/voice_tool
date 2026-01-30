@echo off
if not exist "venv" (
    echo [INFO] Virtual environment not found. Running setup...
    call setup.bat
)

echo [INFO] Starting Voice AI Editor Pro...
call venv\Scripts\activate
python voice_app.py
pause
