"""
Infrastructure Layer

External dependency implementations

Structure:
- config: Configuration loaders (JSON-based)
- storage: Repositories (Session, Context)
- claude: Claude SDK client (Worker)
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
    WorkerAgent,
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
    "WorkerAgent",
    # Template
    "Jinja2TemplateEngine",
    "FileBasedTemplateRepository",
    "get_builtin_templates",
]
