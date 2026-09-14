@echo off
chcp 65001 >nul 2>&1
title Room Change Detector

echo ========================================
echo   Room Change Detector - Setup ^& Start
echo ========================================
echo.

:: Check for .env file
if not exist "%~dp0.env" (
    echo [WARNING] No .env file found.
    echo Please create a .env file in this directory and add your API key:
    echo GEMINI_API_KEY="your-key-here"
    echo.
    pause
    exit /b 1
)

:: Find Python
set PYTHON=
where python >nul 2>&1 && set PYTHON=python
if "%PYTHON%"=="" (where python3 >nul 2>&1 && set PYTHON=python3)
if "%PYTHON%"=="" (where py >nul 2>&1 && set PYTHON=py)

if "%PYTHON%"=="" (
    echo [ERROR] Python not found!
    echo Download and install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Found Python: %PYTHON%
%PYTHON% --version
echo.

:: Install dependencies
echo [1/2] Installing dependencies...
%PYTHON% -m pip install --quiet fastapi uvicorn pillow google-genai python-multipart python-dotenv
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.
echo.

:: Start server
echo [2/2] Starting server...
echo.
echo ========================================
echo   Server running at:
echo   http://localhost:8000
echo.
echo   Press Ctrl+C to stop.
echo ========================================
echo.

cd "%~dp0"
%PYTHON% -m uvicorn backend.app:app --host 127.0.0.1 --port 8000

pause
