@echo off
REM Run file_modifier.exe to generate detection signals
REM This simulates ransomware behavior and should trigger Layer 2 scoring

echo [*] Starting file_modifier.exe simulation...
echo [*] This will create file, registry, and process-chain activity
echo.

cd /d "%~dp0"

REM Create a visible artifact burst and suspicious registry activity
if not exist C:\fyp_test mkdir C:\fyp_test
for /l %%i in (1,1,10) do (
	> C:\fyp_test\runner_%%i.tmp echo Argus runner %%i %%random%%
)
reg add HKCU\Software\ArgusFYP\Runner /v FileModifier /t REG_SZ /d enabled /f >nul 2>&1

REM Add a CMD-only marker so the runner stays Windows-safe
cmd.exe /c echo Argus file_modifier runner > C:\fyp_test\file_modifier_runner.txt

REM Run the malware sample
file_modifier.exe

REM Wait a moment for Argus to process events
timeout /t 2 /nobreak

echo [+] Simulation complete. Check Argus dashboard for incidents.
pause
