"""
OpenClaw LLM Adapter

Connects to the OpenClaw Gateway (ws://127.0.0.1:18789) for local LLM inference
using DeepSeek R1 via Ollama. Each agent runs as an independent OpenClaw instance
with its own session, workspace, and skills.

OpenClaw features used:
- Gateway WebSocket control plane
- Multi-session routing (sessions_* tools)
- Local model support via ollama/deepseek-r1:14b
- Skills registry for agent capabilities
- Agent-to-agent communication via sessions_send
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import websockets
from websockets.exceptions import ConnectionClosed

from .base import LLMAdapter, LLMMessage, LLMResponse, MessageRole

logger = logging.getLogger(__name__)


class OpenClawSession:
    """
    Represents an OpenClaw agent session with its own workspace and state.
    
    Each agent (orchestrator, subagent, code agent, etc.) runs as a separate
    session within the OpenClaw Gateway, enabling agent-to-agent communication.
    """
    
    def __init__(
        self,
        session_id: str,
        agent_name: str,
        agent_role: str,
        model: str = "ollama/deepseek-r1:14b",
        thinking_level: str = "medium",
    ):
        self.session_id = session_id
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.model = model
        self.thinking_level = thinking_level
        self.created_at = datetime.utcnow()
        self.message_history: List[Dict] = []
        self.active = False
        
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "model": self.model,
            "thinking_level": self.thinking_level,
            "created_at": self.created_at.isoformat(),
            "message_count": len(self.message_history),
            "active": self.active
        }


class OpenClawAdapter(LLMAdapter):
    """
    LLM Adapter that connects to OpenClaw Gateway for local inference.
    
    This adapter:
    - Connects to the OpenClaw Gateway WebSocket
    - Creates and manages agent sessions
    - Routes messages through the Pi agent runtime
    - Supports agent-to-agent communication via sessions_send
    - Uses local DeepSeek R1 via Ollama (no API keys required)
    
    Configuration:
        gateway_url: OpenClaw Gateway WebSocket URL (default: ws://127.0.0.1:18789)
        model: Local model identifier (default: ollama/deepseek-r1:14b)
        workspace: Agent workspace path (default: ~/.openclaw/workspace)
    """
    
    def __init__(
        self,
        model: str = "ollama/deepseek-r1:14b",
        gateway_url: str = "ws://127.0.0.1:18789",
        workspace: str = None,
        thinking_level: str = "medium",
        **kwargs: Any
    ) -> None:
        super().__init__(model=model, api_key=None, **kwargs)
        
        self.gateway_url = gateway_url
        self.workspace = workspace or "~/.openclaw/workspace"
        self.thinking_level = thinking_level
        
        # WebSocket connection
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._connection_lock = asyncio.Lock()
        
        # Session management
        self._sessions: Dict[str, OpenClawSession] = {}
        self._main_session_id: Optional[str] = None
        
        # Message tracking
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._message_handler_task: Optional[asyncio.Task] = None
        
        logger.info(f"OpenClaw adapter initialized: gateway={gateway_url}, model={model}")
    
    async def connect(self) -> bool:
        """
        Establish connection to OpenClaw Gateway.
        
        Returns:
            True if connection successful, False otherwise
        """
        async with self._connection_lock:
            if self._connected and self._ws:
                return True
            
            try:
                logger.info(f"Connecting to OpenClaw Gateway: {self.gateway_url}")
                self._ws = await websockets.connect(
                    self.gateway_url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5
                )
                self._connected = True
                
                # Start message handler
                self._message_handler_task = asyncio.create_task(
                    self._handle_messages()
                )
                
                # Initialize main session
                self._main_session_id = await self._create_session(
                    agent_name="orchestrator",
                    agent_role="orchestrator"
                )
                
                logger.info(f"Connected to OpenClaw Gateway, main session: {self._main_session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect to OpenClaw Gateway: {e}")
                self._connected = False
                return False
    
    async def disconnect(self) -> None:
        """Close connection to OpenClaw Gateway."""
        if self._message_handler_task:
            self._message_handler_task.cancel()
            try:
                await self._message_handler_task
            except asyncio.CancelledError:
                pass
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        self._connected = False
        self._sessions.clear()
        logger.info("Disconnected from OpenClaw Gateway")
    
    async def _handle_messages(self) -> None:
        """Background task to handle incoming WebSocket messages."""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from Gateway: {message[:100]}")
        except ConnectionClosed:
            logger.warning("OpenClaw Gateway connection closed")
            self._connected = False
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            self._connected = False
    
    async def _process_message(self, data: Dict) -> None:
        """Process incoming message from Gateway."""
        msg_type = data.get("type")
        request_id = data.get("requestId")
        
        if request_id and request_id in self._pending_requests:
            # This is a response to a pending request
            future = self._pending_requests.pop(request_id)
            if not future.done():
                if data.get("error"):
                    future.set_exception(Exception(data["error"]))
                else:
                    future.set_result(data)
        
        elif msg_type == "agent.response":
            # Streaming agent response
            session_id = data.get("sessionId")
            if session_id in self._sessions:
                session = self._sessions[session_id]
                session.message_history.append({
                    "role": "assistant",
                    "content": data.get("content", ""),
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        elif msg_type == "sessions.message":
            # Agent-to-agent message
            logger.info(f"Inter-agent message: {data}")
    
    async def _send_request(
        self,
        method: str,
        params: Dict = None,
        timeout: float = 120.0
    ) -> Dict:
        """
        Send request to Gateway and await response.
        
        Args:
            method: Gateway method (e.g., "agent.send", "sessions.list")
            params: Method parameters
            timeout: Response timeout in seconds
            
        Returns:
            Response data from Gateway
        """
        if not self._connected:
            await self.connect()
        
        request_id = str(uuid4())
        request = {
            "type": method,
            "requestId": request_id,
            "params": params or {}
        }
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future
        
        try:
            await self._ws.send(json.dumps(request))
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"Gateway request timed out: {method}")
        except Exception as e:
            self._pending_requests.pop(request_id, None)
            raise
    
    async def _create_session(
        self,
        agent_name: str,
        agent_role: str,
        system_prompt: str = None
    ) -> str:
        """
        Create a new agent session in OpenClaw.
        
        Args:
            agent_name: Name for the agent
            agent_role: Role (orchestrator, code, research, etc.)
            system_prompt: Custom system prompt
            
        Returns:
            Session ID
        """
        session_id = f"{agent_role}-{uuid4().hex[:8]}"
        
        session = OpenClawSession(
            session_id=session_id,
            agent_name=agent_name,
            agent_role=agent_role,
            model=self.model,
            thinking_level=self.thinking_level
        )
        
        # Register session with Gateway
        response = await self._send_request("sessions.create", {
            "sessionId": session_id,
            "model": self.model,
            "thinkingLevel": self.thinking_level,
            "workspace": self.workspace,
            "systemPrompt": system_prompt or self._get_default_system_prompt(agent_role)
        })
        
        session.active = True
        self._sessions[session_id] = session
        
        logger.info(f"Created OpenClaw session: {session_id} ({agent_name})")
        return session_id
    
    def _get_default_system_prompt(self, agent_role: str) -> str:
        """Get default system prompt for agent role."""
        prompts = {
            "orchestrator": """You are the Orchestrator Agent - the central coordinator of a multi-agent system.
Your responsibilities:
- Analyze incoming requests and determine which specialized agents to invoke
- Coordinate work between Research, Code, Verify, and Synthesis agents
- Aggregate results and provide comprehensive responses
- Manage agent lifecycle and inter-agent communication

You have access to these agent types:
- ResearchAgent: Deep web research and information gathering
- CodeAgent: Code generation, modification, and execution
- VerifyAgent: Validation, testing, and quality checks
- SynthesisAgent: Combining results and generating summaries

For complex tasks, spawn multiple agents to work in parallel.
Always learn from past attempts via the memory system.""",

            "code": """You are a Code Agent - specialized in software development.
Your responsibilities:
- Generate high-quality, production-ready code
- Modify existing codebases following best practices
- Execute code and analyze results
- Debug issues and implement fixes

Guidelines:
- Write clean, documented, testable code
- Follow language-specific conventions
- Consider edge cases and error handling
- Use the diary system to log your implementation attempts
- Apply learnings from past similar tasks""",

            "research": """You are a Research Agent - specialized in information gathering.
Your responsibilities:
- Search and analyze documentation
- Gather context from multiple sources
- Synthesize findings into actionable insights
- Support other agents with background research

Guidelines:
- Verify information from multiple sources
- Cite sources and provide references
- Focus on relevant, actionable information
- Log research sessions in the diary system""",

            "verify": """You are a Verify Agent - specialized in validation and testing.
Your responsibilities:
- Run tests and quality checks
- Validate code against requirements
- Check for security vulnerabilities
- Ensure compliance with standards

Guidelines:
- Be thorough and systematic
- Report all findings clearly
- Suggest fixes for issues found
- Track verification results in diary""",

            "synthesis": """You are a Synthesis Agent - specialized in combining and summarizing.
Your responsibilities:
- Aggregate results from multiple agents
- Generate comprehensive summaries
- Identify patterns and insights
- Create final deliverables

Guidelines:
- Maintain context across agent outputs
- Highlight key findings
- Provide actionable recommendations
- Document synthesis process in diary"""
        }
        
        return prompts.get(agent_role, prompts["orchestrator"])
    
    async def complete(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Complete a conversation using OpenClaw Gateway.
        
        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Available tools for function calling
            tool_choice: Tool selection strategy
            **kwargs: Additional parameters
            
        Returns:
            LLM response with content and metadata
        """
        if not self._connected:
            await self.connect()
        
        session_id = kwargs.get("session_id", self._main_session_id)
        
        # Format messages for OpenClaw
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role.value if isinstance(msg.role, MessageRole) else msg.role,
                "content": msg.content
            })
        
        # Send to agent
        start_time = datetime.utcnow()
        response = await self._send_request("agent.send", {
            "sessionId": session_id,
            "messages": formatted_messages,
            "model": self.model,
            "temperature": temperature,
            "maxTokens": max_tokens,
            "tools": tools,
            "toolChoice": tool_choice,
            "thinking": self.thinking_level
        })
        
        # Parse response
        content = response.get("content", "")
        tool_calls = response.get("toolCalls")
        usage = response.get("usage", {})
        
        # Track in session history
        if session_id in self._sessions:
            self._sessions[session_id].message_history.extend([
                {"role": "user", "content": messages[-1].content if messages else ""},
                {"role": "assistant", "content": content}
            ])
        
        return LLMResponse(
            content=content,
            finish_reason=response.get("finishReason", "stop"),
            model=self.model,
            usage={
                "prompt_tokens": usage.get("promptTokens", 0),
                "completion_tokens": usage.get("completionTokens", 0),
                "total_tokens": usage.get("totalTokens", 0)
            },
            tool_calls=tool_calls,
            raw_response=response,
            timestamp=datetime.utcnow()
        )
    
    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ):
        """
        Stream a response from OpenClaw Gateway.
        
        Yields response chunks as they arrive.
        """
        if not self._connected:
            await self.connect()
        
        session_id = kwargs.get("session_id", self._main_session_id)
        
        # Format messages
        formatted_messages = [
            {
                "role": msg.role.value if isinstance(msg.role, MessageRole) else msg.role,
                "content": msg.content
            }
            for msg in messages
        ]
        
        # Send streaming request
        request_id = str(uuid4())
        await self._ws.send(json.dumps({
            "type": "agent.stream",
            "requestId": request_id,
            "params": {
                "sessionId": session_id,
                "messages": formatted_messages,
                "model": self.model,
                "temperature": temperature,
                "maxTokens": max_tokens,
                "thinking": self.thinking_level
            }
        }))
        
        # Yield chunks
        full_content = ""
        async for message in self._ws:
            try:
                data = json.loads(message)
                if data.get("requestId") == request_id:
                    if data.get("type") == "agent.chunk":
                        chunk = data.get("content", "")
                        full_content += chunk
                        yield chunk
                    elif data.get("type") == "agent.done":
                        break
                    elif data.get("error"):
                        raise Exception(data["error"])
            except json.JSONDecodeError:
                continue
    
    # ============ Agent-to-Agent Communication ============
    
    async def create_agent_session(
        self,
        agent_name: str,
        agent_role: str,
        system_prompt: str = None
    ) -> str:
        """
        Create a new agent session for spawning sub-agents.
        
        Args:
            agent_name: Name for the agent
            agent_role: Role type
            system_prompt: Custom system prompt
            
        Returns:
            Session ID for the new agent
        """
        return await self._create_session(agent_name, agent_role, system_prompt)
    
    async def send_to_agent(
        self,
        target_session_id: str,
        message: str,
        reply_back: bool = True
    ) -> Optional[str]:
        """
        Send message to another agent session (sessions_send).
        
        Args:
            target_session_id: Target agent's session ID
            message: Message content
            reply_back: Whether to await reply
            
        Returns:
            Reply content if reply_back=True
        """
        response = await self._send_request("sessions.send", {
            "targetSessionId": target_session_id,
            "message": message,
            "replyBack": reply_back
        })
        
        return response.get("reply") if reply_back else None
    
    async def list_agent_sessions(self) -> List[Dict]:
        """
        List all active agent sessions (sessions_list).
        
        Returns:
            List of session metadata
        """
        response = await self._send_request("sessions.list", {})
        return response.get("sessions", [])
    
    async def get_agent_history(self, session_id: str) -> List[Dict]:
        """
        Get message history for an agent session (sessions_history).
        
        Args:
            session_id: Agent session ID
            
        Returns:
            Message history
        """
        response = await self._send_request("sessions.history", {
            "sessionId": session_id
        })
        return response.get("history", [])
    
    async def terminate_agent_session(self, session_id: str) -> bool:
        """
        Terminate an agent session.
        
        Args:
            session_id: Session to terminate
            
        Returns:
            True if successful
        """
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)
            session.active = False
        
        response = await self._send_request("sessions.terminate", {
            "sessionId": session_id
        })
        
        return response.get("success", False)
    
    # ============ Skills Management ============
    
    async def list_skills(self) -> List[Dict]:
        """List available skills from ClawHub registry."""
        response = await self._send_request("skills.list", {})
        return response.get("skills", [])
    
    async def invoke_skill(
        self,
        skill_name: str,
        params: Dict = None
    ) -> Dict:
        """
        Invoke a skill from the registry.
        
        Args:
            skill_name: Name of the skill to invoke
            params: Skill parameters
            
        Returns:
            Skill execution result
        """
        response = await self._send_request("skills.invoke", {
            "skill": skill_name,
            "params": params or {}
        })
        return response
    
    # ============ Utility Methods ============
    
    def get_session_info(self, session_id: str = None) -> Optional[Dict]:
        """Get information about a session."""
        sid = session_id or self._main_session_id
        if sid in self._sessions:
            return self._sessions[sid].to_dict()
        return None
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Gateway."""
        return self._connected
    
    @property
    def active_sessions(self) -> int:
        """Count of active sessions."""
        return sum(1 for s in self._sessions.values() if s.active)


# Factory function for creating OpenClaw adapters
def create_openclaw_adapter(
    gateway_url: str = None,
    model: str = None,
    **kwargs
) -> OpenClawAdapter:
    """
    Factory function to create an OpenClaw adapter.
    
    Args:
        gateway_url: OpenClaw Gateway URL (default from env or ws://127.0.0.1:18789)
        model: Model identifier (default from env or ollama/deepseek-r1:14b)
        **kwargs: Additional configuration
        
    Returns:
        Configured OpenClawAdapter instance
    """
    import os
    
    url = gateway_url or os.getenv("OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789")
    mdl = model or os.getenv("OPENCLAW_MODEL", "ollama/deepseek-r1:14b")
    
    return OpenClawAdapter(
        model=mdl,
        gateway_url=url,
        **kwargs
    )
