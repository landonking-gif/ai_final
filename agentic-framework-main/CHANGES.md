# Changes Summary - Ralph Loop Always-On Configuration

## Date: February 1, 2026

## Overview
Modified the Agentic Framework to **always** route all code generation requests through the Ralph Loop, regardless of task complexity.

## Changes Made

### 1. agent.py Modifications

**File:** `orchestrator/service/agent.py`

**Changes:**
- Removed simple code request detection logic (lines 617-630)
- Removed `_handle_simple_code_request()` method (lines 897-933)
- Simplified routing: ALL code requests → Ralph Loop

**Previous Behavior:**
```python
# Simple code: single function, snippet
is_simple_code = any(pattern in message_lower for pattern in simple_code_patterns) or len(message) < 150

# For simple code requests, use direct LLM response (much faster)
if is_simple_code and not is_complex_project:
    response = await self._handle_simple_code_request(message, session_id, stream)
```

**New Behavior:**
```python
# ALWAYS use Ralph Loop for all code generation requests
# This ensures consistent quality and proper multi-agent workflow execution

# Handle code generation requests - ALL go through Ralph Loop
if is_code_request and (is_execution_request or has_explicit_instructions ...):
    # ALWAYS use full Ralph Loop workflow for ALL code requests
    response = await self._handle_code_request(message, session_id, stream)
```

### 2. Documentation Updates

**New Files Created:**
- `DEPLOYMENT.md` - Comprehensive deployment guide
- `deploy.sh` - Bash deployment script (Linux/Mac)
- `CHANGES.md` - This file

**Modified Files:**
- `deploy.ps1` - Updated version to 3.1, clarified Ralph Loop usage

### 3. Deployment Scripts

**deploy.ps1 (PowerShell - Windows):**
- Version updated to 3.1
- Added "ALL TASKS USE RALPH LOOP" banner
- Made AWS_IP optional (defaults to 34.229.112.127)
- Streamlined deployment process

**deploy.sh (Bash - Linux/Mac):**
- New comprehensive deployment script
- Color-coded output
- Health check validation
- Step-by-step progress reporting

## Why This Change?

### Benefits of Always Using Ralph Loop:

1. **Consistent Quality**: All code generation goes through the same rigorous workflow
2. **PRD-Based Approach**: Every task gets proper requirements documentation
3. **Multi-Agent Workflow**: Leverages specialized agents for different aspects
4. **Testing & Validation**: Built-in quality checks for all generated code
5. **Learning Integration**: All implementations feed back into memory system

### Trade-offs:

1. **Response Time**: Ralph Loop takes longer (30-120s vs 5-15s for simple tasks)
2. **Resource Usage**: More intensive multi-agent coordination
3. **Complexity Overhead**: Even simple tasks get full PRD treatment

## System Architecture

```
User Request
     ↓
Agent.py (chat endpoint)
     ↓
Code Request Detection
     ↓
Ralph Loop (ALWAYS) ←─── Changed: No bypass
     ↓
┌─────────────────────────┐
│  1. Generate PRD         │
│  2. Break into Stories   │
│  3. Implement with Agents│
│  4. Run Tests            │
│  5. Iterate if Needed    │
└─────────────────────────┘
     ↓
Response to User
```

## Testing

### Test Files Created:

1. **test_ralph_loop.py** - 3 multi-step tasks
2. **test_simple_ralph.py** - 3 simple tasks
3. **complex_tasks_test.py** - 3 complex multi-agent tasks

### Test Results:

⚠️ **Note**: Ralph Loop currently experiences timeouts on the test system
- Issue: Agent naming conflicts and subagent spawn errors
- Root Cause: Multiple concurrent Ralph Loop instances creating duplicate agent names
- Status: Known issue requiring further investigation

**Successful Tests:**
- ✅ Simple direct LLM responses (before this change): 20/20 passed (100%)
- ✅ Chat/Math/Explanations: Working
- ❌ Ralph Loop tasks: Timing out (90-180s)

## Configuration

### Environment Variables:

