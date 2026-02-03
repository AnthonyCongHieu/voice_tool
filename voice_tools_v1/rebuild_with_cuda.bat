@echo off
REM ============================================
REM  Full Rebuild: Kill processes + Build
REM ============================================
echo.
echo ================================================
echo   Complete Rebuild with CUDA Support
echo ================================================
echo.

REM Step 1: Kill all running instances
echo [1/4] Stopping all Voice AI Pro processes...
taskkill /F /IM Voice_AI_Editor_Pro.exe 2>nul
taskkill /F /IM python.exe 2>nul
taskkill /F /IM pythonw.exe 2>nul
timeout /t 3 /nobreak >nul

REM Step 2: Verify CUDA DLLs
echo.
echo [2/4] Checking CUDA DLLs...
if not exist "cuda_dlls" (
    echo [ERROR] cuda_dlls folder not found!
    echo [INFO] Run: quick_fix_cuda.bat first to get DLLs
    pause
    exit /b 1
)

set DLL_COUNT=0
if exist "cuda_dlls\cublas64_12.dll" set /a DLL_COUNT+=1
if exist "cuda_dlls\cublasLt64_12.dll" set /a DLL_COUNT+=1
if exist "cuda_dlls\cudart64_12.dll" set /a DLL_COUNT+=1

if %DLL_COUNT% LSS 3 (
    echo [ERROR] Found %DLL_COUNT%/3 CUDA DLLs
    echo [INFO] Run: quick_fix_cuda.bat first to get missing DLLs
    pause
    exit /b 1
)

echo [SUCCESS] Found all 3 required CUDA DLLs

REM Step 3: Force clean dist folder
echo.
echo [3/4] Force cleaning dist folder...
if exist "dist" (
    rmdir /s /q "dist" 2>nul
    if exist "dist" (
        echo [WARN] Some files locked, retrying...
        timeout /t 2 /nobreak >nul
        rmdir /s /q "dist" 2>nul
    )
)
if exist "build" rmdir /s /q "build" 2>nul

REM Step 4: Build with CUDA
echo.
echo [4/4] Building with CUDA DLLs...
call build.bat

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================
    echo [SUCCESS] Build Complete with CUDA Support!
    echo ================================================
    echo.
    echo Verify DLLs are bundled:
    dir dist\Voice_AI_Editor_Pro\cublas*.dll
    echo.
    echo Test the app:
    echo   dist\Voice_AI_Editor_Pro\Voice_AI_Editor_Pro.exe
    echo.
) else (
    echo.
    echo [ERROR] Build failed!
)

pause
