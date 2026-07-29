#!/usr/bin/env bash
set -euo pipefail

echo ""
echo "========================================================"
echo "   Whisper Utility - Docker Launcher"
echo "========================================================"
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] Docker daemon is not running!"
    echo ""
    echo "Please start Docker and run this script again."
    exit 1
fi

# Detect NVIDIA GPU hardware and Docker GPU runtime support
PROFILE="cpu"
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    if docker run --rm --gpus all hello-world >/dev/null 2>&1; then
        echo "[INFO] NVIDIA GPU & Docker GPU runtime verified! Starting GPU container..."
        PROFILE="gpu"
    else
        echo "[WARNING] NVIDIA GPU detected, but Docker GPU runtime is not enabled in your container engine."
        echo "[TIP] To use GPU acceleration, enable NVIDIA GPU support in Docker Desktop / Rancher Desktop."
        echo "[INFO] Starting lightweight CPU container..."
    fi
else
    echo "[INFO] NVIDIA GPU not found. Starting lightweight CPU container..."
fi

echo ""
docker compose --profile "$PROFILE" up --build -d

echo ""
echo "[SUCCESS] Container started!"
echo "[INFO]    App available at: http://localhost:7860"
echo ""

# Open browser (Linux: xdg-open, macOS: open)
if command -v xdg-open >/dev/null 2>&1; then
    sleep 2 && xdg-open http://localhost:7860 &
elif command -v open >/dev/null 2>&1; then
    sleep 2 && open http://localhost:7860 &
fi

echo "--------------------------------------------------------"
echo "  Press ENTER to STOP the container and exit."
echo "--------------------------------------------------------"
read -r

echo ""
echo "[INFO] Stopping container..."
docker compose --profile "$PROFILE" down
echo "[INFO] Container stopped. Goodbye!"
