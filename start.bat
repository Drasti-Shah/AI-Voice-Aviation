@echo off
REM Start the aviation voice demo server.
REM Runs in this console window. Press Ctrl+C (or close the window) to stop.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [start] .venv not found. Creating it and installing dependencies...
    python -m venv .venv
    if errorlevel 1 (
        echo [start] Failed to create venv. Is Python installed and on PATH?
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [start] pip install failed.
        pause
        exit /b 1
    )
)

echo [start] Launching uvicorn on http://127.0.0.1:8080
echo [start] Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8080 --log-level info
