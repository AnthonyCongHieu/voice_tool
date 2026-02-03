@echo off
REM ========================================
REM Package Project for Sharing
REM ========================================

echo.
echo ============================================
echo   DONG GOI DU AN - VOICE AI EDITOR PRO
echo ============================================
echo.

REM Get current directory name
for %%I in (.) do set "PROJECT_NAME=%%~nxI"

REM Output ZIP name
set "ZIP_NAME=%PROJECT_NAME%_share.zip"

echo [1/3] Checking required files...
echo.

REM Check critical files exist
set "MISSING=0"

if not exist "voice_app.py" (
    echo   X voice_app.py NOT FOUND!
    set "MISSING=1"
)

if not exist "config.py" (
    echo   X config.py NOT FOUND!
    set "MISSING=1"
)

if not exist "requirements.txt" (
    echo   X requirements.txt NOT FOUND!
    set "MISSING=1"
)

if not exist "core\processor.py" (
    echo   X core\processor.py NOT FOUND!
    set "MISSING=1"
)

if not exist "README.md" (
    echo   ! WARNING: README.md not found
)

if "%MISSING%"=="1" (
    echo.
    echo ERROR: Missing critical files! Cannot package.
    pause
    exit /b 1
)

echo   ✓ All critical files found!
echo.

echo [2/3] Creating smart ZIP (excluding venv, cache, build)...
echo.
echo   Excluding:
echo     - venv/
echo     - __pycache__/
echo     - build/
echo     - dist/
echo     - models/ (will auto-download)
echo     - .git/ (if exists)
echo.

REM Create temporary folder list
set "TEMP_LIST=%TEMP%\voice_package_list.txt"
if exist "%TEMP_LIST%" del "%TEMP_LIST%"

REM List all items to include
for /D %%D in (*) do (
    if not "%%D"=="venv" (
        if not "%%D"=="build" (
            if not "%%D"=="dist" (
                if not "%%D"=="models" (
                    if not "%%D"==".git" (
                        if not "%%D"=="__pycache__" (
                            echo %%D>> "%TEMP_LIST%"
                        )
                    )
                )
            )
        )
    )
)

REM Add all root files (*.py, *.bat, *.txt, *.md)
for %%F in (*.py *.bat *.txt *.md *.json *.spec) do (
    if exist "%%F" echo %%F>> "%TEMP_LIST%"
)

REM Use PowerShell to create ZIP with exclusions
powershell -NoProfile -ExecutionPolicy Bypass -Command "$items = @(); Get-ChildItem -Path . -Directory | Where-Object { $_.Name -notin @('venv', 'build', 'dist', 'models', '__pycache__', '.git') } | ForEach-Object { $items += $_.FullName }; Get-ChildItem -Path . -File -Include *.py,*.bat,*.txt,*.md,*.json,*.spec,*.gitignore | ForEach-Object { $items += $_.FullName }; if ($items.Count -gt 0) { Compress-Archive -Path $items -DestinationPath '%ZIP_NAME%' -Force } else { Write-Host 'ERROR: No files to package!'; exit 1 }"


if errorlevel 1 (
    echo.
    echo ERROR: Failed to create ZIP!
    if exist "%TEMP_LIST%" del "%TEMP_LIST%"
    pause
    exit /b 1
)

REM Cleanup
if exist "%TEMP_LIST%" del "%TEMP_LIST%"

echo.
echo [3/3] Verifying ZIP...
echo.

if exist "%ZIP_NAME%" (
    for %%A in ("%ZIP_NAME%") do set "SIZE=%%~zA"
    echo   ✓ File: %ZIP_NAME%
    echo   ✓ Size: %SIZE% bytes
    echo.
    echo ============================================
    echo   SUCCESS!
    echo ============================================
    echo.
    echo   📦 Output: %ZIP_NAME%
    echo   📁 Location: %CD%
    echo.
    echo   ✓ Excluded: venv, build, dist, models, cache
    echo   ✓ Your working environment intact!
    echo   ✓ Ready to share!
    echo.
) else (
    echo   ERROR: ZIP file not created!
    pause
    exit /b 1
)

echo Press any key to exit...
pause >nul

