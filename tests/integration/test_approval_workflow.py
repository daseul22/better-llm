"""
승인 워크플로우 통합 테스트

전체 승인 워크플로우 테스트:
- 승인 요청 생성 → 대기 중 조회 → 승인/거부/수정
- 세션과의 연동 테스트
- 외래키 제약조건 실제 동작 확인
- 트랜잭션 롤백 시나리오 테스트
- Use Case + Repository 통합 테스트
"""

import pytest
from pathlib import Path
from datetime import datetime

from src.infrastructure.storage.sqlite_approval_repository import SqliteApprovalRepository
from src.infrastructure.storage.sqlite_session_repository import SqliteSessionRepository
from src.application.use_cases.approval_management import (
    RequestApprovalUseCase,
    ProcessApprovalResponseUseCase,
    GetPendingApprovalsUseCase,
    ApprovalHistoryUseCase
)
from src.domain.models.approval import ApprovalStatus, ApprovalType
from src.domain.models.session import SessionStatus, SessionResult
from src.domain.services.conversation import ConversationHistory


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """임시 SQLite 데이터베이스 경로"""
    return tmp_path / "test_workflow.db"


@pytest.fixture
def session_repository(temp_db: Path) -> SqliteSessionRepository:
    """세션 리포지토리"""
    return SqliteSessionRepository(db_path=temp_db)


@pytest.fixture
def approval_repository(temp_db: Path, session_repository) -> SqliteApprovalRepository:
    """승인 리포지토리"""
    return SqliteApprovalRepository(db_path=temp_db)


@pytest.fixture
def request_approval_use_case(approval_repository) -> RequestApprovalUseCase:
    """승인 요청 생성 Use Case"""
    return RequestApprovalUseCase(approval_repository)


@pytest.fixture
def process_approval_use_case(approval_repository) -> ProcessApprovalResponseUseCase:
    """승인 응답 처리 Use Case"""
    return ProcessApprovalResponseUseCase(approval_repository)


@pytest.fixture
def get_pending_use_case(approval_repository) -> GetPendingApprovalsUseCase:
    """대기 중인 승인 조회 Use Case"""
    return GetPendingApprovalsUseCase(approval_repository)


@pytest.fixture
def approval_history_use_case(approval_repository) -> ApprovalHistoryUseCase:
    """승인 이력 조회 Use Case"""
    return ApprovalHistoryUseCase(approval_repository)


@pytest.fixture
def sample_session_id(session_repository: SqliteSessionRepository) -> str:
    """샘플 세션 생성"""
    session_id = "test-session-workflow"
    history = ConversationHistory(max_length=50)
    history.add_message("user", "새로운 기능을 추가해주세요.")

    result = SessionResult(
        status=SessionStatus.COMPLETED,
        files_modified=[],
        tests_passed=False,
        error_message=None
    )

    session_repository.save(session_id, "새로운 기능을 추가해주세요.", history, result)
    return session_id


# ============================================================================
# 승인 워크플로우 통합 테스트
# ============================================================================

