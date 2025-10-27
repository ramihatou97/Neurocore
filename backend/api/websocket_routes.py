"""
WebSocket API Routes
Real-time communication for chapter generation and task progress
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from typing import Optional
import asyncio
import json

from backend.services.websocket_manager import manager
from backend.services.auth_service import AuthService
from backend.utils import get_logger
from backend.database import get_db
from backend.database.models import User, Chapter, Task
from sqlalchemy.orm import Session

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


async def get_current_user_ws(
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db)
) -> User:
    """
    Authenticate WebSocket connection using JWT token

    Args:
        token: JWT access token
        db: Database session

    Returns:
        Authenticated User

    Raises:
        HTTPException: If authentication fails
    """
    try:
        auth_service = AuthService(db)
        payload = auth_service.decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

        return user

    except Exception as e:
        logger.error(f"WebSocket authentication failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")


@router.websocket("/chapters/{chapter_id}")
async def chapter_progress_websocket(
    websocket: WebSocket,
    chapter_id: str,
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chapter generation progress

    Sends updates for all 14 stages of chapter generation.

    Query Parameters:
    - token: JWT access token for authentication

    Events:
    - chapter_started: Generation started
    - chapter_progress: Stage progress update
    - chapter_stage_update: Stage changed
    - chapter_completed: Generation completed
    - chapter_failed: Generation failed
    """
    try:
        # Authenticate user
        user = await get_current_user_ws(token, db)

        # Verify chapter exists and user has access
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Chapter not found")
            return

        # Connect WebSocket
        await manager.connect(websocket, str(user.id))

        # Join chapter-specific room
        room_id = f"chapter:{chapter_id}"
        manager.join_room(websocket, room_id)

        # Send initial connection confirmation
        await websocket.send_json({
            "event": "connected",
            "data": {
                "chapter_id": chapter_id,
                "user_id": str(user.id),
                "message": "Connected to chapter progress updates"
            }
        })

        # Start heartbeat
        heartbeat_task = asyncio.create_task(manager.heartbeat_loop(websocket, interval=30))

        try:
            # Listen for client messages (mainly for pong responses)
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle pong
                if message.get("type") == "pong":
                    logger.debug(f"Received pong from user {user.id}")
                    continue

                # Handle disconnect request
                if message.get("type") == "disconnect":
                    break

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for chapter {chapter_id}, user {user.id}")
        finally:
            heartbeat_task.cancel()
            manager.leave_room(websocket, room_id)
            manager.disconnect(websocket)

    except Exception as e:
        logger.error(f"WebSocket error for chapter {chapter_id}: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass


@router.websocket("/tasks/{task_id}")
async def task_progress_websocket(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time task progress updates

    Sends updates for background task execution (PDF processing, etc.)

    Query Parameters:
    - token: JWT access token for authentication

    Events:
    - task_started: Task started
    - task_progress: Progress update
    - task_completed: Task completed
    - task_failed: Task failed
    - task_cancelled: Task cancelled
    """
    try:
        # Authenticate user
        user = await get_current_user_ws(token, db)

        # Verify task exists and user has access
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Task not found")
            return

        if str(task.created_by) != str(user.id) and not user.is_admin:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
            return

        # Connect WebSocket
        await manager.connect(websocket, str(user.id))

        # Join task-specific room
        room_id = f"task:{task_id}"
        manager.join_room(websocket, room_id)

        # Send initial connection confirmation
        await websocket.send_json({
            "event": "connected",
            "data": {
                "task_id": task_id,
                "user_id": str(user.id),
                "message": "Connected to task progress updates"
            }
        })

        # Start heartbeat
        heartbeat_task = asyncio.create_task(manager.heartbeat_loop(websocket, interval=30))

        try:
            # Listen for client messages
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle pong
                if message.get("type") == "pong":
                    logger.debug(f"Received pong from user {user.id}")
                    continue

                # Handle disconnect request
                if message.get("type") == "disconnect":
                    break

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for task {task_id}, user {user.id}")
        finally:
            heartbeat_task.cancel()
            manager.leave_room(websocket, room_id)
            manager.disconnect(websocket)

    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass


@router.websocket("/notifications")
async def notifications_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for general user notifications

    Sends system notifications, alerts, and updates.

    Query Parameters:
    - token: JWT access token for authentication

    Events:
    - notification: General notification
    - error: Error notification
    """
    try:
        # Authenticate user
        user = await get_current_user_ws(token, db)

        # Connect WebSocket
        await manager.connect(websocket, str(user.id))

        # Join user-specific notification room
        room_id = f"notifications:{user.id}"
        manager.join_room(websocket, room_id)

        # Send initial connection confirmation
        await websocket.send_json({
            "event": "connected",
            "data": {
                "user_id": str(user.id),
                "message": "Connected to notifications"
            }
        })

        # Start heartbeat
        heartbeat_task = asyncio.create_task(manager.heartbeat_loop(websocket, interval=30))

        try:
            # Listen for client messages
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle pong
                if message.get("type") == "pong":
                    logger.debug(f"Received pong from user {user.id}")
                    continue

                # Handle disconnect request
                if message.get("type") == "disconnect":
                    break

        except WebSocketDisconnect:
            logger.info(f"Notifications WebSocket disconnected for user {user.id}")
        finally:
            heartbeat_task.cancel()
            manager.leave_room(websocket, room_id)
            manager.disconnect(websocket)

    except Exception as e:
        logger.error(f"WebSocket error for notifications: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass


@router.get("/health")
async def websocket_health():
    """
    WebSocket service health check

    Returns connection statistics
    """
    return {
        "status": "healthy",
        "total_connections": manager.get_total_connections(),
        "service": "websocket"
    }
