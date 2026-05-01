@echo off
echo ============================================================
echo MALWARE: Backdoor/RAT Simulation
echo ============================================================
echo.
echo This simulates remote access trojan:
echo   - Persistence installation
echo   - C2 communication (7 cmd.exe beacons)
echo   - System enumeration (PowerShell)
echo   - Payload deployment
echo.
echo Expected Detection: CRITICAL (10+ alerts)
echo.
pause
echo.
python "%~dp0malware_backdoor.py"
echo.
echo ============================================================
echo Backdoor simulation complete!
echo Check dashboard: http://localhost:3000
echo ============================================================
pause
