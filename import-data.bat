@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :failed
)
.venv\Scripts\python.exe -m pip install -r requirements-service.txt
if errorlevel 1 goto :failed
.venv\Scripts\python.exe scripts\worker_launcher.py import %*
if errorlevel 1 goto :failed
exit /b 0
:failed
echo Import nebyl dokoncen. Overte argumenty, pripojeni a service\.env.
pause
exit /b 1
