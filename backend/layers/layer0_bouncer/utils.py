"""
Layer 0 Utility Functions:
- Shannon entropy calculation
- Sample-based entropy (for large files)
- Digital signature verification
- Known packer detection
- Code section entropy extraction
"""

import numpy as np
from scipy.stats import entropy
from pathlib import Path
import hashlib
import subprocess
from shared.logger import setup_logger
from shared.constants import KNOWN_PACKERS

logger = setup_logger(__name__)


def calculate_shannon_entropy(file_path: str) -> float:
    """
    Calculate Shannon entropy of entire file.
    
    High entropy (>7.9) suggests encryption/compression/packing.
    
    Args:
        file_path: Path to file
        
    Returns:
        Shannon entropy value (0.0-8.0)
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        if not data:
            logger.warning(f"Empty file: {file_path}")
            return 0.0
        
        # Count byte frequencies
        byte_counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
        byte_probs = byte_counts / len(data)
        
        # Shannon entropy: -sum(p * log2(p))
        shannon = entropy(byte_probs, base=2)
        
        logger.debug(f"📊 Entropy of {Path(file_path).name}: {shannon:.2f}")
        return float(shannon)
    
    except FileNotFoundError:
        logger.error(f"❌ File not found: {file_path}")
        return 0.0
    except Exception as e:
        logger.error(f"❌ Failed to calculate entropy: {e}")
        return 0.0


def calculate_sample_entropy(file_path: str, sample_size_mb: int = 1) -> float:
    """
    Calculate entropy on random sample (for large files >10MB).
    Defeats file padding evasion.
    
    Args:
        file_path: Path to file
        sample_size_mb: Sample size in MB (default 1MB)
        
    Returns:
        Shannon entropy of sample
    """
    try:
        file_size = Path(file_path).stat().st_size
        sample_bytes = sample_size_mb * 1024 * 1024
        
        with open(file_path, 'rb') as f:
            # Seek to random position
            if file_size > sample_bytes:
                import random
                random_pos = random.randint(0, file_size - sample_bytes)
                f.seek(random_pos)
            
            sample_data = f.read(sample_bytes)
        
        if not sample_data:
            return 0.0
        
        byte_counts = np.bincount(np.frombuffer(sample_data, dtype=np.uint8), minlength=256)
        byte_probs = byte_counts / len(sample_data)
        shannon = entropy(byte_probs, base=2)
        
        logger.debug(f"📊 Sample entropy ({sample_size_mb}MB) of {Path(file_path).name}: {shannon:.2f}")
        return float(shannon)
    
    except Exception as e:
        logger.error(f"❌ Failed to calculate sample entropy: {e}")
        return 0.0


def check_digital_signature(file_path: str) -> bool:
    """
    Check if file is digitally signed by Microsoft.
    
    Uses Windows PowerShell to verify Authenticode signature.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if signed by Microsoft, False otherwise
    """
    try:
        # PowerShell command to verify signature
        ps_cmd = f"""
        $sig = Get-AuthenticodeSignature '{file_path}' -ErrorAction SilentlyContinue
        if ($sig.Status -eq 'Valid') {{
            if ($sig.SignerCertificate.Subject -like '*Microsoft*') {{
                Write-Host 'MICROSOFT_SIGNED'
            }} else {{
                Write-Host 'OTHER_SIGNED'
            }}
        }} else {{
            Write-Host 'UNSIGNED'
        }}
        """
        
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_cmd],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        is_microsoft = 'MICROSOFT_SIGNED' in result.stdout
        
        if is_microsoft:
            logger.debug(f"🔐 {Path(file_path).name}: Microsoft-signed ✅")
        else:
            logger.debug(f"🔐 {Path(file_path).name}: Not Microsoft-signed")
        
        return is_microsoft
    
    except subprocess.TimeoutExpired:
        logger.warning(f"⚠️  Signature check timeout: {file_path}")
        return False
    except Exception as e:
        logger.warning(f"⚠️  Could not verify signature: {e}")
        return False


def is_known_packer(file_path: str) -> bool:
    """
    Check if file appears to be packed with known packing tool.
    
    Searches first 512 bytes for packer signatures.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if known packer detected
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read(512)
        
        for packer in KNOWN_PACKERS:
            if packer.encode() in data:
                logger.debug(f"📦 Known packer detected: {packer}")
                return True
        
        return False
    
    except Exception as e:
        logger.warning(f"⚠️  Could not check packer: {e}")
        return False


def get_file_code_section_entropy(file_path: str) -> float:
    """
    Extract .text (code) section and calculate its entropy.
    Low entropy in code section = data, not packed code.
    
    Args:
        file_path: Path to PE file
        
    Returns:
        Code section entropy (0.0-8.0)
    """
    try:
        try:
            import pefile
        except ImportError:
            logger.debug("⚠️  pefile not installed, skipping code section analysis")
            return 0.0
        
        pe = pefile.PE(file_path)
        
        for section in pe.sections:
            section_name = section.Name.decode().rstrip('\x00')
            if section_name == '.text':
                section_data = pe.get_data(section.VirtualAddress, section.Misc_VirtualSize)
                
                if not section_data:
                    return 0.0
                
                byte_counts = np.bincount(np.frombuffer(section_data, dtype=np.uint8), minlength=256)
                byte_probs = byte_counts / len(section_data)
                code_entropy = entropy(byte_probs, base=2)
                
                logger.debug(f"📊 Code section entropy: {code_entropy:.2f}")
                return float(code_entropy)
        
        return 0.0
    
    except Exception as e:
        logger.debug(f"⚠️  Could not extract code section: {e}")
        return 0.0


def calculate_file_hash(file_path: str, algorithm: str = 'sha256') -> str:
    """
    Calculate file hash (MD5, SHA1, SHA256, etc.).
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (default SHA256)
        
    Returns:
        Hex digest of file hash
    """
    try:
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    except Exception as e:
        logger.error(f"❌ Failed to hash file: {e}")
        return ""