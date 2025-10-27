"""
WebSocket Event Emitter
Helper functions for emitting WebSocket events from services
"""

from typing import Dict, Any, Optional
import asyncio

from backend.services.websocket_manager import manager
from backend.utils.events import (
    ChapterProgressEvent,
    TaskProgressEvent,
    PDFProcessingEvent,
    ChapterStage,
    EventType
)
from backend.utils import get_logger

logger = get_logger(__name__)


class WebSocketEmitter:
    """
    WebSocket event emitter for services

    Provides simple methods to emit events without dealing with rooms directly
    """

    @staticmethod
    async def emit_chapter_progress(
        chapter_id: str,
        stage: ChapterStage,
        stage_number: int,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Emit chapter generation progress event

        Args:
            chapter_id: Chapter UUID
            stage: Current stage
            stage_number: Stage number (1-14)
            message: Human-readable message
            details: Additional details
        """
        try:
            # Calculate progress percentage
            progress_percent = int((stage_number / 14) * 100)

            # Create event
            event = ChapterProgressEvent.create(
                chapter_id=chapter_id,
                stage=stage,
                stage_number=stage_number,
                total_stages=14,
                progress_percent=progress_percent,
                message=message,
                details=details
            )

            # Send to chapter room
            room_id = f"chapter:{chapter_id}"
            await manager.send_to_room(event, room_id)

            logger.debug(f"Emitted chapter progress: {chapter_id} - Stage {stage_number}")

        except Exception as e:
            logger.error(f"Failed to emit chapter progress: {str(e)}")

    @staticmethod
    async def emit_chapter_completed(
        chapter_id: str,
        message: str = "Chapter generation completed",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Emit chapter completion event

        Args:
            chapter_id: Chapter UUID
            message: Completion message
            details: Additional details (scores, etc.)
        """
        try:
            from backend.utils.events import WebSocketEvent

            event = WebSocketEvent.create(
                EventType.CHAPTER_COMPLETED,
                {
                    "chapter_id": chapter_id,
                    "message": message,
                    "details": details or {}
                }
            )

            room_id = f"chapter:{chapter_id}"
            await manager.send_to_room(event, room_id)

            logger.info(f"Emitted chapter completed: {chapter_id}")

        except Exception as e:
            logger.error(f"Failed to emit chapter completed: {str(e)}")

    @staticmethod
    async def emit_chapter_failed(
        chapter_id: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Emit chapter failure event

        Args:
            chapter_id: Chapter UUID
            error_message: Error message
            details: Additional error details
        """
        try:
            from backend.utils.events import WebSocketEvent

            event = WebSocketEvent.create(
                EventType.CHAPTER_FAILED,
                {
                    "chapter_id": chapter_id,
                    "error_message": error_message,
                    "details": details or {}
                }
            )

            room_id = f"chapter:{chapter_id}"
            await manager.send_to_room(event, room_id)

            logger.warning(f"Emitted chapter failed: {chapter_id}")

        except Exception as e:
            logger.error(f"Failed to emit chapter failed: {str(e)}")

    @staticmethod
    async def emit_task_progress(
        task_id: str,
        task_type: str,
        status: str,
        progress: int,
        current_step: int,
        total_steps: int,
        message: str,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Emit task progress event

        Args:
            task_id: Task UUID
            task_type: Type of task
            status: Current status
            progress: Progress percentage (0-100)
            current_step: Current step
            total_steps: Total steps
            message: Status message
            entity_id: Related entity ID
            entity_type: Related entity type
            details: Additional details
        """
        try:
            event = TaskProgressEvent.create(
                task_id=task_id,
                task_type=task_type,
                status=status,
                progress=progress,
                current_step=current_step,
                total_steps=total_steps,
                message=message,
                entity_id=entity_id,
                entity_type=entity_type,
                details=details
            )

            room_id = f"task:{task_id}"
            await manager.send_to_room(event, room_id)

            logger.debug(f"Emitted task progress: {task_id} - {progress}%")

        except Exception as e:
            logger.error(f"Failed to emit task progress: {str(e)}")

    @staticmethod
    async def emit_pdf_processing_event(
        pdf_id: str,
        event_type: EventType,
        stage: str,
        message: str,
        progress: int = 0,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Emit PDF processing event

        Args:
            pdf_id: PDF UUID
            event_type: Type of event
            stage: Processing stage
            message: Status message
            progress: Progress percentage
            details: Additional details
        """
        try:
            event = PDFProcessingEvent.create(
                pdf_id=pdf_id,
                event_type=event_type,
                stage=stage,
                message=message,
                progress=progress,
                details=details
            )

            # Send to PDF processing room (based on task)
            # This would typically be linked to a task ID
            room_id = f"pdf:{pdf_id}"
            await manager.send_to_room(event, room_id)

            logger.debug(f"Emitted PDF processing event: {pdf_id} - {stage}")

        except Exception as e:
            logger.error(f"Failed to emit PDF processing event: {str(e)}")


# Singleton instance
emitter = WebSocketEmitter()
