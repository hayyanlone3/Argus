@echo off
echo ============================================================
echo AGGRESSIVE MALWARE 4 - LOLBin abuse
echo ============================================================
echo.
echo This will execute:
echo   - wscript.exe
echo   - cscript.exe
echo   - rundll32.exe
echo Expected: CRITICAL detection
echo.
pause
echo.
echo Running malware...
echo.

python "%~dp0AGGRESSIVE_MALWARE_4.py"

echo.
echo ============================================================
echo Done! Check backend console for detection
echo ============================================================
pause
