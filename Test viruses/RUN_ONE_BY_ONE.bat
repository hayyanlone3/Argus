@echo off
:menu
cls
echo ============================================================
echo TEST VIRUS MENU - Run Individual Malware
echo ============================================================
echo.
echo Choose malware to run:
echo.
echo  1. malware.exe           - File creation + Registry + Process enum
echo  2. virus.exe             - Replication + Network enum
echo  3. spyware.exe           - Data collection simulation
echo  4. ransomware.exe        - File encryption simulation
echo  5. strong_ransomware.exe - Advanced ransomware (high entropy)
echo  6. stager1.exe           - Multi-stage payload
echo  7. stager2.exe           - Second stage
echo  8. stager3.exe           - Third stage
echo.
echo  0. Exit
echo.
echo ============================================================
set /p choice="Enter choice (0-8): "

if "%choice%"=="0" goto :end
if "%choice%"=="1" goto :mal1
if "%choice%"=="2" goto :mal2
if "%choice%"=="3" goto :mal3
if "%choice%"=="4" goto :mal4
if "%choice%"=="5" goto :mal5
if "%choice%"=="6" goto :mal6
if "%choice%"=="7" goto :mal7
if "%choice%"=="8" goto :mal8

echo Invalid choice!
timeout /t 2 >nul
goto :menu

:mal1
cls
echo Running malware.exe...
echo.
"exe files\malware.exe"
echo.
echo Check ARGUS for detection!
pause
goto :menu

:mal2
cls
echo Running virus.exe...
echo.
"exe files\virus.exe"
echo.
echo Check ARGUS for detection!
pause
goto :menu

:mal3
cls
echo Running spyware.exe...
echo.
"exe files\spyware.exe"
echo.
echo Check ARGUS for detection!
pause
goto :menu

:mal4
cls
echo Running ransomware.exe...
echo.
"exe files\ransomware.exe"
echo.
echo Check ARGUS for detection!
pause
goto :menu

:mal5
cls
echo Running strong_ransomware.exe...
echo.
"exe files\strong_ransomware.exe"
echo.
echo Check ARGUS for detection!
pause
goto :menu

:mal6
cls
echo Running stager1.exe...
echo.
"exe files\stager1.exe"
echo.
echo Check ARGUS for detection!
pause
goto :menu

:mal7
cls
echo Running stager2.exe...
echo.
"exe files\stager2.exe"
echo.
echo Check ARGUS for detection!
pause
goto :menu

:mal8
cls
echo Running stager3.exe...
echo.
"exe files\stager3.exe"
echo.
echo Check ARGUS for detection!
pause
goto :menu

:end
echo Exiting...
