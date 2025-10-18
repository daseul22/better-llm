"""
세션 도메인 모델

SessionResult: 작업 세션 결과
SessionStatus: 세션 상태 (Enum)
"""

from dataclasses import dataclass, field
from typing import List, Optional
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
        status: 종료 상태
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
