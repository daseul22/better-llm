"""
Application Ports (Interfaces)

External dependency interfaces (Dependency Inversion Principle)
Implemented by Infrastructure layer
"""

from .agent_port import IAgentClient
from .config_port import IConfigLoader, ISystemConfig
from .storage_port import ISessionRepository, IContextRepository

# Re-export from domain.ports (Clean Architecture DIP)
from ...domain.ports import IMetricsRepository

__all__ = [
    "IAgentClient",
    "IConfigLoader",
    "ISystemConfig",
    "ISessionRepository",
    "IContextRepository",
    "IMetricsRepository",
]
