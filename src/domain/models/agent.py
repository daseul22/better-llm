"""
에이전트 도메인 모델

AgentConfig: 에이전트 설정
AgentRole: 에이전트 역할 (Enum)
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class AgentRole(str, Enum):
    """에이전트 역할"""
    MANAGER = "manager"
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"


@dataclass
class AgentConfig:
    """
    에이전트 설정 도메인 모델

    Attributes:
        name: 에이전트 식별자 (예: 'planner', 'coder', 'tester')
        role: 에이전트 역할 설명
        system_prompt: 시스템 프롬프트 (또는 파일 경로)
        allowed_tools: 사용 가능한 도구 목록 (예: ['read', 'write', 'bash'])
        model: Claude 모델명 (예: 'claude-sonnet-4')
        thinking: Thinking 모드 활성화 여부 (ultrathink 추가, 기본값: False)
    """
    name: str
    role: str
    system_prompt: str
    allowed_tools: List[str]
    model: str = "claude-sonnet-4"
    thinking: bool = False

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "name": self.name,
            "role": self.role,
            "system_prompt": self.system_prompt,
            "allowed_tools": self.allowed_tools,
            "model": self.model,
            "thinking": self.thinking
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        """딕셔너리에서 AgentConfig 객체 생성"""
        return cls(**data)
