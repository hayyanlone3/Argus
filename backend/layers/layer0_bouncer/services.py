import hashlib
import aiohttp
import time
from datetime import datetime, timedelta
from collections import deque
from sqlalchemy.orm import Session
from backend.database.models import VTCache
from backend.config import settings
from backend.shared.logger import setup_logger
from backend.shared.constants import (
    VT_POSITIVE_THRESHOLD,
    ENTROPY_THRESHOLD_HIGH,
    ENTROPY_THRESHOLD_MEDIUM,
)
from .utils import (
    calculate_shannon_entropy,
    calculate_sample_entropy,
    check_digital_signature,
    is_known_packer,
    get_file_code_section_entropy,
    calculate_file_hash,
)
import os

logger = setup_logger(__name__)

# VT Rate Limiter (free tier: 4 requests/minute)
class VTRateLimiter:
    def __init__(self):
        self.requests = deque()
        self.max_requests = int(os.getenv("VT_RATE_LIMIT_REQUESTS", "4"))
        self.window = int(os.getenv("VT_RATE_LIMIT_WINDOW", "60"))
    
    def can_request(self) -> bool:
        now = time.time()
        # Remove old requests outside the window
        while self.requests and self.requests[0] < now - self.window:
            self.requests.popleft()
        
        return len(self.requests) < self.max_requests
    
    def record_request(self):
        self.requests.append(time.time())
    
    def get_wait_time(self) -> float:
        if not self.requests:
            return 0.0
        oldest = self.requests[0]
        wait = (oldest + self.window) - time.time()
        return max(0.0, wait)

VT_LIMITER = VTRateLimiter()


