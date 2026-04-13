@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM ARGUS v2.2 — Windows Dependency Installation (Global, No venv)
REM ═══════════════════════════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║  ARGUS v2.2 — Windows Dependency Installation                             ║
echo ║  (Installing to global Python, no virtual environment)                     ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM Check Python installation
echo 🔍 Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ Python not found in PATH
    echo.
    echo Please install Python 3.11+ from: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation
    echo.
    echo After installation, restart this CMD window and run again.
    echo.
    pause
    exit /b 1
)

echo ✅ Python detected:
python --version
echo.

REM Upgrade pip
echo 📦 Upgrading pip to latest version...
python -m pip install --upgrade pip >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Failed to upgrade pip
    pause
    exit /b 1
)
echo ✅ pip upgraded
echo.

REM Install Python dependencies
echo 📥 Installing Python dependencies from requirements.txt...
echo    (This may take 5-10 minutes on first run)
echo.

pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ❌ Failed to install Python dependencies
    pause
    exit /b 1
)

echo.
echo ✅ All Python dependencies installed successfully
echo.

REM Check Node.js
echo 🔍 Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  Node.js not found in PATH
    echo.
    echo Download and install from: https://nodejs.org/
    echo IMPORTANT: Check "Add to PATH" during installation
    echo.
    echo After installation, run: npm install (in frontend/ directory)
    echo.
) else (
    echo ✅ Node.js detected:
    node --version
    echo.
    
    echo 📥 Installing React dependencies...
    cd frontend
    call npm install
    if %errorlevel% neq 0 (
        echo ❌ Failed to install React dependencies
        cd ..
        pause
        exit /b 1
    )
    echo ✅ React dependencies installed
    cd ..
)

echo.
echo ════════════════════════════════════════════════════════════════════════════
echo ✅ ALL DEPENDENCIES INSTALLED SUCCESSFULLY!
echo ════════════════════════════════════════════════════════════════════════════
echo.
echo Next steps:
echo.
echo 1. Setup PostgreSQL (if not already done):
echo    scripts\init_postgres.bat
echo.
echo 2. Initialize database:
echo    python scripts/init_db.py
echo.
echo 3. Start development servers:
echo    scripts\run_dev.bat
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo.
pause