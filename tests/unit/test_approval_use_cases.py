"""
승인 관리 Use Cases 단위 테스트

RequestApprovalUseCase, ProcessApprovalResponseUseCase,
GetPendingApprovalsUseCase, ApprovalHistoryUseCase 테스트
- SQL Injection 입력 검증 테스트 (중요!)
- 경계값 테스트 (빈 문자열, None, 특수 문자)
- 비즈니스 로직 검증
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.application.use_cases.approval_management import (
    RequestApprovalUseCase,
    ProcessApprovalResponseUseCase,
    GetPendingApprovalsUseCase,
    ApprovalHistoryUseCase,
    _validate_session_id
)
from src.domain.models.approval import (
    ApprovalRequest, ApprovalResponse, ApprovalStatus, ApprovalType
)
from src.domain.models.feedback import Feedback


# ============================================================================
# _validate_session_id 함수 테스트 (SQL Injection 방지)
# ============================================================================

class TestValidateSessionId:
    """세션 ID 검증 함수 테스트 (SQL Injection 방지)"""

    def test_valid_session_id(self):
        """유효한 세션 ID는 통과"""
        valid_ids = [
            "session-123",
            "abc_def_456",
            "SESSION-ABC-DEF-123",
            "s" * 100  # 긴 문자열
        ]

        for session_id in valid_ids:
            _validate_session_id(session_id)  # 예외 발생 안 함

    def test_empty_session_id(self):
        """빈 세션 ID는 거부"""
        with pytest.raises(ValueError, match="세션 ID는 공백일 수 없습니다"):
            _validate_session_id("")

    def test_whitespace_only_session_id(self):
        """공백만 포함된 세션 ID는 거부"""
        with pytest.raises(ValueError, match="세션 ID는 공백일 수 없습니다"):
            _validate_session_id("   ")

    def test_sql_injection_single_quote(self):
        """SQL Injection: 싱글 쿼트 포함 시 거부"""
        with pytest.raises(ValueError, match="허용되지 않는 문자"):
            _validate_session_id("session' OR '1'='1")

    def test_sql_injection_double_quote(self):
        """SQL Injection: 더블 쿼트 포함 시 거부"""
        with pytest.raises(ValueError, match="허용되지 않는 문자"):
            _validate_session_id('session" OR "1"="1')

    def test_sql_injection_semicolon(self):
        """SQL Injection: 세미콜론 포함 시 거부"""
        with pytest.raises(ValueError, match="허용되지 않는 문자"):
            _validate_session_id("session-123; DROP TABLE sessions")

    def test_sql_injection_comment(self):
        """SQL Injection: SQL 주석 포함 시 거부"""
        with pytest.raises(ValueError, match="허용되지 않는 문자"):
            _validate_session_id("session-123--")

        with pytest.raises(ValueError, match="허용되지 않는 문자"):
            _validate_session_id("session-123/*comment*/")

    def test_sql_injection_backslash(self):
        """SQL Injection: 백슬래시 포함 시 거부"""
        with pytest.raises(ValueError, match="허용되지 않는 문자"):
            _validate_session_id("session-123\\")


# ============================================================================
# RequestApprovalUseCase 테스트
# ============================================================================

class TestRequestApprovalUseCase:
    """승인 요청 생성 Use Case 테스트"""

    @pytest.fixture
    def mock_approval_repository(self):
        """Mock 승인 리포지토리"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_approval_repository):
        """RequestApprovalUseCase 인스턴스"""
        return RequestApprovalUseCase(mock_approval_repository)

    def test_execute_success(self, use_case, mock_approval_repository):
        """승인 요청 생성 성공"""
        # Mock 설정
        expected_request = ApprovalRequest(
            id=1,
            session_id="session-123",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="새로운 기능 추가",
            context_data='{"file": "main.py"}',
            status=ApprovalStatus.PENDING,
            created_at=datetime(2025, 10, 19, 10, 0, 0)
        )
        mock_approval_repository.create_approval_request.return_value = expected_request

        # 실행
        result = use_case.execute(
            session_id="session-123",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="새로운 기능 추가",
            context_data='{"file": "main.py"}'
        )

        # 검증
        assert result == expected_request
        mock_approval_repository.create_approval_request.assert_called_once()

        # 전달된 인자 검증
        call_args = mock_approval_repository.create_approval_request.call_args[0][0]
        assert call_args.session_id == "session-123"
        assert call_args.approval_type == ApprovalType.BEFORE_CODE_WRITE
        assert call_args.task_description == "새로운 기능 추가"
        assert call_args.context_data == '{"file": "main.py"}'
        assert call_args.status == ApprovalStatus.PENDING

    def test_execute_without_context_data(self, use_case, mock_approval_repository):
        """context_data 없이 승인 요청 생성"""
        expected_request = ApprovalRequest(
            id=2,
            session_id="session-456",
            approval_type=ApprovalType.AFTER_CODE_WRITE,
            task_description="코드 리뷰",
            context_data=None,
            status=ApprovalStatus.PENDING,
            created_at=datetime.now()
        )
        mock_approval_repository.create_approval_request.return_value = expected_request

        result = use_case.execute(
            session_id="session-456",
            approval_type=ApprovalType.AFTER_CODE_WRITE,
            task_description="코드 리뷰"
        )

        assert result == expected_request

    def test_execute_empty_session_id(self, use_case):
        """빈 세션 ID로 요청 시 ValueError"""
        with pytest.raises(ValueError, match="세션 ID는 공백일 수 없습니다"):
            use_case.execute(
                session_id="",
                approval_type=ApprovalType.BEFORE_CODE_WRITE,
                task_description="테스트"
            )

    def test_execute_sql_injection_session_id(self, use_case):
        """SQL Injection 시도 시 ValueError"""
        with pytest.raises(ValueError, match="허용되지 않는 문자"):
            use_case.execute(
                session_id="session'; DROP TABLE approvals--",
                approval_type=ApprovalType.BEFORE_CODE_WRITE,
                task_description="테스트"
            )

    def test_execute_empty_task_description(self, use_case):
        """빈 작업 설명으로 요청 시 ValueError"""
        with pytest.raises(ValueError, match="작업 설명은 필수입니다"):
            use_case.execute(
                session_id="session-789",
                approval_type=ApprovalType.BEFORE_TEST_RUN,
                task_description=""
            )

    def test_execute_whitespace_task_description(self, use_case):
        """공백만 포함된 작업 설명으로 요청 시 ValueError"""
        with pytest.raises(ValueError, match="작업 설명은 필수입니다"):
            use_case.execute(
                session_id="session-789",
                approval_type=ApprovalType.BEFORE_TEST_RUN,
                task_description="   "
            )

    def test_execute_repository_raises_value_error(self, use_case, mock_approval_repository):
        """리포지토리에서 ValueError 발생 시 전파"""
        mock_approval_repository.create_approval_request.side_effect = ValueError(
            "세션을 찾을 수 없습니다"
        )

        with pytest.raises(ValueError, match="세션을 찾을 수 없습니다"):
            use_case.execute(
                session_id="nonexistent-session",
                approval_type=ApprovalType.BEFORE_CODE_WRITE,
                task_description="테스트"
            )


