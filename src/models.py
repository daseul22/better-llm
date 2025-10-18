"""
데이터 모델 정의

Message: 대화 메시지
AgentConfig: 에이전트 설정
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
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
    대화 메시지

    Attributes:
        role: 메시지 발신자 역할 ('user' or 'agent')
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


@dataclass
class AgentConfig:
    """
    에이전트 설정

    Attributes:
        name: 에이전트 식별자 (예: 'planner', 'coder', 'tester')
        role: 에이전트 역할 설명
        system_prompt: 시스템 프롬프트 (또는 파일 경로)
        tools: 사용 가능한 도구 목록 (예: ['read', 'write', 'bash'])
        model: Claude 모델명 (예: 'claude-sonnet-4')
    """
    name: str
    role: str
    system_prompt: str
    tools: List[str]
    model: str = "claude-sonnet-4"

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "name": self.name,
            "role": self.role,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "model": self.model
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        """딕셔너리에서 AgentConfig 객체 생성"""
        return cls(**data)


@dataclass
class SessionResult:
    """
    작업 세션 결과

    Attributes:
        status: 종료 상태 ('completed', 'terminated', 'error')
        files_modified: 수정된 파일 목록
        tests_passed: 테스트 통과 여부
        error_message: 에러 메시지 (있을 경우)
    """
    status: str
    files_modified: List[str] = field(default_factory=list)
    tests_passed: Optional[bool] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "status": self.status,
            "files_modified": self.files_modified,
            "tests_passed": self.tests_passed,
            "error_message": self.error_message
        }
