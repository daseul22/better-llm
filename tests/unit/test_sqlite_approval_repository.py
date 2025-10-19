"""
SQLite 승인 리포지토리 단위 테스트

테스트 범위:
- create_approval_request() 테스트
- update_approval_status() 테스트
- create_feedback() 테스트
- get_pending_approvals() 테스트
- get_approval_history() 테스트
- update_approval_with_feedback() 트랜잭션 테스트 (중요!)
- 외래키 제약조건 검증 테스트 (중요!)
- UTF-8 인코딩 테스트 (한글 데이터)
"""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime
from dataclasses import replace

from src.infrastructure.storage.sqlite_approval_repository import SqliteApprovalRepository
from src.infrastructure.storage.sqlite_session_repository import SqliteSessionRepository
from src.domain.models.approval import (
    ApprovalRequest, ApprovalResponse, ApprovalStatus, ApprovalType
)
from src.domain.models.feedback import Feedback
from src.domain.models.session import SessionStatus, SessionResult
from src.domain.services.conversation import ConversationHistory


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """임시 SQLite 데이터베이스 경로 생성"""
    return tmp_path / "test_approvals.db"


@pytest.fixture
def session_repository(temp_db: Path) -> SqliteSessionRepository:
    """테스트용 SQLite 세션 리포지토리 (sessions 테이블 생성용)"""
    return SqliteSessionRepository(db_path=temp_db)


@pytest.fixture
def approval_repository(temp_db: Path, session_repository) -> SqliteApprovalRepository:
    """테스트용 SQLite 승인 리포지토리 (sessions 테이블이 먼저 생성되어야 함)"""
    return SqliteApprovalRepository(db_path=temp_db)


@pytest.fixture
def sample_session_id(session_repository: SqliteSessionRepository) -> str:
    """샘플 세션 생성 후 session_id 반환"""
    session_id = "test-session-123"
    history = ConversationHistory(max_length=50)
    history.add_message("user", "테스트 요청")

    result = SessionResult(
        status=SessionStatus.COMPLETED,
        files_modified=[],
        tests_passed=False,
        error_message=None
    )

    session_repository.save(session_id, "테스트 요청", history, result)
    return session_id


@pytest.fixture
def sample_approval_request(sample_session_id: str) -> ApprovalRequest:
    """샘플 승인 요청 객체"""
    return ApprovalRequest(
        session_id=sample_session_id,
        approval_type=ApprovalType.BEFORE_CODE_WRITE,
        task_description="새로운 기능 추가",
        context_data='{"file": "main.py"}',
        status=ApprovalStatus.PENDING,
        created_at=datetime(2025, 10, 19, 10, 0, 0)
    )


# ============================================================================
# 데이터베이스 초기화 테스트
# ============================================================================

