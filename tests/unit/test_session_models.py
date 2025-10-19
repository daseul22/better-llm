"""
세션 도메인 모델 단위 테스트

테스트 범위:
- SessionResult 직렬화/역직렬화
- SessionMetadata 직렬화/역직렬화
- SessionMetadata.from_dict() 예외 처리
- SessionSearchCriteria 기본값
- SessionDetail 직렬화
"""

import pytest
from datetime import datetime
from src.domain.models.session import (
    SessionStatus,
    SessionResult,
    SessionMetadata,
    SessionSearchCriteria,
    SessionDetail
)


class TestSessionResult:
    """SessionResult 도메인 모델 테스트"""

    def test_to_dict_completed(self):
        """완료 상태 SessionResult의 직렬화 테스트"""
        result = SessionResult(
            status=SessionStatus.COMPLETED,
            files_modified=["main.py", "test.py"],
            tests_passed=True,
            error_message=None
        )

        data = result.to_dict()

        assert data["status"] == "completed"
        assert data["files_modified"] == ["main.py", "test.py"]
        assert data["tests_passed"] is True
        assert data["error_message"] is None

    def test_to_dict_error(self):
        """에러 상태 SessionResult의 직렬화 테스트"""
        result = SessionResult(
            status=SessionStatus.ERROR,
            files_modified=[],
            tests_passed=False,
            error_message="Connection timeout"
        )

        data = result.to_dict()

        assert data["status"] == "error"
        assert data["files_modified"] == []
        assert data["tests_passed"] is False
        assert data["error_message"] == "Connection timeout"

    def test_default_values(self):
        """기본값 테스트"""
        result = SessionResult(status=SessionStatus.COMPLETED)

        assert result.files_modified == []
        assert result.tests_passed is None
        assert result.error_message is None


class TestSessionMetadata:
    """SessionMetadata 도메인 모델 테스트"""

    def test_to_dict(self):
        """SessionMetadata의 직렬화 테스트"""
        metadata = SessionMetadata(
            session_id="session-123",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            completed_at=datetime(2024, 1, 1, 12, 30, 0),
            user_request="Implement login feature",
            status="completed",
            total_turns=5,
            agents_used=["planner", "coder"],
            files_modified=["auth.py", "login.py"],
            tests_passed=True,
            error_message=None
        )

        data = metadata.to_dict()

        assert data["session_id"] == "session-123"
        assert data["created_at"] == "2024-01-01T12:00:00"
        assert data["completed_at"] == "2024-01-01T12:30:00"
        assert data["user_request"] == "Implement login feature"
        assert data["status"] == "completed"
        assert data["total_turns"] == 5
        assert data["agents_used"] == ["planner", "coder"]
        assert data["files_modified"] == ["auth.py", "login.py"]
        assert data["tests_passed"] is True
        assert data["error_message"] is None

    def test_from_dict_success(self):
        """딕셔너리에서 SessionMetadata 생성 테스트"""
        data = {
            "session_id": "session-456",
            "created_at": "2024-02-01T10:00:00",
            "completed_at": "2024-02-01T10:15:00",
            "user_request": "Fix bug in payment",
            "status": "completed",
            "total_turns": 3,
            "agents_used": ["debugger"],
            "files_modified": ["payment.py"],
            "tests_passed": True,
            "error_message": None
        }

        metadata = SessionMetadata.from_dict(data)

        assert metadata.session_id == "session-456"
        assert metadata.created_at == datetime(2024, 2, 1, 10, 0, 0)
        assert metadata.completed_at == datetime(2024, 2, 1, 10, 15, 0)
        assert metadata.user_request == "Fix bug in payment"
        assert metadata.status == "completed"
        assert metadata.total_turns == 3
        assert metadata.agents_used == ["debugger"]
        assert metadata.files_modified == ["payment.py"]
        assert metadata.tests_passed is True
        assert metadata.error_message is None

    def test_from_dict_with_defaults(self):
        """선택적 필드가 없는 경우 기본값 테스트"""
        data = {
            "session_id": "session-789",
            "created_at": "2024-03-01T14:00:00",
            "completed_at": "2024-03-01T14:20:00",
            "user_request": "Add new feature",
            "status": "terminated",
            "total_turns": 2
        }

        metadata = SessionMetadata.from_dict(data)

        assert metadata.session_id == "session-789"
        assert metadata.agents_used == []
        assert metadata.files_modified == []
        assert metadata.tests_passed is None
        assert metadata.error_message is None

    def test_from_dict_missing_required_field(self):
        """필수 필드 누락 시 예외 발생 테스트"""
        data = {
            "session_id": "session-999",
            "created_at": "2024-04-01T16:00:00",
            # completed_at 누락
            "user_request": "Test task",
            "status": "error",
            "total_turns": 1
        }

        with pytest.raises(ValueError, match="필수 필드가 누락"):
            SessionMetadata.from_dict(data)

    def test_from_dict_invalid_date_format(self):
        """잘못된 날짜 형식 시 예외 발생 테스트"""
        data = {
            "session_id": "session-888",
            "created_at": "invalid-date",  # 잘못된 형식
            "completed_at": "2024-05-01T18:15:00",
            "user_request": "Invalid date test",
            "status": "error",
            "total_turns": 1
        }

        with pytest.raises(ValueError, match="날짜 형식 오류"):
            SessionMetadata.from_dict(data)


