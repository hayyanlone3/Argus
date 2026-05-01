@echo off
echo ============================================================
echo MALWARE: Credential Stealer Simulation
echo ============================================================
echo.
echo This simulates credential harvesting:
echo   - PowerShell reconnaissance
echo   - Browser profile access
echo   - Data exfiltration prep (3 cmd.exe)
echo.
echo Expected Detection: CRITICAL (8+ alerts)
echo.
pause
echo.
python "%~dp0malware_credential_stealer.py"
echo.
echo ============================================================
echo Credential stealer simulation complete!
echo Check dashboard: http://localhost:3000
echo ============================================================
pause
