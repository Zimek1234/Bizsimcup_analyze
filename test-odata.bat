@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-sync\Scripts\python.exe" (
  echo Nejprve spustte install-sync.bat 3.13 nebo install-sync.bat 3.12.
  exit /b 1
)
.venv-sync\Scripts\python.exe scripts\worker_launcher.py probe %*
if errorlevel 1 goto :failed
pause
exit /b 0
:failed
echo Test pripojeni selhal. Detaily jsou uvedene vyse; heslo se nevypisuje.
pause
exit /b 1
