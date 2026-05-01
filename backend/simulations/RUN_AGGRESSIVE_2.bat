@echo off
echo ============================================================
echo AGGRESSIVE MALWARE 2 - PowerShell attacks
echo ============================================================
echo.
echo This will execute 5 PowerShell commands with suspicious flags
echo Expected: CRITICAL detection
echo.
pause
echo.
echo Running malware...
echo.

python "%~dp0AGGRESSIVE_MALWARE_2.py"

echo.
echo ============================================================
echo Done! Check backend console for detection
echo ============================================================
pause
