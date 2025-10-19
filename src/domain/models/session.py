"""
세션 도메인 모델

SessionResult: 작업 세션 결과
SessionStatus: 세션 상태 (Enum)
SessionMetadata: 세션 메타데이터
SessionSearchCriteria: 세션 검색 조건
SessionDetail: 세션 상세 정보
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class SessionStatus(str, Enum):
    """세션 상태"""
    COMPLETED = "completed"
    TERMINATED = "terminated"
    ERROR = "error"
    INVALID_INPUT = "invalid_input"
    MAX_TURNS_REACHED = "max_turns_reached"


@dataclass
class SessionResult:
    """
    작업 세션 결과 도메인 모델

    Attributes:
        status: 종료 상태 (SessionStatus Enum)
        files_modified: 수정된 파일 목록
        tests_passed: 테스트 통과 여부
        error_message: 에러 메시지 (있을 경우)
    """
    status: SessionStatus
    files_modified: List[str] = field(default_factory=list)
    tests_passed: Optional[bool] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "status": self.status.value,
            "files_modified": self.files_modified,
            "tests_passed": self.tests_passed,
            "error_message": self.error_message
        }


@dataclass
class SessionMetadata:
    """
    세션 메타데이터 (목록/검색용)

    Attributes:
        session_id: 세션 고유 ID
        created_at: 생성 시각
        completed_at: 완료 시각
        user_request: 사용자 요청 (원본)
        status: 세션 상태
        total_turns: 총 대화 턴 수
        agents_used: 사용된 에이전트 목록
        files_modified: 수정된 파일 목록
        tests_passed: 테스트 통과 여부
        error_message: 에러 메시지 (있을 경우)
    """
    session_id: str
    created_at: datetime
    completed_at: datetime
    user_request: str
    status: str
    total_turns: int
    agents_used: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    tests_passed: Optional[bool] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "user_request": self.user_request,
            "status": self.status,
            "total_turns": self.total_turns,
            "agents_used": self.agents_used,
            "files_modified": self.files_modified,
            "tests_passed": self.tests_passed,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMetadata":
        """
        딕셔너리에서 객체 생성

        Args:
            data: 세션 메타데이터 딕셔너리

        Returns:
            SessionMetadata 객체

        Raises:
            ValueError: 필수 필드가 누락되었거나 날짜 형식이 잘못된 경우
        """
        try:
            return cls(
                session_id=data["session_id"],
                created_at=datetime.fromisoformat(data["created_at"]),
                completed_at=datetime.fromisoformat(data["completed_at"]),
                user_request=data["user_request"],
                status=data["status"],
                total_turns=data["total_turns"],
                agents_used=data.get("agents_used", []),
                files_modified=data.get("files_modified", []),
                tests_passed=data.get("tests_passed"),
                error_message=data.get("error_message")
            )
        except KeyError as e:
            raise ValueError(f"필수 필드가 누락되었습니다: {e}")
        except ValueError as e:
            raise ValueError(f"날짜 형식 오류: {e}")


@dataclass
class SessionSearchCriteria:
    """
    세션 검색 조건

    Attributes:
        keyword: 키워드 검색 (user_request, messages 내용)
        status: 상태 필터
        agent_name: 에이전트 이름 필터
        date_from: 시작 날짜 (YYYY-MM-DD)
        date_to: 종료 날짜 (YYYY-MM-DD)
        limit: 최대 결과 수
        offset: 결과 오프셋 (페이징)
    """
    keyword: Optional[str] = None
    status: Optional[str] = None
    agent_name: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass
class SessionDetail:
    """
    세션 상세 정보 (재생/분석용)

    Attributes:
        metadata: 세션 메타데이터
        messages: 대화 메시지 목록 (dict 형태)
    """
    metadata: SessionMetadata
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "metadata": self.metadata.to_dict(),
            "messages": self.messages
        }
