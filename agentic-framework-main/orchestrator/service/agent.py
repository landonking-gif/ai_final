"""
Orchestrator Agent - The Lead Agent with actual tool execution capabilities.

This module implements the Lead Agent/Orchestrator that can:
- Maintain conversation context across sessions (NOW WITH PERSISTENT STORAGE)
- Spawn and coordinate subagents with PARALLEL EXECUTION
- Access the memory service for persistent storage
- Execute research and verification tasks
- Generate and manage PRDs
- Stream responses in REAL-TIME via WebSocket
- Enable INTER-AGENT COMMUNICATION
- Use OpenClaw with DeepSeek R1 for local LLM inference

Enhanced with features from multi-agent-orchestration-main:
- WebSocket streaming for real-time updates
- Redis-backed persistent session storage (fixes memory issues)
- Agent Manager for parallel coordination
- Agent-to-agent messaging
- OpenClaw integration for local AI
"""

import asyncio
import json
import logging
import httpx
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

from .config import config
from .websocket_manager import get_websocket_manager, WebSocketManager
from .session_storage import get_session_storage, SessionStorage
from .agent_manager import get_agent_manager, AgentManager, AgentStatus
from .ralph_loop import create_ralph_loop, PRD, UserStory
from .memory_learning import MemoryLearningClient
import subprocess
from pathlib import Path

# OpenClaw adapter import with fallback
try:
    from adapters.llm.openclaw import OpenClawAdapter, OPENCLAW_AVAILABLE
