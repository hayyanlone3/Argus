"""
Start the Argus FastAPI backend.

Use this instead of `uvicorn ...` when port 8000 is often already taken: we verify
the port is free *before* starting uvicorn, so background workers are not started and
then torn down on Windows Errno 10048.

From repository root:

  python run_argus.py

Or with a free port:

  set ARGUS_PORT=8001
  python run_argus.py
"""
from __future__ import annotations

import os
import socket
import sys


def _repo_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _port_is_free(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def main() -> None:
    root = _repo_root()
    if root not in sys.path:
        sys.path.insert(0, root)

    host = os.environ.get("ARGUS_HOST", "127.0.0.1")
    port = int(os.environ.get("ARGUS_PORT", os.environ.get("PORT", "8000")))

    if not _port_is_free(host, port):
        sys.stderr.write(
            f"\n[Argus] Port {port} on {host} is already in use (another Argus or app is listening).\n"
            f"  Free it (Windows):  netstat -ano | findstr :{port}\n"
            f"  Then:               taskkill /PID <pid> /F\n"
            f"  Or use another port: set ARGUS_PORT=8001\n"
            f"                        python run_argus.py\n\n"
        )
        sys.exit(1)

    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=os.environ.get("ARGUS_RELOAD", "").lower() in ("1", "true", "yes"),
        log_level=os.environ.get("ARGUS_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
