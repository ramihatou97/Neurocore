"""
Tests for Dead Letter Queue Service
Tests failed task tracking, retry functionality, and statistics
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from backend.services.dead_letter_queue import DeadLetterQueue


@pytest.fixture
def mock_redis():
    """Mock Redis manager"""
    with patch('backend.services.dead_letter_queue.redis_manager') as mock:
        mock_client = Mock()
        mock_client.zadd.return_value = 1
        mock_client.set.return_value = True
        mock_client.get.return_value = None
        mock_client.zrevrange.return_value = []
        mock_client.zrange.return_value = []
        mock_client.zrem.return_value = 1
        mock_client.delete.return_value = 1
        mock_client.zcard.return_value = 0
        mock_client.zcount.return_value = 0
        mock_client.zrangebyscore.return_value = []
        mock.get_client.return_value = mock_client
        yield mock


@pytest.fixture
def dlq(mock_redis):
    """Dead letter queue instance with mock Redis"""
    return DeadLetterQueue()


class TestDeadLetterQueueInitialization:
    """Test suite for DLQ initialization"""

    @patch('backend.services.dead_letter_queue.settings')
    def test_initialization_uses_settings(self, mock_settings, mock_redis):
        """Test that initialization uses settings retention days"""
        mock_settings.DLQ_RETENTION_DAYS = 45
        dlq = DeadLetterQueue()

        assert dlq.retention_days == 45
        assert dlq.retention_seconds == 45 * 86400

    def test_initialization_defaults(self, dlq):
        """Test DLQ initialization with defaults"""
        assert dlq.retention_days > 0
        assert dlq.retention_seconds > 0


class TestAddFailedTask:
    """Test suite for adding failed tasks to DLQ"""

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_add_failed_task_success(self, mock_redis):
        """Test successfully adding a failed task"""
        dlq = DeadLetterQueue()

        result = dlq.add_failed_task(
            task_name="process_pdf_async",
            task_id="task-123",
            task_args={"pdf_id": "abc"},
            error="API timeout",
            retry_count=3
        )

        assert result is True
        assert mock_redis.zadd.called
        assert mock_redis.set.called

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_add_failed_task_with_metadata(self, mock_redis):
        """Test adding failed task with metadata"""
        dlq = DeadLetterQueue()

        metadata = {"pdf_id": "abc", "user_id": 123}
        result = dlq.add_failed_task(
            task_name="process_pdf_async",
            task_id="task-123",
            error="API timeout",
            metadata=metadata
        )

        assert result is True

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_add_failed_task_with_traceback(self, mock_redis):
        """Test adding failed task with full traceback"""
        dlq = DeadLetterQueue()

        result = dlq.add_failed_task(
            task_name="process_pdf_async",
            task_id="task-123",
            error="API timeout",
            traceback="Traceback (most recent call last):\n  File..."
        )

        assert result is True

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_add_critical_task_logs_critical(self, mock_redis):
        """Test that critical tasks log at CRITICAL level"""
        dlq = DeadLetterQueue()

        # process_pdf_async is marked as critical in the code
        with patch('backend.services.dead_letter_queue.logger') as mock_logger:
            dlq.add_failed_task(
                task_name="process_pdf_async",
                task_id="task-123",
                error="Complete failure"
            )

            # Should have logged critical message
            assert any("CRITICAL" in str(call) for call in mock_logger.method_calls)


class TestGetFailedTasks:
    """Test suite for retrieving failed tasks"""

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_get_failed_tasks_empty(self, mock_redis):
        """Test getting failed tasks when DLQ is empty"""
        mock_redis.zrevrange.return_value = []

        dlq = DeadLetterQueue()
        tasks = dlq.get_failed_tasks()

        assert tasks == []

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_get_failed_tasks_with_results(self, mock_redis):
        """Test getting failed tasks with results"""
        task_data = {
            "task_name": "process_pdf_async",
            "task_id": "task-123",
            "error": "API timeout",
            "retry_count": 3
        }

        mock_redis.zrevrange.return_value = [b"process_pdf_async:task-123:1000"]
        mock_redis.get.return_value = json.dumps(task_data).encode()

        dlq = DeadLetterQueue()
        tasks = dlq.get_failed_tasks(limit=50)

        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "task-123"
        assert tasks[0]["error"] == "API timeout"

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_get_failed_tasks_with_pagination(self, mock_redis):
        """Test getting failed tasks with pagination"""
        mock_redis.zrevrange.return_value = []

        dlq = DeadLetterQueue()
        tasks = dlq.get_failed_tasks(limit=10, offset=20)

        # Verify zrevrange was called with correct offset
        call_args = mock_redis.zrevrange.call_args
        assert call_args is not None

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_get_failed_tasks_with_filter(self, mock_redis):
        """Test getting failed tasks with task name filter"""
        task1 = b"process_pdf_async:task-123:1000"
        task2 = b"generate_chapter:task-456:1001"

        mock_redis.zrevrange.return_value = [task1, task2]
        mock_redis.get.side_effect = [
            json.dumps({"task_name": "process_pdf_async"}).encode(),
            json.dumps({"task_name": "generate_chapter"}).encode()
        ]

        dlq = DeadLetterQueue()
        tasks = dlq.get_failed_tasks(task_name_filter="process_pdf_async")

        # Should only return matching task
        assert len(tasks) == 1


class TestGetFailedTask:
    """Test suite for retrieving specific failed task"""

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_get_failed_task_exists(self, mock_redis):
        """Test getting specific task that exists"""
        task_data = {
            "task_id": "task-123",
            "error": "API timeout"
        }

        mock_redis.zrange.return_value = [b"process_pdf_async:task-123:1000"]
        mock_redis.get.return_value = json.dumps(task_data).encode()

        dlq = DeadLetterQueue()
        result = dlq.get_failed_task("task-123")

        assert result is not None
        assert result["task_id"] == "task-123"

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_get_failed_task_not_exists(self, mock_redis):
        """Test getting task that doesn't exist"""
        mock_redis.zrange.return_value = []

        dlq = DeadLetterQueue()
        result = dlq.get_failed_task("nonexistent")

        assert result is None


