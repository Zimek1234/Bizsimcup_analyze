@echo off
setlocal
cd /d "%~dp0web"
call npm ci --no-audit --no-fund
if errorlevel 1 goto :failed
call npm run build
if errorlevel 1 goto :failed
echo Otevrete http://localhost:3000 na tomto notebooku.
call npm start
exit /b %errorlevel%
:failed
echo Web nebyl spusten. Overte Node.js 24 LTS a web\.env.local.
pause
exit /b 1