except ImportError:
    OpenClawAdapter = None
    OPENCLAW_AVAILABLE = False

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Lead Agent/Orchestrator with real tool execution capabilities.
    
    This agent can:
    - Coordinate subagents via the subagent-manager service
    - Access memory service for context and history
    - Execute research using web search capabilities
    - Maintain conversation state and context (PERSISTENT via Redis)
    - Stream responses in real-time via WebSocket
    - Execute parallel workflows with agent coordination
    - Use OpenClaw with DeepSeek R1 for local LLM inference
    
    Enhanced features:
    - Persistent session storage (fixes conversation forgetting)
    - Real-time WebSocket streaming
    - Parallel agent execution
    - Inter-agent communication
    - OpenClaw integration (no API costs!)
    """
    
    def __init__(self):
        self.subagent_url = config.subagent_manager_url
        self.memory_url = config.memory_service_url
        self.mcp_url = config.mcp_gateway_url
        self.ollama_endpoint = config.ollama_endpoint
        self.model = config.local_model
        self.logger = logging.getLogger(__name__)
        
        # OpenClaw configuration
        self.use_openclaw = getattr(config, 'use_openclaw', True)
        self.openclaw_gateway_url = getattr(config, 'openclaw_gateway_url', 'ws://openclaw:18789')
        self.openclaw_adapter: Optional[OpenClawAdapter] = None
        
        # WebSocket manager for real-time streaming
        self.ws_manager: WebSocketManager = get_websocket_manager()
        
        # Session storage will be initialized async
        self.session_storage: Optional[SessionStorage] = None
        
        # Agent manager for coordination
        self.agent_manager: Optional[AgentManager] = None
        
        # Legacy in-memory sessions (fallback)
        self.sessions: Dict[str, Dict] = {}
        
        # Active workflows
        self.workflows: Dict[str, Dict] = {}
        
        # PRDs
        self.prds: Dict[str, Dict] = {}
        
        # Streaming callbacks
        self._stream_callbacks: Dict[str, Callable] = {}
        
        # Initialization flag
        self._initialized = False
    
    async def initialize(self):
        """Initialize async components (must be called before use)."""
        if self._initialized:
            return
        
        # Initialize OpenClaw adapter if available and enabled
        if self.use_openclaw and OPENCLAW_AVAILABLE:
            try:
                self.openclaw_adapter = OpenClawAdapter(
                    gateway_url=self.openclaw_gateway_url,
                    model=self.model,
                )
                await self.openclaw_adapter.connect()
                self.logger.info(f"OpenClaw adapter connected to {self.openclaw_gateway_url}")
            except Exception as e:
                self.logger.warning(f"OpenClaw connection failed, using fallback: {e}")
                self.openclaw_adapter = None
        
        try:
            # Initialize session storage (Redis-backed)
            self.session_storage = await get_session_storage(
                redis_url=getattr(config, 'redis_url', 'redis://redis:6379')
            )
            self.logger.info("Session storage initialized")
        except Exception as e:
            self.logger.warning(f"Redis unavailable, using in-memory storage: {e}")
        
        try:
            # Initialize agent manager
            self.agent_manager = get_agent_manager(
                subagent_manager_url=self.subagent_url,
                ollama_endpoint=self.ollama_endpoint,
                model=self.model,
            )
            await self.agent_manager.start()
            self.logger.info("Agent manager initialized")
        except Exception as e:
            self.logger.warning(f"Agent manager initialization failed: {e}")
        
        self._initialized = True
        self.logger.info("OrchestratorAgent fully initialized")
    
    async def _ensure_initialized(self):
        """Ensure agent is initialized before operations."""
        if not self._initialized:
            await self.initialize()
        
    async def _get_session(self, session_id: str) -> Dict:
        """Get or create a session with persistent storage."""
        await self._ensure_initialized()
        
        # Check persistent storage first
        if self.session_storage:
            exists = await self.session_storage.session_exists(session_id)
            if not exists:
                await self.session_storage.create_session(session_id)
            
            session_data = await self.session_storage.get_session(session_id)
            return session_data or {}
        
        # Fallback to in-memory
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "id": session_id,
                "messages": [],
                "context": {},
                "created_at": datetime.utcnow().isoformat(),
                "active_workflow": None,
            }
        return self.sessions[session_id]
    
    async def _add_message(self, session_id: str, role: str, content: str, metadata: Dict = None):
        """Add a message to session with persistent storage."""
        if self.session_storage:
            await self.session_storage.add_message(session_id, role, content, metadata)
            
            # Broadcast via WebSocket for real-time updates
            await self.ws_manager.broadcast_chat_message({
                "session_id": session_id,
                "role": role,
                "content": content[:200] + "..." if len(content) > 200 else content,
                "timestamp": datetime.utcnow().isoformat(),
            })
        else:
            # Fallback
            if session_id in self.sessions:
                self.sessions[session_id]["messages"].append({
                    "role": role,
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat(),
                })
    
    async def _get_conversation_context(self, session_id: str, num_messages: int = 20) -> List[Dict]:
        """Get recent conversation context for LLM."""
        if self.session_storage:
            return await self.session_storage.get_recent_context(session_id, num_messages)
        
        # Fallback
        session = self.sessions.get(session_id, {})
        messages = session.get("messages", [])[-num_messages:]
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]
    
    async def _call_llm(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """
        Call the LLM with optional tool definitions.
        
        Priority:
        1. OpenClaw adapter (if available and connected)
        2. Direct Ollama API fallback
        """
        # Try OpenClaw first if available
        if self.openclaw_adapter and self.openclaw_adapter.connected:
            try:
                # Format messages for OpenClaw
                prompt = ""
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "system":
                        prompt = f"System: {content}\n\n{prompt}"
                    elif role == "user":
                        prompt += f"User: {content}\n"
                    elif role == "assistant":
                        prompt += f"Assistant: {content}\n"
                
                response_text = await self.openclaw_adapter.complete(prompt)
                return {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": response_text
                        }
                    }],
                    "model": self.model,
                    "via": "openclaw"
                }
            except Exception as e:
                logger.warning(f"OpenClaw call failed, falling back to Ollama: {e}")
        
        # Fallback to direct Ollama API
        async with httpx.AsyncClient(timeout=180.0) as client:
            payload = {
                "model": self.model.replace("ollama/", ""),  # Strip ollama/ prefix
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4096,
            }
            
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
            
            try:
                response = await client.post(
                    f"{self.ollama_endpoint}/v1/chat/completions",
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"LLM error: {response.status_code} - {response.text}")
                    return {"error": f"LLM returned {response.status_code}"}
                
                result = response.json()
                result["via"] = "ollama"
                return result
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return {"error": str(e)}
    
    async def spawn_subagent(self, role: str, task: str, capabilities: List[str] = None) -> Dict:
        """Spawn a subagent via the subagent-manager service."""
        system_prompts = {
            "research": f"""You are a Research Agent. Your task is to gather comprehensive information.
Task: {task}
Provide detailed, factual research with sources where possible.""",
            "verify": f"""You are a Verification Agent. Your task is to validate and verify information.
Task: {task}
Cross-reference claims and provide confidence assessments.""",
            "code": f"""You are a Code Agent. Your task is to write clean, efficient code.
Task: {task}
Follow best practices and include comments.""",
            "synthesis": f"""You are a Synthesis Agent. Your task is to combine and summarize information.