class TestApprovalWorkflow:
    """승인 워크플로우 통합 테스트"""

    def test_complete_approval_workflow_approved(
        self,
        sample_session_id: str,
        request_approval_use_case: RequestApprovalUseCase,
        get_pending_use_case: GetPendingApprovalsUseCase,
        process_approval_use_case: ProcessApprovalResponseUseCase,
        approval_history_use_case: ApprovalHistoryUseCase
    ):
        """전체 워크플로우: 승인 요청 → 대기 조회 → 승인 → 이력 조회"""

        # 1. 승인 요청 생성
        created_approval = request_approval_use_case.execute(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="새로운 기능 추가",
            context_data='{"file": "feature.py"}'
        )

        assert created_approval.id is not None
        assert created_approval.status == ApprovalStatus.PENDING

        # 2. 대기 중인 승인 조회
        pending_approvals = get_pending_use_case.execute(session_id=sample_session_id)

        assert len(pending_approvals) == 1
        assert pending_approvals[0].id == created_approval.id

        # 3. 승인 응답 처리 (승인 + 피드백)
        updated_approval, feedback = process_approval_use_case.execute(
            approval_id=created_approval.id,
            status=ApprovalStatus.APPROVED,
            feedback_content="잘 작성되었습니다."
        )

        assert updated_approval.status == ApprovalStatus.APPROVED
        assert updated_approval.responded_at is not None
        assert feedback is not None
        assert feedback.feedback_content == "잘 작성되었습니다."

        # 4. 대기 중인 승인 목록에서 제거되었는지 확인
        pending_after_approval = get_pending_use_case.execute(session_id=sample_session_id)

        assert len(pending_after_approval) == 0

        # 5. 승인 이력 조회
        history = approval_history_use_case.execute(session_id=sample_session_id)

        assert len(history) == 1
        approval, feedbacks = history[0]
        assert approval.status == ApprovalStatus.APPROVED
        assert len(feedbacks) == 1
        assert feedbacks[0].feedback_content == "잘 작성되었습니다."

    def test_complete_approval_workflow_rejected(
        self,
        sample_session_id: str,
        request_approval_use_case: RequestApprovalUseCase,
        process_approval_use_case: ProcessApprovalResponseUseCase,
        approval_history_use_case: ApprovalHistoryUseCase
    ):
        """전체 워크플로우: 승인 요청 → 거부 (피드백 없음)"""

        # 1. 승인 요청 생성
        created_approval = request_approval_use_case.execute(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_TEST_RUN,
            task_description="테스트 실행"
        )

        # 2. 승인 거부 (피드백 없음)
        updated_approval, feedback = process_approval_use_case.execute(
            approval_id=created_approval.id,
            status=ApprovalStatus.REJECTED
        )

        assert updated_approval.status == ApprovalStatus.REJECTED
        assert feedback is None

        # 3. 승인 이력 확인
        history = approval_history_use_case.execute(session_id=sample_session_id)

        assert len(history) == 1
        approval, feedbacks = history[0]
        assert approval.status == ApprovalStatus.REJECTED
        assert len(feedbacks) == 0

    def test_complete_approval_workflow_modified(
        self,
        sample_session_id: str,
        request_approval_use_case: RequestApprovalUseCase,
        process_approval_use_case: ProcessApprovalResponseUseCase,
        approval_history_use_case: ApprovalHistoryUseCase
    ):
        """전체 워크플로우: 승인 요청 → 수정 요청 (피드백 포함)"""

        # 1. 승인 요청 생성
        created_approval = request_approval_use_case.execute(
            session_id=sample_session_id,
            approval_type=ApprovalType.AFTER_CODE_WRITE,
            task_description="코드 리뷰"
        )

        # 2. 수정 요청
        updated_approval, feedback = process_approval_use_case.execute(
            approval_id=created_approval.id,
            status=ApprovalStatus.MODIFIED,
            feedback_content="변수명을 더 명확하게 변경해주세요."
        )

        assert updated_approval.status == ApprovalStatus.MODIFIED
        assert feedback is not None
        assert feedback.feedback_content == "변수명을 더 명확하게 변경해주세요."

        # 3. 승인 이력 확인
        history = approval_history_use_case.execute(session_id=sample_session_id)

        assert len(history) == 1
        approval, feedbacks = history[0]
        assert approval.status == ApprovalStatus.MODIFIED
        assert len(feedbacks) == 1

    def test_multiple_approvals_in_session(
        self,
        sample_session_id: str,
        request_approval_use_case: RequestApprovalUseCase,
        process_approval_use_case: ProcessApprovalResponseUseCase,
        get_pending_use_case: GetPendingApprovalsUseCase,
        approval_history_use_case: ApprovalHistoryUseCase
    ):
        """하나의 세션에 여러 승인 요청 처리"""

        # 1. 여러 승인 요청 생성
        approval1 = request_approval_use_case.execute(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="작업 1"
        )

        approval2 = request_approval_use_case.execute(
            session_id=sample_session_id,
            approval_type=ApprovalType.AFTER_CODE_WRITE,
            task_description="작업 2"
        )

        approval3 = request_approval_use_case.execute(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_DEPLOYMENT,
            task_description="작업 3"
        )

        # 2. 대기 중인 승인 3개 확인
        pending = get_pending_use_case.execute(session_id=sample_session_id)
        assert len(pending) == 3

        # 3. 첫 번째 승인
        process_approval_use_case.execute(
            approval_id=approval1.id,
            status=ApprovalStatus.APPROVED
        )

        # 4. 두 번째 거부
        process_approval_use_case.execute(
            approval_id=approval2.id,
            status=ApprovalStatus.REJECTED,
            feedback_content="다시 작성 필요"
        )

        # 5. 세 번째는 대기 중으로 유지

        # 6. 대기 중인 승인 1개만 남음
        pending_after = get_pending_use_case.execute(session_id=sample_session_id)
        assert len(pending_after) == 1
        assert pending_after[0].id == approval3.id

        # 7. 이력 확인 (3개 모두 포함)
        history = approval_history_use_case.execute(session_id=sample_session_id)
        assert len(history) == 3

        # 상태별 확인
        statuses = [approval.status for approval, _ in history]
        assert ApprovalStatus.APPROVED in statuses
        assert ApprovalStatus.REJECTED in statuses
        assert ApprovalStatus.PENDING in statuses


