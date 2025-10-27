"""
WebSocket Event Definitions
Defines event types and structures for real-time updates
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class EventType(str, Enum):
    """WebSocket event types"""
    # Chapter generation events
    CHAPTER_STARTED = "chapter_started"
    CHAPTER_PROGRESS = "chapter_progress"
    CHAPTER_STAGE_UPDATE = "chapter_stage_update"
    CHAPTER_COMPLETED = "chapter_completed"
    CHAPTER_FAILED = "chapter_failed"

    # Task events
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"

    # PDF processing events
    PDF_PROCESSING_STARTED = "pdf_processing_started"
    PDF_TEXT_EXTRACTED = "pdf_text_extracted"
    PDF_IMAGES_EXTRACTED = "pdf_images_extracted"
    PDF_IMAGES_ANALYZED = "pdf_images_analyzed"
    PDF_EMBEDDINGS_GENERATED = "pdf_embeddings_generated"
    PDF_PROCESSING_COMPLETED = "pdf_processing_completed"
    PDF_PROCESSING_FAILED = "pdf_processing_failed"

    # System events
    NOTIFICATION = "notification"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class ChapterStage(str, Enum):
    """Chapter generation stages"""
    STAGE_1_INPUT = "stage_1_input"
    STAGE_2_CONTEXT = "stage_2_context"
    STAGE_3_RESEARCH_INTERNAL = "stage_3_research_internal"
    STAGE_4_RESEARCH_EXTERNAL = "stage_4_research_external"
    STAGE_5_PLANNING = "stage_5_planning"
    STAGE_6_GENERATION = "stage_6_generation"
    STAGE_7_IMAGES = "stage_7_images"
    STAGE_8_CITATIONS = "stage_8_citations"
    STAGE_9_QA = "stage_9_qa"
    STAGE_10_FACT_CHECK = "stage_10_fact_check"
    STAGE_11_FORMATTING = "stage_11_formatting"
    STAGE_12_REVIEW = "stage_12_review"
    STAGE_13_FINALIZATION = "stage_13_finalization"
    STAGE_14_DELIVERY = "stage_14_delivery"


CHAPTER_STAGE_NAMES = {
    ChapterStage.STAGE_1_INPUT: "Input Validation",
    ChapterStage.STAGE_2_CONTEXT: "Context Building",
    ChapterStage.STAGE_3_RESEARCH_INTERNAL: "Internal Research",
    ChapterStage.STAGE_4_RESEARCH_EXTERNAL: "External Research",
    ChapterStage.STAGE_5_PLANNING: "Synthesis Planning",
    ChapterStage.STAGE_6_GENERATION: "Section Generation",
    ChapterStage.STAGE_7_IMAGES: "Image Integration",
    ChapterStage.STAGE_8_CITATIONS: "Citation Network",
    ChapterStage.STAGE_9_QA: "Quality Assurance",
    ChapterStage.STAGE_10_FACT_CHECK: "Fact Checking",
    ChapterStage.STAGE_11_FORMATTING: "Formatting",
    ChapterStage.STAGE_12_REVIEW: "Review & Refinement",
    ChapterStage.STAGE_13_FINALIZATION: "Finalization",
    ChapterStage.STAGE_14_DELIVERY: "Delivery"
}


class WebSocketEvent(BaseModel):
    """Base WebSocket event"""
    event: EventType
    timestamp: str
    data: Dict[str, Any]

    @classmethod
    def create(cls, event_type: EventType, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create event dictionary"""
        return {
            "event": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }


class ChapterProgressEvent:
    """Chapter generation progress event"""

    @staticmethod
    def create(
        chapter_id: str,
        stage: ChapterStage,
        stage_number: int,
        total_stages: int = 14,
        progress_percent: int = 0,
        message: str = "",
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create chapter progress event

        Args:
            chapter_id: Chapter UUID
            stage: Current stage
            stage_number: Stage number (1-14)
            total_stages: Total number of stages
            progress_percent: Overall progress percentage
            message: Human-readable status message
            details: Additional stage-specific details

        Returns:
            Event dictionary
        """
        return WebSocketEvent.create(
            EventType.CHAPTER_PROGRESS,
            {
                "chapter_id": chapter_id,
                "stage": stage.value,
                "stage_name": CHAPTER_STAGE_NAMES.get(stage, "Unknown"),
                "stage_number": stage_number,
                "total_stages": total_stages,
                "progress_percent": progress_percent,
                "message": message,
                "details": details or {}
            }
        )


class TaskProgressEvent:
    """Background task progress event"""

    @staticmethod
    def create(
        task_id: str,
        task_type: str,
        status: str,
        progress: int,
        current_step: int,
        total_steps: int,
        message: str = "",
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create task progress event

        Args:
            task_id: Task UUID
            task_type: Type of task
            status: Current status
            progress: Progress percentage (0-100)
            current_step: Current step number
            total_steps: Total number of steps
            message: Human-readable status message
            entity_id: Related entity ID
            entity_type: Related entity type
            details: Additional details

        Returns:
            Event dictionary
        """
        return WebSocketEvent.create(
            EventType.TASK_PROGRESS,
            {
                "task_id": task_id,
                "task_type": task_type,
                "status": status,
                "progress": progress,
                "current_step": current_step,
                "total_steps": total_steps,
                "message": message,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "details": details or {}
            }
        )


class PDFProcessingEvent:
    """PDF processing event"""

    @staticmethod
    def create(
        pdf_id: str,
        event_type: EventType,
        stage: str,
        message: str,
        progress: int = 0,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create PDF processing event

        Args:
            pdf_id: PDF UUID
            event_type: Type of event
            stage: Processing stage
            message: Human-readable message
            progress: Progress percentage (0-100)
            details: Additional details

        Returns:
            Event dictionary
        """
        return WebSocketEvent.create(
            event_type,
            {
                "pdf_id": pdf_id,
                "stage": stage,
                "message": message,
                "progress": progress,
                "details": details or {}
            }
        )


class NotificationEvent:
    """General notification event"""

    @staticmethod
    def create(
        level: str,  # info, warning, error, success
        title: str,
        message: str,
        action_url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create notification event

        Args:
            level: Notification level (info, warning, error, success)
            title: Notification title
            message: Notification message
            action_url: Optional URL for action
            details: Additional details

        Returns:
            Event dictionary
        """
        return WebSocketEvent.create(
            EventType.NOTIFICATION,
            {
                "level": level,
                "title": title,
                "message": message,
                "action_url": action_url,
                "details": details or {}
            }
        )


class ErrorEvent:
    """Error event"""

    @staticmethod
    def create(
        error_code: str,
        error_message: str,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create error event

        Args:
            error_code: Error code
            error_message: Error message
            entity_id: Related entity ID
            entity_type: Related entity type
            details: Additional error details

        Returns:
            Event dictionary
        """
        return WebSocketEvent.create(
            EventType.ERROR,
            {
                "error_code": error_code,
                "error_message": error_message,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "details": details or {}
            }
        )
