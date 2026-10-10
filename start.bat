@echo off
setlocal
cd /d "%~dp0"
set "ERPSIM_PY=py -3.12"
py -3.12 --version >nul 2>&1
if not errorlevel 1 goto run
set "ERPSIM_PY=py -3.13"
py -3.13 --version >nul 2>&1
if not errorlevel 1 goto run
set "ERPSIM_PY=python"
python --version >nul 2>&1
if errorlevel 1 goto missing
:run
%ERPSIM_PY% bootstrap.py
set "ERPSIM_EXIT=%errorlevel%"
if not "%ERPSIM_EXIT%"=="0" pause
exit /b %ERPSIM_EXIT%
:missing
echo Nainstalujte 64bit Python 3.12 nebo 3.13 z python.org a spustte znovu.
pause
exit /b 1
