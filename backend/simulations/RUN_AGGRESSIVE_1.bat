@echo off
echo ============================================================
echo AGGRESSIVE MALWARE 1 - 10 cmd.exe spawns
echo ============================================================
echo.
echo This will spawn 10 cmd.exe processes in 2 seconds
echo Expected: CRITICAL detection
echo.
pause
echo.
echo Running malware...
echo.

python "%~dp0AGGRESSIVE_MALWARE_1.py"

echo.
echo ============================================================
echo Done! Check backend console for detection
echo ============================================================
pause
