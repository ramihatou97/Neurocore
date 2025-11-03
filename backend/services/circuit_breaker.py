"""
Circuit Breaker Pattern for AI Provider Resilience
Prevents cascading failures when AI APIs are down or rate-limited

Implementation Strategy:
- Track failures per provider in Redis (persistent across restarts)
- After N consecutive failures, open circuit (stop trying)
- After timeout, half-open circuit (allow test request)
- If test succeeds, close circuit (resume normal operation)
- Automatic fallback to alternative providers

Benefits:
- Fail fast instead of accumulating delays
- Preserve AI API rate limits
- Automatic recovery
- Transparent fallback
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import json

from backend.config.redis import redis_manager
from backend.config.settings import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    # Number of consecutive failures before opening circuit
    failure_threshold: int = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD

    # Time window for counting failures (seconds)
    failure_window: int = settings.CIRCUIT_BREAKER_FAILURE_WINDOW

    # Time to wait before attempting recovery (seconds)
    recovery_timeout: int = settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT

    # Time to wait after recovery before closing circuit (seconds)
    half_open_timeout: int = 30

    # Success threshold in half-open state before closing
    half_open_success_threshold: int = settings.CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS


@dataclass
class CircuitBreakerStats:
    """Statistics for a circuit breaker"""
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: Optional[float]
    last_success_time: Optional[float]
    opened_at: Optional[float]
    half_opened_at: Optional[float]
    closed_at: Optional[float]
    total_failures: int
    total_successes: int


class CircuitBreaker:
    """
    Circuit breaker implementation for AI providers

    Features:
    - Per-provider circuit state tracking
    - Redis-backed persistence
    - Configurable thresholds and timeouts
    - Comprehensive statistics
    - Automatic recovery testing

    Usage:
        breaker = CircuitBreaker(provider="claude")

        if breaker.is_call_allowed():
            try:
                result = await call_ai_provider()
                breaker.record_success()
            except Exception as e:
                breaker.record_failure()
                raise
    """

    def __init__(
        self,
        provider: str,
        config: Optional[CircuitBreakerConfig] = None,
        redis_client = None
    ):
        """
        Initialize circuit breaker for a specific provider

        Args:
            provider: Provider name (claude, gpt4, gemini)
            config: Circuit breaker configuration
            redis_client: Redis client (uses global if not provided)
        """
        self.provider = provider
        self.config = config or CircuitBreakerConfig()
        self.redis = redis_client or redis_manager

        # Redis keys for state tracking
        self._state_key = f"circuit_breaker:{provider}:state"
        self._stats_key = f"circuit_breaker:{provider}:stats"
        self._failure_window_key = f"circuit_breaker:{provider}:failures"

        # Initialize state if not exists
        self._ensure_initialized()

    def _ensure_initialized(self):
        """Ensure circuit breaker state exists in Redis"""
        if not self.redis.exists(self._stats_key):
            initial_stats = CircuitBreakerStats(
                state=CircuitState.CLOSED,
                failure_count=0,
                success_count=0,
                last_failure_time=None,
                last_success_time=None,
                opened_at=None,
                half_opened_at=None,
                closed_at=time.time(),
                total_failures=0,
                total_successes=0
            )
            self._save_stats(initial_stats)
            logger.info(f"Circuit breaker initialized for provider: {self.provider}")

    def _get_stats(self) -> CircuitBreakerStats:
        """Retrieve current circuit breaker statistics"""
        stats_dict = self.redis.get(self._stats_key, deserialize="json", default=None)
        if stats_dict:
            return CircuitBreakerStats(**stats_dict)
        else:
            # Fallback to initialized state
            initial_stats = CircuitBreakerStats(
                state=CircuitState.CLOSED,
                failure_count=0,
                success_count=0,
                last_failure_time=None,
                last_success_time=None,
                opened_at=None,
                half_opened_at=None,
                closed_at=time.time(),
                total_failures=0,
                total_successes=0
            )
            self._save_stats(initial_stats)
            return initial_stats

    def _save_stats(self, stats: CircuitBreakerStats):
        """Save circuit breaker statistics to Redis"""
        self.redis.set(
            self._stats_key,
            asdict(stats),  # RedisManager handles serialization
            ttl=86400,  # Expire after 24 hours of inactivity
            serialize="json"
        )

    def _get_state(self) -> CircuitState:
        """Get current circuit state"""
        stats = self._get_stats()
        return CircuitState(stats.state)

    def _set_state(self, new_state: CircuitState):
        """Update circuit state"""
        stats = self._get_stats()
        old_state = stats.state
        stats.state = new_state

        # Update state-specific timestamps
        now = time.time()
        if new_state == CircuitState.OPEN:
            stats.opened_at = now
        elif new_state == CircuitState.HALF_OPEN:
            stats.half_opened_at = now
        elif new_state == CircuitState.CLOSED:
            stats.closed_at = now

        self._save_stats(stats)

        if old_state != new_state:
            logger.warning(
                f"Circuit breaker state changed for {self.provider}: "
                f"{old_state} → {new_state}"
            )

    def is_call_allowed(self) -> bool:
        """
        Check if calls are allowed in current circuit state

        Returns:
            bool: True if call should proceed, False if circuit is open
        """
        stats = self._get_stats()
        state = CircuitState(stats.state)
        now = time.time()

        # CLOSED state: All calls allowed
        if state == CircuitState.CLOSED:
            return True

        # OPEN state: Check if recovery timeout elapsed
        elif state == CircuitState.OPEN:
            if stats.opened_at and (now - stats.opened_at) >= self.config.recovery_timeout:
                # Transition to HALF_OPEN for recovery testing
                self._set_state(CircuitState.HALF_OPEN)
                logger.info(f"Circuit breaker for {self.provider} entering HALF_OPEN state (recovery test)")
                return True
            else:
                # Still open, reject call
                remaining = self.config.recovery_timeout - (now - stats.opened_at) if stats.opened_at else 0
                logger.warning(
                    f"Circuit breaker OPEN for {self.provider}, "
                    f"rejecting call (retry in {remaining:.0f}s)"
                )
                return False

        # HALF_OPEN state: Allow limited calls for testing
        elif state == CircuitState.HALF_OPEN:
            # Allow test calls (caller should be cautious)
            return True

        return False

    def record_success(self):
        """Record successful AI provider call"""
        stats = self._get_stats()
        state = CircuitState(stats.state)
        now = time.time()

        stats.success_count += 1
        stats.total_successes += 1
        stats.last_success_time = now

        # State transitions on success
        if state == CircuitState.HALF_OPEN:
            # Successful test in half-open state
            if stats.success_count >= self.config.half_open_success_threshold:
                # Enough successes, close circuit
                stats.failure_count = 0
                stats.success_count = 0
                self._set_state(CircuitState.CLOSED)
                logger.info(f"Circuit breaker CLOSED for {self.provider} (recovery successful)")

                # Clear failure window
                self.redis.delete(self._failure_window_key)

                # Reload stats to get updated state from _set_state
                stats = self._get_stats()
            else:
                # Still testing
                logger.debug(
                    f"Circuit breaker HALF_OPEN test success for {self.provider} "
                    f"({stats.success_count}/{self.config.half_open_success_threshold})"
                )

        elif state == CircuitState.CLOSED:
            # Normal success, reset failure count
            stats.failure_count = 0

        self._save_stats(stats)

    def record_failure(self, error: Optional[Exception] = None):
        """
        Record failed AI provider call

        Args:
            error: Exception that caused the failure (for logging)
        """
        stats = self._get_stats()
        state = CircuitState(stats.state)
        now = time.time()

        stats.failure_count += 1
        stats.total_failures += 1
        stats.last_failure_time = now

        # Add to failure window (for rate calculation)
        self.redis.zadd(
            self._failure_window_key,
            {str(now): now}
        )

        # Remove old failures outside window
        cutoff = now - self.config.failure_window
        self.redis.zremrangebyscore(self._failure_window_key, '-inf', cutoff)

        # Count recent failures
        recent_failures = self.redis.zcount(self._failure_window_key, cutoff, '+inf')

        logger.warning(
            f"Circuit breaker failure for {self.provider}: "
            f"{recent_failures} failures in {self.config.failure_window}s window "
            f"(threshold: {self.config.failure_threshold})"
            f"{' - ' + str(error) if error else ''}"
        )

        # State transitions on failure
        if state == CircuitState.CLOSED:
            # Check if failure threshold exceeded
            if recent_failures >= self.config.failure_threshold:
                # Too many failures, open circuit
                self._set_state(CircuitState.OPEN)
                logger.error(
                    f"Circuit breaker OPENED for {self.provider} "
                    f"({recent_failures} failures exceeded threshold {self.config.failure_threshold})"
                )

                # Reload stats to get updated state from _set_state
                stats = self._get_stats()

        elif state == CircuitState.HALF_OPEN:
            # Failure during recovery test, reopen circuit
            stats.success_count = 0
            self._set_state(CircuitState.OPEN)
            logger.error(
                f"Circuit breaker reopened for {self.provider} "
                f"(recovery test failed)"
            )

            # Reload stats to get updated state from _set_state
            stats = self._get_stats()

        self._save_stats(stats)

    def force_open(self):
        """Manually open circuit (for maintenance/testing)"""
        self._set_state(CircuitState.OPEN)
        logger.warning(f"Circuit breaker manually OPENED for {self.provider}")

    def force_close(self):
        """Manually close circuit (for maintenance/testing)"""
        stats = self._get_stats()
        stats.failure_count = 0
        stats.success_count = 0
        self._save_stats(stats)
        self._set_state(CircuitState.CLOSED)
        self.redis.delete(self._failure_window_key)
        logger.info(f"Circuit breaker manually CLOSED for {self.provider}")

    def reset(self):
        """Reset circuit breaker to initial state"""
        self.force_close()
        logger.info(f"Circuit breaker RESET for {self.provider}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive circuit breaker statistics

        Returns:
            dict with state, counts, timestamps, and health metrics
        """
        # Check availability first (may trigger state transitions)
        is_available = self.is_call_allowed()

        # Get stats AFTER checking availability to get updated state
        stats = self._get_stats()
        now = time.time()

        # Calculate uptime
        if stats.total_successes + stats.total_failures > 0:
            success_rate = stats.total_successes / (stats.total_successes + stats.total_failures)
        else:
            success_rate = 1.0

        # Time since last state change
        state_duration = None
        if stats.state == CircuitState.CLOSED and stats.closed_at:
            state_duration = now - stats.closed_at
        elif stats.state == CircuitState.OPEN and stats.opened_at:
            state_duration = now - stats.opened_at
        elif stats.state == CircuitState.HALF_OPEN and stats.half_opened_at:
            state_duration = now - stats.half_opened_at

        return {
            'provider': self.provider,
            'state': stats.state,
            'is_available': is_available,
            'failure_count': stats.failure_count,
            'success_count': stats.success_count,
            'total_failures': stats.total_failures,
            'total_successes': stats.total_successes,
            'success_rate': round(success_rate, 3),
            'last_failure_time': datetime.fromtimestamp(stats.last_failure_time).isoformat() if stats.last_failure_time else None,
            'last_success_time': datetime.fromtimestamp(stats.last_success_time).isoformat() if stats.last_success_time else None,
            'state_duration_seconds': round(state_duration, 1) if state_duration else None,
            'config': asdict(self.config)
        }


