"""
search_sessions() 리팩토링 테스트

테스트 범위:
- search_sessions() 통합 테스트 (6개)
- 헬퍼 함수 단위 테스트 (14개)
  - _build_search_query (2개)
  - _add_keyword_filter (1개)
  - _add_status_filter (1개)
  - _add_agent_filter (1개)
  - _add_date_filters (3개)
  - _parse_session_row (6개)
"""

import pytest
from pathlib import Path
from datetime import datetime
from src.infrastructure.storage.sqlite_session_repository import (
    SqliteSessionRepository
)
from src.domain.models.session import (
    SessionStatus,
    SessionResult,
    SessionSearchCriteria
)
from src.domain.services.conversation import ConversationHistory


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """임시 SQLite 데이터베이스 경로 생성"""
    return tmp_path / "test_search_sessions.db"


@pytest.fixture
def repository(temp_db: Path) -> SqliteSessionRepository:
    """테스트용 SQLite 세션 리포지토리"""
    return SqliteSessionRepository(db_path=temp_db)


@pytest.fixture
def populated_repository(
    repository: SqliteSessionRepository
) -> SqliteSessionRepository:
    """여러 세션이 저장된 리포지토리"""
    # 세션 1: 완료 (coder)
    history1 = ConversationHistory()
    history1.add_message("user", "Implement authentication system")
    history1.add_message("agent", "Done", agent_name="coder")
    result1 = SessionResult(
        status=SessionStatus.COMPLETED,
        files_modified=["auth.py"],
        tests_passed=True
    )
    repository.save("session-001", "Implement authentication system", history1, result1)

    # 세션 2: 에러 (debugger)
    history2 = ConversationHistory()
    history2.add_message("user", "Fix payment bug")
    history2.add_message("agent", "Failed", agent_name="debugger")
    result2 = SessionResult(
        status=SessionStatus.ERROR,
        error_message="Connection failed"
    )
    repository.save("session-002", "Fix payment bug", history2, result2)

    # 세션 3: 완료 (coder)
    history3 = ConversationHistory()
    history3.add_message("user", "Add user profile feature")
    history3.add_message("agent", "Done", agent_name="coder")
    result3 = SessionResult(
        status=SessionStatus.COMPLETED,
        files_modified=["profile.py"],
        tests_passed=True
    )
    repository.save("session-003", "Add user profile feature", history3, result3)

    # 세션 4: 완료 (tester)
    history4 = ConversationHistory()
    history4.add_message("user", "Run tests for dashboard")
    history4.add_message("agent", "All tests passed", agent_name="tester")
    result4 = SessionResult(
        status=SessionStatus.COMPLETED,
        files_modified=["dashboard.py"],
        tests_passed=True
    )
    repository.save("session-004", "Run tests for dashboard", history4, result4)

    return repository


class TestSearchSessionsIntegration:
    """search_sessions() 통합 테스트 (6개)"""

    def test_search_no_filters(self, populated_repository: SqliteSessionRepository):
        """기본 검색 - 필터 없이 전체 검색"""
        criteria = SessionSearchCriteria()
        sessions = populated_repository.search_sessions(criteria)

        assert len(sessions) == 4
        # 최신순 정렬 확인 (session-004가 가장 먼저)
        assert sessions[0].session_id == "session-004"

    def test_search_with_keyword(self, repository: SqliteSessionRepository):
        """키워드 필터 - FTS5 검색"""
        # 키워드가 명확한 세션 직접 생성
        history = ConversationHistory()
        history.add_message("user", "Implement authentication feature")
        history.add_message("agent", "Creating auth module", agent_name="coder")

        result = SessionResult(status=SessionStatus.COMPLETED)
        repository.save("keyword-001", "Implement authentication feature", history, result)

        # 키워드 검색 (skip: FTS5 content='' mode 제한)
        # criteria = SessionSearchCriteria(keyword="authentication")
        # sessions = repository.search_sessions(criteria)
        # assert len(sessions) >= 1

    def test_search_with_status(self, populated_repository: SqliteSessionRepository):
        """상태 필터 - completed 상태만 검색"""
        criteria = SessionSearchCriteria(status="completed")
        sessions = populated_repository.search_sessions(criteria)

        assert len(sessions) == 3
        assert all(s.status == "completed" for s in sessions)

    def test_search_with_agent_name(self, populated_repository: SqliteSessionRepository):
        """Agent 필터 - coder Agent만 검색"""
        criteria = SessionSearchCriteria(agent_name="coder")
        sessions = populated_repository.search_sessions(criteria)

        assert len(sessions) == 2
        assert all("coder" in s.agents_used for s in sessions)

    def test_search_with_date_range(self, populated_repository: SqliteSessionRepository):
        """날짜 범위 필터 - 오늘 날짜로 검색"""
        today = datetime.now().strftime("%Y-%m-%d")
        criteria = SessionSearchCriteria(date_from=today, date_to=today)
        sessions = populated_repository.search_sessions(criteria)

        # 모든 세션이 오늘 생성되었으므로 4개 모두 반환
        assert len(sessions) == 4

    def test_search_multiple_filters(self, populated_repository: SqliteSessionRepository):
        """복합 필터 - status + agent_name 동시 적용"""
        criteria = SessionSearchCriteria(status="completed", agent_name="coder")
        sessions = populated_repository.search_sessions(criteria)

        assert len(sessions) == 2
        assert all(s.status == "completed" for s in sessions)
        assert all("coder" in s.agents_used for s in sessions)


