import json
import time
import uuid
import urllib.request
import urllib.error
import argparse


def post_event(base_url: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{base_url}/api/layer2/ingest",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        resp.read()


def make_event(kind: str, **kwargs) -> dict:
    evt = {
        "event_id": f"sim-{uuid.uuid4().hex[:12]}",
        "ts": time.time(),
        "source": "simulator",
        "kind": kind,
        "session_id": kwargs.pop("session_id", f"sim-session-{uuid.uuid4().hex[:8]}"),
    }
    evt.update(kwargs)
    return evt


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe detection simulator for ARGUS Layer 2")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="Backend base URL")
    parser.add_argument("--count", type=int, default=8, help="Number of process events")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    session_id = f"sim-session-{uuid.uuid4().hex[:8]}"

    # 1) Suspicious PROCESS_CREATE events with encoded command (A/B/C should spike)
    for i in range(args.count):
        evt = make_event(
            "PROCESS_CREATE",
            session_id=session_id,
            parent_process="C:\\Windows\\System32\\notepad.exe",
            child_process="C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            child_cmd="powershell.exe -NoProfile -EncodedCommand SQBFAFgA",
            file_entropy=7.9,
        )
        post_event(base_url, evt)
        time.sleep(0.05)

    # 2) High-entropy FILE_CREATE event to reinforce entropy scoring
    file_evt = make_event(
        "FILE_CREATE",
        session_id=session_id,
        parent_process="C:\\Windows\\System32\\notepad.exe",
        child_process="C:\\Windows\\System32\\cmd.exe",
        target_path="C:\\Users\\Public\\safe_simulated_payload.bin",
        file_entropy=7.95,
    )
    post_event(base_url, file_evt)

    # 3) Registry persistence-like event (adds additional signal)
    reg_evt = make_event(
        "REG_SET",
        session_id=session_id,
        parent_process="C:\\Windows\\System32\\notepad.exe",
        child_process="C:\\Windows\\System32\\cmd.exe",
        reg_target="HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\SafeSim",
    )
    post_event(base_url, reg_evt)

    print("SAFE detection simulation sent.")
    print(f"Session: {session_id}")


if __name__ == "__main__":
    main()
