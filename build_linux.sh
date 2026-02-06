#!/bin/bash
# Linux Build Script for Whisper Utility

# Exit on error
set -e

echo "🐧 Setting up build environment for Linux..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv_linux" ]; then
    echo "Creating virtual environment .venv_linux..."
    python3 -m venv .venv_linux
fi

# Activate virtual environment
source .venv_linux/bin/activate

# Install dependencies
echo "Installing dependencies..."
# Filter out Windows-specific packages from requirements_cpu.txt
grep -vE "pywin32|pyreadline3|pypiwin32" requirements_cpu.txt > requirements_linux.txt
pip install -r requirements_linux.txt

# Run PyInstaller
echo "Running PyInstaller..."
pyinstaller --noconfirm whisper.spec

# Verify build
if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "Executable located in dist/Whisper/Whisper"
else
    echo "❌ Build failed!"
    exit 1
fi

# Copy configuration folder
echo "Copying configuration files..."
mkdir -p dist/Whisper/config
mkdir -p dist/Whisper/default_values
mkdir -p dist/Whisper/settings

cp -r config/* dist/Whisper/config/
cp -r default_values/* dist/Whisper/default_values/
cp -r settings/* dist/Whisper/settings/

# Copy faster-whisper internal files if needed (PyInstaller usually handles this via hooks, but good to be safe)
# Note: Linux paths in venv are different (.venv_linux/lib/python3.x/site-packages/...)
SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")

if [ -d "$SITE_PACKAGES/faster_whisper" ]; then
    mkdir -p dist/Whisper/_internal/faster_whisper
    cp -r "$SITE_PACKAGES/faster_whisper/"* dist/Whisper/_internal/faster_whisper/
fi

if [ -d "$SITE_PACKAGES/safehttpx" ]; then
    mkdir -p dist/Whisper/_internal/safehttpx
    cp -r "$SITE_PACKAGES/safehttpx/"* dist/Whisper/_internal/safehttpx/
fi

echo "🎉 Build process completed!"
