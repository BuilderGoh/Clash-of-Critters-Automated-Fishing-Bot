@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run setup.bat first.
 pause
 exit /b 1
)
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $p=Join-Path (Get-Location) 'scrcpy-server-v3.3.4'; $h='8588238c9a5a00aa542906b6ec7e6d5541d9ffb9b5d0f6e1bc0e365e2303079e'; if (!(Test-Path $p) -or (Get-FileHash $p -Algorithm SHA256).Hash.ToLower() -ne $h) { Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/Genymobile/scrcpy/releases/download/v3.3.4/scrcpy-server-v3.3.4' -OutFile $p }; if ((Get-FileHash $p -Algorithm SHA256).Hash.ToLower() -ne $h) { Remove-Item $p; throw 'scrcpy server checksum mismatch' }; Write-Host 'scrcpy server verified.'"
if errorlevel 1 goto error
where ffmpeg.exe >nul 2>nul
if errorlevel 1 if not exist "ffmpeg.exe" (
 echo FFmpeg is required. Run the following command in CMD:
 echo winget install --id Gyan.FFmpeg -e
 echo Then reopen CMD and run setup-stream.bat again.
 pause
 exit /b 1
)
echo Streaming dependencies ready.
pause
exit /b 0
:error
echo Server setup failed. Download the pinned server manually from the official release; see STREAM-README.txt.
pause
exit /b 1
