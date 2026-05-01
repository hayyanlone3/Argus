@echo off
echo ============================================================
echo MALWARE: Ransomware Simulation
echo ============================================================
echo.
echo This simulates ransomware behavior:
echo   - Rapid file encryption (10 files)
echo   - File system manipulation (5 cmd.exe)
echo   - PowerShell persistence
echo.
echo Expected Detection: CRITICAL (15+ alerts)
echo.
pause
echo.
python "%~dp0malware_ransomware.py"
echo.
echo ============================================================
echo Ransomware simulation complete!
echo Check dashboard: http://localhost:3000
echo ============================================================
pause
