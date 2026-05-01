#!/usr/bin/env python3
"""
Simple detection test - spawns suspicious processes that MUST be detected
"""

import subprocess
import time
import sys

print("="*60)
print("ARGUS DETECTION TEST")
print("="*60)
print()
print("This will spawn 5 cmd.exe processes with suspicious commands")
print("Expected: CRITICAL detection within 2 seconds")
print()
print("Starting in 2 seconds...")
time.sleep(2)

start_time = time.time()

# Spawn 5 cmd.exe processes rapidly
processes = []
for i in range(5):
    cmd = ["cmd.exe", "/c", f"echo Malicious command {i+1}"]
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    processes.append(p)
    print(f"  [{i+1}/5] Spawned cmd.exe (PID: {p.pid})")
    time.sleep(0.2)

# Wait for processes
for p in processes:
    try:
        p.wait(timeout=2)
    except:
        p.kill()

elapsed = time.time() - start_time

print()
print("="*60)
print(f"✓ Test complete in {elapsed:.2f}s")
print("="*60)
print()
print("Check backend logs for:")
print("  [SYSMON] ⚠️  SUSPICIOUS PROCESS: cmd.exe")
print("  [AUTO-SCORE] 🚨 CRITICAL")
print("  [CORRELATOR] 🚨 CRITICAL INCIDENT CREATED!")
print()
print("If you don't see these logs, the system is NOT working!")
print()
