@echo off
REM Path to the virtual environment
set VENV_DIR=%~dp0.venv

REM Path to the Python script
set PYTHON_SCRIPT=main.py

REM Activate the virtual environment
call "%VENV_DIR%\Scripts\activate"

REM Esegui PyInstaller con il file spec
"%VENV_DIR%\Scripts\python.exe" -m PyInstaller --noconfirm whisper.spec

REM Verifica se l'operazione di PyInstaller è andata a buon fine
if errorlevel 1 (
    echo Errore durante la creazione dell'eseguibile.
    pause
    exit /b 1
)

REM Copia delle cartelle nella destinazione
echo Copia delle cartelle...
xcopy /E /I /Y "settings" "dist\Whisper\settings"
if exist "secrets" xcopy /E /I /Y "secrets" "dist\Whisper\secrets"
xcopy /E /I /Y ".venv\Lib\site-packages\faster_whisper" "dist\Whisper\_internal\faster_whisper"
xcopy /E /I /Y ".venv\Lib\site-packages\safehttpx" "dist\Whisper\_internal\safehttpx"

echo Operazione completata.
pause