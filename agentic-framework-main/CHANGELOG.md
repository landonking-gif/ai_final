# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.0] - 2026-02-01

### Added

#### OpenClaw Integration - Local AI Inference
- **OpenClaw Adapter** (`adapters/llm/openclaw.py`): WebSocket-based LLM adapter connecting to OpenClaw Gateway
- **Local LLM Support**: Each agent runs as its own OpenClaw instance using DeepSeek R1 14B via Ollama
- **Agent Sessions**: Multi-session routing with agent-to-agent communication via `sessions_send`
- **Role-Based System Prompts**: Specialized prompts for Orchestrator, Researcher, Coder, Reviewer, and Generalist agents
- **Gateway at ws://127.0.0.1:18789**: Standard OpenClaw Gateway protocol support
- **All Components Updated**: Orchestrator, SubAgent Manager, and all agents now use OpenClaw

#### Ralph Loop - Autonomous PRD Implementation
- **Ralph Loop Module** (`orchestrator/service/ralph_loop.py`): Autonomous code implementation system
- **PRD Parser**: Reads JSON PRD files with user stories, acceptance criteria, and priorities
- **Story Iteration**: Implements user stories one by one with retry logic (max 3 attempts per story)
- **AI Code Generation**: Uses OpenClaw or Copilot CLI for actual code implementation
- **Progress Tracking**: Tracks completion percentage and story status across iterations
- **Git Integration**: Automatic commits after each successful story implementation

#### Copilot Memory Plugin - Learning System
- **Memory Learning Client** (`orchestrator/service/memory_learning.py`): Diary and reflect capabilities
- **Diary Tool (`/diary`)**: Logs each implementation attempt with success/failure, files modified, quality checks
- **Reflect Tool (`/reflect`)**: Analyzes failure patterns, identifies success factors, generates recommendations
- **COPILOT.md Updates**: Automatically updates project COPILOT.md with learnings and insights
- **Query Past Learnings**: Retrieves relevant past experiences to enhance future tasks
- **Local Storage**: Diary entries in `.copilot/memory/diary/`, reflections in `.copilot/memory/reflections/`

#### Codebase Indexing - Agent Code Access
- **Codebase Indexer** (`orchestrator/service/codebase_indexer.py`): Indexes source code into memory service
- **Semantic Search**: Agents can query the codebase for relevant code sections
- **Structure Extraction**: Parses classes, functions, imports from Python/JS/TS files
- **Change Detection**: Only re-indexes files when content changes (via hash comparison)
- **Automatic Indexing**: Codebase indexed on deployment for agent access

#### Git Repository Management
- **Auto-initialization**: Git repository created on first deployment
- **OpenClaw Upstream Sync**: Configured remote tracking for `opencodelabs/openclaw`
- **Sync Script** (`sync-openclaw.sh`): Fetches and merges upstream improvements
- **Cron Job**: Auto-sync runs every 6 hours

#### Self-Improving Agent Architecture
- **Learning Injection**: Past learnings automatically injected into task prompts
- **Failure Pattern Analysis**: Identifies common failure causes (test failures, syntax errors, import errors)
- **Success Factor Extraction**: Learns what approaches led to successful implementations
- **Memory Service Integration**: Vector search for semantically similar past tasks

### Changed
- **AgentManager**: Now supports OpenClaw adapter with fallback to subagent-manager and direct LLM
- **Orchestrator Agent**: Uses OpenClaw for all LLM calls with Ollama fallback
- **SubAgent Manager**: Default LLM provider changed from "local" to "openclaw"
- **Task Execution Flow**: Query learnings → Enhance prompt → Execute → Diary → Reflect
- **Docker Compose**: Added OpenClaw dependencies for subagent-manager service
- **deploy.sh**: Major rewrite with 7-step deployment including git init and codebase indexing

### Removed
- **Extra deploy scripts**: Removed `hotfix_deploy.ps1`, `deploy-aws.sh`, `quick-deploy.ps1` - only `deploy.sh` remains

### Infrastructure
- **Node.js 22**: Added for OpenClaw CLI (`npm install -g openclaw@latest`)
- **OpenClaw Configuration**: `~/.openclaw/openclaw.json` with DeepSeek R1 model
- **Docker Volumes**: Added `openclaw_config`, `openclaw_workspace`, `copilot_memory`
- **nginx Proxy**: Added `/openclaw` route for Gateway access
- **Git + Cron**: Repository management with upstream sync

## [2.1.0] - 2026-02-01

### Fixed
- **Agent Tool Execution**: Fixed critical bug where AI would describe solutions instead of actually executing agents
- **Code Request Detection**: Expanded keyword detection to trigger code generation without requiring "execute" keyword
- **Redis NoneType Error**: Fixed `Invalid input of type: 'NoneType'` error when storing session data
- **Multi-Agent Coordination**: Complex tasks now properly spawn multiple specialized agents (ResearchAgent + CodeAgent)

### Changed  
- **Code Generation Logic**: "create", "build", "write" requests now automatically trigger agent execution
- **System Prompt**: Updated to emphasize ACTION over DESCRIPTION - agents now execute instead of just explaining
- **Complex Task Detection**: Added detection for multi-step requests (numbered lists, step-by-step instructions)
- **Agent Workflow**: Complex tasks now use ResearchAgent for analysis THEN CodeAgent for implementation

