"""
Tests for RateLimitService
Tests rate limiting strategies, violation tracking, and blocking
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.services.rate_limit_service import (
    RateLimitService,
    RateLimitStrategy,
    RateLimitResult
)


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock(spec=Session)
    db.execute = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def rate_limit_service(mock_db):
    """Rate limit service instance with mock database"""
    return RateLimitService(mock_db)


class TestRateLimitService:
    """Test suite for RateLimitService"""

    def test_initialization(self, mock_db):
        """Test service initialization"""
        service = RateLimitService(mock_db)
        assert service.db == mock_db
        assert isinstance(service.default_limits, dict)
        assert 'api' in service.default_limits

    def test_whitelist_exemption(self, rate_limit_service):
        """Test that whitelisted identifiers bypass rate limiting"""
        rate_limit_service.add_to_whitelist('whitelisted_user')

        result = rate_limit_service.check_rate_limit(
            identifier='whitelisted_user',
            identifier_type='user',
            endpoint='/api/test'
        )

        assert result.allowed is True
        assert result.limit == 999999

    @patch('backend.services.rate_limit_service.redis_manager')
    def test_fixed_window_within_limit(self, mock_redis, rate_limit_service):
        """Test fixed window strategy within limit"""
        mock_redis.get.return_value = "5"  # 5 requests so far
        mock_redis.incr.return_value = 6
        mock_redis.ttl.return_value = 30

        result = rate_limit_service._fixed_window_check(
            identifier='user123',
            identifier_type='user',
            endpoint='/api/test',
            limit=10,
            window=60
        )

        assert result.allowed is True
        assert result.remaining == 4

    @patch('backend.services.rate_limit_service.redis_manager')
    def test_fixed_window_exceeded(self, mock_redis, rate_limit_service):
        """Test fixed window strategy when limit exceeded"""
        mock_redis.get.return_value = "10"  # At limit
        mock_redis.ttl.return_value = 30

        result = rate_limit_service._fixed_window_check(
            identifier='user123',
            identifier_type='user',
            endpoint='/api/test',
            limit=10,
            window=60
        )

        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None

    @patch('backend.services.rate_limit_service.redis_manager')
    def test_sliding_window_within_limit(self, mock_redis, rate_limit_service):
        """Test sliding window strategy within limit"""
        mock_client = Mock()
        mock_client.zremrangebyscore.return_value = 0
        mock_client.zcard.return_value = 5  # 5 requests in window
        mock_client.zadd.return_value = 1
        mock_redis.get_client.return_value = mock_client
        mock_redis.expire = Mock()

        result = rate_limit_service._sliding_window_check(
            identifier='user123',
            identifier_type='user',
            endpoint='/api/test',
            limit=10,
            window=60
        )

        assert result.allowed is True
        assert result.remaining == 4

    @patch('backend.services.rate_limit_service.redis_manager')
    def test_sliding_window_exceeded(self, mock_redis, rate_limit_service):
        """Test sliding window strategy when limit exceeded"""
        mock_client = Mock()
        mock_client.zremrangebyscore.return_value = 0
        mock_client.zcard.return_value = 10  # At limit
        mock_client.zrange.return_value = [(b'request', 1234567890.0)]
        mock_redis.get_client.return_value = mock_client

        result = rate_limit_service._sliding_window_check(
            identifier='user123',
            identifier_type='user',
            endpoint='/api/test',
            limit=10,
            window=60
        )

        assert result.allowed is False
        assert result.remaining == 0

    @patch('backend.services.rate_limit_service.redis_manager')
    def test_token_bucket_with_tokens(self, mock_redis, rate_limit_service):
        """Test token bucket strategy with available tokens"""
        mock_redis.hgetall.return_value = {
            'tokens': 5.0,
            'last_refill': 1234567890.0
        }
        mock_redis.hset = Mock()
        mock_redis.expire = Mock()

        result = rate_limit_service._token_bucket_check(
            identifier='user123',
            identifier_type='user',
            endpoint='/api/test',
            limit=10,
            window=60
        )

        assert result.allowed is True
        assert result.remaining >= 0

    @patch('backend.services.rate_limit_service.redis_manager')
    def test_token_bucket_no_tokens(self, mock_redis, rate_limit_service):
        """Test token bucket strategy without tokens"""
        import time
        current_time = time.time()

        mock_redis.hgetall.return_value = {
            'tokens': 0.0,
            'last_refill': current_time
        }

        result = rate_limit_service._token_bucket_check(
            identifier='user123',
            identifier_type='user',
            endpoint='/api/test',
            limit=10,
            window=60
        )

        assert result.allowed is False
        assert result.retry_after is not None

    def test_violation_tracking(self, rate_limit_service, mock_db):
        """Test violation tracking"""
        with patch('backend.services.rate_limit_service.redis_manager') as mock_redis:
            mock_redis.incr.return_value = 1

            rate_limit_service._track_violation(
                identifier='user123',
                identifier_type='user',
                endpoint='/api/test',
                limit=10,
                window=60
            )

            mock_db.execute.assert_called_once()
            mock_db.commit.assert_called_once()

    def test_blocking_after_violations(self, rate_limit_service, mock_db):
        """Test automatic blocking after multiple violations"""
        with patch('backend.services.rate_limit_service.redis_manager') as mock_redis:
            mock_redis.incr.return_value = 3  # 3rd violation
            mock_redis.set = Mock()

            rate_limit_service._track_violation(
                identifier='abuser123',
                identifier_type='user',
                endpoint='/api/test',
                limit=10,
                window=60
            )

            # Should call block method
            mock_redis.set.assert_called_once()

    @patch('backend.services.rate_limit_service.redis_manager')
    def test_is_blocked(self, mock_redis, rate_limit_service):
        """Test checking if identifier is blocked"""
        future_time = datetime.now() + timedelta(hours=1)
        mock_redis.get.return_value = future_time.isoformat()

        is_blocked = rate_limit_service._is_blocked('user123', 'user')

        assert is_blocked is True

    @patch('backend.services.rate_limit_service.redis_manager')
    def test_is_not_blocked(self, mock_redis, rate_limit_service):
        """Test checking if identifier is not blocked"""
        past_time = datetime.now() - timedelta(hours=1)
        mock_redis.get.return_value = past_time.isoformat()

        is_blocked = rate_limit_service._is_blocked('user123', 'user')

        assert is_blocked is False

    def test_unblock_identifier(self, rate_limit_service, mock_db):
        """Test manually unblocking an identifier"""
        with patch('backend.services.rate_limit_service.redis_manager') as mock_redis:
            mock_redis.delete = Mock()

            success = rate_limit_service.unblock_identifier('user123', 'user')

            assert success is True
            mock_redis.delete.assert_called_once()
            mock_db.commit.assert_called_once()

    def test_whitelist_management(self, rate_limit_service):
        """Test whitelist add/remove operations"""
        identifier = 'special_user'

        # Add to whitelist
        rate_limit_service.add_to_whitelist(identifier)
        assert rate_limit_service.is_whitelisted(identifier)

        # Remove from whitelist
        rate_limit_service.remove_from_whitelist(identifier)
        assert not rate_limit_service.is_whitelisted(identifier)

    def test_endpoint_limits_classification(self, rate_limit_service):
        """Test endpoint limit classification"""
        # Search endpoint
        limit, window = rate_limit_service._get_endpoint_limits('/api/v1/search')
        assert limit == 30  # Search has lower limit

        # AI endpoint
        limit, window = rate_limit_service._get_endpoint_limits('/api/v1/ai/qa/ask')
        assert limit == 10  # AI has lowest limit

        # Regular API
        limit, window = rate_limit_service._get_endpoint_limits('/api/v1/chapters')
        assert limit == 100  # Default API limit

    def test_record_request(self, rate_limit_service, mock_db):
        """Test recording successful request"""
        success = rate_limit_service.record_request(
            identifier='user123',
            identifier_type='user',
            endpoint='/api/test'
        )

        assert success is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_get_rate_limit_statistics(self, rate_limit_service, mock_db):
        """Test getting rate limit statistics"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [100, 5, 3, 2]
        mock_db.execute.return_value = mock_result

        stats = rate_limit_service.get_rate_limit_statistics()

        assert 'total_violations' in stats
        assert stats['total_violations'] == 100

    def test_check_rate_limit_strategies(self, rate_limit_service):
        """Test that different strategies can be specified"""
        with patch('backend.services.rate_limit_service.redis_manager'):
            # Test each strategy
            for strategy in [
                RateLimitStrategy.FIXED_WINDOW,
                RateLimitStrategy.SLIDING_WINDOW,
                RateLimitStrategy.TOKEN_BUCKET
            ]:
                result = rate_limit_service.check_rate_limit(
                    identifier='user123',
                    identifier_type='user',
                    endpoint='/api/test',
                    limit=10,
                    window=60,
                    strategy=strategy
                )
                assert isinstance(result, RateLimitResult)


class TestRateLimitResult:
    """Test RateLimitResult class"""

    def test_rate_limit_result_creation(self):
        """Test creating RateLimitResult"""
        reset_at = datetime.now() + timedelta(seconds=60)
        result = RateLimitResult(
            allowed=True,
            limit=100,
            remaining=95,
            reset_at=reset_at,
            retry_after=None
        )

        assert result.allowed is True
        assert result.limit == 100
        assert result.remaining == 95
        assert result.reset_at == reset_at

    def test_rate_limit_result_to_dict(self):
        """Test converting RateLimitResult to dict"""
        reset_at = datetime.now() + timedelta(seconds=60)
        result = RateLimitResult(
            allowed=False,
            limit=100,
            remaining=0,
            reset_at=reset_at,
            retry_after=60
        )

        data = result.to_dict()

        assert data['allowed'] is False
        assert data['limit'] == 100
        assert data['remaining'] == 0
        assert 'reset_at' in data
        assert data['retry_after'] == 60
