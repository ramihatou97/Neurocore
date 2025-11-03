"""
Dead Letter Queue (DLQ) - Capture and manage permanently failed tasks
Prevents silent task failures and enables manual intervention

Benefits:
- Track all failed tasks after max retries
- Admin visibility into failures
- Manual retry capability
- Failure pattern analysis

Example:
    # Automatically called when task exhausts retries
    dlq = DeadLetterQueue()
    dlq.add_failed_task(
        task_name="process_pdf_async",
        task_id="abc-123",
        error="AI API timeout",
        metadata={"pdf_id": "xyz", "attempt": 3}
    )

    # Admin can review and retry
    failed_tasks = dlq.get_failed_tasks(limit=50)
    dlq.retry_task(task_id="abc-123")
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from backend.config.redis import redis_manager
from backend.config.settings import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class DeadLetterQueue:
    """
    Dead Letter Queue for permanently failed Celery tasks

    Features:
    - Store failed tasks with full context
    - Searchable by task type, error type, date range
    - Manual retry capability
    - Automatic cleanup of old entries (configurable, default 30 days)
    - Statistics and failure patterns

    Storage:
    - Redis sorted set for chronological ordering
    - Individual keys for task details
    """

    def __init__(self):
        """Initialize Dead Letter Queue"""
        self.redis = redis_manager

        # Redis keys
        self._dlq_queue_key = "dlq:failed_tasks"  # Sorted set
        self._dlq_data_key_prefix = "dlq:task:"  # Individual task data

        # Retention period (from settings)
        self.retention_days = settings.DLQ_RETENTION_DAYS
        self.retention_seconds = self.retention_days * 86400

    def add_failed_task(
        self,
        task_name: str,
        task_id: str,
        task_args: Optional[Dict] = None,
        error: str = "",
        traceback: Optional[str] = None,
        retry_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a permanently failed task to the dead letter queue

        Args:
            task_name: Celery task name
            task_id: Unique task identifier
            task_args: Task arguments
            error: Error message
            traceback: Full traceback (optional)
            retry_count: Number of retries attempted
            metadata: Additional context

        Returns:
            bool: True if added successfully
        """
        try:
            now = datetime.utcnow()
            timestamp = now.timestamp()

            # Prepare task data
            task_data = {
                "task_name": task_name,
                "task_id": task_id,
                "task_args": task_args or {},
                "error": error,
                "traceback": traceback,
                "retry_count": retry_count,
                "metadata": metadata or {},
                "failed_at": now.isoformat(),
                "timestamp": timestamp,
                "status": "failed",
                "retry_attempted": False
            }

            # Store in sorted set (for chronological queries)
            dlq_entry_key = f"{task_name}:{task_id}:{int(timestamp)}"
            self.redis.zadd(self._dlq_queue_key, {dlq_entry_key: timestamp})

            # Store detailed data
            data_key = f"{self._dlq_data_key_prefix}{dlq_entry_key}"
            self.redis.set(
                data_key,
                json.dumps(task_data),
                ex=self.retention_seconds
            )

            logger.error(
                f"Task added to DLQ: {task_name} (task_id={task_id}, "
                f"retries={retry_count}, error={error[:100]})"
            )

            # Emit alert if critical
            if self._is_critical_task(task_name):
                logger.critical(
                    f"CRITICAL TASK FAILED: {task_name} - Manual intervention required"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to add task to DLQ: {str(e)}", exc_info=True)
            return False

    def get_failed_tasks(
        self,
        limit: int = 50,
        offset: int = 0,
        task_name_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get failed tasks from DLQ

        Args:
            limit: Maximum number of tasks to return
            offset: Offset for pagination
            task_name_filter: Optional filter by task name

        Returns:
            List of failed task data
        """
        try:
            # Get task keys from sorted set (most recent first)
            task_keys = self.redis.zrevrange(
                self._dlq_queue_key,
                offset,
                offset + limit - 1
            )

            failed_tasks = []

            for key in task_keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')

                # Apply filter if specified
                if task_name_filter and not key.startswith(task_name_filter):
                    continue

                # Get task data
                data_key = f"{self._dlq_data_key_prefix}{key}"
                task_data = self.redis.get(data_key)

                if task_data:
                    if isinstance(task_data, bytes):
                        task_data = task_data.decode('utf-8')

                    try:
                        failed_tasks.append(json.loads(task_data))
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse DLQ task data: {e}")
                        continue

            return failed_tasks

        except Exception as e:
            logger.error(f"Failed to get failed tasks: {str(e)}", exc_info=True)
            return []

    def get_failed_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific failed task by ID

        Args:
            task_id: Task identifier

        Returns:
            Task data or None
        """
        try:
            # Search for task in sorted set
            all_keys = self.redis.zrange(self._dlq_queue_key, 0, -1)

            for key in all_keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')

                if task_id in key:
                    data_key = f"{self._dlq_data_key_prefix}{key}"
                    task_data = self.redis.get(data_key)

                    if task_data:
                        if isinstance(task_data, bytes):
                            task_data = task_data.decode('utf-8')
                        return json.loads(task_data)

            return None

        except Exception as e:
            logger.error(f"Failed to get failed task: {str(e)}", exc_info=True)
            return None

    def retry_task(self, task_id: str) -> bool:
        """
        Mark task for manual retry

        Args:
            task_id: Task identifier

        Returns:
            bool: True if marked successfully

        Note: Actual retry must be implemented in calling code
        """
        try:
            task_data = self.get_failed_task(task_id)

            if not task_data:
                logger.warning(f"Task not found in DLQ: {task_id}")
                return False

            # Update status
            task_data["retry_attempted"] = True
            task_data["retry_requested_at"] = datetime.utcnow().isoformat()
            task_data["status"] = "retry_pending"

            # Find and update task key
            all_keys = self.redis.zrange(self._dlq_queue_key, 0, -1)

            for key in all_keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')

                if task_id in key:
                    data_key = f"{self._dlq_data_key_prefix}{key}"
                    self.redis.set(
                        data_key,
                        json.dumps(task_data),
                        ex=self.retention_seconds
                    )

                    logger.info(f"Task marked for retry: {task_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to mark task for retry: {str(e)}", exc_info=True)
            return False

    def remove_task(self, task_id: str) -> bool:
        """
        Remove task from DLQ (after successful retry or manual resolution)

        Args:
            task_id: Task identifier

        Returns:
            bool: True if removed successfully
        """
        try:
            # Find and remove from sorted set
            all_keys = self.redis.zrange(self._dlq_queue_key, 0, -1)

            for key in all_keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')

                if task_id in key:
                    # Remove from sorted set
                    self.redis.zrem(self._dlq_queue_key, key)

                    # Remove data
                    data_key = f"{self._dlq_data_key_prefix}{key}"
                    self.redis.delete(data_key)

                    logger.info(f"Task removed from DLQ: {task_id}")
                    return True

            logger.warning(f"Task not found in DLQ for removal: {task_id}")
            return False

        except Exception as e:
            logger.error(f"Failed to remove task from DLQ: {str(e)}", exc_info=True)
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get DLQ statistics

        Returns:
            Statistics about failed tasks
        """
        try:
            total_failed = self.redis.zcard(self._dlq_queue_key)

            # Get recent failures (last 24 hours)
            one_day_ago = (datetime.utcnow() - timedelta(days=1)).timestamp()
            recent_failed = self.redis.zcount(
                self._dlq_queue_key,
                one_day_ago,
                '+inf'
            )

            # Count by task type
            all_keys = self.redis.zrange(self._dlq_queue_key, 0, -1)
            task_type_counts = {}

            for key in all_keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')

                task_name = key.split(':')[0]
                task_type_counts[task_name] = task_type_counts.get(task_name, 0) + 1

            return {
                "total_failed_tasks": total_failed,
                "recent_failures_24h": recent_failed,
                "failures_by_task_type": task_type_counts,
                "oldest_failure": self._get_oldest_failure_time(),
                "newest_failure": self._get_newest_failure_time()
            }

        except Exception as e:
            logger.error(f"Failed to get DLQ statistics: {str(e)}", exc_info=True)
            return {}

    def cleanup_old_entries(self, days: int = 30) -> int:
        """
        Remove entries older than specified days

        Args:
            days: Number of days to retain

        Returns:
            Number of entries removed
        """
        try:
            cutoff = (datetime.utcnow() - timedelta(days=days)).timestamp()

            # Get old entries
            old_keys = self.redis.zrangebyscore(
                self._dlq_queue_key,
                '-inf',
                cutoff
            )

            removed = 0

            for key in old_keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')

                # Remove from sorted set
                self.redis.zrem(self._dlq_queue_key, key)

                # Remove data
                data_key = f"{self._dlq_data_key_prefix}{key}"
                self.redis.delete(data_key)

                removed += 1

            if removed > 0:
                logger.info(f"DLQ cleanup: Removed {removed} old entries (>{days} days)")

            return removed

        except Exception as e:
            logger.error(f"DLQ cleanup failed: {str(e)}", exc_info=True)
            return 0

    def _get_oldest_failure_time(self) -> Optional[str]:
        """Get timestamp of oldest failure"""
        try:
            oldest = self.redis.zrange(self._dlq_queue_key, 0, 0, withscores=True)
            if oldest:
                timestamp = oldest[0][1]  # Score is timestamp
                return datetime.fromtimestamp(timestamp).isoformat()
            return None
        except:
            return None

    def _get_newest_failure_time(self) -> Optional[str]:
        """Get timestamp of newest failure"""
        try:
            newest = self.redis.zrevrange(self._dlq_queue_key, 0, 0, withscores=True)
            if newest:
                timestamp = newest[0][1]
                return datetime.fromtimestamp(timestamp).isoformat()
            return None
        except:
            return None

    def _is_critical_task(self, task_name: str) -> bool:
        """Determine if task is critical (requires immediate attention)"""
        critical_tasks = [
            "process_pdf_async",
            "generate_chapter",
            "backup_database"
        ]
        return any(critical in task_name for critical in critical_tasks)


# Global DLQ instance
dlq = DeadLetterQueue()
