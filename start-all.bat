@echo off
REM Jalankan Backend (FastAPI) dan Frontend (Next.js) sekaligus - 1 klik
setlocal

set ROOT=%~dp0

echo Menjalankan Backend...
start "Backend - FastAPI" cmd /k "cd /d "%ROOT%backend" && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Menjalankan Frontend...
start "Frontend - Next.js" cmd /k "cd /d "%ROOT%frontend" && npm run dev"

echo.
echo Backend  : http://localhost:8000
echo Frontend : http://localhost:3000
echo.
exit