class BouncerService:
    @staticmethod
    async def vt_hash_lookup(file_hash: str, db: Session, entropy: float = 0.0) -> dict:
        try:
            # Check local cache first (always check cache, no API cost)
            vt_cache = db.query(VTCache).filter(VTCache.hash_sha256 == file_hash).first()
            
            if vt_cache:
                # Check if cache is still valid
                cache_age = datetime.utcnow() - vt_cache.queried_at
                if cache_age < timedelta(days=settings.vt_cache_ttl_days):
                    logger.debug(f"VT cache hit: {file_hash[:8]}...")
                    
                    # Determine status
                    if vt_cache.score > 0.5:
                        status = "malicious"
                    elif vt_cache.score > 0.1:
                        status = "suspicious"
                    else:
                        status = "clean"
                    
                    return {
                        "cached": True,
                        "score": vt_cache.score,
                        "status": status
                    }
            
            # Check if VT API is configured
            if not settings.virustotal_api_key:
                logger.debug("   VT API key not configured, skipping lookup")
                return {"cached": False, "score": 0.0, "status": "unknown"}
            
            # Priority mode: Only check high-risk files to save API quota
            priority_mode = os.getenv("VT_PRIORITY_MODE", "true").lower() == "true"
            min_entropy = float(os.getenv("VT_MIN_ENTROPY_FOR_VT", "7.5"))
            
            if priority_mode and entropy < min_entropy:
                logger.debug(f"   VT skipped: low entropy ({entropy:.2f}) in priority mode")
                return {"cached": False, "score": 0.0, "status": "unknown"}
            
            # Check rate limit
            if not VT_LIMITER.can_request():
                wait_time = VT_LIMITER.get_wait_time()
                logger.warning(f"   VT rate limit reached, wait {wait_time:.0f}s")
                return {"cached": False, "score": 0.0, "status": "rate_limited"}
            
            logger.debug(f"Querying VirusTotal for {file_hash[:8]}...")
            VT_LIMITER.record_request()
            
            async with aiohttp.ClientSession() as session:
                headers = {"x-apikey": settings.virustotal_api_key}
                url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
                
                try:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
                            
                            malicious = stats.get("malicious", 0)
                            total = sum(stats.values())
                            score = malicious / total if total > 0 else 0.0
                            
                            # Determine status
                            if score > 0.5:
                                status = "malicious"
                            elif score > 0.1:
                                status = "suspicious"
                            else:
                                status = "clean"
                            
                            # Cache result (even clean results to avoid re-checking)
                            vt_cache = VTCache(hash_sha256=file_hash, score=score, queried_at=datetime.utcnow())
                            db.add(vt_cache)
                            db.commit()
                            
                            logger.info(f"  VT: {file_hash[:8]}... = {score:.1%} malicious ({status})")
                            
                            return {
                                "cached": False,
                                "score": score,
                                "status": status
                            }
                        
                        elif resp.status == 404:
                            logger.debug(f"VT: {file_hash[:8]}... not found (benign)")
                            # Cache 404 as clean to avoid re-checking
                            vt_cache = VTCache(hash_sha256=file_hash, score=0.0, queried_at=datetime.utcnow())
                            db.add(vt_cache)
                            db.commit()
                            return {"cached": False, "score": 0.0, "status": "clean"}
                        
                        elif resp.status == 429:
                            logger.warning(f"   VT API rate limit (429)")
                            return {"cached": False, "score": 0.0, "status": "rate_limited"}
                        
                        else:
                            logger.warning(f"   VT API error: {resp.status}")
                            return {"cached": False, "score": 0.0, "status": "unknown"}
                
                except aiohttp.ClientError as e:
                    logger.warning(f"   VT API connection error: {e}")
                    return {"cached": False, "score": 0.0, "status": "unknown"}
        
        except Exception as e:
            logger.warning(f"   VT lookup failed: {e}")
            return {"cached": False, "score": 0.0, "status": "unknown"}
    
    @staticmethod
    def entropy_check(file_path: str, file_size: int) -> tuple:
        try:
            # Tier 2: Full entropy for files ≤10MB
            if file_size <= 10 * 1024 * 1024:
                entropy_val = calculate_shannon_entropy(file_path)
                logger.debug(f"Tier 2 (full file) entropy: {entropy_val:.2f}")
            else:
                # Tier 3: Sample-based entropy for >10MB
                entropy_val = calculate_sample_entropy(file_path)
                logger.debug(f"Tier 3 (sample) entropy: {entropy_val:.2f}")
            
            # Low entropy = normal
            if entropy_val < ENTROPY_THRESHOLD_MEDIUM:
                logger.debug(f"  Low entropy ({entropy_val:.2f}) = likely normal")
                return ("PASS", entropy_val)
            
            # High entropy requires multi-layer confirmation
            if entropy_val > ENTROPY_THRESHOLD_HIGH:
                logger.warning(f"   High entropy detected: {entropy_val:.2f}")
                
                # Exception 1: Microsoft-signed
                if check_digital_signature(file_path):
                    logger.info(f"  High entropy but Microsoft-signed: PASS")
                    return ("PASS", entropy_val)
                
                # Exception 2: Known packer
                if is_known_packer(file_path):
                    logger.info(f"  High entropy but known packer: PASS")
                    return ("PASS", entropy_val)
                
                # Exception 3: Low code section entropy
                code_entropy = get_file_code_section_entropy(file_path)
                if code_entropy < 6.5:
                    logger.info(f"  High overall entropy but low code entropy ({code_entropy:.2f}): PASS")
                    return ("PASS", entropy_val)
                
                # No exceptions → flag as anomalous
                logger.warning(f"   High entropy + no exceptions: WARN")
                return ("WARN", entropy_val)
            
            return ("PASS", entropy_val)
        
        except Exception as e:
            logger.error(f"Entropy check failed: {e}")
            return ("UNCERTAIN", 0.0)
    
    @staticmethod
    def bouncer_decision(
        file_path: str,
        file_size: int,
        vt_score: float,
        db: Session
    ) -> dict:
        try:
            logger.info(f"Bouncer analyzing: {file_path}")
            
            signals = []
            
            # Calculate file hash
            file_hash = calculate_file_hash(file_path)
            logger.debug(f"   Hash: {file_hash[:16]}...")
            
            # Signal 1: VT lookup
            if vt_score > VT_POSITIVE_THRESHOLD:
                signals.append(f"VirusTotal positive ({vt_score:.1%})")
                logger.warning(f"Signal 1: VT positive ({vt_score:.1%})")
            
            # Signal 2: Entropy
            bouncer_status, entropy_val = BouncerService.entropy_check(file_path, file_size)
            if bouncer_status in ["WARN", "CRITICAL"]:
                signals.append(f"High entropy ({entropy_val:.2f})")
                logger.warning(f"Signal 2: High entropy ({entropy_val:.2f})")
            
            # Final decision
            if vt_score > VT_POSITIVE_THRESHOLD:
                status = "BLOCK"
                message = f"VT positive: {vt_score:.1%} malicious"
            elif bouncer_status == "CRITICAL" and len(signals) > 1:
                status = "CRITICAL"
                message = "Multiple suspicious signals"
            elif bouncer_status == "WARN":
                status = "WARN"
                message = "Entropy anomaly detected"
            else:
                status = "PASS"
                message = "No anomalies detected"
            
            logger.info(f"Bouncer decision: {status} - {message}")
            
            return {
                "status": status,
                "file_hash": file_hash,
                "entropy": entropy_val,
                "vt_score": vt_score,
                "signals": signals,
                "message": message
            }
        
        except Exception as e:
            logger.error(f"  Bouncer decision failed: {e}")
            return {
                "status": "UNCERTAIN",
                "file_hash": "",
                "entropy": 0.0,
                "vt_score": 0.0,
                "signals": ["Error in analysis"],
                "message": str(e)
            }