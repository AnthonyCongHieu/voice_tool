@echo off
REM =========================================
REM  CUDA DLL Bundling Fix for Voice AI Pro
REM =========================================
echo.
echo [INFO] This script will fix the CUDA DLL missing error
echo [INFO] by bundling required CUDA 12.x DLLs with your app
echo.

REM Step 1: Create cuda_dlls folder if not exists
if not exist "cuda_dlls" (
    echo [1/3] Creating cuda_dlls folder...
    mkdir cuda_dlls
) else (
    echo [1/3] cuda_dlls folder already exists
)

REM Step 2: Inform user
echo.
echo [2/3] CUDA DLL Setup Required
echo.
echo You need to download CUDA 12.x DLLs and place them in the cuda_dlls\ folder.
echo.
echo Required DLLs:
echo   - cublas64_12.dll
echo   - cublasLt64_12.dll
echo   - cudart64_12.dll
echo.
echo Options to get DLLs:
echo   A) Install CUDA Toolkit 12.x from NVIDIA (https://developer.nvidia.com/cuda-downloads)
echo      Then copy DLLs from: C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin\
echo.
echo   B) Install PyTorch with CUDA support:
echo      venv\Scripts\pip.exe uninstall torch -y
echo      venv\Scripts\pip.exe install torch --index-url https://download.pytorch.org/whl/cu121
echo      Then run python find_cuda_dlls.py to locate and copy DLLs
echo.
echo   C) Download individual DLLs from NVIDIA redistributables
echo.

REM Step 3: Check if DLLs exist
echo [3/3] Checking for DLLs in cuda_dlls folder...
set DLL_COUNT=0
if exist "cuda_dlls\cublas64_12.dll" set /a DLL_COUNT+=1
if exist "cuda_dlls\cublasLt64_12.dll" set /a DLL_COUNT+=1
if exist "cuda_dlls\cudart64_12.dll" set /a DLL_COUNT+=1

echo.
if %DLL_COUNT% GEQ 3 (
    echo [SUCCESS] Found %DLL_COUNT%/3 required DLLs!
    echo.
    echo Next Step: Run build.bat to rebuild with CUDA DLLs bundled
) else (
    echo [INCOMPLETE] Found %DLL_COUNT%/3 required DLLs
    echo.
    echo Please follow one of the options above to get the DLLs
    echo Place them in: %CD%\cuda_dlls\
)

echo.
pause
