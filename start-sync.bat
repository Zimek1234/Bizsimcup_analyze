@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-sync\Scripts\python.exe" (
  echo Nejprve spustte install-sync.bat 3.13 nebo install-sync.bat 3.12.
  exit /b 1
)
.venv-sync\Scripts\python.exe scripts\worker_launcher.py sync %*
if errorlevel 1 goto :failed
exit /b 0
:failed
echo Synchronizator skoncil chybou. Overte chybu vyse a navod docs\windows-sync.md.
pause
exit /b 1
