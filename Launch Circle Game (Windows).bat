@echo off
REM Circle Clicker Game Launch Script for Windows
REM This batch file can be double-clicked to launch the game

title Circle Clicker Game Launcher
color 0A

echo.
echo     🎯 Circle Clicker Game Launcher
echo     ===============================
echo     Starting game from: %~dp0
echo.

REM Change to the directory where this batch file is located
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.7+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo 🐍 Python found:
python --version

REM Check if pygame is installed
echo.
echo 🔍 Checking for pygame...
python -c "import pygame" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: pygame is not installed
    echo.
    echo To install pygame, open Command Prompt as Administrator and run:
    echo     pip install pygame
    echo.
    echo Or try:
    echo     python -m pip install pygame
    echo.
    pause
    exit /b 1
)

echo ✅ pygame found

REM Check if main.py exists
if not exist "main.py" (
    echo.
    echo ❌ Error: main.py not found in %~dp0
    echo Make sure this batch file is in the same directory as the game files
    echo.
    pause
    exit /b 1
)

echo ✅ Game files found
echo.
echo 🚀 Launching Circle Clicker Game...
echo    ^(Close this window to stop the game^)
echo.

REM Launch the game
python main.py

REM Check exit code
if %errorlevel% equ 0 (
    echo.
    echo ✅ Game closed successfully
) else (
    echo.
    echo ❌ Game exited with error code: %errorlevel%
    echo.
    echo If you're experiencing issues:
    echo 1. Make sure Python 3.7+ is installed from https://python.org
    echo 2. Make sure pygame is installed: pip install pygame
    echo 3. Check that all game files are present
    echo 4. Try running as Administrator
    echo.
    pause
)

REM Keep window open briefly to show success message
timeout /t 2 /nobreak >nul
