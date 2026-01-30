@echo off
echo ===========================================
echo      Building Voice AI Editor Pro EXE
echo ===========================================

:: Install PyInstaller if missing
pip install pyinstaller

:: Clean previous builds
rmdir /s /q build
rmdir /s /q dist

:: Build EXE
:: --noconsole: Hide console window
:: --onefile: Single EXE file
:: --name: Output name
:: --add-data: Include ffmpeg if needed (optional)
:: --hidden-import: Ensure faster-whisper is included

python -m PyInstaller --noconsole --onefile ^
    --name "Voice_AI_Editor_Pro" ^
    --icon=NONE ^
    --hidden-import=faster_whisper ^
    --hidden-import=pydub ^
    --hidden-import=customtkinter ^
    voice_app.py

echo ===========================================
echo      Build Complete! Check 'dist' folder
echo ===========================================
pause
