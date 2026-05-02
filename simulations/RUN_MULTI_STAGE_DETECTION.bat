@echo off
REM Run multiple malware samples to generate detection signals
REM This should trigger multiple incident types in Argus

echo [*] Starting multi-stage malware simulation suite...
echo.

cd /d "%~dp0"

REM Seed the run with file and registry activity so the batch itself is not treated as benign
if not exist C:\fyp_test mkdir C:\fyp_test
for /l %%i in (1,1,20) do (
	> C:\fyp_test\multi_%%i.bin echo Argus multi-stage %%i %%random%% %%time%%
)
reg add HKCU\Software\ArgusFYP\MultiStage /v Enabled /t REG_SZ /d 1 /f >nul 2>&1

REM Launch a simple CMD marker before the sample set starts
cmd.exe /c echo Argus multi-stage detection test > C:\fyp_test\multi_stage_marker.txt

REM Stage 1: High-signal ransomware sample
echo [+] Stage 1: Running ransom_sim.exe...
start /wait ransom_sim.exe
timeout /t 1 /nobreak

REM Stage 2: High-entropy stressor
echo [+] Stage 2: Running entropy_stressor.exe...
start /min entropy_stressor.exe
timeout /t 2 /nobreak

REM Stage 3: Process trigger chain
echo [+] Stage 3: Running process_trigger.exe...
start /min process_trigger.exe
timeout /t 2 /nobreak

REM Stage 4: Fileless ransomware
echo [+] Stage 4: Running fileless_ransomware.exe...
start /min fileless_ransomware.exe
timeout /t 2 /nobreak

echo.
echo [+] All simulations started. Argus is processing events...
echo [*] Check the dashboard for MALWARE, SUSPICIOUS, or CRITICAL incidents.
timeout /t 5 /nobreak

pause
