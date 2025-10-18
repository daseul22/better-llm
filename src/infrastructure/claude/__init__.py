"""
Claude SDK Infrastructure

Manager and Worker Agent implementations using Claude Agent SDK
"""

from .manager_client import ManagerAgent
from .worker_client import WorkerAgent

__all__ = ["ManagerAgent", "WorkerAgent"]
