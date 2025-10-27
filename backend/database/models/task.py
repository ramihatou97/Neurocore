"""
Task Model - Background task tracking
Tracks Celery task execution status and progress
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, TIMESTAMP, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from backend.database.base import Base


class Task(Base):
    """
    Background task tracking model

    Tracks Celery tasks for:
    - PDF processing
    - Image analysis
    - Embedding generation
    - Chapter generation
    """

    __tablename__ = "tasks"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), unique=True, nullable=False, index=True)  # Celery task ID

    # Task information
    task_type = Column(String(100), nullable=False)  # pdf_processing, image_analysis, etc.
    status = Column(String(50), nullable=False, index=True)  # queued, processing, completed, failed

    # Progress tracking
    progress = Column(Integer, default=0)  # 0-100
    total_steps = Column(Integer, default=0)
    current_step = Column(Integer, default=0)

    # Related entity
    entity_id = Column(UUID(as_uuid=True), index=True)  # PDF ID, Chapter ID, etc.
    entity_type = Column(String(50))  # pdf, chapter, image

    # Results and errors
    result = Column(JSONB)  # Task result data
    error = Column(Text)  # Error message if failed

    # Timestamps
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    user = relationship("User", back_populates="tasks")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')",
            name="chk_status"
        ),
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="chk_progress"
        ),
    )

    def __repr__(self):
        return f"<Task {self.task_id} ({self.task_type}): {self.status}>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "entity_id": str(self.entity_id) if self.entity_id else None,
            "entity_type": self.entity_type,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None
        }

    @property
    def is_complete(self) -> bool:
        """Check if task is complete"""
        return self.status in ["completed", "failed", "cancelled"]

    @property
    def is_running(self) -> bool:
        """Check if task is currently running"""
        return self.status in ["queued", "processing"]

    @property
    def duration_seconds(self) -> float:
        """Calculate task duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
