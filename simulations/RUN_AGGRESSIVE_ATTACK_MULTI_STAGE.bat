@echo off
REM Multi-stage aggressive malware attack simulator
REM Generates sustained spawn rate anomalies and file operations for Layer 2 detection

setlocal enabledelayedexpansion

echo [*] Starting multi-stage malware attack sequence...
echo [*] Target: Trigger Layer 2 Channel A (spawn rate anomaly)

REM Stage 1: Multiple rapid cmd.exe spawns to establish baseline anomaly
echo.
echo [STAGE 1] Spawning cmd instances (15x)...
for /L %%i in (1,1,15) do (
    start /b cmd.exe /c "echo Spawn_%%i & timeout /t 1 /nobreak >nul" >nul 2>&1
)
timeout /t 2 /nobreak >nul

REM Stage 2: Run file_modifier malware
echo.
echo [STAGE 2] Executing file_modifier.exe payload...
start "file_modifier" "d:\FYP\Argus\simulations\file_modifier.exe"
timeout /t 5 /nobreak >nul

REM Stage 3: Additional cmd.exe spawns during file operations
echo.
echo [STAGE 3] Concurrent command spawns (20x)...
for /L %%i in (1,1,20) do (
    start /b cmd.exe /c "echo Concurrent_%%i" >nul 2>&1
    timeout /t 0 /nobreak >nul
)
timeout /t 3 /nobreak >nul

REM Stage 4: File system activity (simulated payload delivery)
echo.
echo [STAGE 4] Simulating file operations...
cd /d C:\fyp_test 2>nul
if exist "victim.txt" (
    for /L %%i in (1,1,10) do (
        copy victim.txt victim_backup_%%i.txt >nul 2>&1
    )
)

echo.
echo [COMPLETE] Multi-stage attack sequence finished
echo [*] Check Layer 3 dashboard for malware alerts
echo [*] Expected: file_modifier pattern should now exceed 0.70 threshold
pause