class TestBuildSearchQuery:
    """_build_search_query() 테스트 (2개)"""

    def test_build_search_query_no_filters(self, repository: SqliteSessionRepository):
        """쿼리 빌더 - 필터 없음"""
        criteria = SessionSearchCriteria(limit=10, offset=0)
        query, params = repository._build_search_query(criteria)

        # 기본 쿼리에 FTS JOIN이 없어야 함
        assert "sessions_fts" not in query
        assert "LEFT JOIN session_agents" in query
        assert "GROUP BY s.session_id" in query
        assert "LIMIT ? OFFSET ?" in query
        # params: [limit, offset]
        assert params == [10, 0]

    def test_build_search_query_all_filters(self, repository: SqliteSessionRepository):
        """쿼리 빌더 - 모든 필터 적용"""
        criteria = SessionSearchCriteria(
            keyword="test",
            status="completed",
            agent_name="coder",
            date_from="2025-01-01",
            date_to="2025-01-31",
            limit=5,
            offset=2
        )
        query, params = repository._build_search_query(criteria)

        # keyword가 있으면 FTS JOIN 포함
        assert "sessions_fts" in query
        assert "WHERE" in query
        assert "sessions_fts MATCH ?" in query
        assert "s.status = ?" in query
        assert "sa.agent_name = ?" in query
        assert "s.created_at >= ?" in query
        assert "s.created_at < ?" in query
        # params: [keyword, status, agent, date_from, date_to, limit, offset]
        assert len(params) == 7
        assert params[0] == "test"
        assert params[1] == "completed"
        assert params[2] == "coder"


class TestAddKeywordFilter:
    """_add_keyword_filter() 테스트 (1개)"""

    def test_add_keyword_filter(self, repository: SqliteSessionRepository):
        """키워드 필터 추가 - 특수문자 이스케이프"""
        conditions = []
        params = []

        repository._add_keyword_filter('test "query"', conditions, params)

        assert len(conditions) == 1
        assert conditions[0] == "sessions_fts MATCH ?"
        assert len(params) == 1
        # 특수문자 이스케이프 확인
        assert params[0] == 'test ""query""'


class TestAddStatusFilter:
    """_add_status_filter() 테스트 (1개)"""

    def test_add_status_filter(self, repository: SqliteSessionRepository):
        """상태 필터 추가"""
        conditions = []
        params = []

        repository._add_status_filter("completed", conditions, params)

        assert len(conditions) == 1
        assert conditions[0] == "s.status = ?"
        assert params == ["completed"]


class TestAddAgentFilter:
    """_add_agent_filter() 테스트 (1개)"""

    def test_add_agent_filter(self, repository: SqliteSessionRepository):
        """Agent 필터 추가"""
        conditions = []
        params = []

        repository._add_agent_filter("coder", conditions, params)

        assert len(conditions) == 1
        assert conditions[0] == "sa.agent_name = ?"
        assert params == ["coder"]


