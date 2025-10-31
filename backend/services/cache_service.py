"""
Cache Service - Redis caching for search results
Improves performance by caching frequent queries

Phase 2 Enhancement: Added detailed analytics and monitoring for cache performance
"""

import json
import hashlib
from typing import Any, Optional, Dict
from datetime import timedelta, datetime
from collections import defaultdict

from backend.utils import get_logger

logger = get_logger(__name__)


class CacheService:
    """
    Redis cache service for search results and embeddings

    Cache strategies:
    - Search results: 5-minute TTL
    - Embeddings: Permanent (until entity updates)
    - Suggestions: 1-hour TTL
    """

    def __init__(self, redis_client=None):
        """
        Initialize cache service

        Args:
            redis_client: Redis client instance (optional)
        """
        self.redis = redis_client
        self.enabled = redis_client is not None

        # Phase 2: In-memory analytics tracking
        self._analytics = {
            "hits": defaultdict(int),      # Cache hits by type
            "misses": defaultdict(int),    # Cache misses by type
            "hit_times": defaultdict(list), # Response times for hits
            "miss_times": defaultdict(list), # Response times for misses
            "last_reset": datetime.now()
        }

    def _generate_cache_key(self, prefix: str, *args) -> str:
        """
        Generate cache key from prefix and arguments

        Args:
            prefix: Key prefix
            *args: Arguments to hash

        Returns:
            Cache key string
        """
        # Create hash from arguments
        content = json.dumps(args, sort_keys=True, default=str)
        hash_value = hashlib.md5(content.encode()).hexdigest()

        return f"{prefix}:{hash_value}"

    async def get_search_results(self, query: str, search_type: str, filters: dict) -> Optional[dict]:
        """
        Get cached search results

        Phase 2: Added analytics tracking for cache hits/misses

        Args:
            query: Search query
            search_type: Type of search
            filters: Search filters

        Returns:
            Cached results or None
        """
        if not self.enabled:
            return None

        try:
            import time
            start_time = time.time()

            cache_key = self._generate_cache_key("search", query, search_type, filters)
            cached = self.redis.get(cache_key)

            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            if cached:
                # Track cache hit
                self._analytics["hits"][search_type] += 1
                self._analytics["hit_times"][search_type].append(response_time)
                logger.debug(f"Cache hit for {search_type}: {query} ({response_time:.2f}ms)")
                return json.loads(cached)

            # Track cache miss
            self._analytics["misses"][search_type] += 1
            self._analytics["miss_times"][search_type].append(response_time)
            logger.debug(f"Cache miss for {search_type}: {query} ({response_time:.2f}ms)")
            return None

        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    async def set_search_results(
        self,
        query: str,
        search_type: str,
        filters: dict,
        results: dict,
        ttl_seconds: int = 300
    ):
        """
        Cache search results

        Args:
            query: Search query
            search_type: Type of search
            filters: Search filters
            results: Search results to cache
            ttl_seconds: Time to live in seconds (default: 5 minutes)
        """
        if not self.enabled:
            return

        try:
            cache_key = self._generate_cache_key("search", query, search_type, filters)
            self.redis.setex(
                cache_key,
                ttl_seconds,
                json.dumps(results, default=str)
            )

            logger.debug(f"Cached search results for: {query} (TTL: {ttl_seconds}s)")

        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")

    async def get_suggestions(self, partial_query: str) -> Optional[list]:
        """
        Get cached search suggestions

        Args:
            partial_query: Partial search query

        Returns:
            Cached suggestions or None
        """
        if not self.enabled:
            return None

        try:
            cache_key = self._generate_cache_key("suggestions", partial_query)
            cached = self.redis.get(cache_key)

            if cached:
                logger.debug(f"Cache hit for suggestions: {partial_query}")
                return json.loads(cached)

            return None

        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    async def set_suggestions(
        self,
        partial_query: str,
        suggestions: list,
        ttl_seconds: int = 3600
    ):
        """
        Cache search suggestions

        Args:
            partial_query: Partial search query
            suggestions: Suggestions list
            ttl_seconds: Time to live (default: 1 hour)
        """
        if not self.enabled:
            return

        try:
            cache_key = self._generate_cache_key("suggestions", partial_query)
            self.redis.setex(
                cache_key,
                ttl_seconds,
                json.dumps(suggestions)
            )

            logger.debug(f"Cached suggestions for: {partial_query}")

        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")

    async def invalidate_entity_cache(self, entity_type: str, entity_id: str):
        """
        Invalidate cache for specific entity

        Called when entity is updated or deleted

        Args:
            entity_type: Type of entity (pdf, chapter, image)
            entity_id: Entity ID
        """
        if not self.enabled:
            return

        try:
            # Pattern matching for entity-related keys
            pattern = f"*:{entity_type}:{entity_id}*"
            keys = self.redis.keys(pattern)

            if keys:
                self.redis.delete(*keys)
                logger.debug(f"Invalidated {len(keys)} cache keys for {entity_type}:{entity_id}")

        except Exception as e:
            logger.error(f"Cache invalidation error: {str(e)}")

    async def clear_all_search_cache(self):
        """
        Clear all search-related cache

        Use with caution - for maintenance or after bulk updates
        """
        if not self.enabled:
            return

        try:
            # Clear search results
            search_keys = self.redis.keys("search:*")
            if search_keys:
                self.redis.delete(*search_keys)
                logger.info(f"Cleared {len(search_keys)} search cache keys")

            # Clear suggestions
            suggestion_keys = self.redis.keys("suggestions:*")
            if suggestion_keys:
                self.redis.delete(*suggestion_keys)
                logger.info(f"Cleared {len(suggestion_keys)} suggestion cache keys")

        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled:
            return {
                "enabled": False,
                "message": "Redis cache not configured"
            }

        try:
            info = self.redis.info()

            return {
                "enabled": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": self.redis.dbsize(),
                "search_keys": len(self.redis.keys("search:*")),
                "suggestion_keys": len(self.redis.keys("suggestions:*")),
                "pubmed_keys": len(self.redis.keys("pubmed:*"))  # Phase 2: Track PubMed cache
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {
                "enabled": True,
                "error": str(e)
            }

    def get_analytics(self, search_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed cache analytics

        Phase 2: Added comprehensive cache performance analytics

        Args:
            search_type: Optional filter by search type (e.g., 'pubmed', 'search')

        Returns:
            Dictionary with detailed analytics
        """
        if not self.enabled:
            return {
                "enabled": False,
                "message": "Cache analytics not available"
            }

        import statistics

        analytics = {
            "enabled": True,
            "tracking_since": self._analytics["last_reset"].isoformat(),
            "search_types": {}
        }

        # Get all search types or filter by specific type
        search_types = [search_type] if search_type else list(
            set(list(self._analytics["hits"].keys()) + list(self._analytics["misses"].keys()))
        )

        for st in search_types:
            hits = self._analytics["hits"].get(st, 0)
            misses = self._analytics["misses"].get(st, 0)
            total_requests = hits + misses

            # Calculate hit rate
            hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0

            # Calculate average response times
            hit_times = self._analytics["hit_times"].get(st, [])
            miss_times = self._analytics["miss_times"].get(st, [])

            avg_hit_time = statistics.mean(hit_times) if hit_times else 0
            avg_miss_time = statistics.mean(miss_times) if miss_times else 0

            # Calculate speedup
            speedup_factor = (avg_miss_time / avg_hit_time) if avg_hit_time > 0 and avg_miss_time > 0 else 0

            analytics["search_types"][st] = {
                "hits": hits,
                "misses": misses,
                "total_requests": total_requests,
                "hit_rate_percent": round(hit_rate, 2),
                "avg_hit_time_ms": round(avg_hit_time, 3),
                "avg_miss_time_ms": round(avg_miss_time, 3),
                "speedup_factor": round(speedup_factor, 2),
                "min_hit_time_ms": round(min(hit_times), 3) if hit_times else 0,
                "max_hit_time_ms": round(max(hit_times), 3) if hit_times else 0,
                "min_miss_time_ms": round(min(miss_times), 3) if miss_times else 0,
                "max_miss_time_ms": round(max(miss_times), 3) if miss_times else 0
            }

        # Overall statistics
        total_hits = sum(self._analytics["hits"].values())
        total_misses = sum(self._analytics["misses"].values())
        total_requests = total_hits + total_misses

        analytics["overall"] = {
            "total_hits": total_hits,
            "total_misses": total_misses,
            "total_requests": total_requests,
            "overall_hit_rate_percent": round((total_hits / total_requests * 100) if total_requests > 0 else 0, 2)
        }

        return analytics

    def reset_analytics(self):
        """
        Reset analytics counters

        Phase 2: Reset in-memory analytics tracking
        """
        self._analytics = {
            "hits": defaultdict(int),
            "misses": defaultdict(int),
            "hit_times": defaultdict(list),
            "miss_times": defaultdict(list),
            "last_reset": datetime.now()
        }
        logger.info("Cache analytics reset")

    def get_pubmed_cache_stats(self) -> Dict[str, Any]:
        """
        Get PubMed-specific cache statistics

        Phase 2: Dedicated PubMed cache performance tracking

        Returns:
            Dictionary with PubMed cache statistics
        """
        if not self.enabled:
            return {
                "enabled": False,
                "message": "Cache not enabled"
            }

        try:
            # Get PubMed-specific analytics
            pubmed_analytics = self.get_analytics(search_type="pubmed")

            # Get key information from Redis
            pubmed_keys = self.redis.keys("pubmed:*")
            total_pubmed_keys = len(pubmed_keys)

            # Sample TTLs to understand cache freshness
            ttls = []
            for key in pubmed_keys[:10]:  # Sample first 10 keys
                ttl = self.redis.ttl(key)
                if ttl > 0:
                    ttls.append(ttl)

            avg_ttl_remaining = sum(ttls) / len(ttls) if ttls else 0

            return {
                "enabled": True,
                "total_pubmed_keys": total_pubmed_keys,
                "avg_ttl_remaining_seconds": round(avg_ttl_remaining, 0),
                "configured_ttl_seconds": 86400,  # 24 hours
                "analytics": pubmed_analytics.get("search_types", {}).get("pubmed", {}),
                "performance_target": {
                    "target_hit_rate": "60-80%",
                    "target_speedup": "100x+"
                }
            }

        except Exception as e:
            logger.error(f"Failed to get PubMed cache stats: {str(e)}")
            return {
                "enabled": True,
                "error": str(e)
            }


# Singleton instance (initialized with Redis client in main.py if available)
cache_service = CacheService()
