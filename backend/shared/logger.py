# backend/shared/logger.py
"""Structured logging configuration for ARGUS."""

import logging
import json
import os
import sys
from datetime import datetime
from config import settings


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Format logs with colors for console output."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        log_msg = f"{color}[{timestamp}] {record.levelname:8} {record.name}: {record.getMessage()}{self.RESET}"
        
        if record.exc_info:
            log_msg += f"\n{self.formatException(record.exc_info)}"
        
        return log_msg


def setup_logger(name):
    """
    Setup and return a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(settings.log_level)
    
    # ═══════════════════════════════════════════════════════════════
    # CONSOLE HANDLER (stdout)
    # ═══════════════════════════════════════════════════════════════
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.log_level)
    
    if settings.log_format == 'json':
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ColoredFormatter())
    
    logger.addHandler(console_handler)
    
    # ═══════════════════════════════════════════════════════════════
    # FILE HANDLER (JSON format)
    # ═══════════════════════════════════════════════════════════════
    try:
        os.makedirs(settings.log_dir, exist_ok=True)
        log_file_path = os.path.join(settings.log_dir, settings.log_file)
        
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        
        logger.addHandler(file_handler)
    
    except Exception as e:
        logger.warning(f"⚠️  Could not setup file handler: {e}")
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger