@echo off
title Flip Finder Launcher
echo 🔄 Shutting down old Python processes...

:: Kill any running Python servers (both FastAPI and http.server)
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 >nul

echo ✅ Old servers stopped.

:: Start FastAPI backend
echo 🚀 Starting FastAPI server...
start "FastAPI" cmd /k "cd backend && uvicorn app:app --reload"

:: Start frontend static server
echo 🌐 Starting frontend at http://localhost:3000...
start "Frontend" cmd /k "cd frontend && python -m http.server 3000"

echo 🟢 Flip Finder is launching! Check your browser: http://localhost:3000
pause