# ============================================================================
# ProcessApprovalResponseUseCase 테스트
# ============================================================================

class TestProcessApprovalResponseUseCase:
    """승인 응답 처리 Use Case 테스트"""

    @pytest.fixture
    def mock_approval_repository(self):
        """Mock 승인 리포지토리"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_approval_repository):
        """ProcessApprovalResponseUseCase 인스턴스"""
        return ProcessApprovalResponseUseCase(mock_approval_repository)

    @pytest.fixture
    def pending_request(self):
        """대기 중인 승인 요청"""
        return ApprovalRequest(
            id=1,
            session_id="session-123",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="새로운 기능 추가",
            status=ApprovalStatus.PENDING,
            created_at=datetime(2025, 10, 19, 10, 0, 0)
        )

    def test_execute_approved_with_feedback(
        self, use_case, mock_approval_repository, pending_request
    ):
        """승인 + 피드백 처리 성공"""
        # Mock 설정
        mock_approval_repository.get_approval_by_id.return_value = pending_request

        updated_request = ApprovalRequest(
            id=1,
            session_id="session-123",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="새로운 기능 추가",
            status=ApprovalStatus.APPROVED,
            created_at=datetime(2025, 10, 19, 10, 0, 0),
            responded_at=datetime(2025, 10, 19, 10, 30, 0)
        )
        mock_approval_repository.update_approval_status.return_value = updated_request

        created_feedback = Feedback(
            id=1,
            approval_id=1,
            session_id="session-123",
            feedback_content="잘 작성되었습니다.",
            created_at=datetime(2025, 10, 19, 10, 30, 0)
        )
        mock_approval_repository.create_feedback.return_value = created_feedback

        # 실행
        result_request, result_feedback = use_case.execute(
            approval_id=1,
            status=ApprovalStatus.APPROVED,
            feedback_content="잘 작성되었습니다."
        )

        # 검증
        assert result_request.status == ApprovalStatus.APPROVED
        assert result_feedback is not None
        assert result_feedback.feedback_content == "잘 작성되었습니다."

        mock_approval_repository.update_approval_status.assert_called_once()
        mock_approval_repository.create_feedback.assert_called_once()

    def test_execute_rejected_without_feedback(
        self, use_case, mock_approval_repository, pending_request
    ):
        """거부 (피드백 없음) 처리 성공"""
        mock_approval_repository.get_approval_by_id.return_value = pending_request

        updated_request = ApprovalRequest(
            id=1,
            session_id="session-123",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="새로운 기능 추가",
            status=ApprovalStatus.REJECTED,
            created_at=datetime(2025, 10, 19, 10, 0, 0),
            responded_at=datetime(2025, 10, 19, 10, 30, 0)
        )
        mock_approval_repository.update_approval_status.return_value = updated_request

        result_request, result_feedback = use_case.execute(
            approval_id=1,
            status=ApprovalStatus.REJECTED
        )

        assert result_request.status == ApprovalStatus.REJECTED
        assert result_feedback is None

        mock_approval_repository.update_approval_status.assert_called_once()
        mock_approval_repository.create_feedback.assert_not_called()

    def test_execute_nonexistent_approval(self, use_case, mock_approval_repository):
        """존재하지 않는 승인 요청에 대한 응답 시도 시 ValueError"""
        mock_approval_repository.get_approval_by_id.return_value = None

        with pytest.raises(ValueError, match="승인 요청을 찾을 수 없습니다"):
            use_case.execute(
                approval_id=999,
                status=ApprovalStatus.APPROVED
            )

    def test_execute_already_processed_approval(
        self, use_case, mock_approval_repository
    ):
        """이미 처리된 승인 요청에 대한 응답 시도 시 ValueError"""
        already_approved = ApprovalRequest(
            id=2,
            session_id="session-456",
            approval_type=ApprovalType.BEFORE_TEST_RUN,
            task_description="테스트 실행",
            status=ApprovalStatus.APPROVED,  # 이미 승인됨
            created_at=datetime(2025, 10, 19, 9, 0, 0),
            responded_at=datetime(2025, 10, 19, 9, 30, 0)
        )
        mock_approval_repository.get_approval_by_id.return_value = already_approved

        with pytest.raises(ValueError, match="이미 처리된 승인 요청입니다"):
            use_case.execute(
                approval_id=2,
                status=ApprovalStatus.REJECTED
            )

    def test_execute_pending_status_not_allowed(
        self, use_case, mock_approval_repository, pending_request
    ):
        """PENDING 상태로 업데이트 시도 시 ValueError"""
        mock_approval_repository.get_approval_by_id.return_value = pending_request

        with pytest.raises(ValueError, match="PENDING 상태로 업데이트할 수 없습니다"):
            use_case.execute(
                approval_id=1,
                status=ApprovalStatus.PENDING
            )

    def test_execute_feedback_too_long(
        self, use_case, mock_approval_repository, pending_request
    ):
        """피드백 길이 초과 시 ValueError"""
        mock_approval_repository.get_approval_by_id.return_value = pending_request

        long_feedback = "A" * 2001  # 기본 max_feedback_length: 2000

        with pytest.raises(ValueError, match="피드백 내용이 너무 깁니다"):
            use_case.execute(
                approval_id=1,
                status=ApprovalStatus.MODIFIED,
                feedback_content=long_feedback
            )

    def test_execute_custom_max_feedback_length(
        self, use_case, mock_approval_repository, pending_request
    ):
        """커스텀 최대 피드백 길이 설정"""
        mock_approval_repository.get_approval_by_id.return_value = pending_request

        feedback_500_chars = "B" * 500

        # 500자 제한 설정 - 성공해야 함
        use_case.execute(
            approval_id=1,
            status=ApprovalStatus.MODIFIED,
            feedback_content=feedback_500_chars,
            max_feedback_length=500
        )

        # 501자 - 실패해야 함
        with pytest.raises(ValueError, match="피드백 내용이 너무 깁니다"):
            use_case.execute(
                approval_id=1,
                status=ApprovalStatus.MODIFIED,
                feedback_content=feedback_500_chars + "X",
                max_feedback_length=500
            )

    def test_execute_empty_feedback_not_created(
        self, use_case, mock_approval_repository, pending_request
    ):
        """빈 피드백 문자열은 피드백 생성하지 않음"""
        mock_approval_repository.get_approval_by_id.return_value = pending_request

        updated_request = ApprovalRequest(
            id=1,
            session_id="session-123",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="새로운 기능 추가",
            status=ApprovalStatus.MODIFIED,
            created_at=datetime(2025, 10, 19, 10, 0, 0),
            responded_at=datetime(2025, 10, 19, 10, 30, 0)
        )
        mock_approval_repository.update_approval_status.return_value = updated_request

        result_request, result_feedback = use_case.execute(
            approval_id=1,
            status=ApprovalStatus.MODIFIED,
            feedback_content=""  # 빈 문자열
        )

        assert result_feedback is None
        mock_approval_repository.create_feedback.assert_not_called()


# ============================================================================
# GetPendingApprovalsUseCase 테스트
# ============================================================================

class TestGetPendingApprovalsUseCase:
    """대기 중인 승인 목록 조회 Use Case 테스트"""

    @pytest.fixture
    def mock_approval_repository(self):
        """Mock 승인 리포지토리"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_approval_repository):
        """GetPendingApprovalsUseCase 인스턴스"""
        return GetPendingApprovalsUseCase(mock_approval_repository)

    def test_execute_all_pending_approvals(self, use_case, mock_approval_repository):
        """전체 대기 중인 승인 목록 조회"""
        pending_approvals = [
            ApprovalRequest(
                id=1,
                session_id="session-123",
                approval_type=ApprovalType.BEFORE_CODE_WRITE,
                task_description="작업 1",
                status=ApprovalStatus.PENDING,
                created_at=datetime(2025, 10, 19, 10, 0, 0)
            ),
            ApprovalRequest(
                id=2,
                session_id="session-456",
                approval_type=ApprovalType.AFTER_CODE_WRITE,
                task_description="작업 2",
                status=ApprovalStatus.PENDING,
                created_at=datetime(2025, 10, 19, 11, 0, 0)
            )
        ]
        mock_approval_repository.get_pending_approvals.return_value = pending_approvals

        result = use_case.execute()

        assert len(result) == 2
        assert result == pending_approvals
        mock_approval_repository.get_pending_approvals.assert_called_once_with(None)

    def test_execute_pending_approvals_by_session(
        self, use_case, mock_approval_repository
    ):
        """특정 세션의 대기 중인 승인 목록 조회"""
        session_approvals = [
            ApprovalRequest(
                id=3,
                session_id="session-789",
                approval_type=ApprovalType.BEFORE_TEST_RUN,
                task_description="테스트 실행",
                status=ApprovalStatus.PENDING,
                created_at=datetime(2025, 10, 19, 12, 0, 0)
            )
        ]
        mock_approval_repository.get_pending_approvals.return_value = session_approvals

        result = use_case.execute(session_id="session-789")

        assert len(result) == 1
        assert result[0].session_id == "session-789"
        mock_approval_repository.get_pending_approvals.assert_called_once_with("session-789")

    def test_execute_no_pending_approvals(self, use_case, mock_approval_repository):
        """대기 중인 승인이 없는 경우"""
        mock_approval_repository.get_pending_approvals.return_value = []

        result = use_case.execute()

        assert result == []

    def test_execute_invalid_session_id(self, use_case):
        """유효하지 않은 세션 ID로 조회 시 ValueError"""
        with pytest.raises(ValueError, match="허용되지 않는 문자"):
            use_case.execute(session_id="session'; DROP TABLE approvals--")


