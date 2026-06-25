@echo off
REM Path to the virtual environment
set VENV_DIR=%~dp0.venv

REM Path to the Python script
set PYTHON_SCRIPT=main.py

REM Activate the virtual environment
call "%VENV_DIR%\Scripts\activate"

REM Run PyInstaller with the spec file
"%VENV_DIR%\Scripts\python.exe" -m PyInstaller --noconfirm whisper.spec

REM Verify if PyInstaller completed successfully
if errorlevel 1 (
    echo [ERROR] Error occurred during executable creation.
    pause
    exit /b 1
)

REM Copy folders to target
echo Copying folders...
xcopy /E /I /Y "settings" "dist\Whisper\settings"
if exist "secrets" xcopy /E /I /Y "secrets" "dist\Whisper\secrets"
xcopy /E /I /Y ".venv\Lib\site-packages\faster_whisper" "dist\Whisper\_internal\faster_whisper"
xcopy /E /I /Y ".venv\Lib\site-packages\safehttpx" "dist\Whisper\_internal\safehttpx"

echo.
echo 🎉 Operation completed successfully!
echo The executable is located in: dist\Whisper\Whisper.exe
echo.
pause