@echo off
REM Stop the aviation voice demo server by killing whatever listens on port 8080.

set PORT=8080
set FOUND=0

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:"LISTENING" ^| findstr ":%PORT% "') do (
    echo [stop] Killing PID %%P on port %PORT%
    taskkill /F /PID %%P >nul 2>&1
    set FOUND=1
)

if "%FOUND%"=="0" (
    echo [stop] Nothing listening on port %PORT%.
) else (
    echo [stop] Server stopped.
)
