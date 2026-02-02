"""
WebSocket Manager Module
Handles WebSocket connections and event broadcasting for real-time updates.

Key features adopted from multi-agent-orchestration-main:
- Real-time chat streaming
- Agent status broadcasting
- Inter-agent communication channels
- Connection state management
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections and broadcasts events to all connected clients.
    
    This provides the real-time communication backbone for:
    - Orchestrator ↔ Frontend streaming
    - Agent ↔ Orchestrator status updates  
    - Agent ↔ Agent inter-communication
    """

    def __init__(self):
        # Active WebSocket connections
        self.active_connections: List[WebSocket] = []
        
        # Connection metadata (client ID, connected time, subscriptions)
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Agent-specific channels for targeted messaging
        self.agent_channels: Dict[str, Set[WebSocket]] = {}
        
        # Message buffer for late joiners (last N messages per channel)
        self.message_buffer: Dict[str, List[Dict]] = {}
        self.buffer_size = 50
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str = None):
        """
        Accept a new WebSocket connection and register it.
        
        Args:
            websocket: The WebSocket connection
            client_id: Optional client identifier
        """
        await websocket.accept()
        
        async with self._lock:
            self.active_connections.append(websocket)
            
            # Store metadata
            client_id = client_id or f"client_{len(self.active_connections)}"
            self.connection_metadata[websocket] = {
                "client_id": client_id,
                "connected_at": datetime.utcnow().isoformat(),
                "subscriptions": set(),
            }
        
        logger.info(
            f"WebSocket client connected: {client_id} | "
            f"Total connections: {len(self.active_connections)}"
        )
        
        # Send welcome message
        await self.send_to_client(
            websocket,
            {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to Agentic Framework Orchestrator",
            },
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection from the active list."""
        if websocket in self.active_connections:
            metadata = self.connection_metadata.get(websocket, {})
            client_id = metadata.get("client_id", "unknown")
            
            self.active_connections.remove(websocket)
            self.connection_metadata.pop(websocket, None)
            
            # Remove from all agent channels
            for channel_sockets in self.agent_channels.values():
                channel_sockets.discard(websocket)
            
            logger.warning(
                f"WebSocket client disconnected: {client_id} | "
                f"Total connections: {len(self.active_connections)}"
            )

    async def send_to_client(self, websocket: WebSocket, data: dict):
        """Send JSON data to a specific client."""
        try:
            await websocket.send_json(data)
            logger.debug(f"📤 Sent to client: {data.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to send to client: {e}")
            self.disconnect(websocket)

    async def broadcast(self, data: dict, exclude: WebSocket = None):
        """
        Broadcast JSON data to all connected clients (except optionally one).
        
        Args:
            data: Message payload to broadcast
            exclude: Optional WebSocket to exclude from broadcast
        """
        if not self.active_connections:
            logger.debug(f"No active connections, skipping broadcast: {data.get('type')}")
            return

        event_type = data.get("type", "unknown")
        
        # Add timestamp if not present
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow().isoformat()

        disconnected = []

        for connection in self.active_connections:
            if connection == exclude:
                continue

            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"Failed to broadcast to client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)

        logger.debug(
            f"📡 Broadcast complete: {event_type} → {len(self.active_connections) - len(disconnected)} clients"
        )

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)

    # ========================================================================
    # Agent Channel Management (for inter-agent communication)
    # ========================================================================

    async def subscribe_to_agent(self, websocket: WebSocket, agent_id: str):
        """Subscribe a connection to a specific agent's updates."""
        if agent_id not in self.agent_channels:
            self.agent_channels[agent_id] = set()
        
        self.agent_channels[agent_id].add(websocket)
        
        # Update connection metadata
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].add(agent_id)
        
        logger.debug(f"Client subscribed to agent: {agent_id}")

    async def unsubscribe_from_agent(self, websocket: WebSocket, agent_id: str):
        """Unsubscribe a connection from an agent's updates."""
        if agent_id in self.agent_channels:
            self.agent_channels[agent_id].discard(websocket)
        
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].discard(agent_id)

    async def broadcast_to_agent_channel(self, agent_id: str, data: dict):
        """Broadcast to all subscribers of a specific agent channel."""
        if agent_id not in self.agent_channels:
            return
        
        data["timestamp"] = datetime.utcnow().isoformat()
        data["agent_id"] = agent_id
        
        disconnected = []
        for ws in self.agent_channels[agent_id]:
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send to agent channel: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            self.agent_channels[agent_id].discard(ws)

    # ========================================================================
    # Event Broadcasting Methods
    # ========================================================================

    async def broadcast_agent_created(self, agent_data: dict):
        """Broadcast agent creation event."""
        await self.broadcast({"type": "agent_created", "agent": agent_data})

    async def broadcast_agent_updated(self, agent_id: str, agent_data: dict):
        """Broadcast agent update event."""
        await self.broadcast(
            {"type": "agent_updated", "agent_id": agent_id, "agent": agent_data}
        )

    async def broadcast_agent_deleted(self, agent_id: str):
        """Broadcast agent deletion event."""
        await self.broadcast({"type": "agent_deleted", "agent_id": agent_id})

    async def broadcast_agent_status_change(
        self, agent_id: str, old_status: str, new_status: str
    ):
        """Broadcast agent status change."""
        await self.broadcast(
            {
                "type": "agent_status_changed",
                "agent_id": agent_id,
                "old_status": old_status,
                "new_status": new_status,
            }
        )
        # Also send to agent's channel
        await self.broadcast_to_agent_channel(
            agent_id,
            {"type": "status_changed", "old_status": old_status, "new_status": new_status}
        )

    async def broadcast_agent_log(self, log_data: dict):
        """Broadcast agent log entry."""
        await self.broadcast({"type": "agent_log", "log": log_data})
        
        # Also send to specific agent's channel if agent_id is present
        if "agent_id" in log_data:
            await self.broadcast_to_agent_channel(
                log_data["agent_id"],
                {"type": "log", "log": log_data}
            )

    async def broadcast_agent_message(
        self, from_agent_id: str, to_agent_id: str, message: str, message_type: str = "message"
    ):
        """
        Broadcast a message from one agent to another.
        This enables real-time agent-to-agent communication.
        """
        data = {
            "type": "agent_message",
            "message_type": message_type,
            "from_agent": from_agent_id,
            "to_agent": to_agent_id,
            "message": message,
        }
        
        # Broadcast globally
        await self.broadcast(data)
        
        # Also send to both agents' channels
        await self.broadcast_to_agent_channel(from_agent_id, data)
        if to_agent_id != from_agent_id:
            await self.broadcast_to_agent_channel(to_agent_id, data)

    async def broadcast_orchestrator_updated(self, orchestrator_data: dict):
        """Broadcast orchestrator update (cost, tokens, status, etc.)."""
        await self.broadcast({
            "type": "orchestrator_updated",
            "orchestrator": orchestrator_data
        })

    async def broadcast_system_log(self, log_data: dict):
        """Broadcast system log entry."""
        await self.broadcast({"type": "system_log", "log": log_data})

    async def broadcast_chat_message(self, message_data: dict):
        """Broadcast chat message."""
        await self.broadcast({"type": "chat_message", "message": message_data})
        
        # Buffer the message
        self._buffer_message("chat", message_data)

    async def broadcast_error(self, error_message: str, details: dict = None):
        """Broadcast error event."""
        await self.broadcast(
            {
                "type": "error",
                "message": error_message,
                "details": details or {},
            }
        )

    async def broadcast_chat_stream(
        self, session_id: str, chunk: str, is_complete: bool = False
    ):
        """
        Broadcast chat response chunk for real-time streaming.

        Args:
            session_id: Session identifier
            chunk: Text chunk to stream
            is_complete: True if this is the final chunk
        """
        await self.broadcast(
            {
                "type": "chat_stream",
                "session_id": session_id,
                "chunk": chunk,
                "is_complete": is_complete,
            }
        )

    async def broadcast_workflow_update(
        self, workflow_id: str, status: str, step: str = None, result: dict = None
    ):
        """Broadcast workflow status update."""
        await self.broadcast(
            {
                "type": "workflow_update",
                "workflow_id": workflow_id,
                "status": status,
                "current_step": step,
                "result": result,
            }
        )

    async def broadcast_agent_collaboration(
        self, agent_ids: List[str], topic: str, status: str
    ):
        """
        Broadcast that multiple agents are collaborating on a topic.
        This is key for showing real-time parallel agent work.
        """
        await self.broadcast(
            {
                "type": "agent_collaboration",
                "agent_ids": agent_ids,
                "topic": topic,
                "status": status,
            }
        )
        
        # Notify each agent's channel
        for agent_id in agent_ids:
            await self.broadcast_to_agent_channel(
                agent_id,
                {"type": "collaboration_update", "topic": topic, "status": status, "participants": agent_ids}
            )

    # ========================================================================
    # Message Buffering (for late joiners)
    # ========================================================================

    def _buffer_message(self, channel: str, message: dict):
        """Buffer a message for late-joining clients."""
        if channel not in self.message_buffer:
            self.message_buffer[channel] = []
        
        self.message_buffer[channel].append(message)
        
        # Keep only last N messages
        if len(self.message_buffer[channel]) > self.buffer_size:
            self.message_buffer[channel] = self.message_buffer[channel][-self.buffer_size:]

    async def send_buffered_messages(self, websocket: WebSocket, channel: str):
        """Send buffered messages to a newly connected client."""
        if channel in self.message_buffer:
            for msg in self.message_buffer[channel]:
                try:
                    await websocket.send_json({
                        "type": "buffered_message",
                        "channel": channel,
                        "message": msg
                    })
                except Exception:
                    break


# Global singleton instance
_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
