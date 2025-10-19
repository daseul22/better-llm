"""
세션 Use Cases 단위 테스트

테스트 범위:
- SessionSearchUseCase 로직
- SessionReplayUseCase 로직
- SessionAnalyticsUseCase 로직
- 입력 검증
- 예외 처리
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
from src.application.use_cases.session_management import (
    SessionSearchUseCase,
    SessionReplayUseCase,
    SessionAnalyticsUseCase
)
from src.domain.models.session import (
    SessionMetadata,
    SessionSearchCriteria,
    SessionDetail
)


class TestSessionSearchUseCase:
    """SessionSearchUseCase 테스트"""

    @pytest.fixture
    def mock_repository(self):
        """Mock 세션 리포지토리"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_repository):
        """SessionSearchUseCase 인스턴스"""
        return SessionSearchUseCase(session_repository=mock_repository)

    def test_execute_success(self, use_case, mock_repository):
        """정상 검색 실행 테스트"""
        criteria = SessionSearchCriteria(keyword="login", limit=10)

        # Mock 리포지토리 응답 설정
        mock_sessions = [
            SessionMetadata(
                session_id="session-001",
                created_at=datetime.now(),
                completed_at=datetime.now(),
                user_request="Implement login",
                status="completed",
                total_turns=5
            )
        ]
        mock_repository.search_sessions.return_value = mock_sessions

        # 실행
        result = use_case.execute(criteria)

        # 검증
        assert len(result) == 1
        assert result[0].session_id == "session-001"
        mock_repository.search_sessions.assert_called_once_with(criteria)

    def test_execute_empty_result(self, use_case, mock_repository):
        """검색 결과가 없는 경우 테스트"""
        criteria = SessionSearchCriteria(keyword="nonexistent")

        mock_repository.search_sessions.return_value = []

        result = use_case.execute(criteria)

        assert len(result) == 0

    def test_validate_criteria_invalid_limit(self, use_case):
        """잘못된 limit 값 검증 테스트"""
        criteria = SessionSearchCriteria(limit=0)

        with pytest.raises(ValueError, match="limit은 양수여야 합니다"):
            use_case.execute(criteria)

    def test_validate_criteria_negative_limit(self, use_case):
        """음수 limit 값 검증 테스트"""
        criteria = SessionSearchCriteria(limit=-5)

        with pytest.raises(ValueError, match="limit은 양수여야 합니다"):
            use_case.execute(criteria)

    def test_validate_criteria_negative_offset(self, use_case):
        """음수 offset 값 검증 테스트"""
        criteria = SessionSearchCriteria(offset=-1)

        with pytest.raises(ValueError, match="offset은 0 이상이어야 합니다"):
            use_case.execute(criteria)

    def test_validate_criteria_invalid_date_from(self, use_case):
        """잘못된 date_from 형식 검증 테스트"""
        criteria = SessionSearchCriteria(date_from="2024/01/01")

        with pytest.raises(ValueError, match="date_from 형식 오류"):
            use_case.execute(criteria)

    def test_validate_criteria_invalid_date_to(self, use_case):
        """잘못된 date_to 형식 검증 테스트"""
        criteria = SessionSearchCriteria(date_to="01-01-2024")

        with pytest.raises(ValueError, match="date_to 형식 오류"):
            use_case.execute(criteria)

    def test_validate_criteria_valid_dates(self, use_case, mock_repository):
        """올바른 날짜 형식 검증 테스트"""
        criteria = SessionSearchCriteria(
            date_from="2024-01-01",
            date_to="2024-01-31"
        )

        mock_repository.search_sessions.return_value = []

        # 예외가 발생하지 않아야 함
        result = use_case.execute(criteria)
        assert result == []


