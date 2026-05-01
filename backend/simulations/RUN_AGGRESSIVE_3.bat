@echo off
echo ============================================================
echo AGGRESSIVE MALWARE 3 - File drops + cmd spawns
echo ============================================================
echo.
echo This will:
echo   - Drop 5 .exe files in temp
echo   - Spawn 7 cmd.exe processes
echo Expected: CRITICAL detection
echo.
pause
echo.
echo Running malware...
echo.

python "%~dp0AGGRESSIVE_MALWARE_3.py"

echo.
echo ============================================================
echo Done! Check backend console for detection
echo ============================================================
pause
