"""
WebSocket Connection Manager
Manages WebSocket connections, authentication, and message broadcasting
"""

from typing import Dict, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from datetime import datetime
import uuid

from backend.utils import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting

    Features:
    - User-specific connections
    - Room/channel management
    - Broadcast to specific users or rooms
    - Connection health monitoring (ping/pong)
    - Automatic cleanup of dead connections
    """

    def __init__(self):
        # Active connections: user_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

        # Room subscriptions: room_id -> Set of user_ids
        self.rooms: Dict[str, Set[str]] = {}

        # Connection metadata: websocket -> metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

        # Heartbeat tracking
        self.last_heartbeat: Dict[WebSocket, datetime] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_id: Optional[str] = None
    ):
        """
        Accept and register a new WebSocket connection

        Args:
            websocket: WebSocket connection
            user_id: User ID
            connection_id: Optional unique connection identifier
        """
        await websocket.accept()

        # Initialize user connections set if doesn't exist
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        # Add connection
        self.active_connections[user_id].add(websocket)

        # Store metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connection_id": connection_id or str(uuid.uuid4()),
            "connected_at": datetime.utcnow(),
            "rooms": set()
        }

        # Initialize heartbeat
        self.last_heartbeat[websocket] = datetime.utcnow()

        logger.info(f"WebSocket connected: user={user_id}, connections={len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection

        Args:
            websocket: WebSocket connection to remove
        """
        if websocket not in self.connection_metadata:
            return

        metadata = self.connection_metadata[websocket]
        user_id = metadata["user_id"]

        # Remove from active connections
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # Remove from rooms
        for room_id in metadata.get("rooms", set()):
            if room_id in self.rooms:
                self.rooms[room_id].discard(user_id)
                if not self.rooms[room_id]:
                    del self.rooms[room_id]

        # Clean up metadata
        del self.connection_metadata[websocket]
        if websocket in self.last_heartbeat:
            del self.last_heartbeat[websocket]

        logger.info(f"WebSocket disconnected: user={user_id}")

    async def send_personal_message(
        self,
        message: Dict[str, Any],
        user_id: str
    ):
        """
        Send message to all connections of a specific user

        Args:
            message: Message dictionary
            user_id: Target user ID
        """
        if user_id not in self.active_connections:
            return

        # Add timestamp
        message["timestamp"] = datetime.utcnow().isoformat()

        # Send to all user's connections
        dead_connections = set()
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {str(e)}")
                dead_connections.add(connection)

        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection)

    async def send_to_room(
        self,
        message: Dict[str, Any],
        room_id: str
    ):
        """
        Send message to all users in a room

        Args:
            message: Message dictionary
            room_id: Target room ID
        """
        if room_id not in self.rooms:
            return

        # Add timestamp
        message["timestamp"] = datetime.utcnow().isoformat()

        # Send to all users in room
        for user_id in self.rooms[room_id]:
            await self.send_personal_message(message, user_id)

    async def broadcast(
        self,
        message: Dict[str, Any],
        exclude_user: Optional[str] = None
    ):
        """
        Broadcast message to all connected users

        Args:
            message: Message dictionary
            exclude_user: Optional user ID to exclude
        """
        # Add timestamp
        message["timestamp"] = datetime.utcnow().isoformat()

        for user_id in list(self.active_connections.keys()):
            if exclude_user and user_id == exclude_user:
                continue
            await self.send_personal_message(message, user_id)

    def join_room(self, websocket: WebSocket, room_id: str):
        """
        Add user to a room

        Args:
            websocket: WebSocket connection
            room_id: Room identifier
        """
        if websocket not in self.connection_metadata:
            return

        user_id = self.connection_metadata[websocket]["user_id"]

        # Initialize room if doesn't exist
        if room_id not in self.rooms:
            self.rooms[room_id] = set()

        # Add user to room
        self.rooms[room_id].add(user_id)

        # Track room in connection metadata
        self.connection_metadata[websocket]["rooms"].add(room_id)

        logger.info(f"User {user_id} joined room {room_id}")

    def leave_room(self, websocket: WebSocket, room_id: str):
        """
        Remove user from a room

        Args:
            websocket: WebSocket connection
            room_id: Room identifier
        """
        if websocket not in self.connection_metadata:
            return

        user_id = self.connection_metadata[websocket]["user_id"]

        # Remove user from room
        if room_id in self.rooms:
            self.rooms[room_id].discard(user_id)
            if not self.rooms[room_id]:
                del self.rooms[room_id]

        # Remove room from connection metadata
        if room_id in self.connection_metadata[websocket]["rooms"]:
            self.connection_metadata[websocket]["rooms"].remove(room_id)

        logger.info(f"User {user_id} left room {room_id}")

    def get_user_connections_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        if user_id not in self.active_connections:
            return 0
        return len(self.active_connections[user_id])

    def get_room_users_count(self, room_id: str) -> int:
        """Get number of users in a room"""
        if room_id not in self.rooms:
            return 0
        return len(self.rooms[room_id])

    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())

    def get_connection_info(self, websocket: WebSocket) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific connection"""
        return self.connection_metadata.get(websocket)

    async def ping(self, websocket: WebSocket):
        """
        Send ping to check connection health

        Args:
            websocket: WebSocket connection
        """
        try:
            await websocket.send_json({"type": "ping"})
            self.last_heartbeat[websocket] = datetime.utcnow()
        except Exception as e:
            logger.error(f"Ping failed: {str(e)}")
            self.disconnect(websocket)

    async def heartbeat_loop(self, websocket: WebSocket, interval: int = 30):
        """
        Periodic heartbeat to keep connection alive

        Args:
            websocket: WebSocket connection
            interval: Ping interval in seconds
        """
        try:
            while True:
                await asyncio.sleep(interval)
                if websocket in self.connection_metadata:
                    await self.ping(websocket)
                else:
                    break
        except Exception as e:
            logger.error(f"Heartbeat loop error: {str(e)}")
            self.disconnect(websocket)


# Global connection manager instance
manager = ConnectionManager()
