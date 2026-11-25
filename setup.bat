@echo off
cd /d "%~dp0"
py -3 -m venv .venv || goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt || goto error
echo Setup complete.
pause
exit /b 0
:error
echo Setup failed. Install Python 3.11 or 3.12 for Windows and try again.
pause
exit /b 1