# ============================================================================
# 세션 연동 테스트
# ============================================================================

class TestSessionIntegration:
    """세션과의 연동 테스트"""

    def test_approval_requires_existing_session(
        self,
        request_approval_use_case: RequestApprovalUseCase
    ):
        """존재하지 않는 세션에 대한 승인 요청 실패"""

        with pytest.raises(ValueError, match="세션을 찾을 수 없습니다"):
            request_approval_use_case.execute(
                session_id="nonexistent-session-id",
                approval_type=ApprovalType.BEFORE_CODE_WRITE,
                task_description="테스트 작업"
            )

    def test_multiple_sessions_with_approvals(
        self,
        session_repository: SqliteSessionRepository,
        request_approval_use_case: RequestApprovalUseCase,
        get_pending_use_case: GetPendingApprovalsUseCase
    ):
        """여러 세션에 각각 승인 요청 생성"""

        # 세션 1 생성
        session_id_1 = "test-session-1"
        history1 = ConversationHistory(max_length=50)
        history1.add_message("user", "세션 1 작업")
        result1 = SessionResult(
            status=SessionStatus.COMPLETED,
            files_modified=[],
            tests_passed=False,
            error_message=None
        )
        session_repository.save(session_id_1, "세션 1 작업", history1, result1)

        # 세션 2 생성
        session_id_2 = "test-session-2"
        history2 = ConversationHistory(max_length=50)
        history2.add_message("user", "세션 2 작업")
        result2 = SessionResult(
            status=SessionStatus.COMPLETED,
            files_modified=[],
            tests_passed=False,
            error_message=None
        )
        session_repository.save(session_id_2, "세션 2 작업", history2, result2)

        # 각 세션에 승인 요청 생성
        request_approval_use_case.execute(
            session_id=session_id_1,
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="세션 1 작업"
        )

        request_approval_use_case.execute(
            session_id=session_id_2,
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="세션 2 작업"
        )

        # 세션별 대기 중인 승인 조회
        pending_session_1 = get_pending_use_case.execute(session_id=session_id_1)
        pending_session_2 = get_pending_use_case.execute(session_id=session_id_2)

        assert len(pending_session_1) == 1
        assert len(pending_session_2) == 1
        assert pending_session_1[0].session_id == session_id_1
        assert pending_session_2[0].session_id == session_id_2

        # 전체 대기 중인 승인 조회
        all_pending = get_pending_use_case.execute()
        assert len(all_pending) == 2


# ============================================================================
# 에러 처리 및 경계값 테스트
# ============================================================================

class TestErrorHandling:
    """에러 처리 및 경계값 테스트"""

    def test_cannot_process_already_processed_approval(
        self,
        sample_session_id: str,
        request_approval_use_case: RequestApprovalUseCase,
        process_approval_use_case: ProcessApprovalResponseUseCase
    ):
        """이미 처리된 승인 요청은 재처리 불가"""

        # 승인 요청 생성
        approval = request_approval_use_case.execute(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="테스트 작업"
        )

        # 첫 번째 응답 처리 (승인)
        process_approval_use_case.execute(
            approval_id=approval.id,
            status=ApprovalStatus.APPROVED
        )

        # 두 번째 응답 처리 시도 (실패해야 함)
        with pytest.raises(ValueError, match="이미 처리된 승인 요청입니다"):
            process_approval_use_case.execute(
                approval_id=approval.id,
                status=ApprovalStatus.REJECTED
            )

    def test_cannot_update_to_pending_status(
        self,
        sample_session_id: str,
        request_approval_use_case: RequestApprovalUseCase,
        process_approval_use_case: ProcessApprovalResponseUseCase
    ):
        """PENDING 상태로 업데이트 불가"""

        approval = request_approval_use_case.execute(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="테스트 작업"
        )

        with pytest.raises(ValueError, match="PENDING 상태로 업데이트할 수 없습니다"):
            process_approval_use_case.execute(
                approval_id=approval.id,
                status=ApprovalStatus.PENDING
            )

    def test_feedback_length_limit(
        self,
        sample_session_id: str,
        request_approval_use_case: RequestApprovalUseCase,
        process_approval_use_case: ProcessApprovalResponseUseCase
    ):
        """피드백 길이 제한 테스트"""

        approval = request_approval_use_case.execute(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="테스트 작업"
        )

        # 2001자 피드백 (기본 최대 2000자)
        long_feedback = "A" * 2001

        with pytest.raises(ValueError, match="피드백 내용이 너무 깁니다"):
            process_approval_use_case.execute(
                approval_id=approval.id,
                status=ApprovalStatus.MODIFIED,
                feedback_content=long_feedback
            )

    def test_sql_injection_prevention(
        self,
        request_approval_use_case: RequestApprovalUseCase
    ):
        """SQL Injection 방지 테스트"""

        dangerous_session_ids = [
            "session'; DROP TABLE approvals--",
            'session" OR "1"="1',
            "session; DELETE FROM approvals",
            "session/*comment*/"
        ]

        for dangerous_id in dangerous_session_ids:
            with pytest.raises(ValueError, match="허용되지 않는 문자"):
                request_approval_use_case.execute(
                    session_id=dangerous_id,
                    approval_type=ApprovalType.BEFORE_CODE_WRITE,
                    task_description="테스트 작업"
                )