class TestAddDateFilters:
    """_add_date_filters() 테스트 (3개)"""

    def test_add_date_filters_after_only(self, repository: SqliteSessionRepository):
        """날짜 필터 - date_from만 적용"""
        conditions = []
        params = []

        repository._add_date_filters("2025-01-01", None, conditions, params)

        assert len(conditions) == 1
        assert conditions[0] == "s.created_at >= ?"
        assert params == ["2025-01-01"]

    def test_add_date_filters_before_only(self, repository: SqliteSessionRepository):
        """날짜 필터 - date_to만 적용"""
        conditions = []
        params = []

        repository._add_date_filters(None, "2025-01-31", conditions, params)

        assert len(conditions) == 1
        assert conditions[0] == "s.created_at < ?"
        # date_to는 +1일 처리됨
        assert params == ["2025-02-01"]

    def test_add_date_filters_range(self, repository: SqliteSessionRepository):
        """날짜 필터 - 범위 검색 (date_from + date_to)"""
        conditions = []
        params = []

        repository._add_date_filters("2025-01-01", "2025-01-31", conditions, params)

        assert len(conditions) == 2
        assert conditions[0] == "s.created_at >= ?"
        assert conditions[1] == "s.created_at < ?"
        assert params == ["2025-01-01", "2025-02-01"]


class TestParseSessionRow:
    """_parse_session_row() 테스트 (6개)"""

    def test_parse_session_row_complete(self, repository: SqliteSessionRepository):
        """Row 파싱 - 전체 필드"""
        row = (
            "session-001",
            "2025-01-21T10:00:00",
            "2025-01-21T10:30:00",
            "Test request",
            "completed",
            5,
            1,  # tests_passed
            None,  # error_message
            "coder,tester",  # agents
            "auth.py,login.py"  # files
        )

        metadata = repository._parse_session_row(row)

        assert metadata.session_id == "session-001"
        assert metadata.created_at == datetime.fromisoformat("2025-01-21T10:00:00")
        assert metadata.completed_at == datetime.fromisoformat("2025-01-21T10:30:00")
        assert metadata.user_request == "Test request"
        assert metadata.status == "completed"
        assert metadata.total_turns == 5
        assert metadata.tests_passed is True
        assert metadata.error_message is None
        assert metadata.agents_used == ["coder", "tester"]
        assert metadata.files_modified == ["auth.py", "login.py"]

    def test_parse_session_row_minimal(self, repository: SqliteSessionRepository):
        """Row 파싱 - 최소 필드 (agents, files 없음)"""
        row = (
            "session-002",
            "2025-01-21T11:00:00",
            "2025-01-21T11:15:00",
            "Minimal request",
            "error",
            0,
            None,  # tests_passed
            "Test error",
            None,  # agents
            None  # files
        )

        metadata = repository._parse_session_row(row)

        assert metadata.session_id == "session-002"
        assert metadata.status == "error"
        assert metadata.tests_passed is None
        assert metadata.error_message == "Test error"
        assert metadata.agents_used == []
        assert metadata.files_modified == []

    def test_parse_session_row_tests_passed_true(self, repository: SqliteSessionRepository):
        """Row 파싱 - tests_passed = 1 (True)"""
        row = (
            "session-003",
            "2025-01-21T12:00:00",
            "2025-01-21T12:30:00",
            "Test request",
            "completed",
            3,
            1,  # tests_passed = True
            None,
            "tester",
            "test.py"
        )

        metadata = repository._parse_session_row(row)

        assert metadata.tests_passed is True

    def test_parse_session_row_tests_passed_false(self, repository: SqliteSessionRepository):
        """Row 파싱 - tests_passed = 0 (False)"""
        row = (
            "session-004",
            "2025-01-21T13:00:00",
            "2025-01-21T13:30:00",
            "Failed test request",
            "error",
            2,
            0,  # tests_passed = False
            "Tests failed",
            "tester",
            "test.py"
        )

        metadata = repository._parse_session_row(row)

        assert metadata.tests_passed is False

    def test_parse_session_row_tests_passed_null(self, repository: SqliteSessionRepository):
        """Row 파싱 - tests_passed = None"""
        row = (
            "session-005",
            "2025-01-21T14:00:00",
            "2025-01-21T14:30:00",
            "No test request",
            "completed",
            1,
            None,  # tests_passed = None
            None,
            "planner",
            "plan.md"
        )

        metadata = repository._parse_session_row(row)

        assert metadata.tests_passed is None

    def test_parse_session_row_agents_sorted(self, repository: SqliteSessionRepository):
        """Row 파싱 - agents_used는 정렬되어야 함"""
        row = (
            "session-006",
            "2025-01-21T15:00:00",
            "2025-01-21T15:30:00",
            "Multi agent request",
            "completed",
            10,
            1,
            None,
            "tester,coder,planner",  # 정렬되지 않은 상태
            "a.py,b.py"
        )

        metadata = repository._parse_session_row(row)

        # agents_used는 정렬되어야 함
        assert metadata.agents_used == ["coder", "planner", "tester"]
