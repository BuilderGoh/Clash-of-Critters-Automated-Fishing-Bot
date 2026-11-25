@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run setup.bat first.
 pause
 exit /b 1
)
.venv\Scripts\python.exe bot.py --backend adb --live --max-catches 2000 --max-seconds 86400 %*
pause
