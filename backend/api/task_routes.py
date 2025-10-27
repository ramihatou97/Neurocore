"""
Task API Routes - Background task management endpoints
Provides endpoints for checking task status, cancelling tasks, and viewing task history
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.database.connection import get_db
from backend.database.models import User
from backend.services.task_service import TaskService
from backend.utils import get_logger, get_current_active_user

logger = get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ==================== Pydantic Models ====================

class TaskResponse(BaseModel):
    """Task response model"""
    id: str
    task_id: str
    task_type: str
    status: str
    progress: int
    total_steps: int
    current_step: int
    entity_id: Optional[str]
    entity_type: Optional[str]
    result: Optional[dict]
    error: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str
    created_by: Optional[str]

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Task list response model"""
    tasks: List[TaskResponse]
    total: int
    skip: int
    limit: int


class TaskStatisticsResponse(BaseModel):
    """Task statistics response model"""
    total_tasks: int
    queued: int
    processing: int
    completed: int
    failed: int
    cancelled: int
    active: int
    success_rate: float


class CancelTaskResponse(BaseModel):
    """Task cancellation response"""
    task_id: str
    status: str
    message: str


# ==================== API Endpoints ====================

@router.get("/health", summary="Task service health check")
async def health_check():
    """Health check endpoint"""
    return {"message": "Task service is healthy", "service": "tasks"}


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task status"
)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> TaskResponse:
    """
    Get task status by Celery task ID

    Returns:
    - Task information including status, progress, and results
    """
    logger.info(f"Getting task status: {task_id}")

    task_service = TaskService(db)
    task = task_service.get_task(task_id)

    # Check ownership (unless admin)
    if not current_user.is_admin and str(task.created_by) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this task"
        )

    return TaskResponse(**task.to_dict())


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List all tasks"
)
async def list_tasks(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> TaskListResponse:
    """
    List tasks with optional filtering

    Filters:
    - task_type: Type of task (pdf_processing, image_analysis, etc.)
    - status: Task status (queued, processing, completed, failed)

    Pagination:
    - skip: Number of records to skip
    - limit: Maximum number of records to return
    """
    logger.info(f"Listing tasks for user {current_user.email}")

    task_service = TaskService(db)

    # Regular users can only see their own tasks
    user_id = None if current_user.is_admin else str(current_user.id)

    tasks = task_service.list_tasks(
        user_id=user_id,
        task_type=task_type,
        status=status,
        skip=skip,
        limit=limit
    )

    # Get total count
    from sqlalchemy import func
    from backend.database.models import Task

    query = db.query(func.count(Task.id))
    if user_id:
        query = query.filter(Task.created_by == user_id)
    if task_type:
        query = query.filter(Task.task_type == task_type)
    if status:
        query = query.filter(Task.status == status)

    total = query.scalar()

    return TaskListResponse(
        tasks=[TaskResponse(**task.to_dict()) for task in tasks],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get(
    "/me/tasks",
    response_model=List[TaskResponse],
    summary="Get current user's tasks"
)
async def get_my_tasks(
    include_completed: bool = Query(True, description="Include completed tasks"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[TaskResponse]:
    """
    Get all tasks for the current user

    Args:
    - include_completed: Include completed/failed tasks (default: true)

    Returns:
    - List of user's tasks
    """
    logger.info(f"Getting tasks for user {current_user.email}")

    task_service = TaskService(db)
    tasks = task_service.get_user_tasks(
        str(current_user.id),
        include_completed=include_completed
    )

    return [TaskResponse(**task.to_dict()) for task in tasks]


@router.post(
    "/{task_id}/cancel",
    response_model=CancelTaskResponse,
    summary="Cancel a running task"
)
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> CancelTaskResponse:
    """
    Cancel a running task

    Requirements:
    - Task must be in 'queued' or 'processing' status
    - User must own the task (or be admin)

    Returns:
    - Cancellation confirmation
    """
    logger.info(f"Cancelling task: {task_id}")

    task_service = TaskService(db)
    task = task_service.get_task(task_id)

    # Check ownership (unless admin)
    if not current_user.is_admin and str(task.created_by) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to cancel this task"
        )

    result = task_service.cancel_task(task_id)
    return CancelTaskResponse(**result)


@router.get(
    "/statistics",
    response_model=TaskStatisticsResponse,
    summary="Get task statistics"
)
async def get_task_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> TaskStatisticsResponse:
    """
    Get overall task statistics

    Returns:
    - Total tasks
    - Tasks by status
    - Success rate

    Note: Only admins can see system-wide statistics
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    logger.info("Getting task statistics")

    task_service = TaskService(db)
    stats = task_service.get_task_statistics()

    return TaskStatisticsResponse(**stats)


@router.delete(
    "/cleanup",
    summary="Clean up old completed tasks"
)
async def cleanup_old_tasks(
    days: int = Query(30, ge=1, le=365, description="Delete tasks older than this many days"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Clean up old completed tasks

    Requirements:
    - Admin access required
    - Only deletes completed/failed/cancelled tasks

    Args:
    - days: Delete tasks older than this many days (default: 30)

    Returns:
    - Number of deleted tasks
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    logger.info(f"Cleaning up tasks older than {days} days")

    task_service = TaskService(db)
    result = task_service.cleanup_old_tasks(days=days)

    return {
        "message": f"Cleaned up {result['deleted_tasks']} old tasks",
        **result
    }
