"""
메시지 도메인 모델

Message: 대화 메시지
Role: 메시지 역할 (Enum)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class Role(str, Enum):
    """메시지 역할"""
    USER = "user"
    AGENT = "agent"
    MANAGER = "manager"
    SYSTEM = "system"


@dataclass
class Message:
    """
    대화 메시지 도메인 모델

    Attributes:
        role: 메시지 발신자 역할
        content: 메시지 내용
        agent_name: 에이전트 이름 (role이 'agent'일 경우)
        timestamp: 메시지 생성 시각
    """
    role: str
    content: str
    agent_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "role": self.role,
            "content": self.content,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """딕셔너리에서 Message 객체 생성"""
        data = data.copy()
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
