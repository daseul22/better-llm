"""
피드백 도메인 모델

Feedback: 사용자 피드백 모델
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Feedback:
    """
    피드백 도메인 모델

    Attributes:
        id: 피드백 고유 ID (DB auto-increment)
        approval_id: 승인 요청 ID (ApprovalRequest와 1:N 관계)
        session_id: 세션 ID (Session과 1:N 관계)
        feedback_content: 피드백 내용
        created_at: 생성 시각
    """
    approval_id: int
    session_id: str
    feedback_content: str
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """
        JSON 직렬화용 딕셔너리 변환

        Returns:
            피드백 데이터 딕셔너리
        """
        return {
            "id": self.id,
            "approval_id": self.approval_id,
            "session_id": self.session_id,
            "feedback_content": self.feedback_content,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feedback":
        """
        딕셔너리에서 객체 생성

        Args:
            data: 피드백 데이터 딕셔너리

        Returns:
            Feedback 객체

        Raises:
            ValueError: 필수 필드가 누락되었거나 날짜 형식이 잘못된 경우
        """
        try:
            return cls(
                id=data.get("id"),
                approval_id=data["approval_id"],
                session_id=data["session_id"],
                feedback_content=data["feedback_content"],
                created_at=datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now()
            )
        except KeyError as e:
            raise ValueError(f"필수 필드가 누락되었습니다: {e}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"데이터 형식 오류: {e}")
