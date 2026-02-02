"""
Persistent Session Storage Module

Provides durable session storage using Redis for conversation state persistence.
This fixes the "AI forgetting mid-conversation" issue by persisting:
- Conversation history
- Session context
- Workflow state
- Agent relationships

Key improvements from multi-agent-orchestration-main:
- Redis for fast session retrieval
- PostgreSQL for permanent audit logs
- Session resumption after restarts
- Cross-service session sharing
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import uuid4

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class SessionStorage:
    """
    Redis-backed persistent session storage.
    
    Stores:
    - Conversation messages (with TTL)
    - Session metadata
    - Workflow states
    - Agent relationships
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        session_ttl_hours: int = 24,
        max_messages_per_session: int = 100,
    ):
        self.redis_url = redis_url
        self.session_ttl = timedelta(hours=session_ttl_hours)
        self.max_messages = max_messages_per_session
        self.redis: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self):
        """Connect to Redis."""
        if not self._connected:
            try:
                self.redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self.redis.ping()
                self._connected = True
                logger.info(f"Connected to Redis at {self.redis_url}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                # Fallback to in-memory storage
                self.redis = None
                self._connected = False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self._connected = False

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"session:{session_id}"

    def _messages_key(self, session_id: str) -> str:
        """Generate Redis key for session messages."""
        return f"messages:{session_id}"

    def _context_key(self, session_id: str) -> str:
        """Generate Redis key for session context."""
        return f"context:{session_id}"

    def _workflow_key(self, session_id: str) -> str:
        """Generate Redis key for session workflows."""
        return f"workflows:{session_id}"

    # ========================================================================
    # Session Operations
    # ========================================================================

    async def create_session(self, session_id: str = None) -> str:
        """Create a new session."""
        session_id = session_id or str(uuid4())
        
        session_data = {
            "id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "message_count": "0",
            "active_workflow": "",  # Redis doesn't accept None, use empty string
            "status": "active",
        }

        if self.redis and self._connected:
            await self.redis.hset(
                self._session_key(session_id),
                mapping=session_data
            )
            await self.redis.expire(
                self._session_key(session_id),
                int(self.session_ttl.total_seconds())
            )
        
        logger.info(f"Created session: {session_id}")
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data."""
        if self.redis and self._connected:
            data = await self.redis.hgetall(self._session_key(session_id))
            if data:
                # Refresh TTL on access
                await self.redis.expire(
                    self._session_key(session_id),
                    int(self.session_ttl.total_seconds())
                )
                return data
        return None

    async def update_session(self, session_id: str, updates: Dict):
        """Update session metadata."""
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        if self.redis and self._connected:
            await self.redis.hset(
                self._session_key(session_id),
                mapping=updates
            )

    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        if self.redis and self._connected:
            return await self.redis.exists(self._session_key(session_id)) > 0
        return False

    # ========================================================================
    # Message Operations (Critical for fixing memory issues)
    # ========================================================================

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Dict = None,
    ) -> Dict:
        """
        Add a message to session history.
        
        This is the core fix for conversation memory - messages are persisted
        in Redis and survive container restarts.
        """
        message = {
            "id": str(uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": json.dumps(metadata or {}),
        }

        if self.redis and self._connected:
            # Add to message list
            await self.redis.rpush(
                self._messages_key(session_id),
                json.dumps(message)
            )
            
            # Trim to max messages (keep recent history)
            await self.redis.ltrim(
                self._messages_key(session_id),
                -self.max_messages,
                -1
            )
            
            # Update message count
            await self.redis.hincrby(
                self._session_key(session_id),
                "message_count",
                1
            )
            
            # Refresh TTL
            await self.redis.expire(
                self._messages_key(session_id),
                int(self.session_ttl.total_seconds())
            )

        return message

    async def get_messages(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """
        Get messages from session history.
        
        Returns messages in chronological order (oldest first).
        Use negative offset for most recent messages.
        """
        messages = []
        
        if self.redis and self._connected:
            # Get messages (negative indices for recent)
            start = -limit - offset if offset else -limit
            end = -1 - offset if offset else -1
            
            raw_messages = await self.redis.lrange(
                self._messages_key(session_id),
                start,
                end
            )
            
            for raw in raw_messages:
                try:
                    msg = json.loads(raw)
                    msg["metadata"] = json.loads(msg.get("metadata", "{}"))
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue

        return messages

    async def get_all_messages(self, session_id: str) -> List[Dict]:
        """Get all messages for a session."""
        messages = []
        
        if self.redis and self._connected:
            raw_messages = await self.redis.lrange(
                self._messages_key(session_id),
                0,
                -1
            )
            
            for raw in raw_messages:
                try:
                    msg = json.loads(raw)
                    msg["metadata"] = json.loads(msg.get("metadata", "{}"))
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue

        return messages

    async def get_recent_context(self, session_id: str, num_messages: int = 20) -> List[Dict]:
        """
        Get recent messages formatted for LLM context.
        
        This is what gets passed to the LLM for conversation continuity.
        """
        messages = await self.get_messages(session_id, limit=num_messages)
        
        # Format for LLM consumption
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]

    # ========================================================================
    # Context Operations (Extended memory)
    # ========================================================================

    async def set_context(self, session_id: str, key: str, value: Any):
        """Store context data for a session."""
        if self.redis and self._connected:
            # Convert None to empty string for Redis compatibility
            if value is None:
                value = ""
            
            await self.redis.hset(
                self._context_key(session_id),
                key,
                json.dumps(value) if not isinstance(value, str) else value
            )
            await self.redis.expire(
                self._context_key(session_id),
                int(self.session_ttl.total_seconds())
            )

    async def get_context(self, session_id: str, key: str = None) -> Any:
        """Get context data from a session."""
        if self.redis and self._connected:
            if key:
                value = await self.redis.hget(self._context_key(session_id), key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
            else:
                # Return all context
                data = await self.redis.hgetall(self._context_key(session_id))
                result = {}
                for k, v in data.items():
                    try:
                        result[k] = json.loads(v)
                    except json.JSONDecodeError:
                        result[k] = v
                return result
        return None

    async def update_context(self, session_id: str, updates: Dict):
        """Update multiple context values."""
        for key, value in updates.items():
            await self.set_context(session_id, key, value)

    # ========================================================================
    # Workflow State Operations
    # ========================================================================

    async def save_workflow(self, session_id: str, workflow_id: str, workflow_data: Dict):
        """Save workflow state."""
        if self.redis and self._connected:
            await self.redis.hset(
                self._workflow_key(session_id),
                workflow_id,
                json.dumps(workflow_data)
            )
            
            # Update session's active workflow
            await self.update_session(session_id, {"active_workflow": workflow_id})

    async def get_workflow(self, session_id: str, workflow_id: str) -> Optional[Dict]:
        """Get workflow state."""
        if self.redis and self._connected:
            data = await self.redis.hget(
                self._workflow_key(session_id),
                workflow_id
            )
            if data:
                return json.loads(data)
        return None

    async def get_all_workflows(self, session_id: str) -> Dict[str, Dict]:
        """Get all workflows for a session."""
        workflows = {}
        if self.redis and self._connected:
            data = await self.redis.hgetall(self._workflow_key(session_id))
            for wf_id, wf_data in data.items():
                try:
                    workflows[wf_id] = json.loads(wf_data)
                except json.JSONDecodeError:
                    continue
        return workflows

    # ========================================================================
    # Cleanup Operations
    # ========================================================================

    async def delete_session(self, session_id: str):
        """Delete a session and all its data."""
        if self.redis and self._connected:
            await self.redis.delete(
                self._session_key(session_id),
                self._messages_key(session_id),
                self._context_key(session_id),
                self._workflow_key(session_id),
            )
            logger.info(f"Deleted session: {session_id}")

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions (run periodically)."""
        # Redis handles this automatically via TTL, but this can be used
        # for additional cleanup logic if needed
        pass


class InMemorySessionStorage:
    """
    In-memory fallback when Redis is unavailable.
    
    This provides the same interface as SessionStorage but stores
    everything in memory. Data is lost on restart.
    """

    def __init__(self, max_messages_per_session: int = 100):
        self.sessions: Dict[str, Dict] = {}
        self.messages: Dict[str, List[Dict]] = {}
        self.contexts: Dict[str, Dict] = {}
        self.workflows: Dict[str, Dict[str, Dict]] = {}
        self.max_messages = max_messages_per_session

    async def connect(self):
        """No-op for in-memory storage."""
        pass

    async def disconnect(self):
        """No-op for in-memory storage."""
        pass

    async def create_session(self, session_id: str = None) -> str:
        session_id = session_id or str(uuid4())
        self.sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "message_count": 0,
            "active_workflow": None,
            "status": "active",
        }
        self.messages[session_id] = []
        self.contexts[session_id] = {}
        self.workflows[session_id] = {}
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)

    async def update_session(self, session_id: str, updates: Dict):
        if session_id in self.sessions:
            self.sessions[session_id].update(updates)
            self.sessions[session_id]["updated_at"] = datetime.utcnow().isoformat()

    async def session_exists(self, session_id: str) -> bool:
        return session_id in self.sessions

    async def add_message(
        self, session_id: str, role: str, content: str, metadata: Dict = None
    ) -> Dict:
        if session_id not in self.messages:
            self.messages[session_id] = []
        
        message = {
            "id": str(uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        
        self.messages[session_id].append(message)
        
        # Trim to max messages
        if len(self.messages[session_id]) > self.max_messages:
            self.messages[session_id] = self.messages[session_id][-self.max_messages:]
        
        if session_id in self.sessions:
            self.sessions[session_id]["message_count"] = len(self.messages[session_id])
        
        return message

    async def get_messages(self, session_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        msgs = self.messages.get(session_id, [])
        start = max(0, len(msgs) - limit - offset)
        end = len(msgs) - offset if offset else len(msgs)
        return msgs[start:end]

    async def get_all_messages(self, session_id: str) -> List[Dict]:
        return self.messages.get(session_id, [])

    async def get_recent_context(self, session_id: str, num_messages: int = 20) -> List[Dict]:
        messages = await self.get_messages(session_id, limit=num_messages)
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

    async def set_context(self, session_id: str, key: str, value: Any):
        if session_id not in self.contexts:
            self.contexts[session_id] = {}
        self.contexts[session_id][key] = value

    async def get_context(self, session_id: str, key: str = None) -> Any:
        if session_id not in self.contexts:
            return None
        if key:
            return self.contexts[session_id].get(key)
        return self.contexts[session_id]

    async def update_context(self, session_id: str, updates: Dict):
        for key, value in updates.items():
            await self.set_context(session_id, key, value)

    async def save_workflow(self, session_id: str, workflow_id: str, workflow_data: Dict):
        if session_id not in self.workflows:
            self.workflows[session_id] = {}
        self.workflows[session_id][workflow_id] = workflow_data
        await self.update_session(session_id, {"active_workflow": workflow_id})

    async def get_workflow(self, session_id: str, workflow_id: str) -> Optional[Dict]:
        return self.workflows.get(session_id, {}).get(workflow_id)

    async def get_all_workflows(self, session_id: str) -> Dict[str, Dict]:
        return self.workflows.get(session_id, {})

    async def delete_session(self, session_id: str):
        self.sessions.pop(session_id, None)
        self.messages.pop(session_id, None)
        self.contexts.pop(session_id, None)
        self.workflows.pop(session_id, None)


# Global storage instance (switches between Redis and in-memory)
_storage: Optional[SessionStorage] = None
_fallback_storage: Optional[InMemorySessionStorage] = None


async def get_session_storage(redis_url: str = None) -> SessionStorage:
    """Get the session storage instance (Redis with in-memory fallback)."""
    global _storage, _fallback_storage
    
    if _storage is None:
        _storage = SessionStorage(redis_url=redis_url or "redis://redis:6379")
        await _storage.connect()
        
        # If Redis connection failed, use in-memory fallback
        if not _storage._connected:
            logger.warning("Redis unavailable, using in-memory session storage")
            _fallback_storage = InMemorySessionStorage()
            return _fallback_storage
    
    if not _storage._connected:
        if _fallback_storage is None:
            _fallback_storage = InMemorySessionStorage()
        return _fallback_storage
    
    return _storage
