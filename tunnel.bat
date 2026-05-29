@echo off
REM Start the ngrok tunnel for the aviation voice demo.
REM Forwards https://purveyor-launder-craving.ngrok-free.dev -> localhost:8080
REM Leave this window open while testing calls. Press Ctrl+C to stop.

cd /d "%~dp0"

where ngrok >nul 2>&1
if errorlevel 1 (
    echo [tunnel] ngrok not found on PATH. Install from https://ngrok.com/download
    pause
    exit /b 1
)

echo [tunnel] Forwarding saloon-untried-maturely.ngrok-free.dev -> localhost:8080
echo [tunnel] Press Ctrl+C to stop.
ngrok http 8080 --url=https://saloon-untried-maturely.ngrok-free.dev
