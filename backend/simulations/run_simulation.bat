@echo off
REM Aggressive Malware Simulation Launcher for Windows
REM Usage: Double-click this file or run from command prompt

echo.
echo ================================================================================
echo ARGUS MALWARE SIMULATION LAUNCHER
echo ================================================================================
echo.
echo This will simulate aggressive malware behavior.
echo Make sure the ARGUS backend is running on http://localhost:8000
echo.
echo Checking prerequisites...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if backend is running
echo Checking if backend is running...
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo WARNING: Backend does not appear to be running
    echo Please start the backend first:
    echo   cd backend
    echo   python main.py
    echo.
    pause
)

echo.
echo Starting malware simulation...
echo.

REM Run the simulation
python -m simulations.aggressive_malware

if errorlevel 1 (
    echo.
    echo ERROR: Simulation failed
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo SIMULATION COMPLETE
echo ================================================================================
echo.
echo Check the dashboard at http://localhost:3000 for detections
echo.
pause