```bash
# LLM Configuration (Required)
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:32b
LLM_BASE_URL=http://host.docker.internal:11434/v1

# Ralph Loop Settings (Optional)
RALPH_LOOP_MAX_ITERATIONS=10
RALPH_LOOP_TIMEOUT=300
```

### Adjusting Ralph Loop Behavior:

To modify Ralph Loop behavior, edit `orchestrator/service/ralph_loop.py`:

```python
class RalphLoop:
    def __init__(self, ...):
        self.max_iterations = int(os.getenv("RALPH_LOOP_MAX_ITERATIONS", "10"))
        self.timeout = int(os.getenv("RALPH_LOOP_TIMEOUT", "300"))
```

## Deployment Instructions

### Quick Deploy (Windows):

```powershell
cd agentic-framework-main
.\deploy.ps1
```

### Quick Deploy (Linux/Mac):

```bash
cd agentic-framework-main
chmod +x deploy.sh
./deploy.sh
```

### Manual Deploy:

```bash
# Upload agent.py
scp -i key.pem orchestrator/service/agent.py ubuntu@server:/tmp/

# Deploy
ssh -i key.pem ubuntu@server
sudo cp /tmp/agent.py /opt/agentic-framework/orchestrator/service/
cd /opt/agentic-framework
sudo docker compose build orchestrator
sudo docker compose up -d orchestrator
```

## Rollback Instructions

If you need to revert this change and re-enable simple code bypass:

1. Restore `agent.py` from git:
```bash
git checkout HEAD~1 -- orchestrator/service/agent.py
```

2. Or manually add back the logic:
   - Add `is_simple_code` detection
   - Add `_handle_simple_code_request()` method
   - Add conditional routing

3. Redeploy:
```bash
sudo docker compose build orchestrator
sudo docker compose up -d orchestrator
```

## Monitoring

### Check Ralph Loop Execution:

```bash
# View logs
docker compose logs -f orchestrator | grep ralph

# Check for agent errors
docker compose logs orchestrator | grep "Agent.*already exists"

# Monitor response times
docker compose logs orchestrator | grep "Task completed in"
```

### Health Checks:

```bash
# Orchestrator health
curl http://localhost:8000/health

# Test endpoint
curl -X POST http://localhost:8000/api/chat/public \
     -H "Content-Type: application/json" \
     -d '{"message": "Write a hello world function"}'
```

## Known Issues

1. **Agent Name Conflicts**: Multiple Ralph Loop instances create duplicate agent names
   - Error: `Agent with name 'CodeAgent-US-002' already exists`
   - Workaround: Add timestamp or UUID to agent names

2. **Subagent Spawn Errors**: HTTP 400 errors from subagent manager
   - Error: `POST http://subagent-manager:8003/subagent/spawn "HTTP/1.1 400 Bad Request"`
   - Status: Under investigation

3. **Timeout on Complex Tasks**: Tasks exceeding 180s timeout
   - Temporary Solution: Increase timeout in client code
   - Long-term: Optimize Ralph Loop iteration speed

## Future Improvements

1. **Hybrid Routing**: Re-introduce intelligent routing with configurable thresholds
2. **Async Ralph Loop**: Allow background processing for long tasks
3. **Progress Updates**: Stream Ralph Loop progress to user
4. **Agent Pool Management**: Better handling of concurrent agent instances
5. **Caching**: Cache PRDs and implementations for similar requests

## Files Modified

```
Modified:
  orchestrator/service/agent.py (routing logic)
  deploy.ps1 (version and documentation)

Created:
  DEPLOYMENT.md (comprehensive guide)
  deploy.sh (bash deployment script)
  CHANGES.md (this file)
  test_ralph_loop.py (test suite)
  test_simple_ralph.py (simple test suite)
  complex_tasks_test.py (complex test suite)
```

## Support

For issues or questions:
- Check logs: `docker compose logs orchestrator`
- Review documentation: `DEPLOYMENT.md`
- Check system health: `http://your-server:8000/health`

## References

- Ralph Loop Documentation: `docs/ralph-loop.md`
- Agent Manager API: `docs/api-reference.md`
- Memory Service: `memory-service/README.md`
