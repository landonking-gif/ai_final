"""
Dashboard integration for the Orchestrator service.

Provides API endpoints and WebSocket support for the React dashboard:
- Chat interface with AI orchestrator
- PRD generation and management
- User authentication
- Real-time updates
"""

import asyncio
import logging
import secrets
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

import socketio
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import config
from .agent import orchestrator_agent
from .models import (
    ChatMessage,
    ChatResponse,
    PRD,
    PRDApprovalRequest,
    PRDGenerateRequest,
    PRDList,
    PRDStatus,
    PRDValidationRequest,
    TokenResponse,
    UserCredentials,
    UserInfo,
)

logger = logging.getLogger(__name__)

# Security settings
SECRET_KEY = config.jwt_secret_key or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing - use argon2 as bcrypt 5.x has compatibility issues with passlib
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

# In-memory storage (replace with database in production)
_users_db: Dict[str, Dict] = {}
_prds_db: Dict[str, PRD] = {}

# Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')


# ============================================================================
# Authentication Functions
# ============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and return user ID."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current authenticated user."""
    token = credentials.credentials
    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user_id not in _users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user_id


# ============================================================================
# Dashboard Service Class
# ============================================================================


class DashboardService:
    """Service for dashboard functionality."""

    def __init__(self):
        # Initialize with a default admin user
        self._create_default_user()

    def _create_default_user(self):
        """Create default admin user."""
        admin_id = "admin"
        if admin_id not in _users_db:
            _users_db[admin_id] = {
                "id": admin_id,
                "username": "admin",
                "email": "admin@example.com",
                "hashed_password": get_password_hash("admin123"),
                "role": "admin",
                "created_at": datetime.utcnow(),
            }

    async def authenticate_user(self, credentials: UserCredentials) -> TokenResponse:
        """Authenticate user and return token."""
        user = None
        for user_data in _users_db.values():
            if user_data["username"] == credentials.username:
                user = user_data
                break

        if not user or not verify_password(credentials.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["id"]}, expires_delta=access_token_expires
        )

        return TokenResponse(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    async def get_user_info(self, user_id: str) -> UserInfo:
        """Get user information."""
        if user_id not in _users_db:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = _users_db[user_id]
        return UserInfo(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            role=user_data["role"],
            created_at=user_data["created_at"],
        )

    async def chat_with_ai(self, message: ChatMessage, user_id: str) -> ChatResponse:
        """Process chat message with AI orchestrator using the OrchestratorAgent."""
        session_id = message.session_id or str(uuid4())

        # Use the orchestrator agent with real capabilities
        try:
            response_text = await orchestrator_agent.chat(message.message, session_id)
        except Exception as e:
            import traceback
            logger.error(f"Orchestrator agent error: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            response_text = f"I apologize, but I encountered an error: {str(e)}. Please try again."

        return ChatResponse(
            response=response_text,
            session_id=session_id,
        )

    async def generate_prd(self, request: PRDGenerateRequest, user_id: str) -> PRD:
        """Generate a new PRD from requirements using the orchestrator agent."""
        prd_id = str(uuid4())

        # Build prompt for PRD generation
        prd_prompt = f"""Based on the following requirements, generate a comprehensive Product Requirements Document (PRD).

Requirements:
{request.requirements}

Generate a detailed PRD with the following sections:
1. Overview - Brief summary of the project
2. Goals and Objectives - What this project aims to achieve
3. Functional Requirements - Detailed list of features and functionality
4. Non-Functional Requirements - Performance, security, scalability requirements
5. Technical Specifications - Architecture, technology stack, integrations
6. User Stories - Key user stories in the format "As a [user], I want [feature] so that [benefit]"
7. Success Criteria - How we'll measure success
8. Timeline and Milestones - Suggested phases and milestones
9. Risks and Mitigations - Potential risks and how to address them
10. Open Questions - Questions that need to be answered before development

Format the output as a well-structured markdown document."""

        messages = [
            {"role": "system", "content": "You are a senior product manager creating a detailed PRD. Be thorough and specific."},
            {"role": "user", "content": prd_prompt}
        ]

        try:
            content = await orchestrator_agent._call_llm(messages)
            title = f"PRD: {request.requirements[:50]}..." if len(request.requirements) > 50 else f"PRD: {request.requirements}"
        except Exception as e:
            logger.error(f"PRD generation failed: {e}")
            # Fallback to basic template if LLM fails
            title = f"PRD for {request.requirements[:50]}..."
            content = f"""# Product Requirements Document

## Overview
{request.requirements}

## Note
PRD generation via AI failed. Please manually fill in the requirements.

Error: {str(e)}
"""

        prd = PRD(
            id=prd_id,
            title=title,
            content=content,
            status=PRDStatus.DRAFT,
            requirements=request.requirements,
            created_by=user_id,
        )

        _prds_db[prd_id] = prd
        return prd

    async def get_prds(self) -> PRDList:
        """Get all PRDs."""
        return PRDList(
            prds=list(_prds_db.values()),
            total=len(_prds_db)
        )

    async def get_prd(self, prd_id: str) -> PRD:
        """Get a specific PRD."""
        if prd_id not in _prds_db:
            raise HTTPException(status_code=404, detail="PRD not found")
        return _prds_db[prd_id]

    async def validate_prd(self, request: PRDValidationRequest, user_id: str) -> PRD:
        """Validate a PRD."""
        if request.prd_id not in _prds_db:
            raise HTTPException(status_code=404, detail="PRD not found")

        prd = _prds_db[request.prd_id]
        prd.status = PRDStatus.VALIDATING
        prd.updated_at = datetime.utcnow()

        # In a real implementation, this would trigger AI validation
        # For now, just mark as validated after some questions
        if not prd.validation_questions:
            prd.validation_questions = [
                "What are the key success criteria?",
                "Who are the target users?",
                "What are the integration requirements?",
            ]
            prd.validation_answers = ["[Pending user input]"] * len(prd.validation_questions)

        return prd

    async def approve_prd(self, request: PRDApprovalRequest, user_id: str) -> PRD:
        """Approve a PRD and trigger agent deployment."""
        if request.prd_id not in _prds_db:
            raise HTTPException(status_code=404, detail="PRD not found")

        prd = _prds_db[request.prd_id]
        prd.status = PRDStatus.APPROVED
        prd.updated_at = datetime.utcnow()

        # In a real implementation, this would trigger the agent workflow
        logger.info(f"PRD {request.prd_id} approved by {user_id}. Triggering agent deployment...")

        return prd


# Global dashboard service instance
dashboard_service = DashboardService()


# ============================================================================
# Socket.IO Event Handlers
# ============================================================================


@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {sid}")


@sio.event
async def chat_message(sid, data):
    """Handle chat messages from dashboard."""
    try:
        message = ChatMessage(**data)
        response = await dashboard_service.chat_with_ai(message, "dashboard_user")

        # Send response back to client
        await sio.emit('message', {
            'response': response.response,
            'session_id': response.session_id,
            'timestamp': response.timestamp.isoformat()
        }, to=sid)

    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        await sio.emit('error', {'message': 'Failed to process message'}, to=sid)