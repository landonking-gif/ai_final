"""
Lead Agent/Orchestrator Service - Main FastAPI Application.

Provides API endpoints for:
- Starting workflows from manifests
- Requesting subagent execution
- Handling and validating artifacts
- Real-time WebSocket streaming for agent updates

Responsibilities:
- Workflow ingestion and planning
- Subagent spawning and coordination
- Policy enforcement
- Artifact validation
- Commit decision making
- Final synthesis
- Real-time agent coordination via WebSocket
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict
from uuid import uuid4

import anyio
from fastapi import Depends, FastAPI, HTTPException, Request, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import socketio

from .config import config
from .dashboard import dashboard_service, sio, get_current_user
from .websocket_manager import get_websocket_manager
from .agent import orchestrator_agent
from .models import (
    ArtifactHandleRequest,
    ArtifactHandleResponse,
    ArtifactType,
    ChatMessage,
    ChatResponse,
    ClaimVerification,
    CodePatch,
    ErrorResponse,
    HealthCheckResponse,
    PRD,
    PRDApprovalRequest,
    PRDGenerateRequest,
    PRDList,
    PRDValidationRequest,
    ResearchSnippet,
    SubagentRequest,
    SubagentResponse,
    SynthesisResult,
    TokenResponse,
    UserCredentials,
    UserInfo,
    WorkflowStartRequest,
    WorkflowStartResponse,
    WorkflowStatus,
)
from .workflow_engine import WorkflowEngine, ManifestValidationError, WorkflowEngineError

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Track service start time for uptime
SERVICE_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown tasks.
    """
    # Startup
    logger.info("Starting Lead Agent/Orchestrator service...")
    logger.info(f"Configuration: LLM Provider={config.default_llm_provider}")
    logger.info(f"MCP Gateway URL: {config.mcp_gateway_url}")
    logger.info(f"Memory Service URL: {config.memory_service_url}")

    # Initialize workflow engine
    app.state.workflow_engine = WorkflowEngine()
    
    # Initialize WebSocket manager
    app.state.ws_manager = get_websocket_manager()
    logger.info("WebSocket manager initialized")
    
    # Initialize orchestrator agent (async components)
    try:
        await orchestrator_agent.initialize()
        logger.info("Orchestrator agent initialized with persistent storage")
    except Exception as e:
        logger.warning(f"Orchestrator agent partial initialization: {e}")

    logger.info("Orchestrator service started successfully")
    yield

    # Shutdown
    logger.info("Shutting down Orchestrator service...")
    await app.state.workflow_engine.close()
    
    # Cleanup agent manager if exists
    if orchestrator_agent.agent_manager:
        await orchestrator_agent.agent_manager.stop()
    
    logger.info("Orchestrator service shutdown complete")


# Create FastAPI application
fastapi_app = FastAPI(
    title="Lead Agent/Orchestrator Service",
    description="Enterprise Agentic Framework - Workflow orchestration and subagent coordination",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# Exception Handlers
# ============================================================================


@fastapi_app.exception_handler(ValidationError)
async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = [f"{err['loc']}: {err['msg']}" for err in exc.errors()]
    logger.warning(f"Validation error: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": errors},
        ).model_dump(),
    )


@fastapi_app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTPException",
            message=exc.detail or "An error occurred",
        ).model_dump(),
    )


@fastapi_app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An internal server error occurred",
            details={"exception": str(exc)},
        ).model_dump(),
    )


# Mount Socket.IO ASGI app (must be after exception handlers are registered)
socket_app = socketio.ASGIApp(sio, fastapi_app)
app = socket_app


# ============================================================================
# API Endpoints
# ============================================================================


