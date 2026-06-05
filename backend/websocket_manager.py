"""
websocket_manager.py
─────────────────────
WebSocket connection manager for real-time updates.

Manages:
- Connection lifecycle
- Message broadcasting
- Session state sync
- Reconnection handling

Usage:
    from backend.websocket_manager import WebSocketManager
    
    manager = WebSocketManager()
    
    # In FastAPI endpoint
    async def websocket_endpoint(websocket):
        await manager.connect(session_id, websocket)
        try:
            while True:
                data = await websocket.receive_json()
                await manager.broadcast(session_id, data)
        finally:
            manager.disconnect(session_id)
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.logging_config import get_logger

logger = get_logger(__name__)


class WebSocketMessage(BaseModel):
    """Standard WebSocket message format."""
    
    id: str  # Unique message ID
    type: str  # Message type (e.g., "chat", "status", "heartbeat")
    timestamp: str  # ISO format timestamp
    data: dict[str, Any]  # Message payload
    session_id: Optional[str] = None  # Session ID
    user_id: Optional[str] = None  # User ID
    
    class Config:
        extra = "allow"


class WebSocketConnection:
    """Represents a single WebSocket connection."""
    
    def __init__(self, websocket: WebSocket, session_id: str, user_id: Optional[str] = None):
        self.websocket = websocket
        self.session_id = session_id
        self.user_id = user_id
        self.connection_id = str(uuid4())
        self.connected_at = datetime.now(timezone.utc)
        self.last_heartbeat = datetime.now(timezone.utc)
    
    async def send(self, message: WebSocketMessage) -> None:
        """Send message to client."""
        try:
            await self.websocket.send_json(message.dict())
            self.last_heartbeat = datetime.now(timezone.utc)
        except Exception as e:
            logger.error(
                "Failed to send WebSocket message",
                extra={
                    "connection_id": self.connection_id,
                    "error": str(e),
                }
            )
            raise
    
    async def receive(self) -> dict[str, Any]:
        """Receive message from client."""
        return await self.websocket.receive_json()
    
    async def close(self, code: int = 1000, reason: str = "Normal closure") -> None:
        """Close connection."""
        try:
            await self.websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.debug(
                "Connection already closed",
                extra={
                    "connection_id": self.connection_id,
                    "error": str(e),
                }
            )
    
    def is_alive(self) -> bool:
        """Check if connection is still active."""
        return self.websocket.application_state.name == "connected"
    
    def to_dict(self) -> dict[str, Any]:
        """Export connection metadata."""
        return {
            "connection_id": self.connection_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "connected_at": self.connected_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
        }


class WebSocketManager:
    """Manages WebSocket connections and broadcasting."""
    
    def __init__(self):
        self.connections: dict[str, list[WebSocketConnection]] = {}  # session_id -> [connections]
        self.user_sessions: dict[str, set[str]] = {}  # user_id -> set of session_ids
        self.message_handlers: dict[str, Callable] = {}  # message_type -> handler
    
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a specific message type."""
        self.message_handlers[message_type] = handler
        logger.info(
            "WebSocket handler registered",
            extra={"message_type": message_type}
        )
    
    async def connect(
        self,
        session_id: str,
        websocket: WebSocket,
        user_id: Optional[str] = None,
    ) -> WebSocketConnection:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            session_id: Session identifier
            websocket: FastAPI WebSocket
            user_id: Optional user identifier
            
        Returns:
            WebSocketConnection object
        """
        await websocket.accept()
        
        connection = WebSocketConnection(websocket, session_id, user_id)
        
        # Add to connections
        if session_id not in self.connections:
            self.connections[session_id] = []
        self.connections[session_id].append(connection)
        
        # Track user sessions
        if user_id:
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)
        
        logger.info(
            "WebSocket connected",
            extra={
                "connection_id": connection.connection_id,
                "session_id": session_id,
                "user_id": user_id,
                "total_connections": len(self.connections[session_id]),
            }
        )
        
        # Send welcome message
        welcome = WebSocketMessage(
            id=str(uuid4()),
            type="welcome",
            timestamp=datetime.now(timezone.utc).isoformat(),
            data={
                "connection_id": connection.connection_id,
                "session_id": session_id,
            },
            session_id=session_id,
            user_id=user_id,
        )
        
        await connection.send(welcome)
        
        return connection
    
    def disconnect(self, session_id: str, connection_id: str) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            session_id: Session identifier
            connection_id: Connection identifier
        """
        if session_id not in self.connections:
            return
        
        connections = self.connections[session_id]
        connection = next(
            (c for c in connections if c.connection_id == connection_id),
            None,
        )
        
        if connection:
            if connection.user_id:
                self.user_sessions.get(connection.user_id, set()).discard(session_id)
            
            connections.remove(connection)
            
            logger.info(
                "WebSocket disconnected",
                extra={
                    "connection_id": connection_id,
                    "session_id": session_id,
                    "remaining": len(connections),
                }
            )
            
            # Clean up empty session
            if not connections:
                del self.connections[session_id]
    
    async def broadcast(
        self,
        session_id: str,
        message: WebSocketMessage,
        exclude_connection_id: Optional[str] = None,
    ) -> int:
        """
        Broadcast message to all connections in a session.
        
        Args:
            session_id: Target session
            message: Message to broadcast
            exclude_connection_id: Optionally exclude sender
            
        Returns:
            Number of recipients
        """
        if session_id not in self.connections:
            return 0
        
        connections = self.connections[session_id]
        failed = []
        count = 0
        
        for connection in list(connections):
            if exclude_connection_id and connection.connection_id == exclude_connection_id:
                continue
            
            try:
                await connection.send(message)
                count += 1
            except Exception as e:
                logger.warning(
                    "Broadcast send failed",
                    extra={
                        "connection_id": connection.connection_id,
                        "error": str(e),
                    }
                )
                failed.append(connection.connection_id)
        
        # Clean up failed connections
        for connection_id in failed:
            self.disconnect(session_id, connection_id)
        
        return count
    
    async def broadcast_to_user(
        self,
        user_id: str,
        message: WebSocketMessage,
    ) -> int:
        """Broadcast to all sessions of a user."""
        session_ids = self.user_sessions.get(user_id, set())
        count = 0
        
        for session_id in session_ids:
            count += await self.broadcast(session_id, message)
        
        return count
    
    async def send_to_connection(
        self,
        session_id: str,
        connection_id: str,
        message: WebSocketMessage,
    ) -> bool:
        """Send message to specific connection."""
        if session_id not in self.connections:
            return False
        
        connection = next(
            (c for c in self.connections[session_id] if c.connection_id == connection_id),
            None,
        )
        
        if not connection:
            return False
        
        try:
            await connection.send(message)
            return True
        except Exception as e:
            logger.error(
                "Failed to send to connection",
                extra={
                    "connection_id": connection_id,
                    "session_id": session_id,
                    "error": str(e),
                }
            )
            return False
    
    async def handle_message(
        self,
        session_id: str,
        connection_id: str,
        message: WebSocketMessage,
    ) -> None:
        """
        Handle incoming message.
        
        Args:
            session_id: Session ID
            connection_id: Connection ID
            message: Received message
        """
        handler = self.message_handlers.get(message.type)
        
        if handler:
            try:
                response = await handler(message) if asyncio.iscoroutinefunction(handler) else handler(message)
                if response:
                    response_msg = WebSocketMessage(
                        id=str(uuid4()),
                        type=f"{message.type}_response",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        data=response,
                        session_id=session_id,
                    )
                    await self.send_to_connection(session_id, connection_id, response_msg)
            except Exception as e:
                logger.error(
                    "Message handler error",
                    extra={
                        "message_type": message.type,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                
                error_msg = WebSocketMessage(
                    id=str(uuid4()),
                    type="error",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    data={"error": str(e), "original_type": message.type},
                    session_id=session_id,
                )
                await self.send_to_connection(session_id, connection_id, error_msg)
        else:
            logger.warning(
                "No handler for message type",
                extra={"message_type": message.type}
            )
    
    def get_connections(self, session_id: str) -> list[dict[str, Any]]:
        """Get all connections for a session."""
        if session_id not in self.connections:
            return []
        
        return [c.to_dict() for c in self.connections[session_id]]
    
    def get_session_info(self, session_id: str) -> dict[str, Any]:
        """Get session information."""
        connections = self.connections.get(session_id, [])
        return {
            "session_id": session_id,
            "connection_count": len(connections),
            "connections": [c.to_dict() for c in connections],
        }
    
    def get_user_sessions(self, user_id: str) -> list[str]:
        """Get all session IDs for a user."""
        return list(self.user_sessions.get(user_id, set()))
    
    def get_stats(self) -> dict[str, Any]:
        """Get manager statistics."""
        total_connections = sum(len(conns) for conns in self.connections.values())
        return {
            "total_sessions": len(self.connections),
            "total_connections": total_connections,
            "total_users": len(self.user_sessions),
            "registered_handlers": len(self.message_handlers),
        }
    
    async def heartbeat(self) -> None:
        """Send heartbeat to all connections."""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        for session_id in list(self.connections.keys()):
            message = WebSocketMessage(
                id=str(uuid4()),
                type="heartbeat",
                timestamp=timestamp,
                data={"timestamp": timestamp},
                session_id=session_id,
            )
            await self.broadcast(session_id, message)


# Global WebSocket manager instance
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """Get or create global WebSocket manager."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
