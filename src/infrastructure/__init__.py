"""
Infrastructure Layer

External dependency implementations

Structure:
- config: Configuration loaders (JSON-based)
- storage: Repositories (Session, Context)
- claude: Claude SDK client (Manager, Worker)
- mcp: MCP Server (Worker Tools)
"""

from .config import (
    JsonConfigLoader,
    SystemConfig,
    validate_environment,
    get_claude_cli_path,
    get_project_root,
)
from .storage import (
    JsonSessionRepository,
    JsonContextRepository,
)
from .claude import (
    ManagerAgent,
    WorkerAgent,
)
from .mcp import (
    initialize_workers,
    create_worker_tools_server,
    get_error_statistics,
    reset_error_statistics,
    log_error_summary,
)

__all__ = [
    # Config
    "JsonConfigLoader",
    "SystemConfig",
    "validate_environment",
    "get_claude_cli_path",
    "get_project_root",
    # Storage
    "JsonSessionRepository",
    "JsonContextRepository",
    # Claude
    "ManagerAgent",
    "WorkerAgent",
    # MCP
    "initialize_workers",
    "create_worker_tools_server",
    "get_error_statistics",
    "reset_error_statistics",
    "log_error_summary",
]
