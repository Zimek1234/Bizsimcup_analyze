@echo off
setlocal
cd /d "%~dp0"
set "ERPSIM_SYNC_VERSION=%~1"
if not defined ERPSIM_SYNC_VERSION set "ERPSIM_SYNC_VERSION=3.13"
if "%ERPSIM_SYNC_VERSION%"=="3.13" goto :install
if "%ERPSIM_SYNC_VERSION%"=="3.12" goto :install
echo Pouziti: install-sync.bat 3.13 nebo install-sync.bat 3.12
exit /b 1
:install
if exist ".venv-sync\Scripts\python.exe" goto :check_version
py -%ERPSIM_SYNC_VERSION% -m venv .venv-sync
if errorlevel 1 goto :failed
:check_version
.venv-sync\Scripts\python.exe -c "import sys; sys.exit(0 if '.'.join(map(str, sys.version_info[:2])) == '%ERPSIM_SYNC_VERSION%' and sys.maxsize > 2**32 else 1)"
if errorlevel 1 (
  echo Prostredi .venv-sync musi pouzivat zvoleny 64bit Python %ERPSIM_SYNC_VERSION%.
  echo Pro jinou verzi prejmenujte pouze .venv-sync a spustte instalaci znovu.
  exit /b 1
)
.venv-sync\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-service.txt
if errorlevel 1 goto :failed
.venv-sync\Scripts\python.exe -m pip check
if errorlevel 1 goto :failed
.venv-sync\Scripts\python.exe scripts\check_sync_install.py
if errorlevel 1 goto :failed
echo Instalace synchronizatoru dokoncena. service\.env zustal beze zmeny.
exit /b 0
:failed
echo Instalace selhala. Overte chybu vyse a navod docs\windows-sync.md.
echo Nevypinejte Smart App Control. service\.env zustal beze zmeny.
exit /b 1
