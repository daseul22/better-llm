"""
Application Ports (Interfaces)

External dependency interfaces (Dependency Inversion Principle)
Implemented by Infrastructure layer
"""

from .agent_port import IAgentClient
from .config_port import IConfigLoader, ISystemConfig
from .storage_port import ISessionRepository, IContextRepository
from .template_port import ITemplateRepository, ITemplateEngine
from .approval_port import IApprovalRepository
from .memory_port import IMemoryBankRepository

# Re-export from domain.ports (Clean Architecture DIP)
from src.domain.ports import IMetricsRepository

__all__ = [
    "IAgentClient",
    "IConfigLoader",
    "ISystemConfig",
    "ISessionRepository",
    "IContextRepository",
    "ITemplateRepository",
    "ITemplateEngine",
    "IApprovalRepository",
    "IMetricsRepository",
    "IMemoryBankRepository",
]
