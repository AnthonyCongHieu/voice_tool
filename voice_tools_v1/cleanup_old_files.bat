@echo off
REM ============================================
REM  Cleanup Old/Duplicate Files
REM ============================================
echo.
echo ================================================
echo   Project Cleanup - Remove Old/Duplicate Files
echo ================================================
echo.
echo This will DELETE the following files:
echo.
echo OLD CUDA SCRIPTS (replaced by quick_fix_cuda.bat):
echo   - auto_install_cuda_pytorch.bat
echo   - bundle_cuda_fix.bat
echo   - find_cuda_dlls.py
echo.
echo OLD RUN/SETUP SCRIPTS (not needed):
echo   - VoiceTools.bat
echo   - start_voice_tools.bat  
echo   - run_app.bat
echo   - install_optimized.bat
echo   - setup.bat
echo.
echo TEST FILES:
echo   - test_imports.py
echo.
echo FOLDERS TO CLEAN:
echo   - __pycache__ (Python cache)
echo   - build (temporary build files)
echo.
echo FILES TO KEEP:
echo   ✓ voice_app.py (main app)
echo   ✓ config.py
echo   ✓ build.bat (main build)
echo   ✓ quick_fix_cuda.bat (CUDA DLL downloader)
echo   ✓ rebuild_with_cuda.bat (rebuild with CUDA)
echo   ✓ download_cuda_dlls.py (CUDA helper)
echo   ✓ package_for_sharing.bat (packaging)
echo   ✓ requirements.txt
echo   ✓ README.md
echo.

choice /C YN /M "Do you want to continue with cleanup"
if errorlevel 2 goto :Cancel
if errorlevel 1 goto :Cleanup

:Cleanup
echo.
echo [INFO] Starting cleanup...

REM Delete old CUDA scripts
if exist "auto_install_cuda_pytorch.bat" (
    del /f "auto_install_cuda_pytorch.bat"
    echo [OK] Deleted: auto_install_cuda_pytorch.bat
)

if exist "bundle_cuda_fix.bat" (
    del /f "bundle_cuda_fix.bat"
    echo [OK] Deleted: bundle_cuda_fix.bat
)

if exist "find_cuda_dlls.py" (
    del /f "find_cuda_dlls.py"
    echo [OK] Deleted: find_cuda_dlls.py
)

REM Delete old run/setup scripts
if exist "VoiceTools.bat" (
    del /f "VoiceTools.bat"
    echo [OK] Deleted: VoiceTools.bat
)

if exist "start_voice_tools.bat" (
    del /f "start_voice_tools.bat"
    echo [OK] Deleted: start_voice_tools.bat
)

if exist "run_app.bat" (
    del /f "run_app.bat"
    echo [OK] Deleted: run_app.bat
)

if exist "install_optimized.bat" (
    del /f "install_optimized.bat"
    echo [OK] Deleted: install_optimized.bat
)

if exist "setup.bat" (
    del /f "setup.bat"
    echo [OK] Deleted: setup.bat
)

REM Delete test files
if exist "test_imports.py" (
    del /f "test_imports.py"
    echo [OK] Deleted: test_imports.py
)

REM Clean cache/temp folders
if exist "__pycache__" (
    rmdir /s /q "__pycache__"
    echo [OK] Deleted: __pycache__ folder
)

if exist "build" (
    rmdir /s /q "build"
    echo [OK] Deleted: build folder (temporary PyInstaller files)
)

REM Delete old .spec file if exists (will be regenerated)
if exist "Voice_AI_Editor_Pro.spec" (
    del /f "Voice_AI_Editor_Pro.spec"
    echo [OK] Deleted: old .spec file (will be regenerated on build)
)

echo.
echo ================================================
echo [SUCCESS] Cleanup Complete!
echo ================================================
echo.
echo Deleted 9 old batch files + 1 python file
echo Cleaned 2 temporary folders
echo.
echo Project is now cleaner and more organized.
echo.
goto :End

:Cancel
echo.
echo [INFO] Cleanup cancelled
goto :End

:End
pause
