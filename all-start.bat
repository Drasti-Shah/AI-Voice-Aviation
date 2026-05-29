@echo off
REM Launch the entire stack in three separate windows:
REM   1. Backend  (FastAPI on :8080)
REM   2. Tunnel   (ngrok -> :8080, needed only for real phone calls)
REM   3. Frontend (Next.js on :3000)

cd /d "%~dp0"

echo Launching the full stack in three windows...

start "Aviation Backend"  cmd /k "%~dp0start.bat"
timeout /t 3 /nobreak >nul

start "Aviation Tunnel"   cmd /k "%~dp0tunnel.bat"
timeout /t 2 /nobreak >nul

start "Aviation Frontend" cmd /k "%~dp0web-start.bat"

echo.
echo Three windows opened:
echo   - Backend  : http://localhost:8080
echo   - Tunnel   : ngrok dashboard
echo   - Frontend : http://localhost:3000  (wait ~5s for it to compile)
echo.
echo Open http://localhost:3000 in your browser once the frontend is ready.
echo Close each window (or Ctrl+C) to stop that service.