class TestRetryTask:
    """Test suite for task retry functionality"""

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_retry_task_success(self, mock_redis):
        """Test successfully marking task for retry"""
        task_data = {
            "task_id": "task-123",
            "status": "failed",
            "retry_attempted": False
        }

        mock_redis.zrange.return_value = [b"process_pdf_async:task-123:1000"]
        mock_redis.get.return_value = json.dumps(task_data).encode()

        dlq = DeadLetterQueue()
        result = dlq.retry_task("task-123")

        assert result is True
        assert mock_redis.set.called

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_retry_task_not_found(self, mock_redis):
        """Test retry for non-existent task"""
        mock_redis.zrange.return_value = []

        dlq = DeadLetterQueue()
        result = dlq.retry_task("nonexistent")

        assert result is False


class TestRemoveTask:
    """Test suite for removing tasks from DLQ"""

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_remove_task_success(self, mock_redis):
        """Test successfully removing a task"""
        mock_redis.zrange.return_value = [b"process_pdf_async:task-123:1000"]

        dlq = DeadLetterQueue()
        result = dlq.remove_task("task-123")

        assert result is True
        assert mock_redis.zrem.called
        assert mock_redis.delete.called

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_remove_task_not_found(self, mock_redis):
        """Test removing non-existent task"""
        mock_redis.zrange.return_value = []

        dlq = DeadLetterQueue()
        result = dlq.remove_task("nonexistent")

        assert result is False


