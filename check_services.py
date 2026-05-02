#!/usr/bin/env python3
"""Check Argus backend status"""
import socket
import requests

ports_to_check = {
    8000: "Layer 2 Scoring API",
    5000: "Flask Backend (fallback)",
    5174: "Frontend (Vite)",
    3000: "Node development server"
}

print("[*] Checking Argus Service Availability")
print()

for port, service in ports_to_check.items():
    try:
        response = requests.get(f"http://localhost:{port}", timeout=2)
        print(f"[+] Port {port} ({service}): ACCESSIBLE (status {response.status_code})")
    except requests.exceptions.ConnectionError:
        print(f"[-] Port {port} ({service}): NOT RUNNING")
    except Exception as e:
        print(f"[?] Port {port} ({service}): ERROR - {type(e).__name__}")

print()
print("[!] To start the backend, run:")
print("    cd d:\\FYP\\Argus")
print("    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload")
print()
print("[!] To start the frontend, run in a new terminal:")
print("    cd d:\\FYP\\Argus\\frontend")
print("    npm run dev")
