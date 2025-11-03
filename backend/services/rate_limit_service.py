"""
Rate Limit Service for Phase 15: Performance & Optimization
Advanced rate limiting with multiple strategies and violation tracking
"""

import time
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from enum import Enum

from backend.config.redis import redis_manager
from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


class RateLimitResult:
    """Rate limit check result"""

    def __init__(
        self,
        allowed: bool,
        limit: int,
        remaining: int,
        reset_at: datetime,
        retry_after: Optional[int] = None
    ):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at
        self.retry_after = retry_after  # seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            'allowed': self.allowed,
            'limit': self.limit,
            'remaining': self.remaining,
            'reset_at': self.reset_at.isoformat(),
            'retry_after': self.retry_after
        }


class RateLimitService:
    """
    Advanced rate limiting service

    Features:
    - Multiple rate limiting strategies
    - Per-user, per-IP, and per-endpoint limits
    - Automatic violation tracking
    - Temporary blocking for repeat offenders
    - Whitelist support
    - Comprehensive analytics
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.redis = redis_manager

        # Default rate limits
        self.default_limits = {
            'api': (100, 60),  # 100 requests per 60 seconds
            'auth': (10, 900),  # 10 login attempts per 15 minutes (critical security)
            'search': (30, 60),  # 30 searches per minute
            'ai': (10, 60),  # 10 AI requests per minute
            'upload': (5, 300),  # 5 uploads per 5 minutes
            'export': (10, 3600)  # 10 exports per hour
        }

        # Whitelist (users/IPs exempt from rate limiting)
        self._whitelist = set()

    # ==================== Core Rate Limiting ====================

    def check_rate_limit(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    ) -> RateLimitResult:
        """
        Check if request is within rate limit

        Args:
            identifier: User ID or IP address
            identifier_type: 'user', 'ip', or 'api_key'
            endpoint: API endpoint being accessed
            limit: Request limit (default from config)
            window: Time window in seconds (default from config)
            strategy: Rate limiting strategy

        Returns:
            RateLimitResult with decision and metadata
        """
        # Check whitelist
        if identifier in self._whitelist:
            return RateLimitResult(
                allowed=True,
                limit=999999,
                remaining=999999,
                reset_at=datetime.now() + timedelta(days=1)
            )

        # Check if blocked
        if self._is_blocked(identifier, identifier_type):
            block_info = self._get_block_info(identifier, identifier_type)
            return RateLimitResult(
                allowed=False,
                limit=0,
                remaining=0,
                reset_at=block_info['blocked_until'],
                retry_after=int((block_info['blocked_until'] - datetime.now()).total_seconds())
            )

        # Get limits
        if limit is None or window is None:
            limit, window = self._get_endpoint_limits(endpoint)

        # Apply strategy
        if strategy == RateLimitStrategy.FIXED_WINDOW:
            result = self._fixed_window_check(identifier, identifier_type, endpoint, limit, window)
        elif strategy == RateLimitStrategy.SLIDING_WINDOW:
            result = self._sliding_window_check(identifier, identifier_type, endpoint, limit, window)
        elif strategy == RateLimitStrategy.TOKEN_BUCKET:
            result = self._token_bucket_check(identifier, identifier_type, endpoint, limit, window)
        else:
            raise ValueError(f"Unknown rate limit strategy: {strategy}")

        # Track violation if exceeded
        if not result.allowed:
            self._track_violation(identifier, identifier_type, endpoint, limit, window)

        return result

    def record_request(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str
    ) -> bool:
        """
        Record a successful request (after rate limit check passed)

        Args:
            identifier: User ID or IP
            identifier_type: Identifier type
            endpoint: Endpoint accessed

        Returns:
            Success status
        """
        try:
            # Update database tracking
            if self.db:
                self._update_rate_limit_db(identifier, identifier_type, endpoint)

            return True

        except Exception as e:
            logger.error(f"Failed to record request: {str(e)}")
            return False

    # ==================== Rate Limiting Strategies ====================

    def _fixed_window_check(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str,
        limit: int,
        window: int
    ) -> RateLimitResult:
        """
        Fixed window rate limiting

        Simple counter that resets at fixed intervals
        """
        key = self._make_key(identifier, identifier_type, endpoint, "fixed")

        try:
            # Get current count
            current_count = self.redis.get(key, deserialize="string", default="0")
            current_count = int(current_count)

            # Get TTL to determine reset time
            ttl = self.redis.ttl(key)
            if ttl == -2:  # Key doesn't exist
                ttl = window
                current_count = 0

            # Check limit
            if current_count >= limit:
                reset_at = datetime.now() + timedelta(seconds=ttl)
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=ttl
                )

            # Increment counter
            new_count = self.redis.incr(key)

            # Set expiry if first request in window
            if new_count == 1:
                self.redis.expire(key, window)

            reset_at = datetime.now() + timedelta(seconds=window)

            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - new_count,
                reset_at=reset_at
            )

        except Exception as e:
            logger.error(f"Fixed window check failed: {str(e)}")
            # Fail open (allow request)
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_at=datetime.now() + timedelta(seconds=window)
            )

    def _sliding_window_check(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str,
        limit: int,
        window: int
    ) -> RateLimitResult:
        """
        Sliding window rate limiting

        More accurate than fixed window, prevents burst at window boundaries
        """
        key = self._make_key(identifier, identifier_type, endpoint, "sliding")

        try:
            current_time = time.time()
            window_start = current_time - window

            # Use Redis sorted set with timestamps as scores
            # Remove old entries
            self.redis.get_client().zremrangebyscore(key, 0, window_start)

            # Count current requests
            current_count = self.redis.get_client().zcard(key)

            if current_count >= limit:
                # Get oldest request time to calculate reset
                oldest = self.redis.get_client().zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    reset_seconds = int(oldest_time + window - current_time)
                    reset_at = datetime.now() + timedelta(seconds=reset_seconds)
                else:
                    reset_at = datetime.now() + timedelta(seconds=window)

                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=reset_seconds if oldest else window
                )

            # Add current request
            request_id = f"{current_time}:{identifier}"
            self.redis.get_client().zadd(key, {request_id: current_time})

            # Set expiry on key
            self.redis.expire(key, window + 1)

            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - current_count - 1,
                reset_at=datetime.now() + timedelta(seconds=window)
            )

        except Exception as e:
            logger.error(f"Sliding window check failed: {str(e)}")
            # Fail open
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_at=datetime.now() + timedelta(seconds=window)
            )

    def _token_bucket_check(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str,
        limit: int,
        window: int
    ) -> RateLimitResult:
        """
        Token bucket rate limiting

        Allows bursts while maintaining average rate
        """
        key = self._make_key(identifier, identifier_type, endpoint, "bucket")

        try:
            # Token bucket parameters
            capacity = limit
            refill_rate = limit / window  # tokens per second

            current_time = time.time()

            # Get bucket state
            bucket_data = self.redis.hgetall(key, deserialize="json")

            if not bucket_data:
                # Initialize bucket
                bucket_data = {
                    'tokens': capacity,
                    'last_refill': current_time
                }

            # Refill tokens based on time elapsed
            time_passed = current_time - bucket_data['last_refill']
            tokens_to_add = time_passed * refill_rate
            bucket_data['tokens'] = min(capacity, bucket_data['tokens'] + tokens_to_add)
            bucket_data['last_refill'] = current_time

            # Check if token available
            if bucket_data['tokens'] < 1:
                # Calculate when next token available
                time_until_token = (1 - bucket_data['tokens']) / refill_rate
                reset_at = datetime.now() + timedelta(seconds=time_until_token)

                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=int(time_until_token) + 1
                )

            # Consume token
            bucket_data['tokens'] -= 1

            # Store updated bucket state
            self.redis.hset(key, 'tokens', bucket_data['tokens'], serialize="json")
            self.redis.hset(key, 'last_refill', bucket_data['last_refill'], serialize="json")
            self.redis.expire(key, window * 2)

            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=int(bucket_data['tokens']),
                reset_at=datetime.now() + timedelta(seconds=window)
            )

        except Exception as e:
            logger.error(f"Token bucket check failed: {str(e)}")
            # Fail open
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_at=datetime.now() + timedelta(seconds=window)
            )

    # ==================== Blocking & Violations ====================

    def _track_violation(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str,
        limit: int,
        window: int,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Track rate limit violation"""
        try:
            # Increment violation counter in Redis
            violation_key = f"violations:{identifier_type}:{identifier}"
            violation_count = self.redis.incr(violation_key)

            # Set expiry (violations reset after 1 hour)
            if violation_count == 1:
                self.redis.expire(violation_key, 3600)

            # Check if should block (3 violations in 1 hour)
            if violation_count >= 3:
                self._block_identifier(identifier, identifier_type, duration=1800)  # 30 minute block

            # Store violation in database
            if self.db:
                query = text("""
                    INSERT INTO rate_limit_violations (
                        identifier, identifier_type, endpoint,
                        violation_count, request_count, limit_threshold,
                        window_duration, user_agent, ip_address, blocked
                    )
                    VALUES (
                        :identifier, :identifier_type, :endpoint,
                        :violation_count, :request_count, :limit,
                        :window, :user_agent, :ip_address, :blocked
                    )
                """)

                self.db.execute(query, {
                    'identifier': identifier,
                    'identifier_type': identifier_type,
                    'endpoint': endpoint,
                    'violation_count': violation_count,
                    'request_count': limit + 1,  # Exceeded by at least 1
                    'limit': limit,
                    'window': window,
                    'user_agent': user_agent,
                    'ip_address': ip_address,
                    'blocked': violation_count >= 3
                })
                self.db.commit()

                logger.warning(
                    f"Rate limit violation: {identifier_type}={identifier}, "
                    f"endpoint={endpoint}, count={violation_count}"
                )

        except Exception as e:
            if self.db:
                self.db.rollback()
            logger.error(f"Failed to track violation: {str(e)}")

    def _block_identifier(
        self,
        identifier: str,
        identifier_type: str,
        duration: int
    ):
        """Temporarily block an identifier"""
        try:
            block_key = f"blocked:{identifier_type}:{identifier}"
            blocked_until = datetime.now() + timedelta(seconds=duration)

            # Store block in Redis
            self.redis.set(
                block_key,
                blocked_until.isoformat(),
                ttl=duration,
                serialize="string"
            )

            # Update database
            if self.db:
                query = text("""
                    UPDATE rate_limits
                    SET is_blocked = TRUE, blocked_until = :blocked_until
                    WHERE identifier = :identifier AND identifier_type = :identifier_type
                """)

                self.db.execute(query, {
                    'identifier': identifier,
                    'identifier_type': identifier_type,
                    'blocked_until': blocked_until
                })
                self.db.commit()

            logger.warning(
                f"Blocked {identifier_type}={identifier} until {blocked_until.isoformat()}"
            )

        except Exception as e:
            if self.db:
                self.db.rollback()
            logger.error(f"Failed to block identifier: {str(e)}")

    def _is_blocked(self, identifier: str, identifier_type: str) -> bool:
        """Check if identifier is currently blocked"""
        try:
            block_key = f"blocked:{identifier_type}:{identifier}"
            blocked_until_str = self.redis.get(block_key, deserialize="string")

            if blocked_until_str:
                blocked_until = datetime.fromisoformat(blocked_until_str)
                return datetime.now() < blocked_until

            return False

        except Exception as e:
            logger.error(f"Failed to check block status: {str(e)}")
            return False

    def _get_block_info(self, identifier: str, identifier_type: str) -> Dict[str, Any]:
        """Get block information"""
        block_key = f"blocked:{identifier_type}:{identifier}"
        blocked_until_str = self.redis.get(block_key, deserialize="string")

        if blocked_until_str:
            blocked_until = datetime.fromisoformat(blocked_until_str)
            return {
                'blocked': True,
                'blocked_until': blocked_until,
                'seconds_remaining': int((blocked_until - datetime.now()).total_seconds())
            }

        return {'blocked': False}

    def unblock_identifier(self, identifier: str, identifier_type: str) -> bool:
        """Manually unblock an identifier"""
        try:
            block_key = f"blocked:{identifier_type}:{identifier}"
            self.redis.delete(block_key)

            if self.db:
                query = text("""
                    UPDATE rate_limits
                    SET is_blocked = FALSE, blocked_until = NULL
                    WHERE identifier = :identifier AND identifier_type = :identifier_type
                """)

                self.db.execute(query, {
                    'identifier': identifier,
                    'identifier_type': identifier_type
                })
                self.db.commit()

            logger.info(f"Unblocked {identifier_type}={identifier}")
            return True

        except Exception as e:
            if self.db:
                self.db.rollback()
            logger.error(f"Failed to unblock identifier: {str(e)}")
            return False

    # ==================== Whitelist Management ====================

    def add_to_whitelist(self, identifier: str):
        """Add identifier to whitelist (exempt from rate limiting)"""
        self._whitelist.add(identifier)
        logger.info(f"Added {identifier} to rate limit whitelist")

    def remove_from_whitelist(self, identifier: str):
        """Remove identifier from whitelist"""
        self._whitelist.discard(identifier)
        logger.info(f"Removed {identifier} from rate limit whitelist")

    def is_whitelisted(self, identifier: str) -> bool:
        """Check if identifier is whitelisted"""
        return identifier in self._whitelist

    # ==================== Helper Methods ====================

    def _make_key(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str,
        strategy: str
    ) -> str:
        """Generate rate limit key"""
        return f"ratelimit:{strategy}:{identifier_type}:{identifier}:{endpoint}"

    def _get_endpoint_limits(self, endpoint: str) -> Tuple[int, int]:
        """Get rate limit configuration for endpoint"""
        # Extract endpoint category from path
        # Auth endpoints get strict limits to prevent brute force attacks
        if '/auth/login' in endpoint or '/auth/register' in endpoint:
            return self.default_limits['auth']
        elif '/search' in endpoint:
            return self.default_limits['search']
        elif '/ai/' in endpoint:
            return self.default_limits['ai']
        elif '/upload' in endpoint:
            return self.default_limits['upload']
        elif '/export' in endpoint:
            return self.default_limits['export']
        else:
            return self.default_limits['api']

    def _update_rate_limit_db(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str
    ):
        """Update rate limit tracking in database"""
        if not self.db:
            return

        try:
            query = text("""
                INSERT INTO rate_limits (
                    identifier, identifier_type, endpoint,
                    request_count, window_start, window_end
                )
                VALUES (
                    :identifier, :identifier_type, :endpoint,
                    1, NOW(), NOW() + INTERVAL '1 minute'
                )
                ON CONFLICT (identifier, identifier_type, endpoint)
                DO UPDATE SET
                    request_count = rate_limits.request_count + 1,
                    updated_at = NOW()
            """)

            self.db.execute(query, {
                'identifier': identifier,
                'identifier_type': identifier_type,
                'endpoint': endpoint
            })
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update rate limit DB: {str(e)}")

    # ==================== Analytics ====================

    def get_rate_limit_statistics(
        self,
        identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get rate limit statistics"""
        if not self.db:
            return {}

        try:
            if identifier:
                # Stats for specific identifier
                query = text("""
                    SELECT
                        COUNT(*) as total_violations,
                        COUNT(DISTINCT endpoint) as affected_endpoints,
                        MAX(created_at) as last_violation,
                        SUM(CASE WHEN blocked = TRUE THEN 1 ELSE 0 END) as block_count
                    FROM rate_limit_violations
                    WHERE identifier = :identifier
                """)

                result = self.db.execute(query, {'identifier': identifier})
            else:
                # Global stats
                query = text("""
                    SELECT
                        COUNT(*) as total_violations,
                        COUNT(DISTINCT identifier) as unique_violators,
                        COUNT(DISTINCT endpoint) as affected_endpoints,
                        SUM(CASE WHEN blocked = TRUE THEN 1 ELSE 0 END) as total_blocks
                    FROM rate_limit_violations
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                """)

                result = self.db.execute(query)

            row = result.fetchone()

            return {
                'total_violations': row[0] or 0,
                'unique_violators' if not identifier else 'affected_endpoints': row[1] or 0,
                'affected_endpoints' if not identifier else 'last_violation': row[2],
                'total_blocks' if not identifier else 'block_count': row[3] or 0
            }

        except Exception as e:
            logger.error(f"Failed to get rate limit statistics: {str(e)}")
            return {}
