"""
Domain Models

Core business entities and value objects
"""

from .message import Message, Role
from .agent import AgentConfig, AgentRole
from .session import (
    SessionResult,
    SessionStatus,
    SessionMetadata,
    SessionSearchCriteria,
    SessionDetail
)
from .task import Task, TaskResult, TaskStatus
from .circuit_breaker import CircuitState, CircuitBreakerState
from .metrics import WorkerMetrics, SessionMetrics
from .template import (
    Template,
    TemplateCategory,
    TemplateVariable,
    TemplateFile,
    VariableType,
    TemplateNotFoundError,
    TemplateValidationError,
    TemplateRenderError
)
from .approval import (
    ApprovalStatus,
    ApprovalType,
    ApprovalRequest,
    ApprovalResponse
)
from .feedback import Feedback

__all__ = [
    "Message",
    "Role",
    "AgentConfig",
    "AgentRole",
    "SessionResult",
    "SessionStatus",
    "SessionMetadata",
    "SessionSearchCriteria",
    "SessionDetail",
    "Task",
    "TaskResult",
    "TaskStatus",
    "CircuitState",
    "CircuitBreakerState",
    "WorkerMetrics",
    "SessionMetrics",
    "Template",
    "TemplateCategory",
    "TemplateVariable",
    "TemplateFile",
    "VariableType",
    "TemplateNotFoundError",
    "TemplateValidationError",
    "TemplateRenderError",
    "ApprovalStatus",
    "ApprovalType",
    "ApprovalRequest",
    "ApprovalResponse",
    "Feedback",
]
