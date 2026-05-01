@echo off
setlocal

set "BASE_URL=http://127.0.0.1:8080"

set "PS64=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS64=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS64%" (
	echo ERROR: PowerShell not found.
	pause
	exit /b 1
)

"%PS64%" -NoProfile -ExecutionPolicy Bypass -Command "$sid='sim-session-'+[guid]::NewGuid().ToString('N').Substring(0,8); $headers=@{'Content-Type'='application/json'}; $url=$env:BASE_URL+'/api/layer2/ingest'; function Send($body){Invoke-RestMethod -Method Post -Uri $url -Headers $headers -Body ($body|ConvertTo-Json -Compress) -ErrorAction Stop | Out-Null}; for($i=0;$i -lt 8;$i++){ $body=@{kind='PROCESS_CREATE'; source='simulator'; session_id=$sid; parent_process='C:\\Windows\\System32\\notepad.exe'; child_process='C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe'; child_cmd='powershell.exe -NoProfile -EncodedCommand SQBFAFgA'; file_entropy=7.9}; Send $body; Start-Sleep -Milliseconds 50 }; $body2=@{kind='FILE_CREATE'; source='simulator'; session_id=$sid; parent_process='C:\\Windows\\System32\\notepad.exe'; child_process='C:\\Windows\\System32\\cmd.exe'; target_path='C:\\Users\\Public\\safe_simulated_payload.bin'; file_entropy=7.95}; Send $body2; $body3=@{kind='REG_SET'; source='simulator'; session_id=$sid; parent_process='C:\\Windows\\System32\\notepad.exe'; child_process='C:\\Windows\\System32\\cmd.exe'; reg_target='HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\SafeSim'}; Send $body3; Write-Host ('SAFE detection simulation sent. Session: '+$sid)"

pause
endlocal
