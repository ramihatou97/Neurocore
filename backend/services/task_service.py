"""
Task Service - Task status tracking and management
Provides CRUD operations and status queries for background tasks
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from celery.result import AsyncResult
from fastapi import HTTPException

from backend.database.models import Task, User
from backend.services.celery_app import celery_app
from backend.utils import get_logger

logger = get_logger(__name__)


class TaskService:
    """
    Service for managing background tasks

    Provides:
    - Task creation and tracking
    - Status queries
    - Progress updates
    - Task cancellation
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_task(
        self,
        task_id: str,
        task_type: str,
        user: User,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        total_steps: int = 0
    ) -> Task:
        """
        Create a new task tracking record

        Args:
            task_id: Celery task ID
            task_type: Type of task
            user: User who initiated the task
            entity_id: Related entity ID
            entity_type: Related entity type
            total_steps: Total number of steps

        Returns:
            Created Task object
        """
        task = Task(
            task_id=task_id,
            task_type=task_type,
            status="queued",
            created_by=user.id,
            entity_id=entity_id,
            entity_type=entity_type,
            total_steps=total_steps,
            progress=0
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        logger.info(f"Created task: {task_id} ({task_type})")
        return task

    def get_task(self, task_id: str) -> Task:
        """
        Get task by Celery task ID

        Args:
            task_id: Celery task ID

        Returns:
            Task object

        Raises:
            HTTPException: If task not found
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        return task

    def get_task_by_id(self, id: str) -> Task:
        """
        Get task by database ID

        Args:
            id: Database UUID

        Returns:
            Task object

        Raises:
            HTTPException: If task not found
        """
        task = self.db.query(Task).filter(Task.id == id).first()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {id}")
        return task

    def update_task_status(
        self,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        current_step: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Task:
        """
        Update task status and progress

        Args:
            task_id: Celery task ID
            status: New status
            progress: Progress percentage (0-100)
            current_step: Current step number
            result: Task result data
            error: Error message

        Returns:
            Updated Task object
        """
        task = self.get_task(task_id)

        task.status = status

        if progress is not None:
            task.progress = min(100, max(0, progress))

        if current_step is not None:
            task.current_step = current_step

        if result is not None:
            task.result = result

        if error is not None:
            task.error = error

        # Set timestamps
        if status == "processing" and not task.started_at:
            from datetime import datetime
            task.started_at = datetime.utcnow()

        if status in ["completed", "failed", "cancelled"] and not task.completed_at:
            from datetime import datetime
            task.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(task)

        logger.info(f"Updated task {task_id}: {status} ({progress}%)")
        return task

    def get_celery_task_info(self, task_id: str) -> Dict[str, Any]:
        """
        Get task status from Celery

        Args:
            task_id: Celery task ID

        Returns:
            Dictionary with task information
        """
        result = AsyncResult(task_id, app=celery_app)

        return {
            "task_id": task_id,
            "state": result.state,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "failed": result.failed() if result.ready() else None,
            "result": result.result if result.ready() else None,
            "traceback": result.traceback if result.failed() else None
        }

    def get_task_with_celery_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get combined task info from database and Celery

        Args:
            task_id: Celery task ID

        Returns:
            Combined task information
        """
        # Get database record
        task = self.get_task(task_id)

        # Get Celery status
        celery_info = self.get_celery_task_info(task_id)

        # Combine information
        return {
            **task.to_dict(),
            "celery_state": celery_info["state"],
            "celery_ready": celery_info["ready"]
        }

    def list_tasks(
        self,
        user_id: Optional[str] = None,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        entity_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Task]:
        """
        List tasks with filtering

        Args:
            user_id: Filter by user ID
            task_type: Filter by task type
            status: Filter by status
            entity_id: Filter by entity ID
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of Task objects
        """
        query = self.db.query(Task)

        if user_id:
            query = query.filter(Task.created_by == user_id)

        if task_type:
            query = query.filter(Task.task_type == task_type)

        if status:
            query = query.filter(Task.status == status)

        if entity_id:
            query = query.filter(Task.entity_id == entity_id)

        query = query.order_by(Task.created_at.desc())
        query = query.offset(skip).limit(limit)

        return query.all()

    def get_user_tasks(
        self,
        user_id: str,
        include_completed: bool = True
    ) -> List[Task]:
        """
        Get all tasks for a specific user

        Args:
            user_id: User ID
            include_completed: Include completed tasks

        Returns:
            List of user's tasks
        """
        query = self.db.query(Task).filter(Task.created_by == user_id)

        if not include_completed:
            query = query.filter(Task.status.in_(["queued", "processing"]))

        query = query.order_by(Task.created_at.desc())

        return query.all()

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        Cancel a running task

        Args:
            task_id: Celery task ID

        Returns:
            Cancellation result
        """
        # Get task from database
        task = self.get_task(task_id)

        if task.is_complete:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task in status: {task.status}"
            )

        # Revoke Celery task
        celery_app.control.revoke(task_id, terminate=True)

        # Update database
        task.status = "cancelled"
        from datetime import datetime
        task.completed_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Task cancelled: {task_id}")

        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task has been cancelled"
        }

    def get_task_statistics(self) -> Dict[str, Any]:
        """
        Get overall task statistics

        Returns:
            Dictionary with statistics
        """
        total_tasks = self.db.query(Task).count()

        queued = self.db.query(Task).filter(Task.status == "queued").count()
        processing = self.db.query(Task).filter(Task.status == "processing").count()
        completed = self.db.query(Task).filter(Task.status == "completed").count()
        failed = self.db.query(Task).filter(Task.status == "failed").count()
        cancelled = self.db.query(Task).filter(Task.status == "cancelled").count()

        return {
            "total_tasks": total_tasks,
            "queued": queued,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "active": queued + processing,
            "success_rate": round(completed / total_tasks * 100, 1) if total_tasks > 0 else 0
        }

    def cleanup_old_tasks(self, days: int = 30) -> Dict[str, Any]:
        """
        Clean up old completed tasks

        Args:
            days: Delete tasks older than this many days

        Returns:
            Cleanup summary
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        deleted = self.db.query(Task).filter(
            Task.status.in_(["completed", "failed", "cancelled"]),
            Task.completed_at < cutoff_date
        ).delete()

        self.db.commit()

        logger.info(f"Cleaned up {deleted} old tasks")

        return {
            "deleted_tasks": deleted,
            "cutoff_date": cutoff_date.isoformat()
        }
