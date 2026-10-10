@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :failed
)
.venv\Scripts\python.exe -m pip install -r requirements-service.txt
if errorlevel 1 goto :failed
.venv\Scripts\python.exe scripts\worker_launcher.py probe %*
if errorlevel 1 goto :failed
pause
exit /b 0
:failed
echo Test pripojeni selhal. Detaily jsou uvedene vyse; heslo se nevypisuje.
pause
exit /b 1
