@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================================
echo    Whisper Utility - Docker Launcher
echo ========================================================
echo.

:: Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker daemon is not running!
    echo.
    echo Please start Docker Desktop and run this script again.
    echo.
    pause
    exit /b 1
)

:: Check for NVIDIA GPU hardware and Docker GPU runtime support
set USE_GPU=0
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    :: Test if Docker daemon actually supports GPU (--gpus all)
    docker run --rm --gpus all hello-world >nul 2>&1
    if !errorlevel! equ 0 (
        set USE_GPU=1
    ) else (
        echo [WARNING] NVIDIA GPU detected, but Docker GPU runtime is not enabled in your container engine.
        echo [TIP] To use GPU acceleration, enable NVIDIA GPU support in Docker Desktop / Rancher Desktop.
    )
)

if !USE_GPU! equ 1 (
    echo [INFO] NVIDIA GPU ^& Docker GPU runtime verified! Starting GPU container...
    echo.
    docker compose --profile gpu up --build -d
    set PROFILE=gpu
) else (
    echo [INFO] Starting lightweight CPU container...
    echo.
    docker compose --profile cpu up --build -d
    set PROFILE=cpu
)

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start the container. See output above for details.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Container started!
echo [INFO] Opening http://localhost:7860 in your browser...
echo.
timeout /t 3 >nul
start http://localhost:7860

echo --------------------------------------------------------
echo  The app is running at: http://localhost:7860
echo  Press any key to STOP the container and exit.
echo --------------------------------------------------------
pause >nul

echo.
echo [INFO] Stopping container...
docker compose --profile %PROFILE% down
echo [INFO] Container stopped. Goodbye!