Task: {task}
Create a coherent summary from multiple sources.""",
        }
        
        spawn_request = {
            "role": role,
            "capabilities": capabilities or [],
            "system_prompt": system_prompts.get(role, f"You are a {role} agent. Task: {task}"),
            "timeout": 300,
            "max_iterations": 10,
            "metadata": {"task": task, "created_at": datetime.utcnow().isoformat()}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.subagent_url}/subagent/spawn",
                    json=spawn_request
                )
                if response.status_code == 201:
                    return response.json()
                else:
                    logger.error(f"Spawn failed: {response.status_code} - {response.text}")
                    return {"error": f"Failed to spawn {role} agent: {response.text}"}
            except Exception as e:
                logger.error(f"Spawn error: {e}")
                return {"error": f"Cannot connect to subagent manager: {e}"}
    
    async def execute_subagent_task(self, subagent_id: str, task: str) -> Dict:
        """Execute a task with a spawned subagent."""
        execute_request = {
            "subagent_id": subagent_id,
            "task": task,
            "input_data": {},
            "output_schema": "research_snippet"  # Default schema
        }
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                response = await client.post(
                    f"{self.subagent_url}/subagent/execute",
                    json=execute_request
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Execution failed: {response.text}"}
            except Exception as e:
                return {"error": f"Execution error: {e}"}
    
    async def get_active_subagents(self) -> List[Dict]:
        """Get list of active subagents."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.subagent_url}/subagents")
                if response.status_code == 200:
                    return response.json().get("subagents", [])
            except Exception as e:
                logger.error(f"Cannot list subagents: {e}")
        return []
    
    async def store_memory(self, key: str, value: Any, session_id: str) -> bool:
        """Store information in memory service."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.memory_url}/memory/store",
                    json={"key": key, "value": value, "session_id": session_id}
                )
                return response.status_code == 200
            except Exception as e:
                logger.error(f"Memory store error: {e}")
                return False
    
    async def retrieve_memory(self, key: str, session_id: str) -> Optional[Any]:
        """Retrieve information from memory service."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.memory_url}/memory/retrieve",
                    params={"key": key, "session_id": session_id}
                )
                if response.status_code == 200:
                    return response.json().get("value")
            except Exception as e:
                logger.error(f"Memory retrieve error: {e}")
        return None
    
    async def execute_workflow(self, workflow_name: str, task: str, session_id: str) -> Dict:
        """
        Execute a multi-agent workflow with parallel execution support.
        
        Enhanced to use AgentManager for parallel workflows when available.
        """
        await self._ensure_initialized()
        workflow_id = str(uuid4())
        
        workflow = {
            "id": workflow_id,
            "name": workflow_name,
            "task": task,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "steps": [],
            "results": {}
        }
        
        self.workflows[workflow_id] = workflow
        
        # Update session
        if self.session_storage:
            await self.session_storage.save_workflow(session_id, workflow_id, workflow)
        
        # Broadcast workflow start
        await self.ws_manager.broadcast_workflow_update(workflow_id, "started", "initialization")
        
        try:
            # Try parallel execution via AgentManager first
            if self.agent_manager and workflow_name == "research_verify_sync":
                self.logger.info(f"Using parallel workflow execution for {workflow_name}")
                
                result = await self.agent_manager.execute_workflow_parallel(
                    workflow_name, task, parent_id="orchestrator"
                )
                
                workflow.update(result)
                workflow["status"] = "completed"
                
                # Broadcast completion
                await self.ws_manager.broadcast_workflow_update(
                    workflow_id, "completed", None, workflow
                )
                
                return workflow
            
            # Fallback to sequential execution
            if workflow_name == "research_verify_sync":
                # Step 1: Research
                workflow["steps"].append({"step": "research", "status": "running"})
                await self.ws_manager.broadcast_workflow_update(
                    workflow_id, "running", "research"
                )
                research_agent = await self.spawn_subagent("research", task)
                
                if "error" not in research_agent:
                    research_result = await self.execute_subagent_task(
                        research_agent.get("subagent_id", ""),
                        task
                    )
                    workflow["results"]["research"] = research_result
                    workflow["steps"][-1]["status"] = "completed"
                else:
                    workflow["results"]["research"] = research_agent
                    workflow["steps"][-1]["status"] = "failed"
                
                # Step 2: Verify
                workflow["steps"].append({"step": "verify", "status": "running"})
                await self.ws_manager.broadcast_workflow_update(
                    workflow_id, "running", "verify"
                )
                verify_agent = await self.spawn_subagent("verify", f"Verify: {task}")
                
                if "error" not in verify_agent:
                    verify_result = await self.execute_subagent_task(
                        verify_agent.get("subagent_id", ""),
                        f"Verify this research: {workflow['results'].get('research', {})}"
                    )
                    workflow["results"]["verify"] = verify_result
                    workflow["steps"][-1]["status"] = "completed"
                else:
                    workflow["results"]["verify"] = verify_agent
                    workflow["steps"][-1]["status"] = "failed"
                
                # Step 3: Synthesize
                workflow["steps"].append({"step": "synthesize", "status": "running"})
                await self.ws_manager.broadcast_workflow_update(
                    workflow_id, "running", "synthesize"
                )
                synthesis_agent = await self.spawn_subagent("synthesis", "Synthesize research findings")
                
                if "error" not in synthesis_agent:
                    sync_result = await self.execute_subagent_task(
                        synthesis_agent.get("subagent_id", ""),
                        f"Synthesize: {json.dumps(workflow['results'])}"
                    )
                    workflow["results"]["synthesis"] = sync_result
                    workflow["steps"][-1]["status"] = "completed"
                else:
                    workflow["results"]["synthesis"] = synthesis_agent
                    workflow["steps"][-1]["status"] = "failed"
                
                workflow["status"] = "completed"
            else:
                # Default single-agent workflow
                agent = await self.spawn_subagent("research", task)
                if "error" not in agent:
                    result = await self.execute_subagent_task(agent.get("subagent_id", ""), task)
                    workflow["results"]["output"] = result
                    workflow["status"] = "completed"
                else:
                    workflow["results"]["error"] = agent
                    workflow["status"] = "failed"
                    
        except Exception as e:
            workflow["status"] = "failed"
            workflow["error"] = str(e)
            logger.error(f"Workflow execution error: {e}")
            await self.ws_manager.broadcast_error(f"Workflow failed: {e}")
        
        workflow["completed_at"] = datetime.utcnow().isoformat()
        
        # Broadcast completion
        await self.ws_manager.broadcast_workflow_update(
            workflow_id, workflow["status"], None, workflow
        )
        
        return workflow
    
    async def _build_system_prompt_async(self, session_id: str) -> str:
        """Build a dynamic system prompt with current context (async version)."""
        active_subagents = 0
        if self.agent_manager:
            agents = await self.agent_manager.list_agents()
            active_subagents = len([a for a in agents if a.status.value == "running"])
        
        # Get message count from persistent storage
        message_count = 0
        active_workflow = None
        if self.session_storage:
            session_data = await self.session_storage.get_session(session_id)
            if session_data:
                msg_count = session_data.get("message_count", 0)
                message_count = int(msg_count) if msg_count is not None else 0
                active_workflow = session_data.get("active_workflow")
            else:
                message_count = 0
                active_workflow = None
        
        return f"""You are the Lead Agent/Orchestrator for the Agentic Framework - an AI-powered software development and research system.

## Your Identity
You are NOT DeepSeek-R1. You ARE the Lead Agent/Orchestrator with real capabilities to execute tasks.

## Your REAL Capabilities (you can actually do these):
1. **Spawn Subagents**: Create specialized agents (ResearchAgent, VerifyAgent, CodeAgent, SynthesisAgent)
2. **Execute Workflows**: Run multi-step workflows like research-verify-synchronize (with PARALLEL execution)
3. **Access Memory**: Store and retrieve information persistently (NOW PERSISTS ACROSS RESTARTS)
4. **Generate PRDs**: Create formal Product Requirement Documents
5. **Coordinate Tasks**: Manage multiple agents working together IN REAL-TIME
6. **Write Code**: Generate programs, create files, and build new agent configurations

## Current System State:
- Active Workflows: {len(self.workflows)}
- Active Subagents: {active_subagents}
- PRDs Created: {len(self.prds)}
- Session Messages: {message_count} messages in this conversation
- Active Workflow: {active_workflow or 'None'}
- Real-time Streaming: ENABLED
- Persistent Memory: ENABLED

## CRITICAL: Action vs Description
When a user asks you to CREATE, BUILD, WRITE, MAKE, or DEVELOP something:
- DO NOT just describe the steps or provide guidance
- ACTUALLY execute the task using your CodeAgent and other subagents
- Generate REAL code, spawn REAL agents, produce REAL output
- The system will automatically route these requests to the appropriate agents

## Important Instructions:
1. REMEMBER the conversation context - refer back to what was discussed (memory is now persistent!)
2. When asked to CREATE or BUILD anything, the system will spawn agents to ACTUALLY do it
3. Provide the actual results - code, files, outputs - not just descriptions
4. When you complete a task, report what was ACTUALLY created
5. If you cannot do something, explain why and what alternatives exist
6. Trust that your code generation and agent spawning capabilities are REAL and WORKING

## Conversation Context:
You are continuing a conversation. Your memory is now PERSISTENT - you will remember everything even if the system restarts. Refer back to what was discussed and maintain context throughout the entire session."""

    async def chat(self, message: str, session_id: str, stream: bool = False) -> str:
        """
        Process a chat message with full context and tool capabilities.
        
        Enhanced with:
        - Persistent session storage (fixes memory issues)
        - Real-time WebSocket streaming
        - Parallel agent coordination
        
        Args:
            message: User message
            session_id: Session identifier
            stream: If True, stream response via WebSocket
        
        Returns:
            Assistant response
        """
        await self._ensure_initialized()
        
        # Ensure session exists
        await self._get_session(session_id)
        
        # Add user message to persistent storage
        await self._add_message(session_id, "user", message)
        
        # Check for action keywords
        message_lower = message.lower()
        
        # Extract potential task from message
        task = None
        
        # Check if this is an execution request - expanded to include natural language patterns
        execution_keywords = ["execute", "begin", "start", "run", "do it", "go ahead", "proceed", 
                              "make", "develop", "design", "set up", "setup", "configure",
                              "i want", "please", "can you", "could you", "let's", "lets"]
        is_execution_request = any(word in message_lower for word in execution_keywords)
        
        # Check if this is a code/program request - indicates user wants something BUILT
        code_keywords = ["write", "create", "generate", "build", "implement", "code", "program", 
                         "script", "application", "app", "tool", "software", "system", "module",
                         "function", "class", "api", "service", "project"]
        is_code_request = any(word in message_lower for word in code_keywords)
        
        # Check if this is a research/workflow request
        is_research_request = any(word in message_lower for word in ["research", "investigate", "analyze", "study", "look into"])
        is_workflow_request = any(word in message_lower for word in ["workflow", "verify", "comprehensive", "full analysis"])
        
        # Detect if user is giving explicit instructions (numbered lists, step-by-step)
        has_explicit_instructions = any(pattern in message_lower for pattern in 
                                        ["1.", "step 1", "first,", "- ", "* ", "follow these"])
        
        # ALWAYS use Ralph Loop for all code generation requests
        # This ensures consistent quality and proper multi-agent workflow execution
        
        # Handle code generation requests - ALL go through Ralph Loop
        if is_code_request and (is_execution_request or has_explicit_instructions or 
                                 any(word in message_lower for word in ["create", "build", "write", "make", "develop"])):
            self.logger.info(f"Code generation request detected - routing to Ralph Loop: {message[:100]}")
            
            # ALWAYS use full Ralph Loop workflow for ALL code requests
            response = await self._handle_code_request(message, session_id, stream)
            await self._add_message(session_id, "assistant", response)
            return response
        
        # If it's both an execution request AND contains a topic, extract the topic
        if is_execution_request:
            # Try to extract the topic from the message
            task_text = message_lower
            for word in execution_keywords + ["please", "a", "on", "the", "topic", "of", "about", "regarding"]:
                task_text = task_text.replace(word, " ")
            task_text = " ".join(task_text.split()).strip()
            
            if task_text and len(task_text) > 3:
                task = message
            else:
                # Check for pending task in context
                if self.session_storage:
                    pending = await self.session_storage.get_context(session_id, "pending_task")
                    if pending:
                        task = pending
                        await self.session_storage.set_context(session_id, "pending_task", None)
        
        # Store as pending task if it's a research request but not immediate execution
        if is_research_request and not is_execution_request:
            if self.session_storage:
                await self.session_storage.set_context(session_id, "pending_task", message)
        
        # Execute workflow if we have a task
        if task:
            self.logger.info(f"Executing workflow for task: {task}")
            
            # Stream status updates if enabled
            if stream:
                await self.ws_manager.broadcast_chat_stream(session_id, "🚀 Starting workflow execution...\n", False)
            
            workflow_result = await self.execute_workflow(
                "research_verify_sync",
                task,
                session_id
            )
            
            # Format the result
            if workflow_result["status"] == "completed":
                response = f"""## Workflow Execution Complete

I've executed the research-verify-synchronize workflow for: **{task[:100]}...**

### Results:

**Research Phase:**
{self._format_result(workflow_result['results'].get('research', {}))}

**Verification Phase:**
{self._format_result(workflow_result['results'].get('verify', {}))}

**Synthesis:**
{self._format_result(workflow_result['results'].get('synthesis', {}))}

Workflow ID: `{workflow_result['id']}`
"""
            elif workflow_result["status"] == "error" or workflow_result["status"] == "failed":
                response = f"""## Workflow Execution

I attempted to execute the workflow for: **{task[:100]}...**

However, I encountered an issue. Let me provide you with a response using my capabilities:

"""
                # Fall back to LLM response
                context = await self._get_conversation_context(session_id, 20)
                system_prompt = await self._build_system_prompt_async(session_id)
                messages = [{"role": "system", "content": system_prompt}] + context
                
                llm_result = await self._call_llm(messages)
                if "error" not in llm_result:
                    response += llm_result.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                response = f"Workflow execution status: {workflow_result.get('status', 'Unknown')}"
            
            await self._add_message(session_id, "assistant", response)
            
            if stream:
                await self.ws_manager.broadcast_chat_stream(session_id, response, True)
            
            return response
        
        # Build conversation for LLM with persistent context
        system_prompt = await self._build_system_prompt_async(session_id)
        context = await self._get_conversation_context(session_id, 20)
        messages = [{"role": "system", "content": system_prompt}] + context
        
        # Call LLM
        result = await self._call_llm(messages)
        
        if "error" in result:
            response = f"I encountered an error: {result['error']}. Please try again."
        else:
            response = result.get("choices", [{}])[0].get("message", {}).get("content", "No response generated.")
        
        # Add assistant response to persistent storage
        await self._add_message(session_id, "assistant", response)
        
        # Stream final response if enabled
        if stream:
            await self.ws_manager.broadcast_chat_stream(session_id, response, True)
        
        return response
    
    async def _generate_prd_from_request(self, message: str, session_id: str) -> Dict[str, Any]:
        """
        Generate a PRD (Product Requirements Document) from a code request.
        
        Uses the LLM to analyze the request and create a structured PRD with:
        - User stories
        - Acceptance criteria
        - Priority ordering
        """
        prd_prompt = f"""Analyze this code generation request and create a formal PRD (Product Requirements Document).

User Request:
{message}

You MUST respond with ONLY valid JSON in this exact format (no other text):
{{
    "name": "Short project name",
    "description": "Brief project description",
    "branchName": "feature/descriptive-branch-name",
    "userStories": [
        {{
            "id": "US-001",
            "title": "Story title",
            "description": "Detailed description of what needs to be done",
            "acceptanceCriteria": [
                "Criterion 1",
                "Criterion 2"
            ],
            "priority": 1
        }}
    ]
}}

Break down the request into 1-5 user stories, each with clear acceptance criteria.
Priority 1 = highest priority, implement first.
Generate descriptive branch name from the project name."""

        context = await self._get_conversation_context(session_id, 5)
        messages = [
            {"role": "system", "content": "You are a Product Manager AI that creates structured PRDs. Output ONLY valid JSON."},
        ] + context + [
            {"role": "user", "content": prd_prompt}
        ]
        
        result = await self._call_llm(messages)
        
        if "error" in result:
            raise Exception(f"Failed to generate PRD: {result['error']}")
        
        response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Parse JSON from response
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                prd_data = json.loads(json_match.group())
            else:
                prd_data = json.loads(response_text)
            
            self.logger.info(f"Generated PRD: {prd_data.get('name')} with {len(prd_data.get('userStories', []))} stories")
            return prd_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse PRD JSON: {e}\nResponse: {response_text}")
            # Create a minimal PRD as fallback
            return {
                "name": "Code Request",
                "description": message[:200],
                "branchName": "feature/code-implementation",
                "userStories": [{
                    "id": "US-001",
                    "title": "Implement requested feature",
                    "description": message,
                    "acceptanceCriteria": ["Code compiles without errors", "All requirements met"],
                    "priority": 1
                }]
            }
    
    def _push_to_github(self, project_root: Path, branch_name: str) -> Dict[str, Any]:
        """
        Push committed changes to GitHub.
        
        Returns:
            Dict with push status and details
        """
        result = {
            "success": False,
            "pushed": False,
            "error": None,
            "remote": None,
            "branch": branch_name
        }
        
        try:
            # Check if remote exists
            remote_check = subprocess.run(
                ["git", "remote", "-v"],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            if "origin" not in remote_check.stdout:
                result["error"] = "No remote 'origin' configured"
                return result
            
            result["remote"] = "origin"
            
            # Push to remote with set-upstream
            push_result = subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=60
            )
            
            if push_result.returncode == 0:
                result["success"] = True
                result["pushed"] = True
                self.logger.info(f"Successfully pushed to origin/{branch_name}")
            else:
                # Try force push if normal push fails (for new branches)
                push_force = subprocess.run(
                    ["git", "push", "--set-upstream", "origin", branch_name],
                    capture_output=True,
                    text=True,
                    cwd=project_root,
                    timeout=60
                )
                if push_force.returncode == 0:
                    result["success"] = True
                    result["pushed"] = True
                else:
                    result["error"] = push_result.stderr or push_force.stderr
                    
        except subprocess.TimeoutExpired:
            result["error"] = "Git push timed out"
        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"Git push failed: {e}")
        
        return result

    async def _handle_code_request(self, message: str, session_id: str, stream: bool = False) -> str:
        """
        Handle code generation requests using the Ralph Loop workflow.
        
        This method implements the full code generation pipeline:
        1. Generate PRD from user's request
        2. Run Ralph Loop to implement user stories
        3. Commit all changes to git
        4. Push to GitHub
        
        The Ralph Loop handles:
        - Breaking down PRD into user stories
        - Iterative implementation with quality checks
        - Memory/learning integration
        - Automatic commits for each story
        """
        response_parts = []
        
        if stream:
            await self.ws_manager.broadcast_chat_stream(
                session_id, "🔨 **Initiating PRD-based code generation workflow...**\n\n", False
            )
        
        response_parts.append("## 🚀 Ralph Loop Code Generation Workflow\n")
        
        # Default project root - use workspace or /tmp
        project_root = Path("/opt/agentic-framework/workspace/ralph-projects")
        project_root.mkdir(parents=True, exist_ok=True)
        
        try:
            # Step 1: Generate PRD from user request
            response_parts.append("\n### 📋 Step 1: Generating PRD\n")
            if stream:
                await self.ws_manager.broadcast_chat_stream(
                    session_id, "📋 Generating Product Requirements Document...\n", False
                )
            
            prd_data = await self._generate_prd_from_request(message, session_id)
            
            prd_name = prd_data.get("name", "Unnamed Project")
            prd_branch = prd_data.get("branchName", "feature/code-implementation")
            stories_count = len(prd_data.get("userStories", []))
            
            response_parts.append(f"✅ **PRD Generated**: {prd_name}\n")
            response_parts.append(f"   - Branch: `{prd_branch}`\n")
            response_parts.append(f"   - User Stories: {stories_count}\n")
            
            # Display user stories
            response_parts.append("\n**User Stories:**\n")
            for story in prd_data.get("userStories", []):
                response_parts.append(f"- **{story.get('id')}**: {story.get('title')} (Priority: {story.get('priority', 'N/A')})\n")
            
            # Store PRD in session
            self.prds[session_id] = prd_data
            
            # Step 2: Initialize and run Ralph Loop
            response_parts.append("\n### 🔄 Step 2: Running Ralph Loop\n")
            if stream:
                await self.ws_manager.broadcast_chat_stream(
                    session_id, "🔄 Initializing Ralph Loop for autonomous implementation...\n", False
                )
            
            # Create memory client for learning integration
            memory_client = None
            try:
                memory_client = MemoryLearningClient(
                    base_url=config.memory_service_url
                )
            except Exception as e:
                self.logger.warning(f"Memory client not available: {e}")
            
            # Create Ralph Loop instance
            ralph_loop = create_ralph_loop(
                project_root=str(project_root),
                prd_data=prd_data,
                agent_manager=self.agent_manager,
                memory_client=memory_client,
                max_iterations=50,
                max_retries_per_story=3
            )
            
            response_parts.append(f"✅ Ralph Loop initialized at: `{project_root}`\n")
            
            if stream:
                await self.ws_manager.broadcast_chat_stream(
                    session_id, "💻 Implementing user stories...\n", False
                )
            
            # Run the Ralph Loop
            ralph_result = await ralph_loop.run()
            
            # Report results
            completed = ralph_result.get("stories", {}).get("completed", 0)
            failed = ralph_result.get("stories", {}).get("failed", 0)
            total = ralph_result.get("stories", {}).get("total", 0)
            completion = ralph_result.get("stories", {}).get("completion_percentage", 0)
            
            response_parts.append(f"\n**Ralph Loop Results:**\n")
            response_parts.append(f"- Stories Completed: {completed}/{total} ({completion:.1f}%)\n")
            response_parts.append(f"- Stories Failed: {failed}\n")
            response_parts.append(f"- Total Iterations: {ralph_result.get('iterations', 0)}\n")
            
            if ralph_result.get("completed_stories"):
                response_parts.append("\n**Completed Stories:**\n")
                for story in ralph_result.get("completed_stories", []):
                    commit_sha = story.get("commit_sha", "N/A")[:8] if story.get("commit_sha") else "N/A"
                    response_parts.append(f"- ✅ {story.get('id')}: {story.get('title')} (commit: `{commit_sha}`)\n")
            
            if ralph_result.get("failed_stories"):
                response_parts.append("\n**Failed Stories:**\n")
                for story in ralph_result.get("failed_stories", []):
                    response_parts.append(f"- ❌ {story.get('id')}: {story.get('title')} - {story.get('last_error', 'Unknown error')}\n")
            
            # Step 3: Push to GitHub
            response_parts.append("\n### 🚀 Step 3: Pushing to GitHub\n")
            if stream:
                await self.ws_manager.broadcast_chat_stream(
                    session_id, "🚀 Pushing changes to GitHub...\n", False
                )
            
            push_result = self._push_to_github(project_root, prd_branch)
            
            if push_result.get("success"):
                response_parts.append(f"✅ **Successfully pushed to GitHub**\n")
                response_parts.append(f"   - Remote: `{push_result.get('remote')}`\n")
                response_parts.append(f"   - Branch: `{push_result.get('branch')}`\n")
            else:
                response_parts.append(f"⚠️ **Push to GitHub failed**: {push_result.get('error')}\n")
                response_parts.append("   - Changes are committed locally\n")
                response_parts.append("   - You can manually push with: `git push origin {prd_branch}`\n")
            
            # Summary
            response_parts.append("\n### ✅ Workflow Complete\n")
            if completed == total and total > 0:
                response_parts.append("🎉 All user stories implemented successfully!\n")
            elif completed > 0:
                response_parts.append(f"📊 Partial success: {completed}/{total} stories completed.\n")
            else:
                response_parts.append("❌ No stories were completed. Check the errors above.\n")
            
            final_response = "\n".join(response_parts)
            await self._add_message(session_id, "assistant", final_response)
            
            if stream:
                await self.ws_manager.broadcast_chat_stream(session_id, final_response, True)
            
            return final_response
            
        except Exception as e:
            self.logger.error(f"Ralph Loop execution failed: {e}")
            import traceback
            traceback.print_exc()
            
            error_response = f"""## ❌ Code Generation Failed

An error occurred during the Ralph Loop execution:
```
{str(e)}
```

**Falling back to direct code generation...**

"""
            response_parts.append(error_response)
            
            # Fallback to direct LLM response for code
            context = await self._get_conversation_context(session_id, 10)
            system_prompt = """You are a Code Agent capable of writing clean, efficient code.
You MUST actually generate the complete code, not just describe what to do.
Follow best practices, include comments, and provide COMPLETE, WORKING implementations.
Do not use placeholders like '...' or 'TODO' - write the actual code."""
            
            messages = [{"role": "system", "content": system_prompt}] + context + [
                {"role": "user", "content": f"Generate complete, working code for: {message}"}
            ]
            
            result = await self._call_llm(messages)
            
            if "error" in result:
                return error_response + f"Fallback also failed: {result['error']}"
            
            fallback_code = result.get("choices", [{}])[0].get("message", {}).get("content", "Unable to generate code.")
            final_response = error_response + fallback_code
            
            await self._add_message(session_id, "assistant", final_response)
            return final_response

    def _build_system_prompt(self, session: Dict) -> str:
        """Build a dynamic system prompt with current context (legacy sync version)."""
        active_subagents = len(self.workflows)
        
        return f"""You are the Lead Agent/Orchestrator for the Agentic Framework - an AI-powered software development and research system.

## Your Identity
You are NOT DeepSeek-R1. You ARE the Lead Agent/Orchestrator with real capabilities to execute tasks.

## Your REAL Capabilities (you can actually do these):
1. **Spawn Subagents**: Create specialized agents (ResearchAgent, VerifyAgent, CodeAgent, SynthesisAgent)
2. **Execute Workflows**: Run multi-step workflows like research-verify-synchronize
3. **Access Memory**: Store and retrieve information persistently
4. **Generate PRDs**: Create formal Product Requirement Documents
5. **Coordinate Tasks**: Manage multiple agents working together

## Current System State:
- Active Workflows: {len(self.workflows)}
- PRDs Created: {len(self.prds)}
- Session Context: {len(session.get('messages', []))} messages in this conversation
- Active Workflow: {session.get('active_workflow', 'None')}

## Important Instructions:
1. REMEMBER the conversation context - refer back to what was discussed
2. When asked to EXECUTE or BEGIN a task, actually coordinate the agents
3. Provide specific, actionable responses - not just descriptions
4. When you complete a task, report the actual results
5. If you cannot do something, explain why and what alternatives exist

## Conversation Context:
You are continuing a conversation. Remember what was discussed and maintain context."""
    
    def _format_result(self, result: Dict) -> str:
        """Format a result dictionary for display."""
        if not result:
            return "No results available."
        # Check for error (but ignore if it's None/null)
        if result.get("error"):
            return f"Error: {result['error']}"
        # Check for raw_response (subagent execution results)
        if result.get("raw_response"):
            return str(result["raw_response"])
        # Check for output
        if result.get("output"):
            return str(result["output"])
        # Check for content
        if result.get("content"):
            return str(result["content"])
        # Fallback to JSON representation
        return json.dumps(result, indent=2)[:1000]  # Truncate long results


# Global orchestrator instance
orchestrator_agent = OrchestratorAgent()
