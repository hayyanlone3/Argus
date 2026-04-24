# backend/shared/decorators.py
"""Utility decorators for ARGUS."""

import functools
import time
from typing import Callable, Any
from shared.logger import setup_logger

logger = setup_logger(__name__)


def measure_execution_time(func: Callable) -> Callable:
    """Decorator to measure and log function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        logger.debug(f"⏱️  {func.__name__} executed in {elapsed:.3f}s")
        return result
    return wrapper


def cache_result(ttl_seconds: int = 300) -> Callable:
    """Decorator to cache function results for TTL seconds."""
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_times = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            key = f"{func.__name__}_{args}_{kwargs}"
            current_time = time.time()
            
            if key in cache:
                cached_time = cache_times.get(key, 0)
                if current_time - cached_time < ttl_seconds:
                    logger.debug(f"  Cache hit: {func.__name__}")
                    return cache[key]
            
            result = func(*args, **kwargs)
            cache[key] = result
            cache_times[key] = current_time
            return result
        
        return wrapper
    return decorator


def retry_on_failure(max_retries: int = 3, delay_seconds: float = 1.0) -> Callable:
    """Decorator to retry function on failure."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"  {func.__name__} failed after {max_retries} attempts: {e}")
                        raise
                    logger.warning(f"   {func.__name__} attempt {attempt + 1} failed, retrying in {delay_seconds}s...")
                    time.sleep(delay_seconds)
        
        return wrapper
    return decorator


def log_entry_exit(func: Callable) -> Callable:
    """Decorator to log function entry and exit."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        logger.debug(f"➡️  Entering {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"⬅️  Exiting {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"  Error in {func.__name__}: {e}")
            raise
    return wrapper