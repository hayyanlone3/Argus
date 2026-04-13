@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM ARGUS v2.2 — Windows Development Startup
REM ═══════════════════════════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║  ARGUS v2.2 — Development Startup (Windows)                               ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found in PATH
    pause
    exit /b 1
)

REM Check if database is initialized
if not exist "argus_project.db" (
    echo 🗄️  Initializing database (first run)...
    python scripts/init_db.py
    if %errorlevel% neq 0 (
        echo ❌ Database initialization failed
        pause
        exit /b 1
    )
    echo.
)

echo 🔌 Starting FastAPI backend server...
echo    Backend URL: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
start cmd /k "title ARGUS Backend & python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend to start
timeout /t 3 /nobreak

echo ⚛️  Starting React frontend server...
echo    Frontend URL: http://localhost:3000
echo.
cd frontend
start cmd /k "title ARGUS Frontend & npm start"
cd ..

echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║  ✅ SERVERS STARTING                                                        ║
echo ║                                                                            ║
echo ║  🔗 Backend:    http://localhost:8000                                     ║
echo ║  🔗 Frontend:   http://localhost:3000                                     ║
echo ║  📚 API Docs:   http://localhost:8000/docs                                ║
echo ║  📘 ReDoc:      http://localhost:8000/redoc                               ║
echo ║                                                                            ║
echo ║  Two new CMD windows have been opened:                                    ║
echo ║    - One for the backend server                                           ║
echo ║    - One for the React frontend                                           ║
echo ║                                                                            ║
echo ║  Frontend will open in your default browser automatically.                ║
echo ║  Close either CMD window to stop that server.                             ║
echo ║                                                                            ║
echo ║  To stop everything:                                                      ║
echo ║    1. Close the backend CMD window                                        ║
echo ║    2. Close the frontend CMD window                                       ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo This window will close in 10 seconds...
timeout /t 10