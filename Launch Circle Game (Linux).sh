#!/bin/bash

# Circle Clicker Game Launch Script
# This script can be double-clicked to launch the game

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the game directory
cd "$SCRIPT_DIR"

echo "🎯 Circle Clicker Game Launcher"
echo "==============================="
echo "Starting game from: $SCRIPT_DIR"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Error: Python is not installed or not in PATH"
    echo "Please install Python 3.7+ to run this game"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# Try python3 first, then python
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "🐍 Using Python: $PYTHON_CMD"

# Check if pygame is installed
echo "🔍 Checking for pygame..."
if ! $PYTHON_CMD -c "import pygame" 2>/dev/null; then
    echo "❌ Error: pygame is not installed"
    echo ""
    echo "To install pygame, run:"
    echo "  pip install pygame"
    echo "  or"
    echo "  pip3 install pygame"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo "✅ pygame found"

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found in $SCRIPT_DIR"
    echo "Make sure this script is in the same directory as the game files"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo "✅ Game files found"
echo ""
echo "🚀 Launching Circle Clicker Game..."
echo "   (Close this terminal window to stop the game)"
echo ""

# Launch the game
$PYTHON_CMD main.py

# Check exit code
EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Game closed successfully"
else
    echo "❌ Game exited with error code: $EXIT_CODE"
    echo ""
    echo "If you're experiencing issues:"
    echo "1. Make sure Python 3.7+ is installed"
    echo "2. Make sure pygame is installed: pip install pygame"
    echo "3. Check that all game files are present"
    echo ""
    read -p "Press Enter to exit..."
fi
