@echo off
setlocal enabledelayedexpansion

REM Argus Malware Simulation Suite - Run Detection Test
REM Select which malware samples to execute

echo.
echo ========================================
echo    ARGUS MALWARE DETECTION TEST SUITE
echo ========================================
echo.
echo Available malware samples:
echo 1. file_modifier.exe        - Ransomware behavior (note.txt manipulation)
echo 2. entropy_stressor.exe     - High entropy file operations
echo 3. fileless_ransomware.exe  - Fileless ransomware simulation
echo 4. process_trigger.exe      - Process chain spawning
echo 5. lotl_dropper.exe         - Living-off-the-land dropper
echo 6. process_hollowing.exe    - Process hollowing technique
echo 7. notepad_cmd_fileless.exe - Fileless cmd spawn
echo 8. malware_sim.exe          - Multi-stage malware (3.2 MB)
echo 9. ransom_sim.exe           - Ransomware simulation (3.2 MB)
echo 10. argus_stress_test_v2.exe - Stress test (high volume)
echo.
echo 0. Exit
echo.

REM Prime detection so the launcher itself contributes suspicious telemetry
if not exist C:\fyp_test mkdir C:\fyp_test
for /l %%i in (1,1,8) do (
	> C:\fyp_test\menu_%%i.tmp echo Argus menu %%i %%random%%
)
reg add HKCU\Software\ArgusFYP\MenuRunner /v Active /t REG_SZ /d 1 /f >nul 2>&1

set /p choice="Select sample (1-10, 0 to exit): "

if "%choice%"=="0" goto :end
if "%choice%"=="1" goto :run_file_modifier
if "%choice%"=="2" goto :run_entropy
if "%choice%"=="3" goto :run_fileless
if "%choice%"=="4" goto :run_trigger
if "%choice%"=="5" goto :run_dropper
if "%choice%"=="6" goto :run_hollowing
if "%choice%"=="7" goto :run_notepad
if "%choice%"=="8" goto :run_malware_sim
if "%choice%"=="9" goto :run_ransom_sim
if "%choice%"=="10" goto :run_stress_test

echo Invalid choice. Exiting.
goto :end

:run_file_modifier
echo.
echo [*] Running file_modifier.exe...
file_modifier.exe
echo [+] Complete. Check Argus dashboard for incidents.
timeout /t 3 /nobreak
goto :end

:run_entropy
echo.
echo [*] Running entropy_stressor.exe...
start /wait entropy_stressor.exe
echo [+] Complete. High-entropy signals should appear in Layer 2.
timeout /t 3 /nobreak
goto :end

:run_fileless
echo.
echo [*] Running fileless_ransomware.exe...
start /wait fileless_ransomware.exe
echo [+] Complete. Check for fileless execution patterns.
timeout /t 3 /nobreak
goto :end

:run_trigger
echo.
echo [*] Running process_trigger.exe...
start /wait process_trigger.exe
echo [+] Complete. Process chain events should appear.
timeout /t 3 /nobreak
goto :end

:run_dropper
echo.
echo [*] Running lotl_dropper.exe...
start /wait lotl_dropper.exe
echo [+] Complete. LOLBin patterns should trigger.
timeout /t 3 /nobreak
goto :end

:run_hollowing
echo.
echo [*] Running process_hollowing.exe...
start /wait process_hollowing.exe
echo [+] Complete. Process hollowing events logged.
timeout /t 3 /nobreak
goto :end

:run_notepad
echo.
echo [*] Running notepad_cmd_fileless.exe...
start /wait notepad_cmd_fileless.exe
echo [+] Complete. Fileless cmd spawn detected.
timeout /t 3 /nobreak
goto :end

:run_malware_sim
echo.
echo [*] Running malware_sim.exe (3.2 MB - may take longer)...
start /wait malware_sim.exe
echo [+] Complete. Multi-stage events should appear.
timeout /t 3 /nobreak
goto :end

:run_ransom_sim
echo.
echo [*] Running ransom_sim.exe (3.2 MB - may take longer)...
start /wait ransom_sim.exe
echo [+] Complete. Ransomware behavior detected.
timeout /t 3 /nobreak
goto :end

:run_stress_test
echo.
echo [*] Running argus_stress_test_v2.exe (high volume test)...
start /wait argus_stress_test_v2.exe
echo [+] Complete. Check for volume-based detection thresholds.
timeout /t 3 /nobreak
goto :end

:end
echo.
echo [*] Exiting.
pause
