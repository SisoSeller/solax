@echo off
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo Python non trovato.
  echo Installalo da https://www.python.org/downloads/
  echo Durante l'installazione spunta "Add python.exe to PATH".
  pause
  exit /b 1
)

python -c "import customtkinter" >nul 2>&1
if errorlevel 1 (
  echo Installo customtkinter...
  python -m pip install customtkinter
)

where pythonw >nul 2>&1
if %errorlevel%==0 (
  start "" pythonw "%~dp0app.py"
  exit /b 0
)

python "%~dp0app.py"
