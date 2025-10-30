# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Claude Flow** (formerly Better-LLM) is a group chat orchestration system based on the Manager-Worker pattern.
The Manager Agent coordinates specialized Worker Agents (Planner, Coder, Reviewer, Tester, etc.) to automate complex software development tasks.

**Core Components:**
- **Manager Agent**: Orchestrates workflow and manages Worker execution
- **Worker Agents**: Specialized for specific tasks (planning, coding, review, testing, etc.)
- **Web UI**: React-based drag-and-drop workflow canvas

## Architecture

### Clean Architecture + Hexagonal Architecture

```
src/
├── domain/           # Core business logic (no dependencies)
│   ├── models/      # Domain entities (Message, Session, AgentConfig, etc.)
│   ├── services/    # Domain services (Context, Conversation, etc.)
│   ├── interfaces/  # Interface definitions (Use Cases)
│   └── errors/      # Domain exceptions
│
├── application/      # Application logic
│   ├── use_cases/   # Use Case implementations (ExecutePlannerUseCase, etc.)
│   ├── ports/       # Port interfaces (IAgentClient, IConfigPort, etc.)
│   ├── resilience/  # Circuit Breaker, Retry Policy
│   └── validation/  # Input validation
│
├── infrastructure/   # External adapter implementations
│   ├── claude/      # Claude SDK integration (WorkerAgent)
│   ├── storage/     # SQLite repositories
│   ├── config/      # Configuration loaders
│   └── mcp/         # MCP callback handlers
│
└── presentation/     # Interface layer
    ├── web/         # FastAPI web server + React UI
    └── cli/         # CLI (planned)
```

### Key Concepts

1. **Dependency Inversion Principle (DIP)**
   - Application layer only uses port interfaces
   - Infrastructure layer implements ports as adapters

2. **Use Case Factory**
   - Located at `src/application/use_cases/use_case_factory.py`
   - Centrally manages dependency injection and Use Case instance creation
   - Loose coupling through Worker Client Factory

3. **Worker Agent Adapter**
   - Located at `src/infrastructure/claude/worker_agent_adapter.py`
   - Adapts Claude SDK's `WorkerAgent` to `IAgentClient` interface

## Development Setup

### 1. Prerequisites

- Python 3.10 or higher
- Node.js (for Web UI build)
- Claude Code OAuth Token
- Claude CLI path

### 2. Installation (Automated Setup Script)

```bash
# Global installation using pipx (recommended)
./setup.sh

# Choose installation mode:
# 1) Normal mode (production use)
# 2) Development mode (editable install, changes reflected immediately)
```

### 3. Environment Variables

Copy `.env.example` to `.env` and set required values:

```bash
# Required
CLAUDE_CODE_OAUTH_TOKEN="your-token-here"
CLAUDE_CLI_PATH="/path/to/claude"

# Optional (defaults exist)
WORKER_TIMEOUT_PLANNER=300
WORKER_TIMEOUT_CODER=600
LOG_LEVEL=INFO
```

### 4. Manual Installation (For Developers)

```bash
# Install Python dependencies
pip install -e .

# Build web frontend
cd src/presentation/web/frontend
npm install
npm run build
```

## Common Commands

### Run Web UI

```bash
# Production mode (serves built React app)
claude-flow-web

# Or
python -m src.presentation.web.app

# Access server at: http://localhost:8000
```

### Frontend Development

```bash
cd src/presentation/web/frontend

# Development server (hot reload)
npm run dev

# Production build (output: ../static-react/)
npm run build

# TypeScript check + build
npm run build:check
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/unit/domain/models/test_task.py

# Specific test function
pytest tests/unit/domain/models/test_task.py::test_task_creation
```

### Code Quality

```bash
# Black formatter
black src/ tests/

# Ruff linter
ruff check src/ tests/

# Type checking (if mypy configured)
# mypy src/
```

## Configuration Files

### config/system_config.json

System-wide configuration:

```json
{
  "manager": {
    "model": "claude-sonnet-4-5-20250929",
    "max_turns": 10
  },
  "timeouts": {
    "planner_timeout": 1200,
    "coder_timeout": 1200
  },
  "workflow_limits": {
    "max_review_iterations": 3
  },
  "permission": {
    "mode": "bypassPermissions"  // Test environments only!
  }
}
```

