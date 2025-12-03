"""
Request Cache Service

Provides request-scoped caching for storing and retrieving data
within the lifecycle of a single request.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


class RequestCacheService:
    """
    Service for request-scoped caching.

    Stores data associated with request IDs for later retrieval.
    Includes automatic cleanup of expired entries.
    """

    _cache: Dict[str, Dict[str, Any]] = {}
    _timestamps: Dict[str, datetime] = {}
    _lock = threading.Lock()
    _default_ttl = timedelta(minutes=30)

    @classmethod
    def store(cls, request_id: str, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """
        Store a value in the cache.

        Args:
            request_id: The request identifier
            key: Cache key within the request scope
            value: Value to store
            ttl: Optional time-to-live (defaults to 30 minutes)
        """
        with cls._lock:
            # Initialize request cache if needed
            if request_id not in cls._cache:
                cls._cache[request_id] = {}

            cls._cache[request_id][key] = value
            cls._timestamps[f"{request_id}:{key}"] = datetime.now()

            logger.debug(f"Cached value for request {request_id}, key {key}")

            # Cleanup old entries periodically
            cls._cleanup_expired()

    @classmethod
    def get(cls, request_id: str, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Args:
            request_id: The request identifier
            key: Cache key within the request scope

        Returns:
            The cached value or None if not found/expired
        """
        with cls._lock:
            timestamp_key = f"{request_id}:{key}"

            # Check if entry exists
            if request_id not in cls._cache or key not in cls._cache[request_id]:
                return None

            # Check if entry is expired
            if timestamp_key in cls._timestamps:
                if datetime.now() - cls._timestamps[timestamp_key] > cls._default_ttl:
                    # Entry expired, remove it
                    del cls._cache[request_id][key]
                    del cls._timestamps[timestamp_key]
                    return None

            return cls._cache[request_id].get(key)

    @classmethod
    def delete(cls, request_id: str, key: Optional[str] = None) -> None:
        """
        Delete cached values.

        Args:
            request_id: The request identifier
            key: Optional specific key to delete. If None, deletes all keys for request.
        """
        with cls._lock:
            if request_id not in cls._cache:
                return

            if key is None:
                # Delete all keys for this request
                for k in list(cls._cache[request_id].keys()):
                    timestamp_key = f"{request_id}:{k}"
                    if timestamp_key in cls._timestamps:
                        del cls._timestamps[timestamp_key]
                del cls._cache[request_id]
            else:
                # Delete specific key
                if key in cls._cache[request_id]:
                    del cls._cache[request_id][key]
                    timestamp_key = f"{request_id}:{key}"
                    if timestamp_key in cls._timestamps:
                        del cls._timestamps[timestamp_key]

    @classmethod
    def clear_request(cls, request_id: str) -> None:
        """
        Clear all cached data for a request.

        Args:
            request_id: The request identifier
        """
        cls.delete(request_id)

    @classmethod
    def cleanup_request(cls, request_id: str) -> None:
        """
        Cleanup all cached data for a request (alias for clear_request).

        Args:
            request_id: The request identifier
        """
        cls.delete(request_id)

    @classmethod
    def _cleanup_expired(cls) -> None:
        """Remove expired entries from the cache."""
        now = datetime.now()
        expired_keys = []

        for timestamp_key, timestamp in cls._timestamps.items():
            if now - timestamp > cls._default_ttl:
                expired_keys.append(timestamp_key)

        for timestamp_key in expired_keys:
            request_id, key = timestamp_key.split(":", 1)
            if request_id in cls._cache and key in cls._cache[request_id]:
                del cls._cache[request_id][key]
                if not cls._cache[request_id]:
                    del cls._cache[request_id]
            del cls._timestamps[timestamp_key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with cls._lock:
            total_requests = len(cls._cache)
            total_entries = sum(len(entries) for entries in cls._cache.values())

            return {
                'total_requests': total_requests,
                'total_entries': total_entries
            }
