"""
Tests for PerformanceCacheService
Tests multi-layer caching, statistics tracking, and cache patterns
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.services.performance_cache_service import PerformanceCacheService, cached


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock(spec=Session)
    db.execute = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def cache_service(mock_db):
    """Cache service instance with mock database"""
    return PerformanceCacheService(mock_db)


class TestPerformanceCacheService:
    """Test suite for PerformanceCacheService"""

    def test_initialization(self, mock_db):
        """Test service initialization"""
        service = PerformanceCacheService(mock_db)
        assert service.db == mock_db
        assert isinstance(service._memory_cache, dict)
        assert service._max_memory_items == 1000

    @patch('backend.services.performance_cache_service.redis_manager')
    def test_get_from_cache_hit(self, mock_redis, cache_service):
        """Test successful cache retrieval"""
        mock_redis.get.return_value = {'data': 'test_value'}

        result = cache_service.get('test_key', cache_type='api')

        assert result == {'data': 'test_value'}
        mock_redis.get.assert_called_once()

    @patch('backend.services.performance_cache_service.redis_manager')
    def test_get_from_cache_miss(self, mock_redis, cache_service):
        """Test cache miss"""
        mock_redis.get.return_value = None

        result = cache_service.get('nonexistent_key', cache_type='api')

        assert result is None

    @patch('backend.services.performance_cache_service.redis_manager')
    def test_set_in_cache(self, mock_redis, cache_service):
        """Test setting value in cache"""
        mock_redis.set.return_value = True

        success = cache_service.set(
            'test_key',
            {'data': 'value'},
            ttl=300,
            cache_type='api'
        )

        assert success is True
        mock_redis.set.assert_called_once()

    def test_memory_cache_operations(self, cache_service):
        """Test memory cache get/set operations"""
        # Store in memory
        cache_service._store_in_memory('mem_key', 'mem_value', ttl=60)

        # Retrieve from memory
        value = cache_service._get_from_memory('mem_key')
        assert value == 'mem_value'

        # Test expiration
        cache_service._store_in_memory('expired_key', 'value', ttl=0)
        import time
        time.sleep(0.1)
        expired_value = cache_service._get_from_memory('expired_key')
        assert expired_value is None

    def test_memory_cache_eviction(self, cache_service):
        """Test memory cache eviction when full"""
        cache_service._max_memory_items = 3

        # Fill cache
        for i in range(5):
            cache_service._store_in_memory(f'key_{i}', f'value_{i}', ttl=60)

        # Should only have max_memory_items
        assert len(cache_service._memory_cache) == 3

    @patch('backend.services.performance_cache_service.redis_manager')
    def test_get_or_compute(self, mock_redis, cache_service):
        """Test get_or_compute pattern"""
        # Cache miss, should compute
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        compute_called = False

        def compute_fn():
            nonlocal compute_called
            compute_called = True
            return 'computed_value'

        result = cache_service.get_or_compute(
            'compute_key',
            compute_fn,
            ttl=300,
            cache_type='query'
        )

        assert result == 'computed_value'
        assert compute_called is True

    @patch('backend.services.performance_cache_service.redis_manager')
    def test_batch_get(self, mock_redis, cache_service):
        """Test batch get operations"""
        mock_redis.get.side_effect = [
            'value1',
            None,
            'value3'
        ]

        results = cache_service.get_many(['key1', 'key2', 'key3'])

        assert 'key1' in results
        assert 'key2' not in results
        assert 'key3' in results

    @patch('backend.services.performance_cache_service.redis_manager')
    def test_batch_set(self, mock_redis, cache_service):
        """Test batch set operations"""
        mock_redis.set.return_value = True

        items = {
            'key1': ('value1', 300),
            'key2': ('value2', 600)
        }

        results = cache_service.set_many(items)

        assert results['key1'] is True
        assert results['key2'] is True

    @patch('backend.services.performance_cache_service.redis_manager')
    def test_invalidate_pattern(self, mock_redis, cache_service):
        """Test pattern-based cache invalidation"""
        mock_redis.delete_pattern.return_value = 5

        deleted_count = cache_service.invalidate_pattern('user:*')

        assert deleted_count == 5
        mock_redis.delete_pattern.assert_called_once_with('user:*')

    def test_cache_statistics(self, cache_service, mock_db):
        """Test cache statistics retrieval"""
        with patch('backend.services.performance_cache_service.redis_manager') as mock_redis:
            mock_redis.health_check.return_value = True
            mock_redis.info.return_value = {
                'used_memory_human': '100MB',
                'connected_clients': 5
            }
            mock_redis.dbsize.return_value = 1000

            mock_result = Mock()
            mock_result.fetchall.return_value = [
                ('api', 100, 80, 20, 80.0, 5000)
            ]
            mock_db.execute.return_value = mock_result

            stats = cache_service.get_cache_statistics()

            assert 'redis' in stats
            assert 'memory' in stats
            assert 'database' in stats

    def test_cleanup_expired(self, cache_service, mock_db):
        """Test cleanup of expired cache entries"""
        mock_result = Mock()
        mock_result.rowcount = 25
        mock_db.execute.return_value = mock_result

        deleted_count = cache_service.cleanup_expired()

        assert deleted_count == 25
        mock_db.commit.assert_called_once()

    def test_top_cached_keys(self, cache_service, mock_db):
        """Test retrieval of top cached keys"""
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ('key1', 'api', 100, 10, 90.0, 5000, datetime.now()),
            ('key2', 'query', 80, 20, 80.0, 3000, datetime.now())
        ]
        mock_db.execute.return_value = mock_result

        top_keys = cache_service.get_top_cached_keys(limit=10)

        assert len(top_keys) == 2
        assert top_keys[0]['key'] == 'key1'
        assert top_keys[0]['hit_count'] == 100


class TestCachedDecorator:
    """Test suite for @cached decorator"""

    @patch('backend.services.performance_cache_service.PerformanceCacheService')
    def test_cached_decorator_cache_hit(self, mock_cache_class):
        """Test decorator with cache hit"""
        mock_cache = Mock()
        mock_cache.get.return_value = 'cached_result'
        mock_cache_class.return_value = mock_cache

        @cached(ttl=300, cache_type="test")
        def expensive_function(arg):
            return f"computed_{arg}"

        result = expensive_function('test')

        assert result == 'cached_result'
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_not_called()

    @patch('backend.services.performance_cache_service.PerformanceCacheService')
    def test_cached_decorator_cache_miss(self, mock_cache_class):
        """Test decorator with cache miss"""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_cache_class.return_value = mock_cache

        @cached(ttl=300, cache_type="test")
        def expensive_function(arg):
            return f"computed_{arg}"

        result = expensive_function('test')

        assert result == 'computed_test'
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()

    @patch('backend.services.performance_cache_service.PerformanceCacheService')
    def test_cached_decorator_with_multiple_args(self, mock_cache_class):
        """Test decorator with multiple arguments"""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_cache_class.return_value = mock_cache

        @cached(ttl=300, cache_type="test", key_prefix="my_func")
        def expensive_function(arg1, arg2, kwarg1=None):
            return f"{arg1}_{arg2}_{kwarg1}"

        result = expensive_function('a', 'b', kwarg1='c')

        assert result == 'a_b_c'
        # Verify cache key includes all arguments
        call_args = mock_cache.get.call_args[0]
        cache_key = call_args[0]
        assert 'my_func' in cache_key
        assert 'a' in cache_key
        assert 'b' in cache_key
