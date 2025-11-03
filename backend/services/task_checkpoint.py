"""
Task Checkpoint Service - Progress tracking for Celery tasks
Prevents wasteful restarts by saving completion status to Redis

Benefits:
- Skip completed steps on retry (saves API costs)
- Resume from failure point
- Track progress across retries
- Automatic cleanup after success

Example:
    checkpoint = TaskCheckpoint(pdf_id="abc-123", task_type="pdf_processing")

    if not checkpoint.is_step_complete("text_extraction"):
        # Do text extraction
        checkpoint.mark_step_complete("text_extraction", metadata={"pages": 100})

    # On retry, text extraction will be skipped
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json

from backend.config.redis import redis_manager
from backend.config.settings import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class TaskCheckpoint:
    """
    Checkpoint manager for long-running Celery tasks

    Features:
    - Per-task progress tracking
    - Step completion status
    - Metadata storage per step
    - Automatic expiration (configurable, default 7 days)
    - Cleanup on success

    Use Cases:
    - PDF processing (text → images → embeddings)
    - Chapter generation (research → synthesis → formatting)
    - Batch operations
    """

    def __init__(
        self,
        task_id: str,
        task_type: str,
        ttl: int = None  # Use settings default if not specified
    ):
        """
        Initialize checkpoint for a task

        Args:
            task_id: Unique task identifier (e.g., PDF ID, Chapter ID)
            task_type: Task type (e.g., "pdf_processing", "chapter_generation")
            ttl: Time-to-live for checkpoint data in seconds (defaults to settings.TASK_CHECKPOINT_TTL)
        """
        self.task_id = task_id
        self.task_type = task_type
        self.ttl = ttl if ttl is not None else settings.TASK_CHECKPOINT_TTL
        self.redis = redis_manager

        # Redis keys
        self._checkpoint_key = f"checkpoint:{task_type}:{task_id}"
        self._metadata_key = f"checkpoint_meta:{task_type}:{task_id}"

    def is_step_complete(self, step_name: str) -> bool:
        """
        Check if a step is already complete

        Args:
            step_name: Name of the step to check

        Returns:
            bool: True if step is complete, False otherwise
        """
        try:
            step_data = self.redis.hget(self._checkpoint_key, step_name)
            if step_data:
                data = json.loads(step_data)
                return data.get("status") == "complete"
            return False

        except Exception as e:
            logger.error(f"Failed to check checkpoint status: {str(e)}")
            # Fail open - assume not complete
            return False

    def mark_step_complete(
        self,
        step_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Mark a step as complete with optional metadata

        Args:
            step_name: Name of the step
            metadata: Optional metadata about the step (e.g., {"pages": 100, "cost": 0.05})
        """
        try:
            step_data = {
                "status": "complete",
                "completed_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }

            self.redis.hset(
                self._checkpoint_key,
                step_name,
                json.dumps(step_data)
            )

            # Set expiration on first step
            if self.redis.hlen(self._checkpoint_key) == 1:
                self.redis.expire(self._checkpoint_key, self.ttl)

            logger.info(
                f"Checkpoint saved: {self.task_type}:{self.task_id} "
                f"step={step_name}"
            )

        except Exception as e:
            logger.error(
                f"Failed to save checkpoint: {str(e)}",
                exc_info=True
            )

    def mark_step_failed(
        self,
        step_name: str,
        error: str,
        retry_count: int = 0
    ):
        """
        Mark a step as failed

        Args:
            step_name: Name of the step
            error: Error message
            retry_count: Number of retries attempted
        """
        try:
            step_data = {
                "status": "failed",
                "failed_at": datetime.utcnow().isoformat(),
                "error": error,
                "retry_count": retry_count
            }

            self.redis.hset(
                self._checkpoint_key,
                step_name,
                json.dumps(step_data)
            )

            logger.warning(
                f"Checkpoint failed: {self.task_type}:{self.task_id} "
                f"step={step_name}, error={error[:100]}"
            )

        except Exception as e:
            logger.error(f"Failed to save failure checkpoint: {str(e)}")

    def get_step_metadata(self, step_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific step

        Args:
            step_name: Name of the step

        Returns:
            Metadata dict or None if step not found
        """
        try:
            step_data = self.redis.hget(self._checkpoint_key, step_name)
            if step_data:
                data = json.loads(step_data)
                return data.get("metadata", {})
            return None

        except Exception as e:
            logger.error(f"Failed to get step metadata: {str(e)}")
            return None

    def get_all_steps(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all steps

        Returns:
            Dict mapping step_name to step data
        """
        try:
            all_data = self.redis.hgetall(self._checkpoint_key)
            result = {}

            for step_name, step_data in all_data.items():
                try:
                    # Redis returns bytes, decode them
                    if isinstance(step_name, bytes):
                        step_name = step_name.decode('utf-8')
                    if isinstance(step_data, bytes):
                        step_data = step_data.decode('utf-8')

                    result[step_name] = json.loads(step_data)
                except Exception as parse_error:
                    logger.error(f"Failed to parse step data: {parse_error}")
                    continue

            return result

        except Exception as e:
            logger.error(f"Failed to get all steps: {str(e)}")
            return {}

    def get_completed_steps(self) -> List[str]:
        """
        Get list of completed step names

        Returns:
            List of step names that are complete
        """
        all_steps = self.get_all_steps()
        return [
            step_name
            for step_name, step_data in all_steps.items()
            if step_data.get("status") == "complete"
        ]

    def get_failed_steps(self) -> List[str]:
        """
        Get list of failed step names

        Returns:
            List of step names that failed
        """
        all_steps = self.get_all_steps()
        return [
            step_name
            for step_name, step_data in all_steps.items()
            if step_data.get("status") == "failed"
        ]

    def clear_checkpoint(self):
        """
        Clear all checkpoint data for this task

        Use after successful completion or when retrying from scratch
        """
        try:
            self.redis.delete(self._checkpoint_key)
            self.redis.delete(self._metadata_key)

            logger.info(
                f"Checkpoint cleared: {self.task_type}:{self.task_id}"
            )

        except Exception as e:
            logger.error(f"Failed to clear checkpoint: {str(e)}")

    def set_metadata(self, metadata: Dict[str, Any]):
        """
        Set overall task metadata

        Args:
            metadata: Metadata about the entire task
        """
        try:
            self.redis.set(
                self._metadata_key,
                json.dumps(metadata),
                ex=self.ttl
            )

        except Exception as e:
            logger.error(f"Failed to set metadata: {str(e)}")

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """
        Get overall task metadata

        Returns:
            Metadata dict or None
        """
        try:
            metadata = self.redis.get(self._metadata_key)
            if metadata:
                if isinstance(metadata, bytes):
                    metadata = metadata.decode('utf-8')
                return json.loads(metadata)
            return None

        except Exception as e:
            logger.error(f"Failed to get metadata: {str(e)}")
            return None

    def get_progress_percent(self, total_steps: int) -> int:
        """
        Calculate completion percentage

        Args:
            total_steps: Total number of steps in task

        Returns:
            Percentage complete (0-100)
        """
        completed = len(self.get_completed_steps())
        return int((completed / total_steps) * 100) if total_steps > 0 else 0

    def has_checkpoint(self) -> bool:
        """
        Check if any checkpoint data exists

        Returns:
            bool: True if checkpoint exists
        """
        return self.redis.exists(self._checkpoint_key) > 0
