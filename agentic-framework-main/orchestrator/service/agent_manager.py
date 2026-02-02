"""
Agent Manager Module

Centralizes agent lifecycle management with:
- Parallel agent execution
- Real-time inter-agent communication
- Agent state tracking
- Coordination between orchestrator and subagents
- OpenClaw integration for local LLM via DeepSeek R1
- Memory learning (diary/reflect) for self-improving agents

Key features from multi-agent-orchestration-main:
- Agents can discuss with each other in real-time
- Orchestrator maintains constant communication
- Parallel task execution with coordination
- Agent templating system

OpenClaw + Ralph + Copilot Memory Integration:
- Each agent runs as independent OpenClaw session
- PRD-based coding via Ralph loop
- diary/reflect for learning from task attempts
- Past learnings injected into agent prompts
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set
from uuid import uuid4
from enum import Enum

import httpx

from .websocket_manager import WebSocketManager, get_websocket_manager
from .session_storage import SessionStorage, get_session_storage
from .memory_learning import MemoryLearningClient, create_memory_learning_client

# Import OpenClaw adapter - use try/except for graceful degradation
try:
    from ...adapters.llm.openclaw import OpenClawAdapter, create_openclaw_adapter
    OPENCLAW_AVAILABLE = True
except ImportError:
    OPENCLAW_AVAILABLE = False
    OpenClawAdapter = None

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"  # Waiting for input/other agent
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class AgentRole(str, Enum):
    """Predefined agent roles with specialized capabilities."""
    RESEARCH = "research"
    VERIFY = "verify"
    CODE = "code"
    SYNTHESIS = "synthesis"
    REVIEW = "review"
    ORCHESTRATOR = "orchestrator"


class Agent:
    """
    Represents a managed agent with state and communication capabilities.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: AgentRole,
        system_prompt: str,
        model: str = "deepseek-r1:14b",
        capabilities: List[str] = None,
        parent_id: str = None,
    ):
        self.id = agent_id
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model
        self.capabilities = capabilities or []
        self.parent_id = parent_id  # The orchestrator or parent agent
        
        self.status = AgentStatus.PENDING
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Task tracking
        self.current_task: Optional[str] = None
        self.task_history: List[Dict] = []
        
        # Communication
        self.message_inbox: asyncio.Queue = asyncio.Queue()
        self.message_outbox: asyncio.Queue = asyncio.Queue()
        
        # Results
        self.results: List[Dict] = []
        
        # Metrics
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_cost = 0.0
        
        # Learning tracking
        self.task_attempts: List[Dict] = []
        self.learnings_applied: List[str] = []
        self.diary_entries: List[str] = []
        
        # OpenClaw session (if using OpenClaw adapter)
        self.openclaw_session_id: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert agent to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "status": self.status.value,
            "model": self.model,
            "capabilities": self.capabilities,
            "parent_id": self.parent_id,
            "current_task": self.current_task,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_cost": self.total_cost,
            "task_attempts": len(self.task_attempts),
            "learnings_applied": len(self.learnings_applied),
            "openclaw_session": self.openclaw_session_id,
        }

    async def send_message(self, to_agent_id: str, message: str, message_type: str = "message"):
        """Queue a message to send to another agent."""
        await self.message_outbox.put({
            "from": self.id,
            "to": to_agent_id,
            "message": message,
            "type": message_type,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def receive_message(self, timeout: float = None) -> Optional[Dict]:
        """Receive a message from the inbox."""
        try:
            if timeout:
                return await asyncio.wait_for(self.message_inbox.get(), timeout)
            return await self.message_inbox.get()
        except asyncio.TimeoutError:
            return None


class AgentManager:
    """
    Manages agent lifecycle, coordination, and inter-agent communication.
    
    This is the central coordinator that enables:
    - Parallel agent execution
    - Real-time inter-agent messaging
    - Orchestrator-agent communication
    - Agent state synchronization
    - OpenClaw integration for local LLM (DeepSeek R1)
    - Memory learning via diary/reflect
    """

    def __init__(
        self,
        subagent_manager_url: str = "http://subagent-manager:9003",
        ollama_endpoint: str = "http://ollama:11434",
        model: str = "deepseek-r1:14b",
        use_openclaw: bool = None,
        openclaw_gateway_url: str = None,
        memory_service_url: str = None,
        workspace_root: str = None,
    ):
        self.subagent_manager_url = subagent_manager_url
        self.ollama_endpoint = ollama_endpoint
        self.model = model
        
        # OpenClaw configuration
        self.use_openclaw = use_openclaw if use_openclaw is not None else os.getenv("USE_OPENCLAW", "true").lower() == "true"
        self.openclaw_gateway_url = openclaw_gateway_url or os.getenv("OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789")
        
        # OpenClaw adapter (initialized lazily)
        self.openclaw_adapter: Optional[OpenClawAdapter] = None
        
        # Memory learning client
        self.memory_client: Optional[MemoryLearningClient] = None
        memory_url = memory_service_url or os.getenv("MEMORY_SERVICE_URL", "http://localhost:8002")
        workspace = workspace_root or os.getenv("WORKSPACE_ROOT", ".")
        
        try:
            self.memory_client = create_memory_learning_client(
                memory_service_url=memory_url,
                workspace_root=workspace
            )
            logger.info("Memory learning client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize memory learning client: {e}")
        
        # Agent registry
        self.agents: Dict[str, Agent] = {}
        self.agent_by_name: Dict[str, str] = {}  # name -> id mapping
        
        # WebSocket manager for broadcasting
        self.ws_manager: WebSocketManager = get_websocket_manager()
        
        # Background tasks for agents
        self.agent_tasks: Dict[str, asyncio.Task] = {}
        
        # Message router task
        self._message_router_task: Optional[asyncio.Task] = None
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Agent templates for quick spawning
        self.templates: Dict[str, Dict] = {
            "research": {
                "role": AgentRole.RESEARCH,
                "system_prompt": """You are a Research Agent. Your task is to gather comprehensive information.
Provide detailed, factual research with sources where possible.
Focus on accuracy and completeness.""",
                "capabilities": ["web_search", "document_analysis", "fact_extraction"],
            },
            "verify": {
                "role": AgentRole.VERIFY,
                "system_prompt": """You are a Verification Agent. Your task is to validate and verify information.
Cross-reference claims and provide confidence assessments.
Be skeptical and thorough.""",
                "capabilities": ["fact_checking", "source_validation", "claim_analysis"],
            },
            "code": {
                "role": AgentRole.CODE,
                "system_prompt": """You are a Code Agent. Your task is to write clean, efficient code.
Follow best practices, include comments, and write tests.
You can create new files and programs.""",
                "capabilities": ["code_generation", "file_operations", "testing"],
            },
            "synthesis": {
                "role": AgentRole.SYNTHESIS,
                "system_prompt": """You are a Synthesis Agent. Your task is to combine and summarize information.
Create coherent summaries from multiple sources.
Highlight key insights and conclusions.""",
                "capabilities": ["summarization", "insight_extraction", "report_generation"],
            },
            "review": {
                "role": AgentRole.REVIEW,
                "system_prompt": """You are a Review Agent. Your task is to review and critique work.
Provide constructive feedback and suggestions for improvement.
Be thorough but fair in your assessment.""",
                "capabilities": ["code_review", "document_review", "quality_assessment"],
            },
        }

    async def start(self):
        """Start the agent manager and background tasks."""
        # Initialize OpenClaw adapter if enabled
        if self.use_openclaw and OPENCLAW_AVAILABLE:
            try:
                self.openclaw_adapter = create_openclaw_adapter(
                    gateway_url=self.openclaw_gateway_url,
                    model=f"ollama/{self.model}"
                )
                await self.openclaw_adapter.connect()
                logger.info(f"OpenClaw adapter connected: {self.openclaw_gateway_url}")
            except Exception as e:
                logger.warning(f"Failed to connect OpenClaw adapter: {e}")
                self.openclaw_adapter = None
        
        # Start message router
        self._message_router_task = asyncio.create_task(self._route_messages())
        logger.info("Agent manager started")

    async def stop(self):
        """Stop the agent manager and all agents."""
        # Cancel message router
        if self._message_router_task:
            self._message_router_task.cancel()
            try:
                await self._message_router_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect OpenClaw adapter
        if self.openclaw_adapter:
            await self.openclaw_adapter.disconnect()
        
        # Terminate all agents
        for agent_id in list(self.agents.keys()):
            await self.terminate_agent(agent_id)
        
        logger.info("Agent manager stopped")

    # ========================================================================
    # Agent Lifecycle Management
    # ========================================================================

    async def create_agent(
        self,
        name: str,
        role: str = "research",
        system_prompt: str = None,
        model: str = None,
        capabilities: List[str] = None,
        parent_id: str = None,
        use_template: bool = True,
    ) -> Agent:
        """
        Create a new managed agent.
        
        Args:
            name: Unique name for the agent
            role: Agent role (research, verify, code, synthesis, review)
            system_prompt: Custom system prompt (overrides template)
            model: LLM model to use
            capabilities: List of capabilities
            parent_id: ID of parent agent (orchestrator)
            use_template: Whether to use role template if no prompt provided
        
        Returns:
            Created Agent instance
        """
        async with self._lock:
            # Check for name collision
            if name in self.agent_by_name:
                raise ValueError(f"Agent with name '{name}' already exists")
            
            agent_id = str(uuid4())
            
            # Get template if using templates
            template = self.templates.get(role.lower()) if use_template else None
            
            # Determine role enum
            try:
                agent_role = AgentRole(role.lower())
            except ValueError:
                agent_role = AgentRole.RESEARCH
            
            # Use template values as defaults
            final_prompt = system_prompt or (template["system_prompt"] if template else f"You are a {role} agent.")
            final_capabilities = capabilities or (template["capabilities"] if template else [])
            final_model = model or self.model
            
            # Create agent
            agent = Agent(
                agent_id=agent_id,
                name=name,
                role=agent_role,
                system_prompt=final_prompt,
                model=final_model,
                capabilities=final_capabilities,
                parent_id=parent_id,
            )
            
            # Register agent
            self.agents[agent_id] = agent
            self.agent_by_name[name] = agent_id
            
            # Create OpenClaw session for this agent if adapter is available
            if self.openclaw_adapter:
                try:
                    session_id = await self.openclaw_adapter.create_agent_session(
                        agent_name=name,
                        agent_role=role,
                        system_prompt=final_prompt
                    )
                    agent.openclaw_session_id = session_id
                    logger.info(f"Created OpenClaw session for agent: {name} -> {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to create OpenClaw session for {name}: {e}")
            
            logger.info(f"Created agent: {name} (ID: {agent_id}, Role: {role})")
            
            # Broadcast creation
            await self.ws_manager.broadcast_agent_created(agent.to_dict())
            
            return agent

    async def get_agent(self, agent_id: str = None, name: str = None) -> Optional[Agent]:
        """Get an agent by ID or name."""
        if agent_id:
            return self.agents.get(agent_id)
        if name:
            agent_id = self.agent_by_name.get(name)
            if agent_id:
                return self.agents.get(agent_id)
        return None

    async def list_agents(
        self,
        status: AgentStatus = None,
        role: AgentRole = None,
        parent_id: str = None,
    ) -> List[Agent]:
        """List agents with optional filtering."""
        agents = list(self.agents.values())
        
        if status:
            agents = [a for a in agents if a.status == status]
        if role:
            agents = [a for a in agents if a.role == role]
        if parent_id:
            agents = [a for a in agents if a.parent_id == parent_id]
        
        return agents

    async def update_agent_status(self, agent_id: str, status: AgentStatus):
        """Update an agent's status and broadcast the change."""
        agent = self.agents.get(agent_id)
        if agent:
            old_status = agent.status
            agent.status = status
            agent.updated_at = datetime.utcnow()
            
            await self.ws_manager.broadcast_agent_status_change(
                agent_id, old_status.value, status.value
            )
            
            logger.info(f"Agent {agent.name} status: {old_status.value} -> {status.value}")

    async def terminate_agent(self, agent_id: str) -> bool:
        """Terminate an agent."""
        async with self._lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return False
            
            # Cancel running task
            if agent_id in self.agent_tasks:
                self.agent_tasks[agent_id].cancel()
                try:
                    await self.agent_tasks[agent_id]
                except asyncio.CancelledError:
                    pass
                del self.agent_tasks[agent_id]
            
            # Update status
            await self.update_agent_status(agent_id, AgentStatus.TERMINATED)
            
            # Remove from registries
            if agent.name in self.agent_by_name:
                del self.agent_by_name[agent.name]
            del self.agents[agent_id]
            
            # Broadcast deletion
            await self.ws_manager.broadcast_agent_deleted(agent_id)
            
            logger.info(f"Terminated agent: {agent.name}")
            return True

    # ========================================================================
    # Task Execution
    # ========================================================================

    async def execute_task(
        self,
        agent_id: str,
        task: str,
        wait: bool = True,
        timeout: float = 300.0,
        inject_learnings: bool = True,
    ) -> Dict:
        """
        Execute a task with an agent.
        
        Args:
            agent_id: Agent ID
            task: Task description
            wait: Whether to wait for completion
            timeout: Timeout in seconds
            inject_learnings: Whether to inject past learnings into task
        
        Returns:
            Task result
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": f"Agent {agent_id} not found"}
        
        # Update status
        agent.current_task = task
        await self.update_agent_status(agent_id, AgentStatus.RUNNING)
        
        # Query past learnings if memory client available and injection enabled
        past_learnings = []
        if inject_learnings and self.memory_client:
            try:
                past_learnings = await self.memory_client.query_past_learnings(
                    query=task,
                    tags=["ralph", "learning", agent.role.value],
                    limit=3
                )
                if past_learnings:
                    agent.learnings_applied.extend([l.get("content", "")[:100] for l in past_learnings])
                    logger.info(f"Injected {len(past_learnings)} past learnings for agent {agent.name}")
            except Exception as e:
                logger.warning(f"Failed to query past learnings: {e}")
        
        # Enhance task with learnings if available
        enhanced_task = self._enhance_task_with_learnings(task, past_learnings) if past_learnings else task
        
        # Broadcast task start
        await self.ws_manager.broadcast_agent_log({
            "agent_id": agent_id,
            "type": "task_start",
            "task": task,
            "learnings_injected": len(past_learnings),
        })

        try:
            # Try OpenClaw first if available, then subagent-manager, fall back to direct LLM
            if self.openclaw_adapter and agent.openclaw_session_id:
                result = await self._execute_via_openclaw(agent, enhanced_task)
            else:
                result = await self._execute_via_subagent_manager(agent, enhanced_task)
            
            if "error" in result:
                # Fall back to direct LLM call
                result = await self._execute_direct_llm(agent, enhanced_task)
            
            success = "error" not in result
            
            # Track attempt
            attempt_data = {
                "task": task,
                "success": success,
                "result": result,
                "learnings_applied": len(past_learnings),
                "timestamp": datetime.utcnow().isoformat(),
            }
            agent.task_attempts.append(attempt_data)
            
            # Log to diary
            if self.memory_client:
                try:
                    diary_id = await self.memory_client.diary(
                        story_id=f"task-{agent_id}-{len(agent.task_attempts)}",
                        story_title=task[:100],
                        attempt_number=len(agent.task_attempts),
                        success=success,
                        changes_made=1 if success else 0,
                        code_generated=result.get("output", "")[:500] if success else None,
                        error=result.get("error") if not success else None,
                        files_modified=[],
                        metadata={"agent_id": agent_id, "agent_name": agent.name}
                    )
                    agent.diary_entries.append(diary_id)
                except Exception as e:
                    logger.warning(f"Failed to write diary entry: {e}")
            
            # Store result
            task_record = {
                "task": task,
                "result": result,
                "completed_at": datetime.utcnow().isoformat(),
            }
            agent.task_history.append(task_record)
            agent.results.append(result)
            
            # Update status
            await self.update_agent_status(agent_id, AgentStatus.COMPLETED)
            
            # Broadcast completion
            await self.ws_manager.broadcast_agent_log({
                "agent_id": agent_id,
                "type": "task_complete",
                "result": result,
            })
            
            return result

        except Exception as e:
            logger.error(f"Task execution failed for agent {agent.name}: {e}")
            await self.update_agent_status(agent_id, AgentStatus.FAILED)
            return {"error": str(e)}

    async def _execute_via_subagent_manager(self, agent: Agent, task: str) -> Dict:
        """Execute task via subagent-manager service (fallback to direct execution on failure)."""
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                # First, spawn the subagent
                spawn_response = await client.post(
                    f"{self.subagent_manager_url}/subagent/spawn",
                    json={
                        "role": agent.role.value,
                        "capabilities": agent.capabilities,
                        "system_prompt": agent.system_prompt,
                        "metadata": {"task": task, "agent_id": agent.id},
                    }
                )
                
                if spawn_response.status_code != 201:
                    logger.warning(f"Subagent spawn failed ({spawn_response.status_code}), falling back to direct execution")
                    # Fallback to direct execution instead of failing
                    return await self._execute_via_direct_llm(agent, task)
                
                subagent_id = spawn_response.json().get("subagent_id")
                
                # Execute the task
                exec_response = await client.post(
                    f"{self.subagent_manager_url}/subagent/execute",
                    json={
                        "subagent_id": subagent_id,
                        "task": task,
                        "input_data": {},
                    }
                )
                
                if exec_response.status_code == 200:
                    return exec_response.json()
                else:
                    logger.warning(f"Subagent execution failed, falling back to direct execution")
                    return await self._execute_via_direct_llm(agent, task)
        
        except Exception as e:
            logger.warning(f"Subagent manager error: {e}, falling back to direct execution")
            return await self._execute_via_direct_llm(agent, task)

    async def _execute_via_openclaw(self, agent: Agent, task: str) -> Dict:
        """Execute task via OpenClaw Gateway with local DeepSeek R1."""
        try:
            from ...adapters.llm.base import LLMMessage, MessageRole
            
            messages = [
                LLMMessage(role=MessageRole.SYSTEM, content=agent.system_prompt),
                LLMMessage(role=MessageRole.USER, content=task),
            ]
            
            response = await self.openclaw_adapter.complete(
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
                session_id=agent.openclaw_session_id
            )
            
            # Update token counts
            agent.input_tokens += response.usage.get("prompt_tokens", 0)
            agent.output_tokens += response.usage.get("completion_tokens", 0)
            
            return {
                "output": response.content,
                "model": response.model,
                "tool_calls": response.tool_calls,
                "finish_reason": response.finish_reason,
                "via_openclaw": True
            }
            
        except Exception as e:
            logger.error(f"OpenClaw execution failed: {e}")
            return {"error": str(e)}

    def _enhance_task_with_learnings(self, task: str, learnings: List[Dict]) -> str:
        """Enhance task prompt with relevant past learnings."""
        if not learnings:
            return task
        
        enhanced = task + "\n\n---\n## Relevant Past Learnings\n\n"
        
        for i, learning in enumerate(learnings[:3], 1):
            content = learning.get("content", "")[:300]
            insights = learning.get("insights", [])
            recommendations = learning.get("recommendations", [])
            
            enhanced += f"### Learning {i}\n"
            if content:
                enhanced += f"{content}\n"
            
            if insights:
                enhanced += "\n**Insights:**\n"
                for insight in insights[:2]:
                    enhanced += f"- {insight}\n"
            
            if recommendations:
                enhanced += "\n**Recommendations:**\n"
                for rec in recommendations[:2]:
                    enhanced += f"- {rec}\n"
            
            enhanced += "\n"
        
        enhanced += "---\n\nApply these learnings to improve your approach to the current task.\n"
        
        return enhanced

    async def _execute_direct_llm(self, agent: Agent, task: str) -> Dict:
        """Execute task directly via LLM (fallback)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{self.ollama_endpoint}/v1/chat/completions",
                json={
                    "model": agent.model,
                    "messages": [
                        {"role": "system", "content": agent.system_prompt},
                        {"role": "user", "content": task},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4096,
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Update token counts
                usage = result.get("usage", {})
                agent.input_tokens += usage.get("prompt_tokens", 0)
                agent.output_tokens += usage.get("completion_tokens", 0)
                
                return {"output": content, "raw_response": result}
            else:
                return {"error": f"LLM error: {response.status_code}"}

    # ========================================================================
    # Parallel Execution
    # ========================================================================

    async def execute_parallel_tasks(
        self,
        tasks: List[Dict],
        coordination_mode: str = "independent",
        timeout: float = 300.0,
    ) -> Dict[str, Dict]:
        """
        Execute multiple tasks in parallel across different agents.
        
        Args:
            tasks: List of {"agent_id": str, "task": str} dicts
            coordination_mode: 
                - "independent": Tasks run independently
                - "collaborative": Agents share results in real-time
                - "sequential_merge": Results merged at end
            timeout: Overall timeout
        
        Returns:
            Dict mapping agent_id to results
        """
        agent_ids = [t["agent_id"] for t in tasks]
        
        # Broadcast collaboration start
        await self.ws_manager.broadcast_agent_collaboration(
            agent_ids,
            "Parallel task execution",
            "started"
        )

        async def execute_with_id(task_info: Dict) -> tuple:
            agent_id = task_info["agent_id"]
            task = task_info["task"]
            result = await self.execute_task(agent_id, task, timeout=timeout)
            
            # In collaborative mode, broadcast intermediate results
            if coordination_mode == "collaborative":
                await self.ws_manager.broadcast_agent_message(
                    agent_id,
                    "broadcast",
                    str(result.get("output", "No output")),
                    "intermediate_result"
                )
            
            return agent_id, result

        # Execute all tasks in parallel
        results = await asyncio.gather(
            *[execute_with_id(t) for t in tasks],
            return_exceptions=True
        )
        
        # Compile results
        result_map = {}
        for item in results:
            if isinstance(item, Exception):
                logger.error(f"Parallel task failed: {item}")
            else:
                agent_id, result = item
                result_map[agent_id] = result
        
        # Broadcast collaboration complete
        await self.ws_manager.broadcast_agent_collaboration(
            agent_ids,
            "Parallel task execution",
            "completed"
        )
        
        return result_map

    async def execute_workflow_parallel(
        self,
        workflow_name: str,
        task: str,
        parent_id: str = None,
    ) -> Dict:
        """
        Execute a predefined workflow with parallel agents.
        
        Workflows:
        - research_verify_sync: Research + Verify in parallel, then Synthesize
        - code_review: Code + Review in parallel
        """
        workflow_id = str(uuid4())
        
        # Broadcast workflow start
        await self.ws_manager.broadcast_workflow_update(
            workflow_id, "started", "initialization"
        )

        if workflow_name == "research_verify_sync":
            # Create agents
            research_agent = await self.create_agent(
                name=f"Research-{workflow_id[:8]}",
                role="research",
                parent_id=parent_id,
            )
            verify_agent = await self.create_agent(
                name=f"Verify-{workflow_id[:8]}",
                role="verify",
                parent_id=parent_id,
            )
            synthesis_agent = await self.create_agent(
                name=f"Synthesis-{workflow_id[:8]}",
                role="synthesis",
                parent_id=parent_id,
            )
            
            # Phase 1: Research and Verify in parallel
            await self.ws_manager.broadcast_workflow_update(
                workflow_id, "running", "research_verify_parallel"
            )
            
            parallel_results = await self.execute_parallel_tasks(
                [
                    {"agent_id": research_agent.id, "task": task},
                    {"agent_id": verify_agent.id, "task": f"Verify the following topic: {task}"},
                ],
                coordination_mode="collaborative"
            )
            
            # Phase 2: Synthesize results
            await self.ws_manager.broadcast_workflow_update(
                workflow_id, "running", "synthesis"
            )
            
            synthesis_task = f"""Synthesize the following research and verification results:

Research Results:
{parallel_results.get(research_agent.id, {}).get('output', 'No research results')}

Verification Results:
{parallel_results.get(verify_agent.id, {}).get('output', 'No verification results')}

Provide a coherent summary with key insights."""

            synthesis_result = await self.execute_task(synthesis_agent.id, synthesis_task)
            
            # Compile workflow results
            workflow_result = {
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "status": "completed",
                "results": {
                    "research": parallel_results.get(research_agent.id, {}),
                    "verify": parallel_results.get(verify_agent.id, {}),
                    "synthesis": synthesis_result,
                },
                "agents_used": [research_agent.id, verify_agent.id, synthesis_agent.id],
            }
            
            # Broadcast completion
            await self.ws_manager.broadcast_workflow_update(
                workflow_id, "completed", None, workflow_result
            )
            
            return workflow_result

        else:
            return {"error": f"Unknown workflow: {workflow_name}"}

    # ========================================================================
    # Inter-Agent Communication
    # ========================================================================

    async def send_message_to_agent(
        self,
        from_agent_id: str,
        to_agent_id: str,
        message: str,
        message_type: str = "message",
    ):
        """
        Send a message from one agent to another.
        This enables real-time agent-to-agent discussion.
        """
        to_agent = self.agents.get(to_agent_id)
        if to_agent:
            # Add to recipient's inbox
            await to_agent.message_inbox.put({
                "from": from_agent_id,
                "to": to_agent_id,
                "message": message,
                "type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            # Broadcast for real-time updates
            await self.ws_manager.broadcast_agent_message(
                from_agent_id, to_agent_id, message, message_type
            )
            
            logger.debug(f"Message sent: {from_agent_id} -> {to_agent_id}")

    async def _route_messages(self):
        """Background task to route messages between agents."""
        while True:
            try:
                # Check each agent's outbox
                for agent in list(self.agents.values()):
                    try:
                        # Non-blocking check
                        if not agent.message_outbox.empty():
                            message = agent.message_outbox.get_nowait()
                            to_agent_id = message["to"]
                            
                            # Handle broadcast messages
                            if to_agent_id == "broadcast":
                                for other_agent in self.agents.values():
                                    if other_agent.id != message["from"]:
                                        await other_agent.message_inbox.put(message)
                            else:
                                to_agent = self.agents.get(to_agent_id)
                                if to_agent:
                                    await to_agent.message_inbox.put(message)
                    except asyncio.QueueEmpty:
                        continue
                
                # Small delay to prevent busy-waiting
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message routing error: {e}")
                await asyncio.sleep(1)

    # ========================================================================
    # Agent Templates
    # ========================================================================

    def list_templates(self) -> List[Dict]:
        """List available agent templates."""
        return [
            {
                "name": name,
                "role": template["role"].value,
                "description": template["system_prompt"].split("\n")[0],
                "capabilities": template["capabilities"],
            }
            for name, template in self.templates.items()
        ]

    def add_template(
        self,
        name: str,
        role: str,
        system_prompt: str,
        capabilities: List[str] = None,
    ):
        """Add a custom agent template."""
        try:
            agent_role = AgentRole(role.lower())
        except ValueError:
            agent_role = AgentRole.RESEARCH
        
        self.templates[name] = {
            "role": agent_role,
            "system_prompt": system_prompt,
            "capabilities": capabilities or [],
        }
        logger.info(f"Added template: {name}")


# Global singleton
_agent_manager: Optional[AgentManager] = None


def get_agent_manager(
    subagent_manager_url: str = None,
    ollama_endpoint: str = None,
    model: str = None,
) -> AgentManager:
    """Get the global agent manager instance."""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager(
            subagent_manager_url=subagent_manager_url or "http://subagent-manager:9003",
            ollama_endpoint=ollama_endpoint or "http://ollama:11434",
            model=model or "deepseek-r1:14b",
        )
    return _agent_manager