@fastapi_app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with service information."""
    return {
        "service": "Lead Agent/Orchestrator",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "features": [
            "persistent_memory",
            "websocket_streaming",
            "parallel_agents",
            "inter_agent_communication",
            "code_generation"
        ]
    }


# ============================================================================
# WebSocket Endpoints (Real-time Agent Updates)
# ============================================================================


@fastapi_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Provides:
    - Chat message streaming
    - Agent status updates
    - Workflow progress
    - Inter-agent communication
    """
    ws_manager = get_websocket_manager()
    client_id = str(uuid4())
    
    await ws_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "ping":
                # Heartbeat
                await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
            
            elif message_type == "subscribe_agent":
                # Subscribe to specific agent updates
                agent_id = data.get("agent_id")
                if agent_id:
                    await ws_manager.subscribe_to_agent(websocket, agent_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "agent_id": agent_id
                    })
            
            elif message_type == "unsubscribe_agent":
                # Unsubscribe from agent updates
                agent_id = data.get("agent_id")
                if agent_id:
                    await ws_manager.unsubscribe_from_agent(websocket, agent_id)
            
            elif message_type == "get_buffered":
                # Get buffered messages for late joiners
                channel = data.get("channel", "chat")
                await ws_manager.send_buffered_messages(websocket, channel)
            
            elif message_type == "chat":
                # Handle chat message with streaming
                session_id = data.get("session_id", str(uuid4()))
                message = data.get("message", "")
                
                if message:
                    # Process chat with streaming enabled
                    response = await orchestrator_agent.chat(message, session_id, stream=True)
                    
                    # Send final response
                    await websocket.send_json({
                        "type": "chat_response",
                        "session_id": session_id,
                        "response": response
                    })
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info(f"WebSocket client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


@fastapi_app.websocket("/ws/agents/{agent_id}")
async def agent_websocket_endpoint(websocket: WebSocket, agent_id: str):
    """
    WebSocket endpoint for specific agent updates.
    
    Provides real-time updates for a specific agent including:
    - Status changes
    - Task progress
    - Inter-agent messages
    """
    ws_manager = get_websocket_manager()
    client_id = f"agent-{agent_id}-{str(uuid4())[:8]}"
    
    await ws_manager.connect(websocket, client_id)
    await ws_manager.subscribe_to_agent(websocket, agent_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif data.get("type") == "send_message":
                # Send message to another agent
                to_agent = data.get("to_agent")
                message = data.get("message")
                if to_agent and message and orchestrator_agent.agent_manager:
                    await orchestrator_agent.agent_manager.send_message_to_agent(
                        agent_id, to_agent, message
                    )
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Agent WebSocket error: {e}")
        ws_manager.disconnect(websocket)


@fastapi_app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns service status and dependency health.
    """
    import httpx

    dependencies: Dict[str, str] = {}

    # Check dependent services
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check MCP Gateway
        try:
            response = await client.get(f"{config.mcp_gateway_url}/health")
            dependencies["mcp_gateway"] = (
                "healthy" if response.status_code == 200 else "unhealthy"
            )
        except Exception:
            dependencies["mcp_gateway"] = "unreachable"

        # Check Memory Service
        try:
            response = await client.get(f"{config.memory_service_url}/health")
            dependencies["memory_service"] = (
                "healthy" if response.status_code == 200 else "unhealthy"
            )
        except Exception:
            dependencies["memory_service"] = "unreachable"

        # Check Subagent Manager
        try:
            response = await client.get(f"{config.subagent_manager_url}/health")
            dependencies["subagent_manager"] = (
                "healthy" if response.status_code == 200 else "unhealthy"
            )
        except Exception:
            dependencies["subagent_manager"] = "unreachable"

    # Determine overall status
    all_healthy = all(status == "healthy" for status in dependencies.values())
    any_unhealthy = any(status == "unhealthy" for status in dependencies.values())

    if all_healthy:
        overall_status = "healthy"
    elif any_unhealthy:
        overall_status = "degraded"
    else:
        overall_status = "degraded"

    uptime = time.time() - SERVICE_START_TIME

    return HealthCheckResponse(
        status=overall_status,
        version="1.0.0",
        dependencies=dependencies,
        uptime_seconds=uptime,
    )


@fastapi_app.post("/workflows/start", response_model=WorkflowStartResponse)
async def start_workflow(request: WorkflowStartRequest) -> WorkflowStartResponse:
    """
    Start a new workflow execution.

    This endpoint:
    1. Loads and validates the workflow manifest (from file or inline YAML)
    2. Validates user input against workflow requirements
    3. Creates a workflow execution context
    4. Initiates workflow execution (async)
    5. Returns workflow ID and status

    Args:
        request: Workflow start request with manifest and inputs

    Returns:
        Workflow start response with execution ID and status

    Raises:
        HTTPException: If manifest is invalid or workflow fails to start
    """
    logger.info(
        f"Received workflow start request: "
        f"manifest_name={request.manifest_name}, "
        f"has_inline_yaml={request.manifest_yaml is not None}"
    )

    workflow_engine: WorkflowEngine = fastapi_app.state.workflow_engine

    try:
        # Load manifest
        if request.manifest_name:
            manifest = await workflow_engine.load_manifest_from_file(request.manifest_name)
            logger.info(f"Loaded manifest '{request.manifest_name}' from file")
        elif request.manifest_yaml:
            manifest = await workflow_engine.load_manifest_from_yaml(request.manifest_yaml)
            logger.info(f"Loaded manifest '{manifest.name}' from inline YAML")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either manifest_name or manifest_yaml must be provided",
            )

        # Check if human approval is required
        if manifest.policies.requires_human_approval:
            logger.info(
                f"Workflow '{manifest.name}' requires human approval per policy"
            )

        # Start workflow execution in background
        # In production, this would be a Celery task or similar
        async def _execute_workflow_background() -> None:
            """Execute workflow in background."""
            try:
                context = await workflow_engine.execute_workflow(
                    manifest, request.user_input
                )
                logger.info(
                    f"Workflow '{manifest.name}' (ID: {context.workflow_id}) "
                    f"completed with status: {context.status}"
                )
            except Exception as e:
                logger.error(f"Background workflow execution failed: {e}", exc_info=True)

        # Start background task
        # Note: In production, use a proper task queue like Celery
        import asyncio

        asyncio.create_task(_execute_workflow_background())

        # Estimate duration based on step timeouts
        estimated_duration = sum(step.timeout for step in manifest.steps)

        # Create response
        from uuid import uuid4

        workflow_id = str(uuid4())

        return WorkflowStartResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            message=f"Workflow '{manifest.name}' started successfully",
            estimated_duration_seconds=estimated_duration,
        )

    except ManifestValidationError as e:
        logger.error(f"Manifest validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid manifest: {str(e)}",
        )
    except FileNotFoundError as e:
        logger.error(f"Manifest file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manifest not found: {str(e)}",
        )
    except WorkflowEngineError as e:
        logger.error(f"Workflow engine error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}",
        )


@fastapi_app.post("/subagent/request", response_model=SubagentResponse)
async def request_subagent(request: SubagentRequest) -> SubagentResponse:
    """
    Request subagent execution for a workflow step.

    This endpoint:
    1. Validates the subagent request
    2. Spawns a subagent with specified role and capabilities
    3. Executes the subagent with provided inputs
    4. Validates and collects output artifacts
    5. Tracks provenance

    Args:
        request: Subagent execution request

    Returns:
        Subagent execution response with artifacts

    Raises:
        HTTPException: If subagent execution fails
    """
    logger.info(
        f"Received subagent request for workflow '{request.workflow_id}', "
        f"step '{request.step_id}', role '{request.role}'"
    )

    start_time = time.time()

    try:
        # In production, this would call the Subagent Manager service
        # For now, simulate subagent execution
        import httpx

        async with httpx.AsyncClient(timeout=request.timeout + 10.0) as client:
            try:
                response = await client.post(
                    f"{config.subagent_manager_url}/subagent/execute",
                    json=request.model_dump(),
                    timeout=request.timeout + 5.0,
                )
                response.raise_for_status()
                result = response.json()

                execution_time = time.time() - start_time

                return SubagentResponse(
                    subagent_id=result.get("subagent_id", str(uuid4())),
                    workflow_id=request.workflow_id,
                    step_id=request.step_id,
                    status=result.get("status", "success"),
                    artifacts=result.get("artifacts", []),
                    error_message=result.get("error_message"),
                    execution_time_seconds=execution_time,
                    token_usage=result.get("token_usage", {}),
                )

            except httpx.TimeoutException:
                logger.error(f"Subagent request timed out after {request.timeout}s")
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Subagent execution timed out after {request.timeout}s",
                )
            except httpx.HTTPStatusError as e:
                logger.error(f"Subagent service error: {e.response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Subagent service error: {e.response.text}",
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subagent request failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Subagent execution failed: {str(e)}",
        )


@fastapi_app.post("/artifact/handle", response_model=ArtifactHandleResponse)
async def handle_artifact(request: ArtifactHandleRequest) -> ArtifactHandleResponse:
    """
    Validate and handle a typed artifact.

    This endpoint:
    1. Validates artifact structure against type schema
    2. Performs safety checks (PII detection, etc.)
    3. Creates provenance record
    4. Optionally persists to memory service
    5. Returns validation result and artifact ID

    Args:
        request: Artifact handling request

    Returns:
        Artifact validation and persistence response

    Raises:
        HTTPException: If artifact handling fails
    """
    logger.info(
        f"Received artifact handle request: type={request.artifact_type}, "
        f"validate_only={request.validate_only}, workflow_id={request.workflow_id}"
    )

    try:
        # Validate artifact structure using Pydantic models
        validation_errors: list[str] = []
        artifact_id = ""
        valid = False

        try:
            if request.artifact_type == ArtifactType.RESEARCH_SNIPPET:
                artifact = ResearchSnippet(**request.artifact_data)
            elif request.artifact_type == ArtifactType.CLAIM_VERIFICATION:
                artifact = ClaimVerification(**request.artifact_data)
            elif request.artifact_type == ArtifactType.CODE_PATCH:
                artifact = CodePatch(**request.artifact_data)
            elif request.artifact_type == ArtifactType.SYNTHESIS_RESULT:
                artifact = SynthesisResult(**request.artifact_data)
            else:
                validation_errors.append(f"Unknown artifact type: {request.artifact_type}")
                artifact = None

            if artifact:
                artifact_id = artifact.id
                valid = True

                # Perform safety checks
                if config.enable_pii_check and artifact.safety_class.value == "pii_risk":
                    logger.warning(
                        f"Artifact {artifact_id} flagged as PII risk, "
                        f"additional review required"
                    )

                logger.info(f"Artifact {artifact_id} validated successfully")

        except ValidationError as e:
            validation_errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            logger.warning(f"Artifact validation failed: {validation_errors}")

        # Persist artifact if requested and valid
        persisted = False
        memory_ref = None

        if valid and not request.validate_only:
            # In production, persist to memory service
            try:
                import httpx

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{config.memory_service_url}/artifacts/store",
                        json={
                            "artifact_id": artifact_id,
                            "artifact_type": request.artifact_type.value,
                            "artifact_data": request.artifact_data,
                            "workflow_id": request.workflow_id,
                        },
                    )
                    if response.status_code == 200:
                        result = response.json()
                        memory_ref = result.get("memory_ref")
                        persisted = True
                        logger.info(
                            f"Artifact {artifact_id} persisted to memory service: "
                            f"{memory_ref}"
                        )
            except Exception as e:
                logger.warning(f"Failed to persist artifact to memory service: {e}")
                # Don't fail the request if persistence fails
                persisted = False

        return ArtifactHandleResponse(
            artifact_id=artifact_id or "invalid",
            valid=valid,
            validation_errors=validation_errors,
            persisted=persisted,
            memory_ref=memory_ref,
        )

    except Exception as e:
        logger.error(f"Artifact handling failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Artifact handling failed: {str(e)}",
        )


# ============================================================================
# Main Entry Point
# ============================================================================


# ============================================================================
# Human Approval Workflow Endpoints
# ============================================================================

from .approvals import (
    approval_manager,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    ApprovalPriority,
)


@fastapi_app.post("/approvals/request", response_model=ApprovalRequest, status_code=status.HTTP_201_CREATED)
async def create_approval_request(
    workflow_id: str,
    step_id: str,
    operation: str,
    description: str,
    requested_by: str,
    priority: ApprovalPriority = ApprovalPriority.MEDIUM,
    context: Dict[str, Any] = {},
    expires_in_seconds: int = 3600,
) -> ApprovalRequest:
    """
    Create a new approval request.

    Args:
        workflow_id: ID of workflow requesting approval
        step_id: ID of step requiring approval
        operation: Operation being requested
        description: Human-readable description
        requested_by: ID of entity requesting approval
        priority: Priority level
        context: Additional context for approver
        expires_in_seconds: Expiration time in seconds

    Returns:
        Created approval request
    """
    try:
        request = await approval_manager.create_approval_request(
            workflow_id=workflow_id,
            step_id=step_id,
            operation=operation,
            description=description,
            requested_by=requested_by,
            priority=priority,
            context=context,
            expires_in_seconds=expires_in_seconds,
        )
        return request
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create approval request: {str(e)}",
        )


@fastapi_app.get("/approvals/{approval_id}", response_model=ApprovalRequest)
async def get_approval_request(approval_id: str) -> ApprovalRequest:
    """
    Get approval request by ID.

    Args:
        approval_id: Approval request ID

    Returns:
        Approval request

    Raises:
        HTTPException: If approval not found
    """
    request = await approval_manager.get_approval_request(approval_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {approval_id} not found",
        )
    return request


@fastapi_app.get("/approvals", response_model=list[ApprovalRequest])
async def list_pending_approvals(
    workflow_id: str | None = None,
    priority: ApprovalPriority | None = None,
) -> list[ApprovalRequest]:
    """
    List pending approval requests.

    Args:
        workflow_id: Optional filter by workflow ID
        priority: Optional filter by priority

    Returns:
        List of pending approval requests
    """
    return await approval_manager.list_pending_approvals(workflow_id, priority)


@fastapi_app.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_request(
    approval_id: str,
    approver_id: str,
) -> ApprovalResponse:
    """
    Approve a request.

    Args:
        approval_id: Approval request ID
        approver_id: ID of approver

    Returns:
        Approval response

    Raises:
        HTTPException: If approval not found or already processed
    """
    try:
        return await approval_manager.approve_request(approval_id, approver_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@fastapi_app.post("/approvals/{approval_id}/reject", response_model=ApprovalResponse)
async def reject_request(
    approval_id: str,
    approver_id: str,
    reason: str,
) -> ApprovalResponse:
    """
    Reject a request.

    Args:
        approval_id: Approval request ID
        approver_id: ID of approver
        reason: Rejection reason

    Returns:
        Approval response

    Raises:
        HTTPException: If approval not found or already processed
    """
    try:
        return await approval_manager.reject_request(approval_id, approver_id, reason)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@fastapi_app.delete("/approvals/{approval_id}", response_model=ApprovalResponse)
async def cancel_approval_request(approval_id: str) -> ApprovalResponse:
    """
    Cancel a pending approval request.

    Args:
        approval_id: Approval request ID

    Returns:
        Approval response

    Raises:
        HTTPException: If approval not found or already processed
    """
    try:
        return await approval_manager.cancel_request(approval_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# Dashboard API Endpoints
# ============================================================================


@fastapi_app.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserCredentials) -> TokenResponse:
    """
    Authenticate user and return JWT token.

    Args:
        credentials: User login credentials

    Returns:
        JWT token response
    """
    return await dashboard_service.authenticate_user(credentials)


@fastapi_app.get("/auth/me", response_model=UserInfo)
async def get_current_user_info(current_user: str = Depends(get_current_user)) -> UserInfo:
    """
    Get current user information.

    Args:
        current_user: Authenticated user ID

    Returns:
        User information
    """
    return await dashboard_service.get_user_info(current_user)


@fastapi_app.post("/api/chat/public", response_model=ChatResponse)
async def public_chat(message: ChatMessage) -> ChatResponse:
    """
    Public chat endpoint (no authentication required).
    
    Args:
        message: Chat message with context
        
    Returns:
        AI response
    """
    return await dashboard_service.chat_with_ai(message, user_id="public")


@fastapi_app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    message: ChatMessage,
    current_user: str = Depends(get_current_user)
) -> ChatResponse:
    """
    Chat with the AI orchestrator.

    Args:
        message: Chat message with context
        current_user: Authenticated user ID

    Returns:
        AI response
    """
    return await dashboard_service.chat_with_ai(message, current_user)


@fastapi_app.post("/prds/generate", response_model=PRD)
async def generate_prd(
    request: PRDGenerateRequest,
    current_user: str = Depends(get_current_user)
) -> PRD:
    """
    Generate a new Product Requirements Document.

    Args:
        request: PRD generation request
        current_user: Authenticated user ID

    Returns:
        Generated PRD
    """
    return await dashboard_service.generate_prd(request, current_user)


@fastapi_app.get("/prds", response_model=PRDList)
async def get_prds(current_user: str = Depends(get_current_user)) -> PRDList:
    """
    Get all PRDs.

    Args:
        current_user: Authenticated user ID

    Returns:
        List of PRDs
    """
    return await dashboard_service.get_prds()


@fastapi_app.get("/prds/{prd_id}", response_model=PRD)
async def get_prd(
    prd_id: str,
    current_user: str = Depends(get_current_user)
) -> PRD:
    """
    Get a specific PRD.

    Args:
        prd_id: PRD identifier
        current_user: Authenticated user ID

    Returns:
        PRD details
    """
    return await dashboard_service.get_prd(prd_id)


@fastapi_app.post("/prds/{prd_id}/validate", response_model=PRD)
async def validate_prd(
    prd_id: str,
    request: PRDValidationRequest,
    current_user: str = Depends(get_current_user)
) -> PRD:
    """
    Validate a PRD.

    Args:
        prd_id: PRD identifier
        request: Validation request
        current_user: Authenticated user ID

    Returns:
        Updated PRD
    """
    request.prd_id = prd_id
    return await dashboard_service.validate_prd(request, current_user)


@fastapi_app.post("/prds/{prd_id}/approve", response_model=PRD)
async def approve_prd(
    prd_id: str,
    current_user: str = Depends(get_current_user)
) -> PRD:
    """
    Approve a PRD and trigger agent deployment.

    Args:
        prd_id: PRD identifier
        current_user: Authenticated user ID

    Returns:
        Updated PRD
    """
    request = PRDApprovalRequest(prd_id=prd_id)
    return await dashboard_service.approve_prd(request, current_user)


def main() -> None:
    """Main entry point for running the service."""
    import uvicorn

    logger.info("Starting Orchestrator service with uvicorn...")

    uvicorn.run(
        "orchestrator.service.main:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
