@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: Xeon - Scrcpy Controller
:: Build Script
:: ============================================================

set APP_NAME=ScrcpyController
set DIST_DIR=dist\%APP_NAME%
set SPEC_FILE=ScrcpyController.spec

echo.
echo ======================================================
echo  Building %APP_NAME%
echo ======================================================
echo.

:: -- Check Python ----------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not available. Please install Python 3.x.
    exit /b 1
)
echo [OK] Python found.

:: -- Check pip -------------------------------------------------------------
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not available.
    exit /b 1
)
echo [OK] pip found.

:: -- Check / install PyInstaller -------------------------------------------
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller not found. Installing...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        exit /b 1
    )
)
echo [OK] PyInstaller available.

:: -- Install runtime dependencies ------------------------------------------
echo [INFO] Installing requirements...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install requirements.
    exit /b 1
)
echo [OK] Requirements installed.

:: -- Clean previous build --------------------------------------------------
echo [INFO] Cleaning previous build...
if exist "build\%APP_NAME%" (
    rmdir /s /q "build\%APP_NAME%"
)
if exist "dist\%APP_NAME%" (
    rmdir /s /q "dist\%APP_NAME%"
)
echo [OK] Clean done.

:: -- Convert icon ----------------------------------------------------------
echo [INFO] Converting icon...
python -c "from PIL import Image; img=Image.open('LogoAplikasi/icon.png'); img.save('app/resources/icon.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]); print('[OK] Icon converted.')" 2>nul
if not exist "app\resources\icon.ico" (
    echo [WARN] Icon conversion failed. Build will continue without custom icon.
)

:: -- Run PyInstaller -------------------------------------------------------
echo [INFO] Running PyInstaller...
python -m PyInstaller %SPEC_FILE% --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)
echo [OK] PyInstaller done.

:: -- Copy runtime files & assets -------------------------------------------
echo [INFO] Copying runtime files...
if not exist "%DIST_DIR%\runtime" mkdir "%DIST_DIR%\runtime"
xcopy "runtime" "%DIST_DIR%\runtime\" /E /I /Y >nul

echo [INFO] Copying assets and resources...
if exist "LogoAplikasi" (
    if not exist "%DIST_DIR%\LogoAplikasi" mkdir "%DIST_DIR%\LogoAplikasi"
    xcopy "LogoAplikasi" "%DIST_DIR%\LogoAplikasi\" /E /I /Y >nul
)
if exist "app\resources" (
    if not exist "%DIST_DIR%\app\resources" mkdir "%DIST_DIR%\app\resources"
    xcopy "app\resources" "%DIST_DIR%\app\resources\" /E /I /Y >nul
)

:: Create empty config and logs dirs
if not exist "%DIST_DIR%\config" mkdir "%DIST_DIR%\config"
if not exist "%DIST_DIR%\logs" mkdir "%DIST_DIR%\logs"

echo [OK] Runtime files and assets copied.

:: -- Verify executable -----------------------------------------------------
echo [INFO] Verifying output...
if not exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo [ERROR] Executable not found at %DIST_DIR%\%APP_NAME%.exe
    exit /b 1
)
if not exist "%DIST_DIR%\_internal" (
    echo [ERROR] _internal folder not found in %DIST_DIR%
    exit /b 1
)
if not exist "%DIST_DIR%\runtime\adb\adb.exe" (
    echo [ERROR] adb.exe not found in dist runtime.
    exit /b 1
)
if not exist "%DIST_DIR%\runtime\scrcpy\scrcpy.exe" (
    echo [ERROR] scrcpy.exe not found in dist runtime.
    exit /b 1
)

echo.
echo ======================================================
echo  Build Successful!
echo  Output: %DIST_DIR%\
echo ======================================================
echo.

endlocal
