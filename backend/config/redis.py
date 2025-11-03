"""
Redis Connection Management
Handles Redis connections, connection pooling, and health checks
"""

import redis
from redis.connection import ConnectionPool
from typing import Optional, Any, Dict
import json
import pickle
from datetime import timedelta

from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class RedisManager:
    """
    Redis connection manager with connection pooling and health checks

    Features:
    - Connection pooling for performance
    - Automatic reconnection
    - Health monitoring
    - Multiple serialization strategies
    - Namespace support for key organization
    """

    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._initialized = False

    def initialize(self):
        """Initialize Redis connection pool"""
        if self._initialized:
            return

        try:
            # Create connection pool
            self._pool = ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=False,  # Handle decoding ourselves for flexibility
                socket_timeout=5,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )

            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection
            self._client.ping()

            self._initialized = True
            logger.info(f"Redis connection initialized: {settings.REDIS_HOST}:{settings.REDIS_PORT}")

        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {str(e)}", exc_info=True)
            self._initialized = False
            raise

    def get_client(self) -> redis.Redis:
        """Get Redis client instance"""
        if not self._initialized:
            self.initialize()
        return self._client

    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            if not self._client:
                return False
            self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False

    def close(self):
        """Close Redis connections"""
        if self._client:
            self._client.close()
        if self._pool:
            self._pool.disconnect()
        self._initialized = False
        logger.info("Redis connections closed")

    # ==================== Key Management ====================

    def make_key(self, *parts: str, namespace: str = "app") -> str:
        """
        Create namespaced Redis key

        Args:
            *parts: Key components
            namespace: Key namespace

        Returns:
            Formatted Redis key
        """
        key_parts = [namespace] + list(parts)
        return ":".join(str(p) for p in key_parts)

    # ==================== Basic Operations ====================

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: str = "json"
    ) -> bool:
        """
        Set value in Redis

        Args:
            key: Redis key
            value: Value to store
            ttl: Time-to-live in seconds
            serialize: Serialization method ('json', 'pickle', 'string')

        Returns:
            Success status
        """
        try:
            client = self.get_client()

            # Serialize value
            serialized = self._serialize(value, method=serialize)

            if ttl:
                client.setex(key, ttl, serialized)
            else:
                client.set(key, serialized)

            return True

        except Exception as e:
            logger.error(f"Redis SET failed for key '{key}': {str(e)}")
            return False

    def get(
        self,
        key: str,
        deserialize: str = "json",
        default: Any = None
    ) -> Any:
        """
        Get value from Redis

        Args:
            key: Redis key
            deserialize: Deserialization method
            default: Default value if key doesn't exist

        Returns:
            Stored value or default
        """
        try:
            client = self.get_client()
            value = client.get(key)

            if value is None:
                return default

            return self._deserialize(value, method=deserialize)

        except Exception as e:
            logger.error(f"Redis GET failed for key '{key}': {str(e)}")
            return default

    def delete(self, *keys: str) -> int:
        """
        Delete keys from Redis

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        try:
            if not keys:
                return 0
            client = self.get_client()
            return client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE failed: {str(e)}")
            return 0

    def exists(self, *keys: str) -> int:
        """Check if keys exist"""
        try:
            client = self.get_client()
            return client.exists(*keys)
        except Exception as e:
            logger.error(f"Redis EXISTS failed: {str(e)}")
            return 0

    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key"""
        try:
            client = self.get_client()
            return client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis EXPIRE failed for key '{key}': {str(e)}")
            return False

    def ttl(self, key: str) -> int:
        """Get remaining TTL for key"""
        try:
            client = self.get_client()
            return client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL failed for key '{key}': {str(e)}")
            return -2

    # ==================== Hash Operations ====================

    def hset(self, name: str, key: str, value: Any, serialize: str = "json") -> int:
        """Set hash field"""
        try:
            client = self.get_client()
            serialized = self._serialize(value, method=serialize)
            return client.hset(name, key, serialized)
        except Exception as e:
            logger.error(f"Redis HSET failed: {str(e)}")
            return 0

    def hget(self, name: str, key: str, deserialize: str = "json", default: Any = None) -> Any:
        """Get hash field"""
        try:
            client = self.get_client()
            value = client.hget(name, key)
            if value is None:
                return default
            return self._deserialize(value, method=deserialize)
        except Exception as e:
            logger.error(f"Redis HGET failed: {str(e)}")
            return default

    def hgetall(self, name: str, deserialize: str = "json") -> Dict[str, Any]:
        """Get all hash fields"""
        try:
            client = self.get_client()
            data = client.hgetall(name)
            return {
                k.decode('utf-8'): self._deserialize(v, method=deserialize)
                for k, v in data.items()
            }
        except Exception as e:
            logger.error(f"Redis HGETALL failed: {str(e)}")
            return {}

    def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields"""
        try:
            client = self.get_client()
            return client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis HDEL failed: {str(e)}")
            return 0

    def hlen(self, name: str) -> int:
        """Get number of fields in hash"""
        try:
            client = self.get_client()
            return client.hlen(name)
        except Exception as e:
            logger.error(f"Redis HLEN failed: {str(e)}")
            return 0

    # ==================== List Operations ====================

    def lpush(self, key: str, *values: Any, serialize: str = "json") -> int:
        """Push values to list (left)"""
        try:
            client = self.get_client()
            serialized = [self._serialize(v, method=serialize) for v in values]
            return client.lpush(key, *serialized)
        except Exception as e:
            logger.error(f"Redis LPUSH failed: {str(e)}")
            return 0

    def rpush(self, key: str, *values: Any, serialize: str = "json") -> int:
        """Push values to list (right)"""
        try:
            client = self.get_client()
            serialized = [self._serialize(v, method=serialize) for v in values]
            return client.rpush(key, *serialized)
        except Exception as e:
            logger.error(f"Redis RPUSH failed: {str(e)}")
            return 0

    def lrange(self, key: str, start: int, end: int, deserialize: str = "json") -> list:
        """Get list range"""
        try:
            client = self.get_client()
            values = client.lrange(key, start, end)
            return [self._deserialize(v, method=deserialize) for v in values]
        except Exception as e:
            logger.error(f"Redis LRANGE failed: {str(e)}")
            return []

    # ==================== Set Operations ====================

    def sadd(self, key: str, *members: Any, serialize: str = "json") -> int:
        """Add members to set"""
        try:
            client = self.get_client()
            serialized = [self._serialize(m, method=serialize) for m in members]
            return client.sadd(key, *serialized)
        except Exception as e:
            logger.error(f"Redis SADD failed: {str(e)}")
            return 0

    def smembers(self, key: str, deserialize: str = "json") -> set:
        """Get all set members"""
        try:
            client = self.get_client()
            members = client.smembers(key)
            return {self._deserialize(m, method=deserialize) for m in members}
        except Exception as e:
            logger.error(f"Redis SMEMBERS failed: {str(e)}")
            return set()

    def sismember(self, key: str, member: Any, serialize: str = "json") -> bool:
        """Check if member in set"""
        try:
            client = self.get_client()
            serialized = self._serialize(member, method=serialize)
            return client.sismember(key, serialized)
        except Exception as e:
            logger.error(f"Redis SISMEMBER failed: {str(e)}")
            return False

    # ==================== Sorted Set Operations ====================

    def zadd(self, key: str, mapping: Dict[Any, float], serialize: str = "json") -> int:
        """Add members to sorted set"""
        try:
            client = self.get_client()
            serialized_mapping = {
                self._serialize(k, method=serialize): v
                for k, v in mapping.items()
            }
            return client.zadd(key, serialized_mapping)
        except Exception as e:
            logger.error(f"Redis ZADD failed: {str(e)}")
            return 0

    def zrange(
        self,
        key: str,
        start: int,
        end: int,
        withscores: bool = False,
        deserialize: str = "json"
    ) -> list:
        """Get sorted set range"""
        try:
            client = self.get_client()
            values = client.zrange(key, start, end, withscores=withscores)

            if withscores:
                return [
                    (self._deserialize(v, method=deserialize), score)
                    for v, score in values
                ]
            return [self._deserialize(v, method=deserialize) for v in values]

        except Exception as e:
            logger.error(f"Redis ZRANGE failed: {str(e)}")
            return []

    def zrevrange(
        self,
        key: str,
        start: int,
        end: int,
        withscores: bool = False,
        deserialize: str = "json"
    ) -> list:
        """Get sorted set range in reverse order (highest to lowest score)"""
        try:
            client = self.get_client()
            values = client.zrevrange(key, start, end, withscores=withscores)

            if withscores:
                return [
                    (self._deserialize(v, method=deserialize), score)
                    for v, score in values
                ]
            return [self._deserialize(v, method=deserialize) for v in values]

        except Exception as e:
            logger.error(f"Redis ZREVRANGE failed: {str(e)}")
            return []

    def zrangebyscore(
        self,
        key: str,
        min_score: float,
        max_score: float,
        deserialize: str = "json"
    ) -> list:
        """Get sorted set members by score range"""
        try:
            client = self.get_client()
            values = client.zrangebyscore(key, min_score, max_score)
            return [self._deserialize(v, method=deserialize) for v in values]
        except Exception as e:
            logger.error(f"Redis ZRANGEBYSCORE failed: {str(e)}")
            return []

    def zcount(self, key: str, min_score: float, max_score: float) -> int:
        """Count members in sorted set within score range"""
        try:
            client = self.get_client()
            return client.zcount(key, min_score, max_score)
        except Exception as e:
            logger.error(f"Redis ZCOUNT failed: {str(e)}")
            return 0

    def zcard(self, key: str) -> int:
        """Get number of members in sorted set"""
        try:
            client = self.get_client()
            return client.zcard(key)
        except Exception as e:
            logger.error(f"Redis ZCARD failed: {str(e)}")
            return 0

    def zrem(self, key: str, *members: Any, serialize: str = "json") -> int:
        """Remove members from sorted set"""
        try:
            client = self.get_client()
            serialized = [self._serialize(m, method=serialize) for m in members]
            return client.zrem(key, *serialized)
        except Exception as e:
            logger.error(f"Redis ZREM failed: {str(e)}")
            return 0

    def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        """Remove members from sorted set by score range"""
        try:
            client = self.get_client()
            return client.zremrangebyscore(key, min_score, max_score)
        except Exception as e:
            logger.error(f"Redis ZREMRANGEBYSCORE failed: {str(e)}")
            return 0

    # ==================== Pattern Matching ====================

    def keys(self, pattern: str) -> list:
        """Get keys matching pattern"""
        try:
            client = self.get_client()
            return [k.decode('utf-8') for k in client.keys(pattern)]
        except Exception as e:
            logger.error(f"Redis KEYS failed for pattern '{pattern}': {str(e)}")
            return []

    def scan_iter(self, pattern: str, count: int = 100):
        """Iterate over keys matching pattern (memory-efficient)"""
        try:
            client = self.get_client()
            for key in client.scan_iter(match=pattern, count=count):
                yield key.decode('utf-8')
        except Exception as e:
            logger.error(f"Redis SCAN_ITER failed: {str(e)}")

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            keys_to_delete = list(self.scan_iter(pattern))
            if keys_to_delete:
                return self.delete(*keys_to_delete)
            return 0
        except Exception as e:
            logger.error(f"Redis delete pattern failed for '{pattern}': {str(e)}")
            return 0

    # ==================== Increment/Decrement ====================

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment key"""
        try:
            client = self.get_client()
            return client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR failed: {str(e)}")
            return 0

    def decr(self, key: str, amount: int = 1) -> int:
        """Decrement key"""
        try:
            client = self.get_client()
            return client.decrby(key, amount)
        except Exception as e:
            logger.error(f"Redis DECR failed: {str(e)}")
            return 0

    # ==================== Serialization ====================

    def _serialize(self, value: Any, method: str = "json") -> bytes:
        """Serialize value for Redis storage"""
        if method == "json":
            return json.dumps(value).encode('utf-8')
        elif method == "pickle":
            return pickle.dumps(value)
        elif method == "string":
            return str(value).encode('utf-8')
        else:
            raise ValueError(f"Unknown serialization method: {method}")

    def _deserialize(self, value: bytes, method: str = "json") -> Any:
        """Deserialize value from Redis"""
        if method == "json":
            return json.loads(value.decode('utf-8'))
        elif method == "pickle":
            return pickle.loads(value)
        elif method == "string":
            return value.decode('utf-8')
        else:
            raise ValueError(f"Unknown deserialization method: {method}")

    # ==================== Statistics ====================

    def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get Redis server info"""
        try:
            client = self.get_client()
            return client.info(section)
        except Exception as e:
            logger.error(f"Redis INFO failed: {str(e)}")
            return {}

    def dbsize(self) -> int:
        """Get number of keys in current database"""
        try:
            client = self.get_client()
            return client.dbsize()
        except Exception as e:
            logger.error(f"Redis DBSIZE failed: {str(e)}")
            return 0

    def flushdb(self) -> bool:
        """Clear current database (use with caution!)"""
        try:
            client = self.get_client()
            client.flushdb()
            logger.warning("Redis database flushed")
            return True
        except Exception as e:
            logger.error(f"Redis FLUSHDB failed: {str(e)}")
            return False


# Global Redis manager instance
redis_manager = RedisManager()


# Convenience functions
def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    return redis_manager.get_client()


def redis_health_check() -> bool:
    """Check Redis health"""
    return redis_manager.health_check()
