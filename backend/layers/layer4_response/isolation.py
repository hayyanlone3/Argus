# backend/layers/layer4_response/isolation.py
"""
Layer 4: Process Isolation Service
Kill malicious processes
"""

import subprocess
import os
from shared.logger import setup_logger
from shared.exceptions import ValidationError

logger = setup_logger(__name__)


class IsolationService:
    """Layer 4: Process Isolation Service"""
    
    @staticmethod
    def kill_process(process_id: int, force: bool = False) -> bool:
        """
        Terminate a process by PID.
        
        Args:
            process_id: Process ID (PID)
            force: Force kill (SIGKILL vs SIGTERM)
            
        Returns:
            True if successful
        """
        try:
            if not isinstance(process_id, int) or process_id <= 0:
                raise ValidationError("Invalid process ID")
            
            logger.warning(f"🛑 Killing process: PID {process_id}")
            
            if os.name == 'nt':  # Windows
                # taskkill /PID <pid> /F (force)
                cmd = ['taskkill', '/PID', str(process_id)]
                if force:
                    cmd.append('/F')
            else:  # Linux/Unix
                # kill -9 <pid> (force) or kill <pid>
                sig = '-9' if force else '-15'
                cmd = ['kill', sig, str(process_id)]
            
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            
            if result.returncode == 0:
                logger.info(f"✅ Process killed: PID {process_id}")
                return True
            else:
                logger.error(f"❌ Failed to kill process: {result.stderr.decode()}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Kill command timeout for PID {process_id}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to kill process: {e}")
            return False
    
    @staticmethod
    def kill_process_by_name(process_name: str, force: bool = False) -> bool:
        """
        Terminate process by name.
        
        Args:
            process_name: Process name (e.g., "malware.exe")
            force: Force kill
            
        Returns:
            True if successful
        """
        try:
            logger.warning(f"🛑 Killing process by name: {process_name}")
            
            if os.name == 'nt':  # Windows
                cmd = ['taskkill', '/IM', process_name]
                if force:
                    cmd.append('/F')
            else:  # Linux/Unix
                cmd = ['pkill', '-9' if force else '', process_name]
            
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            
            if result.returncode == 0:
                logger.info(f"✅ Process killed by name: {process_name}")
                return True
            else:
                logger.warning(f"⚠️  Process not found or kill failed: {process_name}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Failed to kill process: {e}")
            return False
    
    @staticmethod
    def get_process_info(process_id: int) -> dict:
        """
        Get process information (Windows).
        
        Args:
            process_id: Process ID
            
        Returns:
            {
                "pid": int,
                "name": str,
                "path": str,
                "memory_mb": float
            }
        """
        try:
            if os.name != 'nt':
                return {}
            
            import psutil
            process = psutil.Process(process_id)
            
            return {
                "pid": process.pid,
                "name": process.name(),
                "path": process.exe(),
                "memory_mb": process.memory_info().rss / 1024 / 1024
            }
        
        except Exception as e:
            logger.warning(f"⚠️  Could not get process info: {e}")
            return {}