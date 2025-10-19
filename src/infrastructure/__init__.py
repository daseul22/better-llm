"""
Infrastructure Layer

External dependency implementations

Structure:
- config: Configuration loaders (JSON-based)
- storage: Repositories (Session, Context)
- claude: Claude SDK client (Manager, Worker)
- mcp: MCP Server (Worker Tools)
- template: Template engine and repository
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
from .template import (
    Jinja2TemplateEngine,
    FileBasedTemplateRepository,
    get_builtin_templates,
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
    # Template
    "Jinja2TemplateEngine",
    "FileBasedTemplateRepository",
    "get_builtin_templates",
]
