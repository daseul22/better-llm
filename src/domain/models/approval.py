"""
승인 요청 및 응답 도메인 모델

ApprovalStatus: 승인 상태 (Enum)
ApprovalType: 승인 지점 타입 (Enum)
ApprovalRequest: 승인 요청 도메인 모델
ApprovalResponse: 승인 응답 도메인 모델
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class ApprovalStatus(str, Enum):
    """승인 상태"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class ApprovalType(str, Enum):
    """승인 지점 타입"""
    BEFORE_CODE_WRITE = "before_code_write"
    AFTER_CODE_WRITE = "after_code_write"
    BEFORE_TEST_RUN = "before_test_run"
    BEFORE_DEPLOYMENT = "before_deployment"


@dataclass
class ApprovalRequest:
    """
    승인 요청 도메인 모델

    Attributes:
        id: 승인 요청 고유 ID (DB auto-increment)
        session_id: 세션 ID (Session과 1:N 관계)
        approval_type: 승인 지점 타입
        status: 승인 상태 (기본값: PENDING)
        task_description: 작업 설명
        context_data: 컨텍스트 데이터 (JSON 문자열)
        created_at: 생성 시각
        responded_at: 응답 시각 (선택적)
    """
    session_id: str
    approval_type: ApprovalType
    task_description: str
    context_data: Optional[str] = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    responded_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        JSON 직렬화용 딕셔너리 변환

        Returns:
            승인 요청 데이터 딕셔너리
        """
        return {
            "id": self.id,
            "session_id": self.session_id,
            "approval_type": self.approval_type.value,
            "status": self.status.value,
            "task_description": self.task_description,
            "context_data": self.context_data,
            "created_at": self.created_at.isoformat(),
            "responded_at": self.responded_at.isoformat() if self.responded_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRequest":
        """
        딕셔너리에서 객체 생성

        Args:
            data: 승인 요청 데이터 딕셔너리

        Returns:
            ApprovalRequest 객체

        Raises:
            ValueError: 필수 필드가 누락되었거나 날짜 형식이 잘못된 경우
        """
        try:
            return cls(
                id=data.get("id"),
                session_id=data["session_id"],
                approval_type=ApprovalType(data["approval_type"]),
                status=ApprovalStatus(data["status"]),
                task_description=data["task_description"],
                context_data=data.get("context_data"),
                created_at=datetime.fromisoformat(data["created_at"]),
                responded_at=datetime.fromisoformat(data["responded_at"])
                if data.get("responded_at")
                else None
            )
        except KeyError as e:
            raise ValueError(f"필수 필드가 누락되었습니다: {e}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"데이터 형식 오류: {e}")


@dataclass
class ApprovalResponse:
    """
    승인 응답 도메인 모델

    Attributes:
        approval_id: 승인 요청 ID
        status: 승인 상태 (APPROVED, REJECTED, MODIFIED)
        feedback_content: 피드백 내용 (선택적)
        responded_at: 응답 시각
    """
    approval_id: int
    status: ApprovalStatus
    feedback_content: Optional[str] = None
    responded_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """
        JSON 직렬화용 딕셔너리 변환

        Returns:
            승인 응답 데이터 딕셔너리
        """
        return {
            "approval_id": self.approval_id,
            "status": self.status.value,
            "feedback_content": self.feedback_content,
            "responded_at": self.responded_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalResponse":
        """
        딕셔너리에서 객체 생성

        Args:
            data: 승인 응답 데이터 딕셔너리

        Returns:
            ApprovalResponse 객체

        Raises:
            ValueError: 필수 필드가 누락되었거나 날짜 형식이 잘못된 경우
        """
        try:
            return cls(
                approval_id=data["approval_id"],
                status=ApprovalStatus(data["status"]),
                feedback_content=data.get("feedback_content"),
                responded_at=datetime.fromisoformat(data["responded_at"])
                if data.get("responded_at")
                else datetime.now()
            )
        except KeyError as e:
            raise ValueError(f"필수 필드가 누락되었습니다: {e}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"데이터 형식 오류: {e}")
