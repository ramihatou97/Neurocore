"""
Tests for Task Checkpoint Service
Tests checkpoint tracking, step completion, and recovery
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from backend.services.task_checkpoint import TaskCheckpoint


@pytest.fixture
def mock_redis():
    """Mock Redis manager"""
    with patch('backend.services.task_checkpoint.redis_manager') as mock:
        mock_client = Mock()
        mock_client.hget.return_value = None
        mock_client.hset.return_value = 1
        mock_client.hgetall.return_value = {}
        mock_client.delete.return_value = 1
        mock_client.hlen.return_value = 0
        mock_client.get.return_value = None
        mock_client.set.return_value = True
        mock_client.exists.return_value = 0
        mock_client.expire.return_value = True
        mock.get_client.return_value = mock_client
        yield mock


@pytest.fixture
def checkpoint(mock_redis):
    """Task checkpoint instance with mock Redis"""
    return TaskCheckpoint(
        task_id="test-task-123",
        task_type="pdf_processing"
    )


class TestTaskCheckpointInitialization:
    """Test suite for TaskCheckpoint initialization"""

    def test_initialization(self, checkpoint):
        """Test checkpoint initialization"""
        assert checkpoint.task_id == "test-task-123"
        assert checkpoint.task_type == "pdf_processing"
        assert checkpoint.ttl > 0

    @patch('backend.services.task_checkpoint.settings')
    def test_initialization_uses_settings_ttl(self, mock_settings, mock_redis):
        """Test that initialization uses settings TTL by default"""
        mock_settings.TASK_CHECKPOINT_TTL = 123456
        checkpoint = TaskCheckpoint(
            task_id="test-task",
            task_type="test_type"
        )
        assert checkpoint.ttl == 123456

    def test_initialization_custom_ttl(self, mock_redis):
        """Test initialization with custom TTL"""
        checkpoint = TaskCheckpoint(
            task_id="test-task",
            task_type="test_type",
            ttl=7200
        )
        assert checkpoint.ttl == 7200


class TestStepCompletion:
    """Test suite for step completion tracking"""

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_is_step_complete_false_when_not_complete(self, mock_redis):
        """Test is_step_complete returns False when step not complete"""
        mock_redis.hget.return_value = None

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.is_step_complete("step1")

        assert result is False

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_is_step_complete_true_when_complete(self, mock_redis):
        """Test is_step_complete returns True when step is complete"""
        step_data = json.dumps({"status": "complete"})
        mock_redis.hget.return_value = step_data.encode()

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.is_step_complete("step1")

        assert result is True

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_is_step_complete_false_when_failed(self, mock_redis):
        """Test is_step_complete returns False when step failed"""
        step_data = json.dumps({"status": "failed"})
        mock_redis.hget.return_value = step_data.encode()

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.is_step_complete("step1")

        assert result is False

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_mark_step_complete(self, mock_redis):
        """Test marking a step as complete"""
        checkpoint = TaskCheckpoint("task-1", "test")
        checkpoint.mark_step_complete("step1", metadata={"pages": 100})

        # Verify hset was called
        assert mock_redis.hset.called

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_mark_step_complete_with_metadata(self, mock_redis):
        """Test marking step complete stores metadata"""
        checkpoint = TaskCheckpoint("task-1", "test")

        metadata = {"pages": 100, "cost": 0.05}
        checkpoint.mark_step_complete("step1", metadata=metadata)

        # Verify hset was called with step name
        call_args = mock_redis.hset.call_args
        assert "step1" in str(call_args)

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_mark_step_failed(self, mock_redis):
        """Test marking a step as failed"""
        checkpoint = TaskCheckpoint("task-1", "test")
        checkpoint.mark_step_failed("step1", error="Test error", retry_count=2)

        # Verify hset was called
        assert mock_redis.hset.called


class TestStepMetadata:
    """Test suite for step metadata management"""

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_get_step_metadata_when_exists(self, mock_redis):
        """Test getting metadata for existing step"""
        metadata = {"pages": 100, "cost": 0.05}
        step_data = json.dumps({
            "status": "complete",
            "metadata": metadata
        })
        mock_redis.hget.return_value = step_data.encode()

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.get_step_metadata("step1")

        assert result == metadata

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_get_step_metadata_when_not_exists(self, mock_redis):
        """Test getting metadata for non-existent step"""
        mock_redis.hget.return_value = None

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.get_step_metadata("step1")

        assert result is None

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_get_all_steps(self, mock_redis):
        """Test getting all steps"""
        step1_data = json.dumps({"status": "complete", "metadata": {}})
        step2_data = json.dumps({"status": "complete", "metadata": {}})

        mock_redis.hgetall.return_value = {
            b"step1": step1_data.encode(),
            b"step2": step2_data.encode()
        }

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.get_all_steps()

        assert len(result) == 2
        assert "step1" in result
        assert "step2" in result

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_get_completed_steps(self, mock_redis):
        """Test getting only completed steps"""
        mock_redis.hgetall.return_value = {
            b"step1": json.dumps({"status": "complete"}).encode(),
            b"step2": json.dumps({"status": "failed"}).encode(),
            b"step3": json.dumps({"status": "complete"}).encode()
        }

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.get_completed_steps()

        assert len(result) == 2
        assert "step1" in result
        assert "step3" in result
        assert "step2" not in result

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_get_failed_steps(self, mock_redis):
        """Test getting only failed steps"""
        mock_redis.hgetall.return_value = {
            b"step1": json.dumps({"status": "complete"}).encode(),
            b"step2": json.dumps({"status": "failed"}).encode(),
            b"step3": json.dumps({"status": "failed"}).encode()
        }

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.get_failed_steps()

        assert len(result) == 2
        assert "step2" in result
        assert "step3" in result
        assert "step1" not in result


class TestCheckpointManagement:
    """Test suite for checkpoint lifecycle management"""

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_clear_checkpoint(self, mock_redis):
        """Test clearing checkpoint data"""
        checkpoint = TaskCheckpoint("task-1", "test")
        checkpoint.clear_checkpoint()

        # Verify delete was called (twice: checkpoint key and metadata key)
        assert mock_redis.delete.called

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_set_metadata(self, mock_redis):
        """Test setting overall task metadata"""
        checkpoint = TaskCheckpoint("task-1", "test")
        metadata = {"total_pages": 200, "estimated_cost": 1.50}

        checkpoint.set_metadata(metadata)

        # Verify set was called
        assert mock_redis.set.called

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_get_metadata(self, mock_redis):
        """Test getting overall task metadata"""
        metadata = {"total_pages": 200, "estimated_cost": 1.50}
        mock_redis.get.return_value = json.dumps(metadata).encode()

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.get_metadata()

        assert result == metadata

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_get_metadata_when_not_exists(self, mock_redis):
        """Test getting metadata when none exists"""
        mock_redis.get.return_value = None

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.get_metadata()

        assert result is None

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_has_checkpoint_true(self, mock_redis):
        """Test has_checkpoint returns True when checkpoint exists"""
        mock_redis.exists.return_value = 1

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.has_checkpoint()

        assert result is True

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_has_checkpoint_false(self, mock_redis):
        """Test has_checkpoint returns False when no checkpoint"""
        mock_redis.exists.return_value = 0

        checkpoint = TaskCheckpoint("task-1", "test")
        result = checkpoint.has_checkpoint()

        assert result is False


class TestProgressCalculation:
    """Test suite for progress tracking"""

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_get_progress_percent_zero(self, mock_redis):
        """Test progress calculation with no completed steps"""
        mock_redis.hgetall.return_value = {}

        checkpoint = TaskCheckpoint("task-1", "test")
        progress = checkpoint.get_progress_percent(total_steps=10)

        assert progress == 0

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_get_progress_percent_partial(self, mock_redis):
        """Test progress calculation with partial completion"""
        mock_redis.hgetall.return_value = {
            b"step1": json.dumps({"status": "complete"}).encode(),
            b"step2": json.dumps({"status": "complete"}).encode(),
            b"step3": json.dumps({"status": "complete"}).encode()
        }

        checkpoint = TaskCheckpoint("task-1", "test")
        progress = checkpoint.get_progress_percent(total_steps=10)

        assert progress == 30  # 3/10 = 30%

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_get_progress_percent_complete(self, mock_redis):
        """Test progress calculation with all steps complete"""
        mock_redis.hgetall.return_value = {
            b"step1": json.dumps({"status": "complete"}).encode(),
            b"step2": json.dumps({"status": "complete"}).encode(),
            b"step3": json.dumps({"status": "complete"}).encode()
        }

        checkpoint = TaskCheckpoint("task-1", "test")
        progress = checkpoint.get_progress_percent(total_steps=3)

        assert progress == 100

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_get_progress_percent_zero_total(self, mock_redis):
        """Test progress calculation with zero total steps"""
        checkpoint = TaskCheckpoint("task-1", "test")
        progress = checkpoint.get_progress_percent(total_steps=0)

        assert progress == 0


class TestCheckpointRecovery:
    """Integration tests for checkpoint recovery scenarios"""

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_recovery_skips_completed_steps(self, mock_redis):
        """Test that recovery can skip completed steps"""
        # Simulate step1 and step2 already complete
        def mock_hget(key, field):
            if field == "step1":
                return json.dumps({"status": "complete"}).encode()
            elif field == "step2":
                return json.dumps({"status": "complete"}).encode()
            return None

        mock_redis.hget.side_effect = mock_hget

        checkpoint = TaskCheckpoint("task-1", "pdf_processing")

        # Check which steps need to be done
        step1_complete = checkpoint.is_step_complete("step1")
        step2_complete = checkpoint.is_step_complete("step2")
        step3_complete = checkpoint.is_step_complete("step3")

        assert step1_complete is True
        assert step2_complete is True
        assert step3_complete is False

    @patch('backend.services.task_checkpoint.redis_manager')
    def test_recovery_with_partial_failure(self, mock_redis):
        """Test recovery after partial task failure"""
        # Step1 complete, step2 failed, step3 not started
        def mock_hget(key, field):
            if field == "step1":
                return json.dumps({"status": "complete", "metadata": {"pages": 50}}).encode()
            elif field == "step2":
                return json.dumps({"status": "failed", "error": "API timeout"}).encode()
            return None

        mock_redis.hget.side_effect = mock_hget

        checkpoint = TaskCheckpoint("task-1", "pdf_processing")

        # Recovery should skip step1, retry step2
        step1_complete = checkpoint.is_step_complete("step1")
        step2_complete = checkpoint.is_step_complete("step2")

        assert step1_complete is True  # Skip this
        assert step2_complete is False  # Retry this

        # Can retrieve metadata from completed step
        step1_metadata = checkpoint.get_step_metadata("step1")
        assert step1_metadata["pages"] == 50
