@echo off
REM Place an outbound test call via the aviation voice demo.
REM Usage:   call.bat                  (calls the default number)
REM         call.bat +919876543210    (overrides the default)
REM Requires start.bat to be running and ngrok to be tunneling port 8080.

cd /d "%~dp0"

set DEFAULT_NUMBER=+919724556935

if "%~1"=="" (
    set TARGET=%DEFAULT_NUMBER%
) else (
    set TARGET=%~1
)

if not exist ".venv\Scripts\python.exe" (
    echo [call] .venv not found. Run start.bat first to set it up.
    exit /b 1
)

echo [call] Target: %TARGET%
".venv\Scripts\python.exe" make_call.py %TARGET%
