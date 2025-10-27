"""
Enhanced Cache Service for Phase 15: Performance & Optimization
Multi-layer caching with Redis, statistics tracking, and intelligent cache warming
"""

import json
import hashlib
import time
from typing import Any, Optional, Callable, Dict, List
from datetime import datetime, timedelta
from functools import wraps
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.config.redis import redis_manager
from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class PerformanceCacheService:
    """
    Enhanced caching service with performance optimizations

    Features:
    - Multi-layer caching (in-memory + Redis)
    - Cache statistics tracking in database
    - Intelligent cache warming
    - TTL management
    - Cache invalidation strategies
    - Batch operations
    - Decorator support
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.redis = redis_manager
        self._memory_cache: Dict[str, tuple] = {}  # key -> (value, expiry)
        self._max_memory_items = 1000

    # ==================== Core Caching Operations ====================

    def get(
        self,
        key: str,
        cache_type: str = "api",
        use_memory: bool = True
    ) -> Optional[Any]:
        """
        Get value from cache with multi-layer support

        Args:
            key: Cache key
            cache_type: Type of cache for statistics
            use_memory: Check memory cache first

        Returns:
            Cached value or None
        """
        try:
            start_time = time.time()

            # Check memory cache first
            if use_memory:
                memory_value = self._get_from_memory(key)
                if memory_value is not None:
                    self._track_cache_hit(key, cache_type, time.time() - start_time)
                    return memory_value

            # Check Redis
            redis_value = self.redis.get(key, deserialize="json")
            if redis_value is not None:
                # Store in memory for future hits
                if use_memory:
                    self._store_in_memory(key, redis_value, ttl=300)
                self._track_cache_hit(key, cache_type, time.time() - start_time)
                return redis_value

            # Cache miss
            self._track_cache_miss(key, cache_type)
            return None

        except Exception as e:
            logger.error(f"Cache get error for key '{key}': {str(e)}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: int,
        cache_type: str = "api",
        use_memory: bool = True
    ) -> bool:
        """
        Set value in cache with multi-layer support

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            cache_type: Type of cache for statistics
            use_memory: Also store in memory

        Returns:
            Success status
        """
        try:
            # Store in Redis
            success = self.redis.set(key, value, ttl=ttl, serialize="json")

            # Store in memory if enabled
            if use_memory and success:
                self._store_in_memory(key, value, ttl=min(ttl, 300))

            # Track metadata
            if success and self.db:
                self._store_cache_metadata(key, cache_type, ttl)

            return success

        except Exception as e:
            logger.error(f"Cache set error for key '{key}': {str(e)}")
            return False

    def delete(self, *keys: str) -> int:
        """Delete keys from all cache layers"""
        try:
            # Remove from memory cache
            for key in keys:
                self._memory_cache.pop(key, None)

            # Remove from Redis
            return self.redis.delete(*keys)

        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return 0

    # ==================== Memory Cache Operations ====================

    def _get_from_memory(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if expiry is None or expiry > time.time():
                return value
            # Expired
            del self._memory_cache[key]
        return None

    def _store_in_memory(self, key: str, value: Any, ttl: Optional[int] = None):
        """Store value in memory cache"""
        # Evict oldest if cache is full
        if len(self._memory_cache) >= self._max_memory_items:
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]

        expiry = time.time() + ttl if ttl else None
        self._memory_cache[key] = (value, expiry)

    def clear_memory_cache(self):
        """Clear memory cache"""
        self._memory_cache.clear()
        logger.info("Memory cache cleared")

    # ==================== Cache Patterns ====================

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl: int,
        cache_type: str = "api"
    ) -> Any:
        """
        Get from cache or compute and store

        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            ttl: Time-to-live for cached value
            cache_type: Cache type for statistics

        Returns:
            Cached or computed value
        """
        # Try cache first
        cached_value = self.get(key, cache_type=cache_type)
        if cached_value is not None:
            return cached_value

        # Compute value
        start_time = time.time()
        computed_value = compute_fn()
        compute_time = int((time.time() - start_time) * 1000)

        # Store in cache
        self.set(key, computed_value, ttl=ttl, cache_type=cache_type)

        # Track time saved
        if self.db:
            self._update_time_saved(key, compute_time)

        return computed_value

    def cache_aside(
        self,
        key: str,
        fetch_fn: Callable[[], Any],
        ttl: int,
        cache_type: str = "query"
    ) -> Any:
        """
        Cache-aside pattern (lazy loading)

        Args:
            key: Cache key
            fetch_fn: Function to fetch data
            ttl: Time-to-live
            cache_type: Cache type

        Returns:
            Cached or fetched value
        """
        return self.get_or_compute(key, fetch_fn, ttl, cache_type)

    def write_through(
        self,
        key: str,
        value: Any,
        write_fn: Callable[[Any], bool],
        ttl: int,
        cache_type: str = "api"
    ) -> bool:
        """
        Write-through pattern (update cache and database)

        Args:
            key: Cache key
            value: Value to write
            write_fn: Function to write to database
            ttl: Time-to-live
            cache_type: Cache type

        Returns:
            Success status
        """
        try:
            # Write to database first
            db_success = write_fn(value)
            if not db_success:
                return False

            # Update cache
            cache_success = self.set(key, value, ttl=ttl, cache_type=cache_type)

            return cache_success

        except Exception as e:
            logger.error(f"Write-through error: {str(e)}")
            return False

    # ==================== Cache Warming ====================

    def warm_cache(
        self,
        keys_and_loaders: List[tuple[str, Callable, int, str]]
    ) -> Dict[str, bool]:
        """
        Warm cache with multiple keys

        Args:
            keys_and_loaders: List of (key, loader_fn, ttl, cache_type)

        Returns:
            Dict of key -> success status
        """
        results = {}

        for key, loader_fn, ttl, cache_type in keys_and_loaders:
            try:
                # Check if already cached
                if self.get(key, cache_type=cache_type) is not None:
                    results[key] = True
                    continue

                # Load and cache
                value = loader_fn()
                results[key] = self.set(key, value, ttl=ttl, cache_type=cache_type)

            except Exception as e:
                logger.error(f"Cache warming failed for key '{key}': {str(e)}")
                results[key] = False

        warm_count = sum(1 for success in results.values() if success)
        logger.info(f"Cache warming: {warm_count}/{len(results)} keys loaded")

        return results

    # ==================== Batch Operations ====================

    def get_many(
        self,
        keys: List[str],
        cache_type: str = "api"
    ) -> Dict[str, Any]:
        """Get multiple keys from cache"""
        results = {}

        for key in keys:
            value = self.get(key, cache_type=cache_type)
            if value is not None:
                results[key] = value

        return results

    def set_many(
        self,
        items: Dict[str, tuple[Any, int]],
        cache_type: str = "api"
    ) -> Dict[str, bool]:
        """
        Set multiple keys in cache

        Args:
            items: Dict of key -> (value, ttl)
            cache_type: Cache type

        Returns:
            Dict of key -> success status
        """
        results = {}

        for key, (value, ttl) in items.items():
            results[key] = self.set(key, value, ttl=ttl, cache_type=cache_type)

        return results

    # ==================== Pattern-based Operations ====================

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        try:
            deleted = self.redis.delete_pattern(pattern)

            # Clear matching keys from memory cache
            keys_to_remove = [k for k in self._memory_cache.keys() if self._matches_pattern(k, pattern)]
            for key in keys_to_remove:
                del self._memory_cache[key]

            logger.info(f"Invalidated {deleted} cache keys matching pattern '{pattern}'")
            return deleted

        except Exception as e:
            logger.error(f"Pattern invalidation failed: {str(e)}")
            return 0

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern (simple * wildcard support)"""
        import re
        regex_pattern = pattern.replace('*', '.*')
        return bool(re.match(f"^{regex_pattern}$", key))

    # ==================== Statistics Tracking ====================

    def _track_cache_hit(self, key: str, cache_type: str, retrieval_time: float):
        """Track cache hit in database"""
        if not self.db:
            return

        try:
            retrieval_ms = int(retrieval_time * 1000)

            query = text("""
                INSERT INTO cache_metadata (cache_key, cache_type, hit_count, total_time_saved_ms, last_accessed)
                VALUES (:key, :cache_type, 1, :time_saved, NOW())
                ON CONFLICT (cache_key)
                DO UPDATE SET
                    hit_count = cache_metadata.hit_count + 1,
                    total_time_saved_ms = cache_metadata.total_time_saved_ms + :time_saved,
                    last_accessed = NOW(),
                    updated_at = NOW()
            """)

            self.db.execute(query, {
                'key': key,
                'cache_type': cache_type,
                'time_saved': retrieval_ms
            })
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to track cache hit: {str(e)}")

    def _track_cache_miss(self, key: str, cache_type: str):
        """Track cache miss in database"""
        if not self.db:
            return

        try:
            query = text("""
                INSERT INTO cache_metadata (cache_key, cache_type, miss_count, last_accessed)
                VALUES (:key, :cache_type, 1, NOW())
                ON CONFLICT (cache_key)
                DO UPDATE SET
                    miss_count = cache_metadata.miss_count + 1,
                    last_accessed = NOW(),
                    updated_at = NOW()
            """)

            self.db.execute(query, {
                'key': key,
                'cache_type': cache_type
            })
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to track cache miss: {str(e)}")

    def _store_cache_metadata(self, key: str, cache_type: str, ttl: int):
        """Store cache metadata in database"""
        if not self.db:
            return

        try:
            query = text("""
                INSERT INTO cache_metadata (
                    cache_key, cache_type, ttl_seconds, expires_at, last_accessed
                )
                VALUES (
                    :key, :cache_type, :ttl, NOW() + INTERVAL '1 second' * :ttl, NOW()
                )
                ON CONFLICT (cache_key)
                DO UPDATE SET
                    ttl_seconds = :ttl,
                    expires_at = NOW() + INTERVAL '1 second' * :ttl,
                    updated_at = NOW()
            """)

            self.db.execute(query, {
                'key': key,
                'cache_type': cache_type,
                'ttl': ttl
            })
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to store cache metadata: {str(e)}")

    def _update_time_saved(self, key: str, compute_time_ms: int):
        """Update time saved by caching"""
        if not self.db:
            return

        try:
            query = text("""
                UPDATE cache_metadata
                SET total_time_saved_ms = total_time_saved_ms + :time_saved
                WHERE cache_key = :key
            """)

            self.db.execute(query, {
                'key': key,
                'time_saved': compute_time_ms
            })
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update time saved: {str(e)}")

    # ==================== Statistics & Analytics ====================

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        try:
            # Redis stats
            redis_info = self.redis.info()
            redis_stats = {
                'connected': self.redis.health_check(),
                'used_memory': redis_info.get('used_memory_human', 'N/A'),
                'total_keys': self.redis.dbsize(),
                'connected_clients': redis_info.get('connected_clients', 0),
                'hit_rate': redis_info.get('keyspace_hits', 0) / max(
                    redis_info.get('keyspace_hits', 0) + redis_info.get('keyspace_misses', 0), 1
                ) * 100 if 'keyspace_hits' in redis_info else 0
            }

            # Memory cache stats
            memory_stats = {
                'size': len(self._memory_cache),
                'max_size': self._max_memory_items,
                'utilization': len(self._memory_cache) / self._max_memory_items * 100
            }

            # Database stats
            db_stats = self._get_db_cache_stats() if self.db else {}

            return {
                'redis': redis_stats,
                'memory': memory_stats,
                'database': db_stats,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get cache statistics: {str(e)}")
            return {'error': str(e)}

    def _get_db_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics from database"""
        try:
            query = text("""
                SELECT
                    cache_type,
                    COUNT(*) as entry_count,
                    SUM(hit_count) as total_hits,
                    SUM(miss_count) as total_misses,
                    ROUND(
                        SUM(hit_count)::NUMERIC / NULLIF(SUM(hit_count + miss_count), 0)::NUMERIC * 100,
                        2
                    ) as hit_rate,
                    ROUND(SUM(total_time_saved_ms)::NUMERIC / 1000, 2) as time_saved_seconds
                FROM cache_metadata
                GROUP BY cache_type
            """)

            result = self.db.execute(query)
            rows = result.fetchall()

            stats_by_type = {}
            for row in rows:
                stats_by_type[row[0]] = {
                    'entry_count': row[1],
                    'total_hits': row[2] or 0,
                    'total_misses': row[3] or 0,
                    'hit_rate': float(row[4]) if row[4] else 0.0,
                    'time_saved_seconds': float(row[5]) if row[5] else 0.0
                }

            return stats_by_type

        except Exception as e:
            logger.error(f"Failed to get DB cache stats: {str(e)}")
            return {}

    # ==================== Maintenance ====================

    def cleanup_expired(self) -> int:
        """Clean up expired cache entries from database"""
        if not self.db:
            return 0

        try:
            query = text("""
                DELETE FROM cache_metadata
                WHERE expires_at IS NOT NULL AND expires_at < NOW()
            """)

            result = self.db.execute(query)
            self.db.commit()

            deleted_count = result.rowcount
            logger.info(f"Cleaned up {deleted_count} expired cache entries")
            return deleted_count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Cache cleanup failed: {str(e)}")
            return 0

    def get_top_cached_keys(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most frequently accessed cache keys"""
        if not self.db:
            return []

        try:
            query = text("""
                SELECT
                    cache_key,
                    cache_type,
                    hit_count,
                    miss_count,
                    ROUND(
                        hit_count::NUMERIC / NULLIF(hit_count + miss_count, 0)::NUMERIC * 100,
                        2
                    ) as hit_rate,
                    total_time_saved_ms,
                    last_accessed
                FROM cache_metadata
                ORDER BY hit_count DESC
                LIMIT :limit
            """)

            result = self.db.execute(query, {'limit': limit})

            return [
                {
                    'key': row[0],
                    'type': row[1],
                    'hit_count': row[2],
                    'miss_count': row[3],
                    'hit_rate': float(row[4]) if row[4] else 0.0,
                    'time_saved_ms': row[5],
                    'last_accessed': row[6].isoformat() if row[6] else None
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get top cached keys: {str(e)}")
            return []


# ==================== Cache Decorators ====================

def cached(
    ttl: int,
    cache_type: str = "api",
    key_prefix: str = "",
    use_memory: bool = True
):
    """
    Decorator for caching function results

    Args:
        ttl: Time-to-live in seconds
        cache_type: Cache type for statistics
        key_prefix: Prefix for cache key
        use_memory: Use memory cache

    Usage:
        @cached(ttl=300, cache_type="query", key_prefix="user_data")
        def get_user_data(user_id: str):
            return expensive_db_query(user_id)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key_parts = [key_prefix or func.__name__]
            cache_key_parts.extend(str(arg) for arg in args)
            cache_key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

            cache_key = ":".join(cache_key_parts)

            # Create cache service instance
            cache = PerformanceCacheService()

            # Try cache
            cached_value = cache.get(cache_key, cache_type=cache_type, use_memory=use_memory)
            if cached_value is not None:
                return cached_value

            # Compute value
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, ttl=ttl, cache_type=cache_type, use_memory=use_memory)

            return result

        return wrapper
    return decorator
