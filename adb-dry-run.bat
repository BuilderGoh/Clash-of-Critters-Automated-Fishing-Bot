@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run setup.bat first.
 pause
 exit /b 1
)
.venv\Scripts\python.exe bot.py --backend adb --max-catches 3 --max-seconds 180 %*
pause