# ============================================================================
# ApprovalHistoryUseCase 테스트
# ============================================================================

class TestApprovalHistoryUseCase:
    """승인 이력 조회 Use Case 테스트"""

    @pytest.fixture
    def mock_approval_repository(self):
        """Mock 승인 리포지토리"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_approval_repository):
        """ApprovalHistoryUseCase 인스턴스"""
        return ApprovalHistoryUseCase(mock_approval_repository)

    def test_execute_success(self, use_case, mock_approval_repository):
        """승인 이력 조회 성공"""
        approvals = [
            ApprovalRequest(
                id=1,
                session_id="session-abc",
                approval_type=ApprovalType.BEFORE_CODE_WRITE,
                task_description="작업 1",
                status=ApprovalStatus.APPROVED,
                created_at=datetime(2025, 10, 19, 10, 0, 0),
                responded_at=datetime(2025, 10, 19, 10, 30, 0)
            ),
            ApprovalRequest(
                id=2,
                session_id="session-abc",
                approval_type=ApprovalType.AFTER_CODE_WRITE,
                task_description="작업 2",
                status=ApprovalStatus.REJECTED,
                created_at=datetime(2025, 10, 19, 11, 0, 0),
                responded_at=datetime(2025, 10, 19, 11, 15, 0)
            )
        ]

        feedbacks_1 = [
            Feedback(
                id=1,
                approval_id=1,
                session_id="session-abc",
                feedback_content="좋습니다.",
                created_at=datetime(2025, 10, 19, 10, 30, 0)
            )
        ]

        feedbacks_2 = []

        mock_approval_repository.get_approval_history.return_value = approvals
        mock_approval_repository.get_feedbacks_by_approval.side_effect = [
            feedbacks_1,
            feedbacks_2
        ]

        result = use_case.execute(session_id="session-abc")

        assert len(result) == 2
        assert result[0] == (approvals[0], feedbacks_1)
        assert result[1] == (approvals[1], feedbacks_2)

        mock_approval_repository.get_approval_history.assert_called_once_with("session-abc")
        assert mock_approval_repository.get_feedbacks_by_approval.call_count == 2

    def test_execute_empty_history(self, use_case, mock_approval_repository):
        """승인 이력이 없는 경우"""
        mock_approval_repository.get_approval_history.return_value = []

        result = use_case.execute(session_id="session-empty")

        assert result == []

    def test_execute_invalid_session_id(self, use_case):
        """유효하지 않은 세션 ID로 조회 시 ValueError"""
        with pytest.raises(ValueError, match="허용되지 않는 문자"):
            use_case.execute(session_id="session\"; DELETE FROM approvals")

    def test_execute_sql_injection_prevention(self, use_case):
        """SQL Injection 방지 테스트"""
        dangerous_ids = [
            "session' OR '1'='1",
            "session--",
            "session/**/",
            "session\\x00"
        ]

        for dangerous_id in dangerous_ids:
            with pytest.raises(ValueError, match="허용되지 않는 문자|공백일 수 없습니다"):
                use_case.execute(session_id=dangerous_id)