### Added
- **Multi-Agent Code Workflow**: Complex code requests spawn research agent first for design, then code agent for implementation
- **Workflow Status Logging**: Clear logging of agent creation, status changes, and termination
- **Enhanced Keyword Detection**: Added natural language patterns ("i want", "please", "can you", "let's")

## [2.0.0] - 2025-01-XX

### Added

#### Real-time Agent Coordination
- **WebSocket Manager** (`websocket_manager.py`): Real-time broadcasting for agent events, chat streaming, and status updates
- **WebSocket endpoints** (`/ws`, `/ws/agents/{agent_id}`): Native WebSocket support for real-time updates
- **Agent-to-agent messaging**: Agents can communicate directly in real-time
- **Broadcast system**: Status changes, logs, and messages broadcast to all connected clients

#### Persistent Session Storage
- **Session Storage** (`session_storage.py`): Redis-backed persistent session storage
- **Conversation memory fixes**: Sessions survive container restarts (fixes "AI forgetting" issue)
- **Context persistence**: Full conversation history stored with configurable TTL
- **In-memory fallback**: Graceful degradation when Redis is unavailable

#### Agent Manager & Parallel Execution
- **Agent Manager** (`agent_manager.py`): Centralized agent lifecycle management
- **Parallel workflow execution**: Multiple agents work simultaneously with coordination
- **Agent templating system**: Pre-defined templates (research, verify, code, synthesis, review)
- **Inter-agent communication channels**: Agents can subscribe to each other's updates

#### Code Generation Agent
- **Code Generation Agent** (`code_agent.py`): Specialized agent for writing programs
- **File write operations**: Actually creates files in the workspace
- **Project scaffolding**: Generate complete project structures
- **Agent configuration generation**: Create new specialized agent configurations

### Changed
- **Orchestrator Agent**: Now initializes async components (session storage, agent manager)
- **Chat method**: Now supports streaming via WebSocket and persistent message storage
- **Workflow execution**: Now uses parallel execution when Agent Manager is available
- **System prompt**: Updated to reflect new capabilities (persistent memory, code generation)

### Fixed
- **Conversation forgetting**: Sessions now persist in Redis across restarts
- **Memory issues**: Increased context window with proper message management
- **Tool execution**: Better error handling and fallback mechanisms

### Infrastructure
- **deploy.sh**: Updated with Redis configuration and WebSocket nginx settings
- **requirements.txt**: Added `websockets>=12.0`, `redis[hiredis]>=5.0.0`
- **nginx config**: Added WebSocket proxy settings with proper timeouts

## [1.0.0] - 2024-01-01

### Added

#### Core Framework
- Multi-agent orchestration platform with typed artifacts
- Workflow engine with YAML-based manifest support
- Subagent lifecycle management with context isolation
- Memory service with multi-tier storage (Redis, Postgres, Milvus, S3)
- MCP gateway for standardized tool access
- Code executor for sandboxed skill execution

#### LLM Adapters
- Anthropic Claude adapter (claude-sonnet-4, claude-opus-4)
- OpenAI GPT adapter (gpt-4o, gpt-4o-mini)
- Azure OpenAI adapter
- Google Gemini adapter (gemini-2.0-flash)
- Ollama adapter for local inference
- vLLM adapter for optimized local inference

#### Skills System
- Skill registry with auto-discovery
- Dual-format support (native and Anthropic marketplace)
- JIT (Just-In-Time) handler loading
- Safety flags and approval workflows
- Example skills: text_summarize, deep-research

#### MCP Integration
- MCP tool binding system
- Wildcard tool patterns (server:*)
- Scoped access control
- Rate limiting and audit logging
- Tool invocation via HTTP gateway

#### CLI Tool (kautilya)
- Agent creation and management
- Skill scaffolding and import
- LLM configuration
- Manifest generation and validation
- Workflow execution

#### Artifacts
- Typed artifact system with JSON Schema validation
- Provenance tracking (actor, tools, timestamps)
- Built-in artifact types:
  - research_snippet
  - claim_verification
  - code_patch
  - synthesis_result

#### Workflows
- Sequential step execution
- Input/output resolution between steps
- Retry logic with exponential backoff
- Timeout enforcement
- Artifact validation at each step

#### Human-in-the-Loop
- Approval manager for sensitive operations
- Priority-based approval queues
- Automatic expiry handling
- Blocking wait for approval

### Infrastructure
- Docker Compose for local development
- FastAPI-based service architecture
- OpenTelemetry instrumentation
- Prometheus metrics
- Structured logging

### Documentation
- Architecture overview
- Getting started guide
- API reference documentation
- Example projects
- Skill development guide

### Developer Experience
- Black code formatting (100 char line length)
- mypy strict type checking
- pytest test suite
- Comprehensive .gitignore
- Development environment setup scripts

## [0.1.0] - 2023-12-01

### Added
- Initial project structure
- Basic orchestrator prototype
- Simple subagent spawning
- Mock LLM adapter for testing

---

[Unreleased]: https://github.com/your-org/agentic-framework/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/agentic-framework/releases/tag/v1.0.0
[0.1.0]: https://github.com/your-org/agentic-framework/releases/tag/v0.1.0