### config/agent_config.json

Worker Agent configuration:

```json
{
  "planner": {
    "agent_type": "planner",
    "prompt_path": "prompts/feature_planner.txt",
    "model": "claude-sonnet-4-5-20250929"
  }
}
```

## Key Workflows

### Worker Execution Flow

1. **Use Case Factory** creates Worker Client
2. **Use Case** (`ExecutePlannerUseCase`, etc.) executes Worker
3. **Worker Agent Adapter** calls Claude SDK
4. **MCP Callback Handler** monitors execution
5. **Results saved** (SQLite)

### Web UI Workflow

1. User drags and drops nodes in React UI
2. Workflow submitted to FastAPI backend
3. Manager Agent executes workflow
4. Real-time log streaming via SSE
5. Results displayed in frontend

## Important File Locations

### Worker Agent Execution

- `src/infrastructure/claude/worker_client.py` - WorkerAgent implementation
- `src/infrastructure/claude/worker_agent_adapter.py` - IAgentClient adapter
- `src/application/use_cases/execute_*_use_case.py` - Worker Use Cases

### Web API

- `src/presentation/web/app.py` - FastAPI app
- `src/presentation/web/routers/workflows_router.py` - Workflow API
- `src/presentation/web/services/workflow_service.py` - Workflow execution service

### Configuration & Storage

- `src/infrastructure/config/loader.py` - JSON config loader
- `src/infrastructure/storage/sqlite_session_repository.py` - Session repository
- `src/infrastructure/storage/optimized_session_storage.py` - Optimized session storage

## Development Guidelines

### 1. Adding a Use Case

```python
# 1. Define Use Case interface (domain/interfaces/use_cases/)
class IExecuteNewWorkerUseCase(Protocol):
    async def execute(self, task: str) -> Result: ...

# 2. Implement Use Case (application/use_cases/)
class ExecuteNewWorkerUseCase(BaseWorkerUseCase):
    async def execute(self, task: str) -> Result:
        # Worker execution logic

# 3. Register in Factory (application/use_cases/use_case_factory.py)
def get_new_worker_use_case(self) -> IExecuteNewWorkerUseCase:
    return ExecuteNewWorkerUseCase(...)
```

### 2. Adding a New Worker Agent

1. Add prompt file to `prompts/` directory
2. Add Worker config to `config/agent_config.json`
3. Verify Worker loads in Use Case Factory

### 3. Adding an API Endpoint

```python
# src/presentation/web/routers/new_router.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/new", tags=["new"])

@router.post("/endpoint")
async def new_endpoint(data: RequestModel):
    # Delegate business logic to Use Case
    use_case = factory.get_use_case()
    return await use_case.execute(data)
```

### 4. Adding a Frontend Component

```typescript
// src/presentation/web/frontend/src/components/NewComponent.tsx
import React from 'react';

export const NewComponent: React.FC = () => {
  // Utilize React Flow nodes/edges
  return <div>...</div>;
};
```

## Troubleshooting

### Worker Execution Timeout

- Increase `WORKER_TIMEOUT_*` values in `.env`
- Or modify `timeouts` section in `config/system_config.json`

### React Build Failure

```bash
cd src/presentation/web/frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### OAuth Token Error

```bash
# Check token
echo $CLAUDE_CODE_OAUTH_TOKEN

# Reset token
export CLAUDE_CODE_OAUTH_TOKEN='new-token'
```

### Check Logs

```bash
# Web UI logs (structlog)
tail -f ~/.claude-flow/better-llm/logs/web_app.log

# Worker execution logs
tail -f ~/.claude-flow/better-llm/logs/worker_*.log
```

## Testing Strategy

- **Unit Tests**: Domain models and Use Case unit tests
- **Integration Tests**: Worker Agent execution integration tests (using mocks)
- **E2E Tests**: Web API end-to-end tests (not implemented)

## References

- Claude Agent SDK: `claude-agent-sdk-features.md`
- Project History: Check Git commit logs
- Workflow Examples: `prompts/workflow_designer.txt`
