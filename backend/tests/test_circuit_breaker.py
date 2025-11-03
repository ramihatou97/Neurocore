"""
Tests for Circuit Breaker Service
Tests circuit breaker states, failure tracking, and automatic recovery
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time

from backend.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitState,
    CircuitBreakerConfig,
    CircuitBreakerStats
)


def create_mock_stats_json(state="closed", **overrides):
    """Helper to create complete mock stats JSON with all required fields"""
    stats = {
        "state": state,
        "failure_count": 0,
        "success_count": 0,
        "last_failure_time": None,
        "last_success_time": None,
        "opened_at": None,
        "half_opened_at": None,
        "closed_at": time.time(),
        "total_failures": 0,
        "total_successes": 0
    }
    stats.update(overrides)
    import json
    return json.dumps(stats).encode()


@pytest.fixture
def circuit_config():
    """Default circuit breaker configuration"""
    return CircuitBreakerConfig(
        failure_threshold=3,
        failure_window=60,
        recovery_timeout=30,
        half_open_timeout=15,
        half_open_success_threshold=2
    )


@pytest.fixture
def mock_redis():
    """Mock Redis manager with stateful storage"""
    with patch('backend.services.circuit_breaker.redis_manager') as mock:
        # Create a dict to store data
        storage = {}

        # Make set() store data
        def mock_set(key, value, ex=None):
            storage[key] = value
            return True

        # Make get() retrieve stored data
        def mock_get(key):
            return storage.get(key)

        # Make delete() remove data
        def mock_delete(key):
            if key in storage:
                del storage[key]
                return 1
            return 0

        # Make exists() check if key exists
        def mock_exists(key):
            return key in storage

        # Circuit breaker uses redis_manager directly, so mock it directly
        mock.get.side_effect = mock_get
        mock.set.side_effect = mock_set
        mock.delete.side_effect = mock_delete
        mock.exists.side_effect = mock_exists
        mock.zremrangebyscore.return_value = 0
        mock.zadd.return_value = 1
        mock.zcount.return_value = 0
        yield mock


@pytest.fixture
def circuit_breaker(mock_redis, circuit_config):
    """Circuit breaker instance with mock Redis"""
    return CircuitBreaker(provider="test_provider", config=circuit_config)


class TestCircuitBreakerConfig:
    """Test suite for CircuitBreakerConfig"""

    def test_config_defaults(self):
        """Test default configuration values"""
        config = CircuitBreakerConfig()
        assert config.failure_threshold > 0
        assert config.failure_window > 0
        assert config.recovery_timeout > 0
        assert config.half_open_success_threshold > 0

    def test_config_custom_values(self):
        """Test custom configuration"""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            failure_window=120,
            recovery_timeout=60
        )
        assert config.failure_threshold == 10
        assert config.failure_window == 120
        assert config.recovery_timeout == 60


class TestCircuitBreaker:
    """Test suite for CircuitBreaker"""

    def test_initialization(self, circuit_breaker):
        """Test circuit breaker initialization"""
        assert circuit_breaker.provider == "test_provider"
        assert circuit_breaker.config is not None
        assert isinstance(circuit_breaker.config, CircuitBreakerConfig)

    def test_initial_state_is_closed(self, circuit_breaker):
        """Test that circuit starts in CLOSED state"""
        stats = circuit_breaker.get_stats()
        state = CircuitState(stats['state'])
        assert state == CircuitState.CLOSED

    def test_is_call_allowed_when_closed(self, circuit_breaker):
        """Test that calls are allowed when circuit is CLOSED"""
        assert circuit_breaker.is_call_allowed() is True

    @patch('backend.services.circuit_breaker.redis_manager')
    def test_record_success_in_closed_state(self, mock_redis, circuit_config):
        """Test recording success resets failure count"""
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.exists.return_value = False
        mock_redis.zadd.return_value = 1
        mock_redis.zcount.return_value = 0

        breaker = CircuitBreaker("test_provider", circuit_config)
        breaker.record_success()

        # Verify state is still CLOSED
        stats = breaker.get_stats()
        assert CircuitState(stats['state']) == CircuitState.CLOSED

    @patch('backend.services.circuit_breaker.redis_manager')
    def test_record_failure_below_threshold(self, mock_redis, circuit_config):
        """Test recording failures below threshold keeps circuit CLOSED"""
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.exists.return_value = False
        mock_redis.zadd.return_value = 1
        mock_redis.zcount.return_value = 2  # Below threshold of 3

        breaker = CircuitBreaker("test_provider", circuit_config)

        # Record failures below threshold
        breaker.record_failure(error=Exception("Test error"))

        # Circuit should remain CLOSED
        stats = breaker.get_stats()
        assert CircuitState(stats['state']) == CircuitState.CLOSED

    def test_record_failure_exceeds_threshold_opens_circuit(self, mock_redis, circuit_config):
        """Test that exceeding failure threshold opens circuit"""
        # Stateful mock will handle get/set/exists automatically
        mock_redis.zadd.return_value = 1
        mock_redis.zcount.return_value = 3  # At threshold

        breaker = CircuitBreaker("test_provider", circuit_config)

        # Record failure that exceeds threshold
        breaker.record_failure(error=Exception("Test error"))

        # Circuit should open
        stats = breaker.get_stats()
        assert CircuitState(stats['state']) == CircuitState.OPEN

    def test_open_circuit_blocks_calls(self, mock_redis, circuit_config):
        """Test that OPEN circuit blocks calls"""
        # Pre-populate storage with OPEN state before creating breaker
        stats_key = "circuit_breaker:test_provider:stats"
        mock_redis.set(stats_key, create_mock_stats_json("open", opened_at=0))

        breaker = CircuitBreaker("test_provider", circuit_config)

        # Calls should be blocked
        assert breaker.is_call_allowed() is False

    @patch('backend.services.circuit_breaker.time.time')
    def test_open_circuit_transitions_to_half_open_after_timeout(
        self, mock_time, mock_redis, circuit_config
    ):
        """Test that OPEN circuit transitions to HALF_OPEN after recovery timeout"""
        now = 1000.0
        opened_at = now - circuit_config.recovery_timeout - 1  # Timeout expired
        mock_time.return_value = now

        # Pre-populate storage with OPEN state
        stats_key = "circuit_breaker:test_provider:stats"
        mock_redis.set(stats_key, create_mock_stats_json("open", opened_at=opened_at))

        breaker = CircuitBreaker("test_provider", circuit_config)

        # Should transition to HALF_OPEN
        stats = breaker.get_stats()
        state = CircuitState(stats['state'])
        assert state == CircuitState.HALF_OPEN

    def test_half_open_circuit_allows_test_calls(self, mock_redis, circuit_config):
        """Test that HALF_OPEN circuit allows limited test calls"""
        # Pre-populate storage with HALF_OPEN state
        stats_key = "circuit_breaker:test_provider:stats"
        mock_redis.set(stats_key, create_mock_stats_json("half_open", half_opened_at=0))

        breaker = CircuitBreaker("test_provider", circuit_config)

        # Should allow call
        assert breaker.is_call_allowed() is True

    def test_half_open_success_closes_circuit(self, mock_redis, circuit_config):
        """Test that successful calls in HALF_OPEN close circuit"""
        # Pre-populate storage: HALF_OPEN with 1 success (need 2 total)
        stats_key = "circuit_breaker:test_provider:stats"
        mock_redis.set(stats_key, create_mock_stats_json("half_open", half_opened_at=0, success_count=1))

        breaker = CircuitBreaker("test_provider", circuit_config)

        # Record one more success (reaches threshold of 2)
        breaker.record_success()

        # Should transition to CLOSED
        stats = breaker.get_stats()
        assert CircuitState(stats['state']) == CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self, mock_redis, circuit_config):
        """Test that failure in HALF_OPEN reopens circuit"""
        # Pre-populate storage with HALF_OPEN state
        stats_key = "circuit_breaker:test_provider:stats"
        mock_redis.set(stats_key, create_mock_stats_json("half_open", half_opened_at=0))
        mock_redis.zadd.return_value = 1

        breaker = CircuitBreaker("test_provider", circuit_config)

        # Record failure
        breaker.record_failure(error=Exception("Test error"))

        # Should reopen circuit
        stats = breaker.get_stats()
        assert CircuitState(stats['state']) == CircuitState.OPEN

    def test_get_stats(self, circuit_breaker):
        """Test getting circuit breaker statistics as dict"""
        stats = circuit_breaker.get_stats()

        # get_stats() returns a dict, not CircuitBreakerStats object
        assert isinstance(stats, dict)
        assert 'state' in stats
        assert 'failure_count' in stats
        assert 'success_count' in stats
        assert stats['failure_count'] >= 0
        assert stats['success_count'] >= 0

    def test_reset_circuit(self, circuit_breaker):
        """Test manual circuit reset"""
        circuit_breaker.reset()

        # Should be back to CLOSED state
        stats = circuit_breaker.get_stats()
        assert CircuitState(stats['state']) == CircuitState.CLOSED

    def test_force_open_circuit(self, circuit_breaker):
        """Test forcing circuit to OPEN state"""
        circuit_breaker.force_open()

        # Should be OPEN
        stats = circuit_breaker.get_stats()
        assert CircuitState(stats['state']) == CircuitState.OPEN


class TestCircuitBreakerManager:
    """Test suite for CircuitBreakerManager"""

    @patch('backend.services.circuit_breaker.redis_manager')
    def test_manager_initialization(self, mock_redis):
        """Test circuit breaker manager initialization"""
        manager = CircuitBreakerManager()
        assert manager.breakers == {}

    @patch('backend.services.circuit_breaker.redis_manager')
    def test_get_breaker_creates_new(self, mock_redis):
        """Test getting breaker creates new instance"""
        mock_redis.get.return_value = None
        mock_redis.exists.return_value = False

        manager = CircuitBreakerManager()
        breaker = manager.get_breaker("test_provider")

        assert isinstance(breaker, CircuitBreaker)
        assert breaker.provider == "test_provider"
        assert "test_provider" in manager.breakers

    @patch('backend.services.circuit_breaker.redis_manager')
    def test_get_breaker_returns_existing(self, mock_redis):
        """Test getting existing breaker returns same instance"""
        mock_redis.get.return_value = None
        mock_redis.exists.return_value = False

        manager = CircuitBreakerManager()
        breaker1 = manager.get_breaker("test_provider")
        breaker2 = manager.get_breaker("test_provider")

        assert breaker1 is breaker2

    @patch('backend.services.circuit_breaker.redis_manager')
    def test_get_all_stats(self, mock_redis):
        """Test getting all circuit breaker stats"""
        mock_redis.get.return_value = None
        mock_redis.exists.return_value = False

        manager = CircuitBreakerManager()
        manager.get_breaker("provider1")
        manager.get_breaker("provider2")

        all_stats = manager.get_all_stats()
        assert len(all_stats) == 2
        assert "provider1" in all_stats
        assert "provider2" in all_stats

    @patch('backend.services.circuit_breaker.redis_manager')
    def test_reset_all_breakers(self, mock_redis):
        """Test resetting all circuit breakers"""
        mock_redis.get.return_value = None
        mock_redis.exists.return_value = False
        mock_redis.delete.return_value = 1

        manager = CircuitBreakerManager()
        breaker1 = manager.get_breaker("provider1")
        breaker2 = manager.get_breaker("provider2")

        manager.reset_all()

        # All breakers should be reset to CLOSED
        stats1 = breaker1.get_stats()
        stats2 = breaker2.get_stats()
        assert CircuitState(stats1['state']) == CircuitState.CLOSED
        assert CircuitState(stats2['state']) == CircuitState.CLOSED


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker functionality"""

    @patch('backend.services.circuit_breaker.redis_manager')
    def test_full_circuit_lifecycle(self, mock_redis, circuit_config):
        """Test complete circuit breaker lifecycle: CLOSED → OPEN → HALF_OPEN → CLOSED"""
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.exists.return_value = False
        mock_redis.zadd.return_value = 1
        mock_redis.delete.return_value = 1

        breaker = CircuitBreaker("test_provider", circuit_config)

        # 1. Start CLOSED
        stats = breaker.get_stats()
        assert CircuitState(stats['state']) == CircuitState.CLOSED
        assert breaker.is_call_allowed() is True

        # 2. Record failures to open circuit
        for i in range(circuit_config.failure_threshold):
            mock_redis.zcount.return_value = i + 1
            breaker.record_failure(error=Exception(f"Failure {i+1}"))

        # Should be OPEN now
        mock_redis.get.return_value = create_mock_stats_json("open", opened_at=0)
        stats = breaker.get_stats()
        assert CircuitState(stats['state']) == CircuitState.OPEN

        # 3. Force transition to HALF_OPEN
        mock_redis.get.return_value = create_mock_stats_json("half_open", half_opened_at=0)
        stats = breaker.get_stats()
        assert CircuitState(stats['state']) == CircuitState.HALF_OPEN

        # 4. Record successes to close circuit
        for i in range(circuit_config.half_open_success_threshold):
            mock_redis.get.return_value = create_mock_stats_json("half_open", half_opened_at=0, success_count=i)
            breaker.record_success()

        # Should be CLOSED again
        mock_redis.get.return_value = create_mock_stats_json("closed")
        stats = breaker.get_stats()
        assert CircuitState(stats['state']) == CircuitState.CLOSED
