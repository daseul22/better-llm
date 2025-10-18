"""
대화 히스토리 도메인 서비스

ConversationHistory: 모든 메시지를 시간순으로 저장하고 관리
"""

from typing import List, Optional
from datetime import datetime
import json
from pathlib import Path

from ..models import Message


class ConversationHistory:
    """
    대화 히스토리 관리 서비스

    모든 에이전트와 사용자 메시지를 하나의 스레드에 저장하고 관리합니다.
    최대 메시지 개수 제한을 적용합니다.

    Attributes:
        max_length: 최대 메시지 개수 (기본값: 50)
        messages: 메시지 리스트
    """

    def __init__(self, max_length: int = 50):
        """
        Args:
            max_length: 최대 메시지 개수. 초과 시 가장 오래된 메시지부터 제거됨
        """
        self.max_length = max_length
        self.messages: List[Message] = []

    def add_message(
        self,
        role: str,
        content: str,
        agent_name: Optional[str] = None
    ) -> None:
        """
        새 메시지를 히스토리에 추가

        최대 길이를 초과하면 가장 오래된 메시지를 제거합니다.

        Args:
            role: 메시지 역할 ('user' or 'agent')
            content: 메시지 내용
            agent_name: 에이전트 이름 (role이 'agent'일 경우 필수)
        """
        message = Message(
            role=role,
            content=content,
            agent_name=agent_name,
            timestamp=datetime.now()
        )
        self.messages.append(message)

        # 최대 길이 초과 시 가장 오래된 메시지 제거
        if len(self.messages) > self.max_length:
            removed = self.messages.pop(0)

    def get_history(self) -> List[Message]:
        """
        전체 대화 히스토리 조회

        Returns:
            시간순으로 정렬된 메시지 리스트
        """
        return self.messages.copy()

    def get_last_message(self) -> Optional[Message]:
        """
        가장 최근 메시지 조회

        Returns:
            가장 최근 메시지 또는 None (히스토리가 비어있을 경우)
        """
        return self.messages[-1] if self.messages else None

    def get_last_n_messages(self, n: int) -> List[Message]:
        """
        최근 N개 메시지 조회

        Args:
            n: 조회할 메시지 개수

        Returns:
            최근 N개 메시지 리스트
        """
        return self.messages[-n:] if n > 0 else []

    def clear(self) -> None:
        """히스토리 초기화"""
        self.messages.clear()

    def to_dict(self) -> dict:
        """
        히스토리를 딕셔너리로 변환 (JSON 저장용)

        Returns:
            딕셔너리 형태의 히스토리 데이터
        """
        return {
            "max_length": self.max_length,
            "messages": [msg.to_dict() for msg in self.messages],
            "total_messages": len(self.messages)
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationHistory":
        """
        딕셔너리에서 히스토리 생성

        Args:
            data: 딕셔너리 데이터

        Returns:
            ConversationHistory 인스턴스
        """
        history = cls(max_length=data.get("max_length", 50))
        for msg_data in data.get("messages", []):
            msg = Message.from_dict(msg_data)
            history.messages.append(msg)
        return history

    def __len__(self) -> int:
        """히스토리 내 메시지 개수"""
        return len(self.messages)

    def __repr__(self) -> str:
        return f"ConversationHistory(messages={len(self.messages)}, max_length={self.max_length})"
