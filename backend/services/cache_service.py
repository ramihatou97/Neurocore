"""
Cache Service - Redis caching for search results
Improves performance by caching frequent queries
"""

import json
import hashlib
from typing import Any, Optional
from datetime import timedelta

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
            cache_key = self._generate_cache_key("search", query, search_type, filters)
            cached = self.redis.get(cache_key)

            if cached:
                logger.debug(f"Cache hit for search: {query}")
                return json.loads(cached)

            logger.debug(f"Cache miss for search: {query}")
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
                "suggestion_keys": len(self.redis.keys("suggestions:*"))
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {
                "enabled": True,
                "error": str(e)
            }


# Singleton instance (initialized with Redis client in main.py if available)
cache_service = CacheService()