class TestDatabaseInitialization:
    """데이터베이스 초기화 테스트"""

    def test_creates_approvals_table(self, approval_repository: SqliteApprovalRepository):
        """approvals 테이블 생성 확인"""
        with sqlite3.connect(approval_repository.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='approvals'
            """)
            result = cursor.fetchone()

            assert result is not None

    def test_creates_feedbacks_table(self, approval_repository: SqliteApprovalRepository):
        """feedbacks 테이블 생성 확인"""
        with sqlite3.connect(approval_repository.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='feedbacks'
            """)
            result = cursor.fetchone()

            assert result is not None

    def test_creates_indexes(self, approval_repository: SqliteApprovalRepository):
        """인덱스 생성 확인"""
        with sqlite3.connect(approval_repository.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index'
                ORDER BY name
            """)
            indexes = [row[0] for row in cursor.fetchall()]

            expected_indexes = [
                "idx_approvals_session",
                "idx_approvals_status",
                "idx_approvals_created_at",
                "idx_approvals_session_status",
                "idx_feedbacks_approval",
                "idx_feedbacks_session"
            ]

            for index_name in expected_indexes:
                assert index_name in indexes

    def test_requires_sessions_table(self, temp_db: Path):
        """sessions 테이블이 없으면 RuntimeError 발생"""
        # 빈 데이터베이스 생성
        with sqlite3.connect(temp_db) as conn:
            conn.execute("SELECT 1")  # 빈 DB 파일 생성

        with pytest.raises(RuntimeError, match="sessions 테이블이 존재하지 않습니다"):
            SqliteApprovalRepository(db_path=temp_db)


# ============================================================================
# create_approval_request() 테스트
# ============================================================================

class TestCreateApprovalRequest:
    """승인 요청 생성 테스트"""

    def test_create_approval_request_success(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """승인 요청 생성 성공"""
        created = approval_repository.create_approval_request(sample_approval_request)

        assert created.id is not None
        assert created.id > 0
        assert created.session_id == sample_approval_request.session_id
        assert created.approval_type == sample_approval_request.approval_type
        assert created.task_description == sample_approval_request.task_description
        assert created.context_data == sample_approval_request.context_data
        assert created.status == ApprovalStatus.PENDING

    def test_create_approval_request_nonexistent_session(
        self,
        approval_repository: SqliteApprovalRepository
    ):
        """존재하지 않는 세션 ID로 승인 요청 생성 시 ValueError"""
        invalid_request = ApprovalRequest(
            session_id="nonexistent-session",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="테스트 작업"
        )

        with pytest.raises(ValueError, match="세션을 찾을 수 없습니다"):
            approval_repository.create_approval_request(invalid_request)

    def test_create_approval_request_without_context_data(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_session_id: str
    ):
        """context_data 없이 승인 요청 생성"""
        request = ApprovalRequest(
            session_id=sample_session_id,
            approval_type=ApprovalType.AFTER_CODE_WRITE,
            task_description="코드 리뷰"
        )

        created = approval_repository.create_approval_request(request)

        assert created.id is not None
        assert created.context_data is None

    def test_create_approval_request_utf8_encoding(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_session_id: str
    ):
        """UTF-8 인코딩 테스트 (한글 데이터)"""
        korean_request = ApprovalRequest(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_TEST_RUN,
            task_description="새로운 기능 추가하기 🚀",
            context_data='{"message": "안녕하세요", "emoji": "👋"}'
        )

        created = approval_repository.create_approval_request(korean_request)

        assert created.id is not None
        assert created.task_description == "새로운 기능 추가하기 🚀"
        assert "안녕하세요" in created.context_data
        assert "👋" in created.context_data


# ============================================================================
# update_approval_status() 테스트
# ============================================================================

class TestUpdateApprovalStatus:
    """승인 상태 업데이트 테스트"""

    def test_update_approval_status_success(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """승인 상태 업데이트 성공"""
        created = approval_repository.create_approval_request(sample_approval_request)

        response = ApprovalResponse(
            approval_id=created.id,
            status=ApprovalStatus.APPROVED,
            feedback_content="좋습니다.",
            responded_at=datetime(2025, 10, 19, 10, 30, 0)
        )

        updated = approval_repository.update_approval_status(created.id, response)

        assert updated.id == created.id
        assert updated.status == ApprovalStatus.APPROVED
        assert updated.responded_at == datetime(2025, 10, 19, 10, 30, 0)

    def test_update_nonexistent_approval(
        self,
        approval_repository: SqliteApprovalRepository
    ):
        """존재하지 않는 승인 요청 업데이트 시 ValueError"""
        response = ApprovalResponse(
            approval_id=999,
            status=ApprovalStatus.APPROVED
        )

        with pytest.raises(ValueError, match="승인 요청을 찾을 수 없습니다"):
            approval_repository.update_approval_status(999, response)

    def test_update_approval_status_to_rejected(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """승인 거부 상태로 업데이트"""
        created = approval_repository.create_approval_request(sample_approval_request)

        response = ApprovalResponse(
            approval_id=created.id,
            status=ApprovalStatus.REJECTED,
            responded_at=datetime(2025, 10, 19, 11, 0, 0)
        )

        updated = approval_repository.update_approval_status(created.id, response)

        assert updated.status == ApprovalStatus.REJECTED


# ============================================================================
# create_feedback() 테스트
# ============================================================================

class TestCreateFeedback:
    """피드백 생성 테스트"""

    def test_create_feedback_success(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """피드백 생성 성공"""
        created_approval = approval_repository.create_approval_request(sample_approval_request)

        feedback = Feedback(
            approval_id=created_approval.id,
            session_id=created_approval.session_id,
            feedback_content="변수명을 더 명확하게 변경하세요.",
            created_at=datetime(2025, 10, 19, 12, 0, 0)
        )

        created_feedback = approval_repository.create_feedback(feedback)

        assert created_feedback.id is not None
        assert created_feedback.id > 0
        assert created_feedback.approval_id == created_approval.id
        assert created_feedback.session_id == created_approval.session_id
        assert created_feedback.feedback_content == "변수명을 더 명확하게 변경하세요."

    def test_create_feedback_nonexistent_approval(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_session_id: str
    ):
        """존재하지 않는 승인 요청에 대한 피드백 생성 시 ValueError"""
        feedback = Feedback(
            approval_id=999,
            session_id=sample_session_id,
            feedback_content="테스트 피드백"
        )

        with pytest.raises(ValueError, match="승인 요청을 찾을 수 없습니다"):
            approval_repository.create_feedback(feedback)

    def test_create_feedback_nonexistent_session(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """존재하지 않는 세션에 대한 피드백 생성 시 ValueError"""
        created_approval = approval_repository.create_approval_request(sample_approval_request)

        feedback = Feedback(
            approval_id=created_approval.id,
            session_id="nonexistent-session",
            feedback_content="테스트 피드백"
        )

        with pytest.raises(ValueError, match="세션을 찾을 수 없습니다"):
            approval_repository.create_feedback(feedback)

    def test_create_feedback_utf8_encoding(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """UTF-8 인코딩 테스트 (한글 피드백)"""
        created_approval = approval_repository.create_approval_request(sample_approval_request)

        korean_feedback = Feedback(
            approval_id=created_approval.id,
            session_id=created_approval.session_id,
            feedback_content="코드 품질이 우수합니다. 계속 이렇게 작성하세요! 👍"
        )

        created_feedback = approval_repository.create_feedback(korean_feedback)

        assert created_feedback.id is not None
        assert "코드 품질이 우수합니다" in created_feedback.feedback_content
        assert "👍" in created_feedback.feedback_content


# ============================================================================
# get_pending_approvals() 테스트
# ============================================================================

class TestGetPendingApprovals:
    """대기 중인 승인 요청 목록 조회 테스트"""

    def test_get_all_pending_approvals(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_session_id: str,
        session_repository: SqliteSessionRepository
    ):
        """전체 대기 중인 승인 목록 조회"""
        # 두 번째 세션 생성
        session_id_2 = "test-session-456"
        history2 = ConversationHistory(max_length=50)
        history2.add_message("user", "테스트 2")
        result2 = SessionResult(
            status=SessionStatus.COMPLETED,
            files_modified=[],
            tests_passed=False,
            error_message=None
        )
        session_repository.save(session_id_2, "테스트 2", history2, result2)

        # 3개의 승인 요청 생성
        request1 = ApprovalRequest(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="작업 1",
            created_at=datetime(2025, 10, 19, 10, 0, 0)
        )
        request2 = ApprovalRequest(
            session_id=session_id_2,
            approval_type=ApprovalType.AFTER_CODE_WRITE,
            task_description="작업 2",
            created_at=datetime(2025, 10, 19, 11, 0, 0)
        )
        request3 = ApprovalRequest(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_TEST_RUN,
            task_description="작업 3",
            status=ApprovalStatus.APPROVED,  # 이미 승인됨
            created_at=datetime(2025, 10, 19, 12, 0, 0)
        )

        approval_repository.create_approval_request(request1)
        approval_repository.create_approval_request(request2)
        approval_repository.create_approval_request(request3)

        # 대기 중인 승인만 조회 (PENDING만)
        pending = approval_repository.get_pending_approvals()

        assert len(pending) == 2
        assert all(a.status == ApprovalStatus.PENDING for a in pending)

        # 생성일시 오름차순 정렬 확인
        assert pending[0].created_at < pending[1].created_at

    def test_get_pending_approvals_by_session(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_session_id: str
    ):
        """특정 세션의 대기 중인 승인 목록 조회"""
        request1 = ApprovalRequest(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="작업 1",
            created_at=datetime(2025, 10, 19, 10, 0, 0)
        )
        request2 = ApprovalRequest(
            session_id=sample_session_id,
            approval_type=ApprovalType.AFTER_CODE_WRITE,
            task_description="작업 2",
            created_at=datetime(2025, 10, 19, 11, 0, 0)
        )

        approval_repository.create_approval_request(request1)
        approval_repository.create_approval_request(request2)

        pending = approval_repository.get_pending_approvals(session_id=sample_session_id)

        assert len(pending) == 2
        assert all(a.session_id == sample_session_id for a in pending)

    def test_get_pending_approvals_empty(
        self,
        approval_repository: SqliteApprovalRepository
    ):
        """대기 중인 승인이 없는 경우"""
        pending = approval_repository.get_pending_approvals()

        assert pending == []


# ============================================================================
# get_approval_history() 테스트
# ============================================================================

class TestGetApprovalHistory:
    """승인 이력 조회 테스트"""

    def test_get_approval_history_success(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_session_id: str
    ):
        """승인 이력 조회 성공"""
        # 여러 승인 요청 생성
        request1 = ApprovalRequest(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="작업 1",
            status=ApprovalStatus.APPROVED,
            created_at=datetime(2025, 10, 19, 10, 0, 0),
            responded_at=datetime(2025, 10, 19, 10, 30, 0)
        )
        request2 = ApprovalRequest(
            session_id=sample_session_id,
            approval_type=ApprovalType.AFTER_CODE_WRITE,
            task_description="작업 2",
            status=ApprovalStatus.REJECTED,
            created_at=datetime(2025, 10, 19, 11, 0, 0),
            responded_at=datetime(2025, 10, 19, 11, 15, 0)
        )

        approval_repository.create_approval_request(request1)
        approval_repository.create_approval_request(request2)

        history = approval_repository.get_approval_history(sample_session_id)

        assert len(history) == 2

        # 생성일시 내림차순 정렬 확인
        assert history[0].created_at > history[1].created_at

    def test_get_approval_history_empty(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_session_id: str
    ):
        """승인 이력이 없는 경우"""
        history = approval_repository.get_approval_history(sample_session_id)

        assert history == []


# ============================================================================
# get_feedbacks_by_approval() 테스트
# ============================================================================

class TestGetFeedbacksByApproval:
    """승인 요청별 피드백 조회 테스트"""

    def test_get_feedbacks_by_approval_success(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """승인 요청별 피드백 조회 성공"""
        created_approval = approval_repository.create_approval_request(sample_approval_request)

        # 여러 피드백 생성
        feedback1 = Feedback(
            approval_id=created_approval.id,
            session_id=created_approval.session_id,
            feedback_content="첫 번째 피드백",
            created_at=datetime(2025, 10, 19, 12, 0, 0)
        )
        feedback2 = Feedback(
            approval_id=created_approval.id,
            session_id=created_approval.session_id,
            feedback_content="두 번째 피드백",
            created_at=datetime(2025, 10, 19, 12, 30, 0)
        )

        approval_repository.create_feedback(feedback1)
        approval_repository.create_feedback(feedback2)

        feedbacks = approval_repository.get_feedbacks_by_approval(created_approval.id)

        assert len(feedbacks) == 2
        assert feedbacks[0].feedback_content == "첫 번째 피드백"
        assert feedbacks[1].feedback_content == "두 번째 피드백"

        # 생성일시 오름차순 정렬 확인
        assert feedbacks[0].created_at < feedbacks[1].created_at

    def test_get_feedbacks_by_approval_empty(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """피드백이 없는 경우"""
        created_approval = approval_repository.create_approval_request(sample_approval_request)

        feedbacks = approval_repository.get_feedbacks_by_approval(created_approval.id)

        assert feedbacks == []


# ============================================================================
# update_approval_with_feedback() 트랜잭션 테스트
# ============================================================================

class TestUpdateApprovalWithFeedback:
    """승인 상태 업데이트 + 피드백 생성 트랜잭션 테스트"""

    def test_update_approval_with_feedback_success(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """승인 상태 업데이트 + 피드백 생성 트랜잭션 성공"""
        created_approval = approval_repository.create_approval_request(sample_approval_request)

        response = ApprovalResponse(
            approval_id=created_approval.id,
            status=ApprovalStatus.MODIFIED,
            feedback_content="수정 요청",
            responded_at=datetime(2025, 10, 19, 13, 0, 0)
        )

        feedback = Feedback(
            approval_id=created_approval.id,
            session_id=created_approval.session_id,
            feedback_content="수정 요청",
            created_at=datetime(2025, 10, 19, 13, 0, 0)
        )

        updated_approval, created_feedback = approval_repository.update_approval_with_feedback(
            approval_id=created_approval.id,
            response=response,
            feedback=feedback
        )

        # 승인 상태 업데이트 확인
        assert updated_approval.status == ApprovalStatus.MODIFIED
        assert updated_approval.responded_at == datetime(2025, 10, 19, 13, 0, 0)

        # 피드백 생성 확인
        assert created_feedback is not None
        assert created_feedback.id is not None
        assert created_feedback.feedback_content == "수정 요청"

    def test_update_approval_without_feedback(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """피드백 없이 승인 상태만 업데이트"""
        created_approval = approval_repository.create_approval_request(sample_approval_request)

        response = ApprovalResponse(
            approval_id=created_approval.id,
            status=ApprovalStatus.APPROVED,
            responded_at=datetime(2025, 10, 19, 14, 0, 0)
        )

        updated_approval, created_feedback = approval_repository.update_approval_with_feedback(
            approval_id=created_approval.id,
            response=response,
            feedback=None
        )

        assert updated_approval.status == ApprovalStatus.APPROVED
        assert created_feedback is None

    def test_transaction_rollback_on_error(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """에러 발생 시 트랜잭션 롤백 확인"""
        created_approval = approval_repository.create_approval_request(sample_approval_request)

        # 존재하지 않는 승인 ID로 업데이트 시도
        response = ApprovalResponse(
            approval_id=999,
            status=ApprovalStatus.APPROVED
        )

        with pytest.raises(ValueError):
            approval_repository.update_approval_with_feedback(
                approval_id=999,
                response=response,
                feedback=None
            )

        # 원본 승인 요청이 변경되지 않았는지 확인
        original = approval_repository.get_approval_by_id(created_approval.id)
        assert original.status == ApprovalStatus.PENDING
        assert original.responded_at is None


# ============================================================================
# 외래키 제약조건 테스트
# ============================================================================

class TestForeignKeyConstraints:
    """외래키 제약조건 테스트"""

    def test_approval_requires_existing_session(
        self,
        approval_repository: SqliteApprovalRepository
    ):
        """승인 요청은 존재하는 세션 ID가 필요"""
        request = ApprovalRequest(
            session_id="nonexistent-session-id",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="테스트 작업"
        )

        with pytest.raises(ValueError, match="세션을 찾을 수 없습니다"):
            approval_repository.create_approval_request(request)

    def test_feedback_requires_existing_approval(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_session_id: str
    ):
        """피드백은 존재하는 승인 요청 ID가 필요"""
        feedback = Feedback(
            approval_id=999,  # 존재하지 않는 승인 ID
            session_id=sample_session_id,
            feedback_content="테스트 피드백"
        )

        with pytest.raises(ValueError, match="승인 요청을 찾을 수 없습니다"):
            approval_repository.create_feedback(feedback)

    def test_feedback_requires_existing_session(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """피드백은 존재하는 세션 ID가 필요"""
        created_approval = approval_repository.create_approval_request(sample_approval_request)

        feedback = Feedback(
            approval_id=created_approval.id,
            session_id="nonexistent-session-id",
            feedback_content="테스트 피드백"
        )

        with pytest.raises(ValueError, match="세션을 찾을 수 없습니다"):
            approval_repository.create_feedback(feedback)


# ============================================================================
# 불변성 및 데이터 무결성 테스트
# ============================================================================

class TestDataImmutability:
    """불변성 및 데이터 무결성 테스트"""

    def test_create_returns_new_instance_with_id(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """create_approval_request는 ID가 포함된 새 인스턴스 반환"""
        original = sample_approval_request
        assert original.id is None

        created = approval_repository.create_approval_request(original)

        # 원본은 변경되지 않음
        assert original.id is None

        # 반환된 객체는 ID 포함
        assert created.id is not None
        assert created.id > 0

    def test_update_returns_updated_instance(
        self,
        approval_repository: SqliteApprovalRepository,
        sample_approval_request: ApprovalRequest
    ):
        """update_approval_status는 업데이트된 인스턴스 반환"""
        created = approval_repository.create_approval_request(sample_approval_request)
        original_status = created.status

        response = ApprovalResponse(
            approval_id=created.id,
            status=ApprovalStatus.APPROVED
        )

        updated = approval_repository.update_approval_status(created.id, response)

        # 업데이트된 객체는 새 상태 포함
        assert updated.status == ApprovalStatus.APPROVED
        assert updated.responded_at is not None

        # 원본 객체는 변경되지 않음 (새 인스턴스 반환)
        assert created.status == original_status
