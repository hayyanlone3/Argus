@echo off
REM PowerShell File Creation Attack
set "PS_CMD=%windir%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_CMD%" set "PS_CMD=powershell.exe"

echo ============================================
echo PowerShell File Creation Attack
echo ============================================
echo.

echo [*] Stage 1: Creating malware executable in temp
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "New-Item -Path \"$env:TEMP\malware.exe\" -ItemType File -Value 'MALWARE_PAYLOAD' -Force"

echo [*] Stage 2: Creating DLL in ProgramData
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "New-Item -Path \"$env:ProgramData\backdoor.dll\" -ItemType File -Value 'BACKDOOR_PAYLOAD' -Force"

echo [*] Stage 3: Creating script in Public
echo MALICIOUS_SCRIPT > "%PUBLIC%\payload.ps1"
echo MALICIOUS_SCRIPT > "%PUBLIC%\loader.bat"

echo [*] Stage 4: PowerShell with malicious patterns
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "Write-Host '[SIM] DownloadString pattern'; Write-Host '[SIM] Invoke-WebRequest pattern'"

echo [*] Stage 5: Cleanup
del "%TEMP%\malware.exe"
del "%ProgramData%\backdoor.dll"

echo.
echo ============================================
echo SIMULATION COMPLETE
echo ============================================
