@echo off
REM PowerShell Registry Modification Attack - Persistence simulation
REM Triggers: registry modification, PowerShell execution, persistence patterns
REM Compatible with 64-bit Windows 10

REM Force 64-bit PowerShell even if running from 32-bit cmd
set "PS_CMD=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS_CMD=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_CMD%" (
	echo ERROR: PowerShell not found.
	pause
	exit /b 1
)


echo ============================================
echo PowerShell Registry Persistence Attack
echo ============================================
echo.

echo [*] Stage 1: Setting Run key persistence
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "New-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'TestMalware' -Value \"$env:PUBLIC\malware.exe\" -PropertyType String -Force 2>$null; Write-Host '[SIM] Run key set'"

echo [*] Stage 2: Setting RunOnce key
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "New-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce' -Name 'Stage2' -Value \"$env:TEMP\stage2.exe\" -PropertyType String -Force 2>$null; Write-Host '[SIM] RunOnce key set'"

echo [*] Stage 3: Dropping payload files
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); foreach ($f in @(\"$env:PUBLIC\malware.exe\", \"$env:TEMP\stage2.exe\")) { $bytes = [byte[]]::new(16384); $rng.GetBytes($bytes); [System.IO.File]::WriteAllBytes($f, $bytes); Write-Host '[SIM] Dropped:' $f }"

echo [*] Stage 4: Cleanup
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'TestMalware' -Force 2>$null; Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce' -Name 'Stage2' -Force 2>$null; Write-Host '[SIM] Cleanup done'"

echo.
echo ============================================
echo SIMULATION COMPLETE
echo ============================================
