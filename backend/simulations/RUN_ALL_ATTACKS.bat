@echo off
echo ============================================================
echo RUN ALL MALWARE ATTACKS
echo ============================================================
echo.
echo This will run ALL 6 malware simulations:
echo   1. Process Injection (5 cmd.exe)
echo   2. Registry Persistence ^& Encryption
echo   3. PowerShell ^& Lateral Movement
echo   4. Ransomware (10 files + 5 cmd.exe)
echo   5. Credential Stealer (PowerShell + 3 cmd.exe)
echo   6. Backdoor/RAT (7 cmd.exe + PowerShell)
echo.
echo Expected Detection: 40-50 CRITICAL alerts total
echo.
pause
echo.

echo [1/6] Process Injection...
python "%~dp0malware_sample_1.py"
timeout /t 2 /nobreak >nul

echo [2/6] Registry Persistence...
python "%~dp0malware_sample_2.py"
timeout /t 2 /nobreak >nul

echo [3/6] PowerShell Attack...
python "%~dp0malware_sample_3.py"
timeout /t 2 /nobreak >nul

echo [4/6] Ransomware...
python "%~dp0malware_ransomware.py"
timeout /t 2 /nobreak >nul

echo [5/6] Credential Stealer...
python "%~dp0malware_credential_stealer.py"
timeout /t 2 /nobreak >nul

echo [6/6] Backdoor/RAT...
python "%~dp0malware_backdoor.py"

echo.
echo ============================================================
echo ALL ATTACKS COMPLETE!
echo ============================================================
echo.
echo Wait 15 seconds for processing, then check:
echo   Dashboard: http://localhost:3000
echo.
pause
