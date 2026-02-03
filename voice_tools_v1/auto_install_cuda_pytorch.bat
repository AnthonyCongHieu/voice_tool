@echo off
REM =========================================
REM  Auto Install PyTorch CUDA Version
REM =========================================
echo.
echo [INFO] This will reinstall PyTorch with CUDA 12.1 support
echo [INFO] This provides all CUDA DLLs needed for GPU acceleration
echo.
echo WARNING: This will:
echo   1. Uninstall current PyTorch (CPU version)
echo   2. Install PyTorch with CUDA 12.1 (~2.5GB download)
echo   3. Extract and copy CUDA DLLs to cuda_dlls folder
echo.

choice /C YN /M "Do you want to continue"
if errorlevel 2 goto :Cancel
if errorlevel 1 goto :Install

:Install
echo.
echo [1/4] Uninstalling PyTorch CPU version...
venv\Scripts\pip.exe uninstall torch torchaudio torchvision -y

echo.
echo [2/4] Installing PyTorch with CUDA 12.1 support...
echo [INFO] This may take 5-10 minutes...
venv\Scripts\pip.exe install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Installation failed!
    pause
    exit /b 1
)

echo.
echo [3/4] Verifying CUDA support...
venv\Scripts\python.exe -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('CUDA Version:', torch.version.cuda)"

echo.
echo [4/4] Locating and copying CUDA DLLs...
venv\Scripts\python.exe find_cuda_dlls.py

if exist "cuda_dlls" (
    rmdir /s /q cuda_dlls
)
mkdir cuda_dlls

REM Copy DLLs from PyTorch to cuda_dlls folder
for %%D in (cublas64_12.dll cublasLt64_12.dll cudart64_12.dll cudnn64_9.dll nvrtc64_120_0.dll) do (
    if exist "venv\Lib\site-packages\torch\lib\%%D" (
        echo Copying %%D...
        copy "venv\Lib\site-packages\torch\lib\%%D" "cuda_dlls\" >nul
    )
)

echo.
echo [SUCCESS] PyTorch CUDA installation complete!
echo [SUCCESS] CUDA DLLs copied to cuda_dlls folder
echo.
echo Next Step: Run build.bat to rebuild with CUDA support
goto :End

:Cancel
echo.
echo [INFO] Installation cancelled
goto :End

:End
echo.
pause
