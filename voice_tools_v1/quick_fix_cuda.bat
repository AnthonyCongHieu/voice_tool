@echo off
REM ============================================
REM  Quick Fix: Auto-download CUDA DLLs
REM ============================================
echo.
echo [INFO] This will download CUDA DLLs from PyTorch CUDA package
echo [INFO] Size: ~2.5GB download (needed for GPU support)
echo.

choice /C YN /M "Do you want to continue"
if errorlevel 2 goto :Manual
if errorlevel 1 goto :AutoDownload

:AutoDownload
echo.
echo [1/4] Uninstalling current PyTorch (CPU version)...
venv\Scripts\pip.exe uninstall -y torch torchvision torchaudio

echo.
echo [2/4] Installing PyTorch with CUDA 12.1...
echo [WAIT] This takes 5-10 minutes depending on internet speed...
echo [INFO] Downloading ~2.5GB from PyTorch CUDA repository...
venv\Scripts\pip.exe install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to install PyTorch CUDA
    echo [INFO] Trying manual download options instead...
    timeout /t 3 /nobreak >nul
    goto :Manual
)

echo.
echo [3/4] Extracting CUDA DLLs to cuda_dlls folder...
if exist cuda_dlls rmdir /s /q cuda_dlls
mkdir cuda_dlls

echo [INFO] Searching for DLLs in PyTorch installation...

REM Copy required DLLs from PyTorch
for %%D in (cublas64_12.dll cublasLt64_12.dll cudart64_12.dll) do (
    if exist "venv\Lib\site-packages\torch\lib\%%D" (
        echo   [OK] Copying %%D...
        copy "venv\Lib\site-packages\torch\lib\%%D" "cuda_dlls\" >nul
    ) else (
        echo   [WARN] %%D not found in PyTorch
    )
)

echo.
echo [4/4] Verifying CUDA installation and DLLs...
venv\Scripts\python.exe -c "import torch; print('PyTorch Version:', torch.__version__); print('CUDA Available:', torch.cuda.is_available()); print('CUDA Version:', torch.version.cuda if torch.cuda.is_available() else 'N/A')"

echo.
venv\Scripts\python.exe download_cuda_dlls.py

set FINAL_DLL_COUNT=0
if exist "cuda_dlls\cublas64_12.dll" set /a FINAL_DLL_COUNT+=1
if exist "cuda_dlls\cublasLt64_12.dll" set /a FINAL_DLL_COUNT+=1
if exist "cuda_dlls\cudart64_12.dll" set /a FINAL_DLL_COUNT+=1

echo.
if %FINAL_DLL_COUNT% GEQ 3 (
    echo ================================================
    echo [SUCCESS] All CUDA DLLs ready!
    echo ================================================
    echo.
    echo Found %FINAL_DLL_COUNT%/3 required DLLs in cuda_dlls folder
    echo.
    echo Next Step: Run rebuild_with_cuda.bat to rebuild app
) else (
    echo ================================================
    echo [PARTIAL] Only %FINAL_DLL_COUNT%/3 DLLs extracted
    echo ================================================
    echo.
    echo This might happen if PyTorch CUDA was not fully installed.
    echo Please try manual download from Option 1 or Option 2 below.
    echo.
    timeout /t 3 /nobreak >nul
    goto :Manual
)
echo.
pause
exit /b 0

:Manual
echo.
echo ================================================
echo Manual Download Options
echo ================================================
echo.
echo Option 1: Whisper Standalone (Quick ~100MB)
echo   1. Visit: https://github.com/Purfview/whisper-standalone-win/releases
echo   2. Download latest release
echo   3. Extract cublas64_12.dll, cublasLt64_12.dll, cudart64_12.dll
echo   4. Copy to: %CD%\cuda_dlls\
echo.
echo Option 2: NVIDIA CUDA Toolkit (Official ~3GB)
echo   1. Visit: https://developer.nvidia.com/cuda-12-1-0-download-archive
echo   2. Install ONLY "Developer ^> Libraries"
echo   3. Copy DLLs from: C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin\
echo   4. Copy to: %CD%\cuda_dlls\
echo.
echo After getting DLLs:
echo   - Run: build.bat
echo   - Then test the app
echo.
pause