class TestSessionReplayUseCase:
    """SessionReplayUseCase 테스트"""

    @pytest.fixture
    def mock_repository(self):
        """Mock 세션 리포지토리"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_repository):
        """SessionReplayUseCase 인스턴스"""
        return SessionReplayUseCase(session_repository=mock_repository)

    @pytest.fixture
    def sample_session_detail(self):
        """샘플 세션 상세 정보"""
        metadata = SessionMetadata(
            session_id="session-replay-001",
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            completed_at=datetime(2024, 1, 1, 10, 30, 0),
            user_request="Create user profile",
            status="completed",
            total_turns=3,
            agents_used=["planner", "coder"],
            files_modified=["profile.py"],
            tests_passed=True
        )

        messages = [
            {
                "role": "user",
                "content": "Create user profile",
                "timestamp": "2024-01-01T10:00:00"
            },
            {
                "role": "agent",
                "content": "Planning the task",
                "agent_name": "planner",
                "timestamp": "2024-01-01T10:05:00"
            },
            {
                "role": "agent",
                "content": "Code implemented",
                "agent_name": "coder",
                "timestamp": "2024-01-01T10:20:00"
            }
        ]

        return SessionDetail(metadata=metadata, messages=messages)

    def test_execute_success(self, use_case, mock_repository, sample_session_detail):
        """정상 세션 재생 테스트"""
        session_id = "session-replay-001"

        mock_repository.get_session_detail.return_value = sample_session_detail

        result = use_case.execute(session_id)

        assert result is not None
        assert result.metadata.session_id == session_id
        assert len(result.messages) == 3
        mock_repository.get_session_detail.assert_called_once_with(session_id)

    def test_execute_session_not_found(self, use_case, mock_repository):
        """존재하지 않는 세션 재생 테스트"""
        session_id = "nonexistent-session"

        mock_repository.get_session_detail.return_value = None

        result = use_case.execute(session_id)

        assert result is None

    def test_execute_empty_session_id(self, use_case):
        """빈 세션 ID 검증 테스트"""
        with pytest.raises(ValueError, match="세션 ID가 필요합니다"):
            use_case.execute("")

    def test_execute_whitespace_session_id(self, use_case):
        """공백 세션 ID 검증 테스트"""
        with pytest.raises(ValueError, match="세션 ID가 필요합니다"):
            use_case.execute("   ")

    def test_format_for_display(self, use_case, sample_session_detail):
        """세션 디스플레이 포맷 테스트"""
        formatted = use_case.format_for_display(sample_session_detail)

        assert "session-replay-001" in formatted
        assert "Create user profile" in formatted
        assert "completed" in formatted
        assert "planner" in formatted
        assert "coder" in formatted
        assert "profile.py" in formatted
        assert "[사용자]" in formatted
        assert "[planner]" in formatted
        assert "[coder]" in formatted

    def test_format_for_display_with_error(self, use_case):
        """에러가 있는 세션 디스플레이 포맷 테스트"""
        metadata = SessionMetadata(
            session_id="session-error-001",
            created_at=datetime(2024, 2, 1, 10, 0, 0),
            completed_at=datetime(2024, 2, 1, 10, 5, 0),
            user_request="Failed task",
            status="error",
            total_turns=1,
            error_message="Connection timeout"
        )

        detail = SessionDetail(
            metadata=metadata,
            messages=[{
                "role": "user",
                "content": "Failed task",
                "timestamp": "2024-02-01T10:00:00"
            }]
        )

        formatted = use_case.format_for_display(detail)

        assert "에러 메시지: Connection timeout" in formatted


class TestSessionAnalyticsUseCase:
    """SessionAnalyticsUseCase 테스트"""

    @pytest.fixture
    def mock_repository(self):
        """Mock 세션 리포지토리"""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_repository):
        """SessionAnalyticsUseCase 인스턴스"""
        return SessionAnalyticsUseCase(session_repository=mock_repository)

    @pytest.fixture
    def sample_sessions(self):
        """샘플 세션 메타데이터 목록"""
        return [
            SessionMetadata(
                session_id="session-001",
                created_at=datetime.now() - timedelta(days=1),
                completed_at=datetime.now() - timedelta(days=1),
                user_request="Task 1",
                status="completed",
                total_turns=5,
                agents_used=["planner", "coder"],
                files_modified=["file1.py", "file2.py"]
            ),
            SessionMetadata(
                session_id="session-002",
                created_at=datetime.now() - timedelta(days=2),
                completed_at=datetime.now() - timedelta(days=2),
                user_request="Task 2",
                status="completed",
                total_turns=3,
                agents_used=["coder"],
                files_modified=["file3.py"]
            ),
            SessionMetadata(
                session_id="session-003",
                created_at=datetime.now() - timedelta(days=3),
                completed_at=datetime.now() - timedelta(days=3),
                user_request="Task 3",
                status="error",
                total_turns=2,
                agents_used=["planner"],
                files_modified=[]
            )
        ]

    def test_get_summary_stats_success(self, use_case, mock_repository, sample_sessions):
        """요약 통계 조회 성공 테스트"""
        mock_repository.search_sessions.return_value = sample_sessions

        stats = use_case.get_summary_stats(days=30)

        assert stats["total_sessions"] == 3
        assert stats["status_distribution"]["completed"] == 2
        assert stats["status_distribution"]["error"] == 1
        assert "planner" in stats["agent_usage"]
        assert "coder" in stats["agent_usage"]
        assert stats["avg_turns"] > 0
        assert stats["success_rate"] > 0
        assert stats["total_files_modified"] == 3
        assert stats["period_days"] == 30

    def test_get_summary_stats_empty(self, use_case, mock_repository):
        """세션이 없는 경우 통계 조회 테스트"""
        mock_repository.search_sessions.return_value = []

        stats = use_case.get_summary_stats(days=30)

        assert stats["total_sessions"] == 0
        assert stats["status_distribution"] == {}
        assert stats["agent_usage"] == {}
        assert stats["avg_turns"] == 0
        assert stats["success_rate"] == 0
        assert stats["total_files_modified"] == 0

    def test_get_summary_stats_invalid_days(self, use_case):
        """잘못된 조회 기간 검증 테스트"""
        with pytest.raises(ValueError, match="조회 기간은 양수여야 합니다"):
            use_case.get_summary_stats(days=0)

        with pytest.raises(ValueError, match="조회 기간은 양수여야 합니다"):
            use_case.get_summary_stats(days=-5)

    def test_calculate_stats_success_rate(self, use_case, sample_sessions):
        """성공률 계산 테스트"""
        stats = use_case._calculate_stats(sample_sessions)

        # 3개 중 2개 완료 = 66.67%
        assert stats["success_rate"] == pytest.approx(66.67, rel=0.01)

    def test_calculate_stats_avg_turns(self, use_case, sample_sessions):
        """평균 턴 수 계산 테스트"""
        stats = use_case._calculate_stats(sample_sessions)

        # (5 + 3 + 2) / 3 = 3.33
        assert stats["avg_turns"] == pytest.approx(3.33, rel=0.01)

    def test_get_agent_performance_success(self, use_case, mock_repository, sample_sessions):
        """에이전트 성능 분석 성공 테스트"""
        # coder 에이전트를 사용한 세션만 필터링
        coder_sessions = [s for s in sample_sessions if "coder" in s.agents_used]
        mock_repository.search_sessions.return_value = coder_sessions

        performance = use_case.get_agent_performance("coder", days=30)

        assert performance["agent_name"] == "coder"
        assert performance["total_uses"] == 2
        assert performance["success_rate"] == 100.0  # 2개 모두 completed
        assert performance["period_days"] == 30

    def test_get_agent_performance_no_sessions(self, use_case, mock_repository):
        """에이전트 사용 기록이 없는 경우 테스트"""
        mock_repository.search_sessions.return_value = []

        performance = use_case.get_agent_performance("tester", days=30)

        assert performance["agent_name"] == "tester"
        assert performance["total_uses"] == 0
        assert performance["success_rate"] == 0
        assert performance["avg_turns"] == 0

    def test_get_agent_performance_invalid_name(self, use_case):
        """잘못된 에이전트 이름 검증 테스트"""
        with pytest.raises(ValueError, match="에이전트 이름이 필요합니다"):
            use_case.get_agent_performance("", days=30)

        with pytest.raises(ValueError, match="에이전트 이름이 필요합니다"):
            use_case.get_agent_performance("   ", days=30)

    def test_get_agent_performance_invalid_days(self, use_case):
        """잘못된 조회 기간 검증 테스트"""
        with pytest.raises(ValueError, match="조회 기간은 양수여야 합니다"):
            use_case.get_agent_performance("coder", days=0)

    def test_calculate_agent_performance_status_distribution(
        self,
        use_case,
        sample_sessions
    ):
        """에이전트 성능 - 상태 분포 계산 테스트"""
        planner_sessions = [s for s in sample_sessions if "planner" in s.agents_used]

        performance = use_case._calculate_agent_performance(
            planner_sessions,
            "planner"
        )

        # planner는 2개 세션: 1개 completed, 1개 error
        assert performance["status_distribution"]["completed"] == 1
        assert performance["status_distribution"]["error"] == 1
        assert performance["success_rate"] == 50.0
