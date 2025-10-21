# -*- coding: utf-8 -*-
"""
ApprovalRequest 매퍼 테스트

_row_to_approval_request() private 메서드의 동작을 검증합니다.
"""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.domain.models.approval import ApprovalRequest, ApprovalStatus, ApprovalType
from src.infrastructure.storage.sqlite_approval_repository import SqliteApprovalRepository
from src.infrastructure.storage.sqlite_session_repository import SqliteSessionRepository


@pytest.fixture
def temp_db():
    """임시 데이터베이스 픽스처"""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # 세션 테이블 먼저 생성 (외래키 제약조건)
        session_repo = SqliteSessionRepository(db_path)

        # 승인 리포지토리 생성
        approval_repo = SqliteApprovalRepository(db_path)

        yield approval_repo


class TestRowToApprovalRequestMapper:
    """_row_to_approval_request() 메서드 테스트"""

    def test_row_to_approval_request_pending(self, temp_db):
        """정상 케이스: status=pending"""
        # Given: pending 상태의 row 데이터
        row = (
            1,  # id
            "session-123",  # session_id
            ApprovalType.PLAN.value,  # approval_type
            ApprovalStatus.PENDING.value,  # status
            "테스트 작업",  # task_description
            '{"key": "value"}',  # context_data
            "2025-01-15T10:30:00",  # created_at
            None  # responded_at
        )

        # When: 매퍼 메서드 호출
        result = temp_db._row_to_approval_request(row)

        # Then: ApprovalRequest 객체로 정확히 변환
        assert isinstance(result, ApprovalRequest)
        assert result.id == 1
        assert result.session_id == "session-123"
        assert result.approval_type == ApprovalType.PLAN
        assert result.status == ApprovalStatus.PENDING
        assert result.task_description == "테스트 작업"
        assert result.context_data == '{"key": "value"}'
        assert result.created_at == datetime.fromisoformat("2025-01-15T10:30:00")
        assert result.responded_at is None

    def test_row_to_approval_request_approved(self, temp_db):
        """정상 케이스: status=approved"""
        # Given: approved 상태의 row 데이터
        row = (
            2,  # id
            "session-456",  # session_id
            ApprovalType.CODE.value,  # approval_type
            ApprovalStatus.APPROVED.value,  # status
            "코드 작성 승인",  # task_description
            None,  # context_data
            "2025-01-15T10:30:00",  # created_at
            "2025-01-15T10:35:00"  # responded_at
        )

        # When: 매퍼 메서드 호출
        result = temp_db._row_to_approval_request(row)

        # Then: responded_at이 올바르게 변환
        assert result.status == ApprovalStatus.APPROVED
        assert result.responded_at == datetime.fromisoformat("2025-01-15T10:35:00")
        assert result.context_data is None

    def test_row_to_approval_request_rejected(self, temp_db):
        """정상 케이스: status=rejected"""
        # Given: rejected 상태의 row 데이터
        row = (
            3,  # id
            "session-789",  # session_id
            ApprovalType.REVIEW.value,  # approval_type
            ApprovalStatus.REJECTED.value,  # status
            "리뷰 거부됨",  # task_description
            '{"reason": "incomplete"}',  # context_data
            "2025-01-15T10:30:00",  # created_at
            "2025-01-15T10:40:00"  # responded_at
        )

        # When: 매퍼 메서드 호출
        result = temp_db._row_to_approval_request(row)

        # Then: rejected 상태로 변환
        assert result.status == ApprovalStatus.REJECTED
        assert result.responded_at is not None

    def test_row_to_approval_request_null_metadata(self, temp_db):
        """특수 케이스: context_data=NULL"""
        # Given: context_data가 NULL인 row
        row = (
            4,
            "session-111",
            ApprovalType.TEST.value,
            ApprovalStatus.PENDING.value,
            "테스트 실행",
            None,  # context_data = NULL
            "2025-01-15T10:30:00",
            None
        )

        # When: 매퍼 메서드 호출
        result = temp_db._row_to_approval_request(row)

        # Then: None으로 처리
        assert result.context_data is None

    def test_row_to_approval_request_empty_metadata(self, temp_db):
        """특수 케이스: context_data="{}" (빈 JSON)"""
        # Given: 빈 JSON 문자열
        row = (
            5,
            "session-222",
            ApprovalType.PLAN.value,
            ApprovalStatus.PENDING.value,
            "계획 작성",
            "{}",  # 빈 JSON
            "2025-01-15T10:30:00",
            None
        )

        # When: 매퍼 메서드 호출
        result = temp_db._row_to_approval_request(row)

        # Then: 빈 JSON 문자열 그대로 유지
        assert result.context_data == "{}"

    def test_row_to_approval_request_null_responded_at(self, temp_db):
        """특수 케이스: responded_at=NULL"""
        # Given: responded_at이 NULL인 row (pending 상태)
        row = (
            6,
            "session-333",
            ApprovalType.CODE.value,
            ApprovalStatus.PENDING.value,
            "코드 작성 대기",
            None,
            "2025-01-15T10:30:00",
            None  # responded_at = NULL
        )

        # When: 매퍼 메서드 호출
        result = temp_db._row_to_approval_request(row)

        # Then: None으로 처리
        assert result.responded_at is None

    def test_row_to_approval_request_unicode(self, temp_db):
        """에지 케이스: 한글 포함"""
        # Given: 한글이 포함된 row
        row = (
            7,
            "세션-한글",
            ApprovalType.PLAN.value,
            ApprovalStatus.PENDING.value,
            "한글 작업 설명입니다. 이것은 긴 텍스트입니다.",
            '{"한글키": "한글값", "emoji": "🚀"}',
            "2025-01-15T10:30:00",
            None
        )

        # When: 매퍼 메서드 호출
        result = temp_db._row_to_approval_request(row)

        # Then: 한글과 이모지가 올바르게 처리
        assert result.session_id == "세션-한글"
        assert "한글 작업 설명" in result.task_description
        assert "한글키" in result.context_data
        assert "🚀" in result.context_data

    def test_row_to_approval_request_special_characters(self, temp_db):
        """에지 케이스: 특수문자 포함"""
        # Given: 특수문자가 포함된 row
        row = (
            8,
            "session-special!@#$%",
            ApprovalType.REVIEW.value,
            ApprovalStatus.PENDING.value,
            "Task with <script>alert('XSS')</script>",
            '{"sql": "SELECT * FROM users; DROP TABLE users;--"}',
            "2025-01-15T10:30:00",
            None
        )

        # When: 매퍼 메서드 호출
        result = temp_db._row_to_approval_request(row)

        # Then: 특수문자가 이스케이프 없이 그대로 유지 (DB에서 읽은 그대로)
        assert "!@#$%" in result.session_id
        assert "<script>" in result.task_description
        assert "DROP TABLE" in result.context_data
