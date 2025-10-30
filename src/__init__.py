"""
그룹 챗 오케스트레이션 시스템 v4.0 - Clean Architecture

여러 Claude 에이전트가 협업하여 복잡한 소프트웨어 개발 작업을 자동화합니다.

아키텍처:
- domain: 핵심 비즈니스 로직 (순수 Python)
- application: Use Cases 및 Ports (인터페이스)
- infrastructure: 외부 의존성 구현 (Claude SDK, Config, Storage)
- presentation: UI (CLI, TUI)

기존 코드 호환성:
- src/models.py, src/conversation.py 등은 새로운 모듈을 re-export하여 호환성 유지
"""

__version__ = "4.0.0"

# Re-export for backward compatibility
# 기존 코드가 "from src.models import Message"를 사용하면 여전히 동작함

from .domain.models import (
    Message,
    Role,
    AgentConfig,
    AgentRole,
)

__all__ = [
    "Message",
    "Role",
    "AgentConfig",
    "AgentRole",
]
