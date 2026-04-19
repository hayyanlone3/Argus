import logging
import os
import sys
import json
from datetime import datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logger(name: str) -> logging.Logger:
    """
    Project logger. Control level with ARGUS_LOG_LEVEL (INFO/WARNING/ERROR).
    """
    level_name = os.getenv("ARGUS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # Configure root once
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid adding duplicate handlers on reload
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')  # Fix Windows emoji crashes
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)

    # Make uvicorn obey the same level (silence INFO access logs)
    for uv_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(uv_name).setLevel(level)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger