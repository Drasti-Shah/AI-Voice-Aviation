@echo off
REM Start the Next.js frontend dev server at http://localhost:3000.
REM Leave this window open while using the dashboard. Press Ctrl+C to stop.

cd /d "%~dp0web"

where node >nul 2>&1
if errorlevel 1 goto no_node

if not exist "node_modules" goto install_deps
goto run

:install_deps
echo [web] node_modules missing - running npm install, first run only...
call npm install
if errorlevel 1 goto install_failed
goto run

:run
echo [web] Starting Next.js on http://localhost:3000
echo [web] Press Ctrl+C to stop.
call npm run dev
goto :eof

:no_node
echo [web] Node.js not found on PATH.
echo [web] Install from https://nodejs.org and reopen the terminal.
pause
exit /b 1

:install_failed
echo [web] npm install failed.
pause
exit /b 1
