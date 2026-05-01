@echo off
echo ============================================================
echo TEST DETECTION - 5 cmd.exe spawns
echo ============================================================
echo.
echo This will spawn 5 cmd.exe processes rapidly
echo Expected: CRITICAL detection within 2 seconds
echo.
pause
echo.
echo Running malware...
echo.

python "%~dp0TEST_DETECTION.py"

echo.
echo ============================================================
echo Done! Check backend console for detection
echo ============================================================
pause
