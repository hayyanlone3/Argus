# backend/layers/layer4_response/isolation.py
import subprocess
import os
from backend.shared.logger import setup_logger
from backend.shared.exceptions import ValidationError

logger = setup_logger(__name__)


class IsolationService:
    @staticmethod
    def suspend_process(process_id: int) -> bool:
        """
        Suspend (pause) a process instead of killing it.
        This is safer as it can be resumed later if it's a false positive.
        """
        try:
            if not isinstance(process_id, int) or process_id <= 0:
                raise ValidationError("Invalid process ID")
            
            logger.warning(f"🛑 Attempting to SUSPEND process: PID {process_id}")
            
            try:
                import psutil
                process = psutil.Process(process_id)
                process.suspend()
                logger.info(f"✅ Process SUSPENDED: PID {process_id} ({process.name()})")
                return True
                
            except psutil.NoSuchProcess:
                logger.warning(f"⚠️  Process already terminated: PID {process_id}")
                return False
            except psutil.AccessDenied:
                logger.error(f"❌ Access denied when trying to suspend PID {process_id}. Run with admin privileges.")
                return False
            except Exception as ps_err:
                logger.error(f"❌ Failed to suspend PID {process_id}: {ps_err}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception while suspending process PID {process_id}: {e}")
            return False
    
    @staticmethod
    def resume_process(process_id: int) -> bool:
        """
        Resume a suspended process.
        """
        try:
            if not isinstance(process_id, int) or process_id <= 0:
                raise ValidationError("Invalid process ID")
            
            logger.info(f"▶️  Attempting to RESUME process: PID {process_id}")
            
            try:
                import psutil
                process = psutil.Process(process_id)
                process.resume()
                logger.info(f"✅ Process RESUMED: PID {process_id} ({process.name()})")
                return True
                
            except psutil.NoSuchProcess:
                logger.warning(f"⚠️  Process not found: PID {process_id}")
                return False
            except psutil.AccessDenied:
                logger.error(f"❌ Access denied when trying to resume PID {process_id}")
                return False
            except Exception as ps_err:
                logger.error(f"❌ Failed to resume PID {process_id}: {ps_err}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception while resuming process PID {process_id}: {e}")
            return False
    
    @staticmethod
    def kill_process(process_id: int, force: bool = False) -> bool:
        try:
            if not isinstance(process_id, int) or process_id <= 0:
                raise ValidationError("Invalid process ID")
            
            logger.warning(f"Attempting to kill process: PID {process_id}")
            try:
                import psutil
                process = psutil.Process(process_id)
                
                if force:
                    process.kill()  # SIGKILL equivalent
                else:
                    process.terminate()  # SIGTERM equivalent
                
                logger.info(f"Process killed via psutil: PID {process_id}")
                return True
                
            except psutil.NoSuchProcess:
                logger.warning(f" Process already terminated: PID {process_id}")
                return True
            except psutil.AccessDenied:
                logger.error(f"  Access denied when trying to kill PID {process_id}. Ensure Argus is running with administrative privileges.")
               
            except Exception as ps_err:
                logger.debug(f"psutil kill failed for PID {process_id}: {ps_err}. Falling back to system command.")

            if os.name == 'nt':
                cmd = ['taskkill', '/F', '/T', '/PID', str(process_id)]
            else:
                cmd = ['kill', '-9', str(process_id)]
            
            result = subprocess.run(cmd, capture_output=True, timeout=5, text=True)
            
            if result.returncode == 0:
                logger.info(f"Process killed via system command: PID {process_id}")
                return True
            elif result.returncode == 128:
              
                logger.warning(f" Process already terminated: PID {process_id}")
                return True
            else:
                stderr = result.stderr or ""
                logger.error(f"  System kill failed for PID {process_id}. Return code: {result.returncode}")
                if "Access is denied" in stderr:
                    logger.error(f"  REASON: Access Denied. Administrative privileges required.")
                elif stderr:
                    logger.error(f"  Stderr: {stderr.strip()}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error(f"  Kill command timeout for PID {process_id}")
            return False
        except Exception as e:
            logger.error(f"  Exception while killing process PID {process_id}: {e}")
            return False
    
    @staticmethod
    def kill_process_by_name(process_name: str, force: bool = False) -> bool:
        try:
            logger.warning(f"Killing process by name: {process_name}")
            
            if os.name == 'nt':  # Windows
                cmd = ['taskkill', '/IM', process_name]
                if force:
                    cmd.append('/F')
            else:  # Linux/Unix
                cmd = ['pkill', '-9' if force else '', process_name]
            
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            
            if result.returncode == 0:
                logger.info(f"Process killed by name: {process_name}")
                return True
            else:
                logger.warning(f"Process not found or kill failed: {process_name}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to kill process: {e}")
            return False
    
    @staticmethod
    def get_process_info(process_id: int) -> dict:
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
            logger.warning(f"Could not get process info: {e}")
            return {}