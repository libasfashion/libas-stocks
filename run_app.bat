@echo off
REM Always start in the folder where this BAT is saved
cd /d "%~dp0"

REM Activate venv if present (supports .venv or venv)
IF EXIST .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
IF EXIST venv\Scripts\activate.bat  call venv\Scripts\activate.bat

REM Make output visible (use python, not pythonw)
set PYTHONUTF8=1
set FLASK_ENV=production
python app.py

REM Keep the window open so we can read any errors
pause
