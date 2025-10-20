"""
Configuration Infrastructure

JSON file-based configuration loader and environment validation
"""

from .loader import JsonConfigLoader, SystemConfig, load_system_config
from .validator import (
    validate_environment,
    get_claude_cli_path,
    get_project_root,
    get_project_name,
    get_data_dir
)

__all__ = [
    "JsonConfigLoader",
    "SystemConfig",
    "load_system_config",
    "validate_environment",
    "get_claude_cli_path",
    "get_project_root",
    "get_project_name",
    "get_data_dir",
]
