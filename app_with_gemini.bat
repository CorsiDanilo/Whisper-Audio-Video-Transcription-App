@echo off

REM Path to the virtual environment
set VENV_DIR=.venv

REM Path to the Python script
set PYTHON_SCRIPT=app_with_gemini.py

REM Activate the virtual environment
call %VENV_DIR%\Scripts\activate

REM Run the Python script
python %PYTHON_SCRIPT%

REM Check the exit code
if %errorlevel% equ 0 (
    echo The Python script was successfully executed within the virtual environment.
) else (
    echo An error occurred while executing the Python script within the virtual environment.
)

pause