class TestSessionSearchCriteria:
    """SessionSearchCriteria 도메인 모델 테스트"""

    def test_default_values(self):
        """기본값 테스트"""
        criteria = SessionSearchCriteria()

        assert criteria.keyword is None
        assert criteria.status is None
        assert criteria.agent_name is None
        assert criteria.date_from is None
        assert criteria.date_to is None
        assert criteria.limit == 50
        assert criteria.offset == 0

    def test_custom_values(self):
        """사용자 정의 값 테스트"""
        criteria = SessionSearchCriteria(
            keyword="login",
            status="completed",
            agent_name="coder",
            date_from="2024-01-01",
            date_to="2024-01-31",
            limit=100,
            offset=20
        )

        assert criteria.keyword == "login"
        assert criteria.status == "completed"
        assert criteria.agent_name == "coder"
        assert criteria.date_from == "2024-01-01"
        assert criteria.date_to == "2024-01-31"
        assert criteria.limit == 100
        assert criteria.offset == 20


class TestSessionDetail:
    """SessionDetail 도메인 모델 테스트"""

    def test_to_dict(self):
        """SessionDetail의 직렬화 테스트"""
        metadata = SessionMetadata(
            session_id="session-detail-1",
            created_at=datetime(2024, 6, 1, 9, 0, 0),
            completed_at=datetime(2024, 6, 1, 9, 30, 0),
            user_request="Create user profile",
            status="completed",
            total_turns=4,
            agents_used=["planner", "coder", "tester"],
            files_modified=["profile.py", "user.py"],
            tests_passed=True
        )

        messages = [
            {
                "role": "user",
                "content": "Create user profile",
                "timestamp": "2024-06-01T09:00:00"
            },
            {
                "role": "agent",
                "content": "Planning the task",
                "agent_name": "planner",
                "timestamp": "2024-06-01T09:05:00"
            }
        ]

        detail = SessionDetail(metadata=metadata, messages=messages)
        data = detail.to_dict()

        assert data["metadata"]["session_id"] == "session-detail-1"
        assert data["metadata"]["user_request"] == "Create user profile"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["agent_name"] == "planner"

    def test_default_messages(self):
        """메시지가 없는 경우 기본값 테스트"""
        metadata = SessionMetadata(
            session_id="session-no-messages",
            created_at=datetime(2024, 7, 1, 10, 0, 0),
            completed_at=datetime(2024, 7, 1, 10, 5, 0),
            user_request="Quick task",
            status="completed",
            total_turns=0
        )

        detail = SessionDetail(metadata=metadata)

        assert detail.messages == []
        assert detail.to_dict()["messages"] == []
