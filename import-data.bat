@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-sync\Scripts\python.exe" (
  echo Nejprve spustte install-sync.bat 3.13 nebo install-sync.bat 3.12.
  exit /b 1
)
.venv-sync\Scripts\python.exe scripts\worker_launcher.py import %*
if errorlevel 1 goto :failed
exit /b 0
:failed
echo Import nebyl dokoncen. Overte argumenty, pripojeni a service\.env.
pause
exit /b 1