# ============================================================================
# UTF-8 인코딩 테스트
# ============================================================================

class TestUTF8Encoding:
    """UTF-8 인코딩 테스트 (한글 데이터)"""

    def test_korean_approval_workflow(
        self,
        sample_session_id: str,
        request_approval_use_case: RequestApprovalUseCase,
        process_approval_use_case: ProcessApprovalResponseUseCase,
        approval_history_use_case: ApprovalHistoryUseCase
    ):
        """한글 데이터 전체 워크플로우"""

        # 1. 한글 승인 요청 생성
        approval = request_approval_use_case.execute(
            session_id=sample_session_id,
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="새로운 기능 추가하기 🚀",
            context_data='{"파일": "메인.py", "설명": "사용자 인증 기능"}'
        )

        assert "새로운 기능" in approval.task_description
        assert "🚀" in approval.task_description
        assert "파일" in approval.context_data

        # 2. 한글 피드백으로 승인 응답
        updated, feedback = process_approval_use_case.execute(
            approval_id=approval.id,
            status=ApprovalStatus.MODIFIED,
            feedback_content="변수명을 더 명확하게 변경해주세요. 예: user_auth → authenticate_user 👍"
        )

        assert feedback is not None
        assert "변수명" in feedback.feedback_content
        assert "👍" in feedback.feedback_content

        # 3. 승인 이력 조회
        history = approval_history_use_case.execute(session_id=sample_session_id)

        approval_record, feedbacks = history[0]
        assert "새로운 기능" in approval_record.task_description
        assert len(feedbacks) == 1
        assert "변수명" in feedbacks[0].feedback_content


# ============================================================================
# 성능 및 대량 데이터 테스트
# ============================================================================

class TestPerformance:
    """성능 및 대량 데이터 테스트"""

    def test_multiple_approvals_performance(
        self,
        sample_session_id: str,
        request_approval_use_case: RequestApprovalUseCase,
        get_pending_use_case: GetPendingApprovalsUseCase
    ):
        """여러 승인 요청 생성 및 조회 성능"""

        # 10개의 승인 요청 생성
        for i in range(10):
            request_approval_use_case.execute(
                session_id=sample_session_id,
                approval_type=ApprovalType.BEFORE_CODE_WRITE,
                task_description=f"작업 {i+1}"
            )

        # 대기 중인 승인 조회
        pending = get_pending_use_case.execute(session_id=sample_session_id)

        assert len(pending) == 10

        # 생성일시 오름차순 정렬 확인
        for i in range(len(pending) - 1):
            assert pending[i].created_at <= pending[i+1].created_at

    def test_approval_history_ordering(
        self,
        sample_session_id: str,
        request_approval_use_case: RequestApprovalUseCase,
        process_approval_use_case: ProcessApprovalResponseUseCase,
        approval_history_use_case: ApprovalHistoryUseCase
    ):
        """승인 이력 정렬 순서 테스트 (최신순)"""

        # 여러 승인 요청 생성 및 처리
        approvals = []
        for i in range(5):
            approval = request_approval_use_case.execute(
                session_id=sample_session_id,
                approval_type=ApprovalType.BEFORE_CODE_WRITE,
                task_description=f"작업 {i+1}"
            )
            approvals.append(approval)

            # 모두 승인 처리
            process_approval_use_case.execute(
                approval_id=approval.id,
                status=ApprovalStatus.APPROVED
            )

        # 승인 이력 조회 (생성일시 내림차순)
        history = approval_history_use_case.execute(session_id=sample_session_id)

        assert len(history) == 5

        # 최신 항목이 먼저 (내림차순)
        for i in range(len(history) - 1):
            approval1, _ = history[i]
            approval2, _ = history[i+1]
            assert approval1.created_at >= approval2.created_at
