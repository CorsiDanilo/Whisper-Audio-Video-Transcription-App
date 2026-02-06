#!/bin/bash
# Windows Build Script (runs in Git Bash / WSL)

# Exit on error
set -e

echo "🪟 Setting up build environment for Windows..."

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "⚠️  Virtual environment '.venv' not found."
    echo "Please create it using: python -m venv .venv"
    echo "And install dependencies: pip install -r requirements_gpu.txt"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/Scripts/activate

# Run PyInstaller
echo "Running PyInstaller..."
pyinstaller --noconfirm whisper.spec

# Check build status
if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

# Create directories
echo "Creating output directories..."
mkdir -p dist/Whisper/config
mkdir -p dist/Whisper/default_values
mkdir -p dist/Whisper/settings
mkdir -p dist/Whisper/_internal/faster_whisper
mkdir -p dist/Whisper/_internal/safehttpx

# Copy configuration files
echo "Copying assets..."
cp -r config/* dist/Whisper/config/
cp -r default_values/* dist/Whisper/default_values/
cp -r settings/* dist/Whisper/settings/

# Copy internal packages (logic from installer.bat)
echo "Copying internal packages..."
if [ -d ".venv/Lib/site-packages/faster_whisper" ]; then
    cp -r .venv/Lib/site-packages/faster_whisper/* dist/Whisper/_internal/faster_whisper/
fi

if [ -d ".venv/Lib/site-packages/safehttpx" ]; then
    cp -r .venv/Lib/site-packages/safehttpx/* dist/Whisper/_internal/safehttpx/
fi

echo "🎉 Build complete! Executable located in dist/Whisper/Whisper.exe"
echo "Don't forget to run it from CMD or PowerShell if double-clicking doesn't work consistently!"
