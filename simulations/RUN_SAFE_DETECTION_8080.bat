@echo off
setlocal

set "WORKDIR=%TEMP%\safe_detection_harness"

set "PS64=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS64=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS64%" (
	echo ERROR: PowerShell not found.
	pause
	exit /b 1
)

if not exist "%WORKDIR%" mkdir "%WORKDIR%" 2>nul

"%PS64%" -NoProfile -ExecutionPolicy Bypass -Command "$dir = $env:WORKDIR; New-Item -ItemType Directory -Force -Path $dir | Out-Null; $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); foreach ($name in @('safe_alpha.bin','safe_beta.dll','safe_gamma.scr')) { $path = Join-Path $dir $name; $bytes = [byte[]]::new(16384); $rng.GetBytes($bytes); [System.IO.File]::WriteAllBytes($path, $bytes) }; Start-Process -FilePath cmd.exe -ArgumentList '/c', ('whoami /all > \"' + (Join-Path $dir 'whoami.txt') + '\"') -WindowStyle Hidden; Start-Process -FilePath powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command',('Get-Process | Select-Object -First 10 | Out-File -FilePath \"' + (Join-Path $dir 'processes.txt') + '\" -Encoding utf8') -WindowStyle Hidden; Start-Process -FilePath cmd.exe -ArgumentList '/c', ('dir \"' + $dir + '\" /s > \"' + (Join-Path $dir 'directory.txt') + '\"') -WindowStyle Hidden; Write-Host ('SAFE local telemetry harness completed in ' + $dir)"

pause
endlocal
