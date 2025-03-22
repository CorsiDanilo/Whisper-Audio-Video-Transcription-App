@echo off
REM Path to the virtual environment
set VENV_DIR=.venv

REM Path to the Python script
set PYTHON_SCRIPT=main.py

REM Activate the virtual environment
call %VENV_DIR%\Scripts\activate

REM Esegui PyInstaller con il file spec
pyinstaller --noconfirm whisper.spec

REM Verifica se l'operazione di PyInstaller è andata a buon fine
if errorlevel 1 (
    echo Errore durante la creazione dell'eseguibile.
    pause
    exit /b 1
)

REM Copia delle cartelle nella destinazione
echo Copia delle cartelle...
xcopy /E /I /Y "config" "dist\Whisper\config"
xcopy /E /I /Y "default_values" "dist\Whisper\default_values"
xcopy /E /I /Y "settings" "dist\Whisper\settings"
xcopy /E /I /Y ".venv\Lib\site-packages\faster_whisper" "dist\Whisper\_internal\faster_whisper"
xcopy /E /I /Y ".venv\Lib\site-packages\safehttpx" "dist\Whisper\_internal\safehttpx"

echo Operazione completata.
pause