class CircuitBreakerManager:
    """
    Centralized manager for all circuit breakers

    Maintains circuit breakers for all AI providers and provides
    unified interface for health checking and statistics
    """

    def __init__(self, redis_client=None):
        """Initialize circuit breaker manager"""
        self.redis = redis_client or redis_manager
        self.breakers: Dict[str, CircuitBreaker] = {}

        # Default config for all providers
        self.default_config = CircuitBreakerConfig(
            failure_threshold=5,
            failure_window=60,
            recovery_timeout=60,
            half_open_timeout=30,
            half_open_success_threshold=2
        )

    def get_breaker(self, provider: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """
        Get or create circuit breaker for provider

        Args:
            provider: Provider name
            config: Optional custom configuration

        Returns:
            CircuitBreaker instance
        """
        if provider not in self.breakers:
            self.breakers[provider] = CircuitBreaker(
                provider=provider,
                config=config or self.default_config,
                redis_client=self.redis
            )
        return self.breakers[provider]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {
            provider: breaker.get_stats()
            for provider, breaker in self.breakers.items()
        }

    def get_available_providers(self) -> list[str]:
        """Get list of providers with closed/half-open circuits"""
        available = []
        for provider, breaker in self.breakers.items():
            if breaker.is_call_allowed():
                available.append(provider)
        return available

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()
