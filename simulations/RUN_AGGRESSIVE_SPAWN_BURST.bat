@echo off
REM ============================================================================
REM AGGRESSIVE MALWARE SIMULATOR - Layer 2 Scoring Booster
REM ============================================================================
REM This batch script simulates aggressive malware behavior to trigger Layer 2
REM scoring thresholds by generating:
REM - Spawn rate anomalies (Channel A)
REM - File rename bursts (Channel A)
REM - Suspicious process chains
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo [ARGUS] ========== AGGRESSIVE MALWARE SIMULATOR ==========
echo [ARGUS] Generating Layer 2 Channel A anomalies...
echo.

REM Create test directory
if not exist "C:\fyp_test" mkdir C:\fyp_test
if not exist "C:\fyp_test\payload" mkdir C:\fyp_test\payload

REM ============================================================================
REM PHASE 1: High-Entropy Burst (File Creation Wave)
REM ============================================================================
echo [PHASE 1] Generating high-entropy file burst (40 files @ 2KB each)...
setlocal enabledelayedexpansion
for /L %%i in (1,1,40) do (
    REM Create file with random-like content
    (
        for /L %%%%j in (1,1,64) do (
            echo !RANDOM!!RANDOM!!RANDOM!!RANDOM!!RANDOM!!RANDOM!!RANDOM!!RANDOM!
        )
    ) > "C:\fyp_test\payload\stage_%%i.bin"
    if %%i equ 40 echo    [OK] 40 entropy files created
)
timeout /t 1 /nobreak >nul

REM ============================================================================
REM PHASE 2: Rapid Process Spawn Anomaly (15x cmd.exe in quick succession)
REM ============================================================================
echo [PHASE 2] Spawning cmd.exe rapidly (15 instances, ~50ms apart)...
for /L %%i in (1,1,15) do (
    start /b cmd.exe /c "title Spawn_%%i & timeout /t 0" >nul 2>&1
    timeout /t 0 /nobreak >nul
)
echo    [OK] 15 rapid cmd.exe spawns completed
timeout /t 2 /nobreak >nul

REM ============================================================================
REM PHASE 3: File Rename Burst (20 renames, ~30ms apart)
REM ============================================================================
echo [PHASE 3] Executing file rename burst (20 renames)...
for /L %%i in (1,1,20) do (
    if exist "C:\fyp_test\payload\stage_%%i.bin" (
        ren "C:\fyp_test\payload\stage_%%i.bin" "stage_%%i_ENCRYPTED.bin" >nul 2>&1
    )
    timeout /t 0 /nobreak >nul
)
echo    [OK] File rename burst completed
timeout /t 1 /nobreak >nul

REM ============================================================================
REM PHASE 4: Execute file_modifier malware (creates parent->child relationship)
REM ============================================================================
echo [PHASE 4] Launching file_modifier.exe (unknown parent -> child chain)...
if exist "file_modifier.exe" (
    start /b "file_modifier_payload" file_modifier.exe
    timeout /t 3 /nobreak >nul
) else (
    echo    [WARN] file_modifier.exe not found, skipping
)

REM ============================================================================
REM PHASE 5: Secondary Spawn Burst (concurrent with file operations)
REM ============================================================================
echo [PHASE 5] Secondary cmd.exe spawn burst (20 instances)...
for /L %%i in (1,1,20) do (
    start /b cmd.exe /c "echo Concurrent_%%i" >nul 2>&1
    timeout /t 0 /nobreak >nul
)
echo    [OK] Secondary spawn burst completed
timeout /t 2 /nobreak >nul

REM ============================================================================
REM PHASE 6: File System Activity (continuous write/rename pattern)
REM ============================================================================
echo [PHASE 6] File system activity burst (rename remaining files)...
for /L %%i in (21,1,40) do (
    if exist "C:\fyp_test\payload\stage_%%i.bin" (
        ren "C:\fyp_test\payload\stage_%%i.bin" "stage_%%i_LOCKED.bin" >nul 2>&1
    )
    timeout /t 0 /nobreak >nul
)
echo    [OK] File system activity completed
timeout /t 1 /nobreak >nul

REM ============================================================================
REM PHASE 7: Cleanup (optional, remove for forensic analysis)
REM ============================================================================
echo.
echo [PHASE 7] Cleanup...
REM Uncomment to auto-cleanup:
REM rmdir /s /q "C:\fyp_test" 2>nul

echo.
echo [ARGUS] ========== ATTACK COMPLETE ==========
echo [ARGUS] Expected Layer 2 Score: >0.70 (MALWARE ALERT threshold)
echo [ARGUS] 
echo [ARGUS] Sysmon Events Generated:
echo [ARGUS]   - 40 file creations (entropy_A channel)
echo [ARGUS]   - 35 file renames (burst_A channel)
echo [ARGUS]   - 35 rapid cmd.exe spawns (spawn_rate_A channel)
echo [ARGUS]   - file_modifier.exe -> cmd.exe parent-child chain (heuristic_B)
echo [ARGUS]
echo [ARGUS] Check http://localhost:5174/layer3 for malware incidents
echo.
pause