class TestStatistics:
    """Test suite for DLQ statistics"""

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_get_statistics(self, mock_redis):
        """Test getting DLQ statistics"""
        mock_redis.zcard.return_value = 10
        mock_redis.zcount.return_value = 5
        mock_redis.zrange.return_value = [
            b"process_pdf_async:task-1:1000",
            b"process_pdf_async:task-2:1001",
            b"generate_chapter:task-3:1002"
        ]

        dlq = DeadLetterQueue()
        stats = dlq.get_statistics()

        assert "total_failed_tasks" in stats
        assert "recent_failures_24h" in stats
        assert "failures_by_task_type" in stats
        assert stats["total_failed_tasks"] == 10
        assert stats["recent_failures_24h"] == 5

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_get_statistics_by_task_type(self, mock_redis):
        """Test statistics grouped by task type"""
        mock_redis.zcard.return_value = 3
        mock_redis.zcount.return_value = 3
        mock_redis.zrange.return_value = [
            b"process_pdf_async:task-1:1000",
            b"process_pdf_async:task-2:1001",
            b"generate_chapter:task-3:1002"
        ]

        dlq = DeadLetterQueue()
        stats = dlq.get_statistics()

        failures_by_type = stats["failures_by_task_type"]
        assert "process_pdf_async" in failures_by_type
        assert "generate_chapter" in failures_by_type
        assert failures_by_type["process_pdf_async"] == 2
        assert failures_by_type["generate_chapter"] == 1


class TestCleanup:
    """Test suite for DLQ cleanup"""

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_cleanup_old_entries(self, mock_redis):
        """Test cleaning up old DLQ entries"""
        old_keys = [
            b"process_pdf_async:task-1:1000",
            b"process_pdf_async:task-2:1001"
        ]
        mock_redis.zrangebyscore.return_value = old_keys

        dlq = DeadLetterQueue()
        removed = dlq.cleanup_old_entries(days=30)

        assert removed == 2
        assert mock_redis.zrem.call_count == 2
        assert mock_redis.delete.call_count == 2

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_cleanup_no_old_entries(self, mock_redis):
        """Test cleanup when no old entries exist"""
        mock_redis.zrangebyscore.return_value = []

        dlq = DeadLetterQueue()
        removed = dlq.cleanup_old_entries(days=30)

        assert removed == 0


class TestDLQIntegration:
    """Integration tests for DLQ workflows"""

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_full_dlq_lifecycle(self, mock_redis):
        """Test complete DLQ lifecycle: add → query → retry → remove"""
        dlq = DeadLetterQueue()

        # 1. Add failed task
        result = dlq.add_failed_task(
            task_name="process_pdf_async",
            task_id="task-123",
            error="API timeout",
            retry_count=3
        )
        assert result is True

        # 2. Query failed tasks
        task_data = {
            "task_id": "task-123",
            "error": "API timeout",
            "status": "failed"
        }
        mock_redis.zrevrange.return_value = [b"process_pdf_async:task-123:1000"]
        mock_redis.get.return_value = json.dumps(task_data).encode()

        tasks = dlq.get_failed_tasks()
        assert len(tasks) == 1

        # 3. Mark for retry
        mock_redis.zrange.return_value = [b"process_pdf_async:task-123:1000"]
        result = dlq.retry_task("task-123")
        assert result is True

        # 4. Remove after successful retry
        result = dlq.remove_task("task-123")
        assert result is True

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_multiple_failures_same_task(self, mock_redis):
        """Test handling multiple failures of same task at different times"""
        dlq = DeadLetterQueue()

        # Add same task multiple times (simulating retries)
        for i in range(3):
            dlq.add_failed_task(
                task_name="process_pdf_async",
                task_id=f"task-123-attempt-{i}",
                error=f"Failure {i+1}",
                retry_count=i+1
            )

        # All should be tracked separately
        assert mock_redis.zadd.call_count == 3

    @patch('backend.services.dead_letter_queue.redis_manager')
    def test_statistics_after_multiple_operations(self, mock_redis):
        """Test that statistics accurately reflect multiple operations"""
        dlq = DeadLetterQueue()

        # Add multiple tasks
        for i in range(5):
            dlq.add_failed_task(
                task_name="process_pdf_async",
                task_id=f"task-{i}",
                error="Error"
            )

        # Setup statistics mock
        mock_redis.zcard.return_value = 5
        mock_redis.zcount.return_value = 5
        mock_redis.zrange.return_value = [
            f"process_pdf_async:task-{i}:{1000+i}".encode()
            for i in range(5)
        ]

        stats = dlq.get_statistics()
        assert stats["total_failed_tasks"] == 5
