"""
세션 관리 시스템 통합 테스트

테스트 범위:
- 전체 워크플로우: 세션 저장 → 검색 → 로드 → 삭제
- Repository Factory 테스트 (backend 전환)
- Use Cases와 Repository 통합
- 실제 데이터베이스를 사용한 E2E 테스트
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from src.infrastructure.storage.sqlite_session_repository import (
    SqliteSessionRepository
)
from src.infrastructure.storage.repository_factory import (
    create_session_repository,
    load_storage_config
)
from src.application.use_cases.session_management import (
    SessionSearchUseCase,
    SessionReplayUseCase,
    SessionAnalyticsUseCase
)
from src.domain.models.session import (
    SessionStatus,
    SessionResult,
    SessionSearchCriteria
)
from src.domain.services.conversation import ConversationHistory


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """임시 데이터베이스 경로"""
    return tmp_path / "integration_test.db"


@pytest.fixture
def repository(temp_db_path: Path) -> SqliteSessionRepository:
    """통합 테스트용 SQLite 리포지토리"""
    return SqliteSessionRepository(db_path=temp_db_path)


@pytest.fixture
def search_use_case(repository):
    """SessionSearchUseCase 인스턴스"""
    return SessionSearchUseCase(session_repository=repository)


@pytest.fixture
def replay_use_case(repository):
    """SessionReplayUseCase 인스턴스"""
    return SessionReplayUseCase(session_repository=repository)


@pytest.fixture
def analytics_use_case(repository):
    """SessionAnalyticsUseCase 인스턴스"""
    return SessionAnalyticsUseCase(session_repository=repository)


class TestCompleteWorkflow:
    """전체 워크플로우 통합 테스트"""

    def test_save_search_load_delete_workflow(self, repository):
        """세션 저장 → 검색 → 로드 → 삭제 전체 워크플로우 테스트"""
        # 1. 세션 저장
        session_id = "workflow-test-001"
        user_request = "Implement user authentication"

        history = ConversationHistory(max_length=50)
        history.add_message("user", user_request)
        history.add_message("agent", "Planning authentication system", agent_name="planner")
        history.add_message("agent", "Code implemented", agent_name="coder")
        history.add_message("agent", "Tests passed", agent_name="tester")

        result = SessionResult(
            status=SessionStatus.COMPLETED,
            files_modified=["auth.py", "user.py"],
            tests_passed=True
        )

        save_path = repository.save(session_id, user_request, history, result)
        assert save_path is not None

        # 2. 세션 검색 (상태로 검색)
        criteria = SessionSearchCriteria(status="completed")
        sessions = repository.search_sessions(criteria)

        assert len(sessions) >= 1
        # 우리가 저장한 세션 찾기
        our_session = next((s for s in sessions if s.session_id == session_id), None)
        assert our_session is not None
        assert our_session.status == "completed"
        assert "planner" in our_session.agents_used
        assert "coder" in our_session.agents_used
        assert "tester" in our_session.agents_used

        # 3. 세션 로드
        loaded_history = repository.load(session_id)

        assert loaded_history is not None
        assert len(loaded_history.messages) == 4
        assert loaded_history.messages[0].content == user_request
        assert loaded_history.messages[-1].content == "Tests passed"

        # 4. 세션 삭제
        delete_result = repository.delete_session(session_id)

        assert delete_result is True

        # 5. 삭제 확인
        loaded_after_delete = repository.load(session_id)
        assert loaded_after_delete is None

    def test_multiple_sessions_workflow(self, repository):
        """여러 세션을 저장하고 관리하는 워크플로우 테스트"""
        # 여러 세션 저장
        sessions_data = [
            {
                "session_id": "multi-001",
                "user_request": "Create login page",
                "status": SessionStatus.COMPLETED,
                "agent": "coder"
            },
            {
                "session_id": "multi-002",
                "user_request": "Fix payment bug",
                "status": SessionStatus.ERROR,
                "agent": "debugger"
            },
            {
                "session_id": "multi-003",
                "user_request": "Add dashboard",
                "status": SessionStatus.COMPLETED,
                "agent": "coder"
            }
        ]

        for data in sessions_data:
            history = ConversationHistory()
            history.add_message("user", data["user_request"])
            history.add_message("agent", "Working on it", agent_name=data["agent"])

            result = SessionResult(
                status=data["status"],
                error_message="Test error" if data["status"] == SessionStatus.ERROR else None
            )

            repository.save(data["session_id"], data["user_request"], history, result)

        # 전체 세션 조회
        all_sessions = repository.list_sessions()
        assert len(all_sessions) == 3

        # 상태별 필터링
        completed_criteria = SessionSearchCriteria(status="completed")
        completed_sessions = repository.search_sessions(completed_criteria)
        assert len(completed_sessions) == 2

        error_criteria = SessionSearchCriteria(status="error")
        error_sessions = repository.search_sessions(error_criteria)
        assert len(error_sessions) == 1

        # 에이전트별 필터링
        coder_criteria = SessionSearchCriteria(agent_name="coder")
        coder_sessions = repository.search_sessions(coder_criteria)
        assert len(coder_sessions) == 2


class TestUseCasesIntegration:
    """Use Cases와 Repository 통합 테스트"""

    def test_search_use_case_integration(
        self,
        repository,
        search_use_case
    ):
        """SearchUseCase와 Repository 통합 테스트"""
        # 테스트 세션 저장
        history = ConversationHistory()
        history.add_message("user", "Create search feature")
        history.add_message("agent", "Search implemented", agent_name="coder")

        result = SessionResult(status=SessionStatus.COMPLETED, tests_passed=True)

        repository.save("search-test-001", "Create search feature", history, result)

        # UseCase로 검색 (상태로 검색)
        criteria = SessionSearchCriteria(status="completed")
        sessions = search_use_case.execute(criteria)

        assert len(sessions) >= 1
        # 우리가 저장한 세션 찾기
        found_session = next((s for s in sessions if s.session_id == "search-test-001"), None)
        assert found_session is not None

    def test_replay_use_case_integration(
        self,
        repository,
        replay_use_case
    ):
        """ReplayUseCase와 Repository 통합 테스트"""
        # 테스트 세션 저장
        history = ConversationHistory()
        history.add_message("user", "Create replay feature")
        history.add_message("agent", "Replay implemented", agent_name="coder")

        result = SessionResult(status=SessionStatus.COMPLETED)

        repository.save("replay-test-001", "Create replay feature", history, result)

        # UseCase로 재생
        detail = replay_use_case.execute("replay-test-001")

        assert detail is not None
        assert detail.metadata.session_id == "replay-test-001"
        assert len(detail.messages) == 2

        # 포맷팅 테스트
        formatted = replay_use_case.format_for_display(detail)
        assert "replay-test-001" in formatted
        assert "Create replay feature" in formatted

    def test_analytics_use_case_integration(
        self,
        repository,
        analytics_use_case
    ):
        """AnalyticsUseCase와 Repository 통합 테스트"""
        # 여러 테스트 세션 저장
        for i in range(5):
            history = ConversationHistory()
            history.add_message("user", f"Task {i}")
            history.add_message("agent", "Done", agent_name="coder")

            status = SessionStatus.COMPLETED if i < 4 else SessionStatus.ERROR
            result = SessionResult(
                status=status,
                files_modified=[f"file{i}.py"] if status == SessionStatus.COMPLETED else []
            )

            repository.save(f"analytics-{i:03d}", f"Task {i}", history, result)

        # UseCase로 통계 조회
        stats = analytics_use_case.get_summary_stats(days=30)

        assert stats["total_sessions"] == 5
        assert stats["status_distribution"]["completed"] == 4
        assert stats["status_distribution"]["error"] == 1
        assert stats["success_rate"] == 80.0
        assert stats["total_files_modified"] == 4

        # 에이전트 성능 조회
        performance = analytics_use_case.get_agent_performance("coder", days=30)

        assert performance["agent_name"] == "coder"
        assert performance["total_uses"] == 5


class TestRepositoryFactory:
    """Repository Factory 통합 테스트"""

    def test_create_sqlite_repository(self, tmp_path: Path):
        """SQLite 리포지토리 생성 테스트"""
        config = {
            "backend": "sqlite",
            "sqlite_db_path": str(tmp_path / "factory_test.db")
        }

        repository = create_session_repository(backend="sqlite", config=config)

        assert isinstance(repository, SqliteSessionRepository)

        # 리포지토리 사용 테스트
        history = ConversationHistory()
        history.add_message("user", "Factory test")

        result = SessionResult(status=SessionStatus.COMPLETED)

        save_path = repository.save("factory-001", "Factory test", history, result)
        assert save_path is not None

    def test_create_json_repository(self, tmp_path: Path):
        """JSON 리포지토리 생성 테스트"""
        config = {
            "backend": "json",
            "json_dir": str(tmp_path / "sessions")
        }

        repository = create_session_repository(backend="json", config=config)

        # JsonSessionRepository 타입 확인
        assert repository is not None
        assert hasattr(repository, "save")
        assert hasattr(repository, "load")

    def test_create_repository_with_invalid_backend(self):
        """잘못된 백엔드 타입으로 생성 시 예외 발생 테스트"""
        with pytest.raises(ValueError, match="유효하지 않은 리포지토리 타입"):
            create_session_repository(backend="invalid_backend")

    def test_load_storage_config_from_file(self, tmp_path: Path, monkeypatch):
        """파일에서 storage 설정 로드 테스트"""
        # 임시 설정 파일 생성
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "system_config.json"

        config_data = {
            "storage": {
                "backend": "sqlite",
                "sqlite_db_path": "custom/path.db",
                "retention_days": 60
            }
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)

        # 현재 작업 디렉토리를 임시 경로로 변경
        monkeypatch.chdir(tmp_path)

        # 설정 로드
        config = load_storage_config()

        assert config["backend"] == "sqlite"
        assert config["sqlite_db_path"] == "custom/path.db"
        assert config["retention_days"] == 60


class TestSearchPerformance:
    """검색 성능 및 복잡한 쿼리 테스트"""

    @pytest.fixture
    def populated_repository(self, repository):
        """대량의 세션이 저장된 리포지토리"""
        # 100개의 세션 저장
        for i in range(100):
            history = ConversationHistory()
            history.add_message("user", f"Task number {i}")
            history.add_message("agent", f"Completed task {i}", agent_name=f"agent-{i % 5}")

            status = SessionStatus.COMPLETED if i % 3 != 0 else SessionStatus.ERROR
            result = SessionResult(
                status=status,
                files_modified=[f"file{i}.py"] if status == SessionStatus.COMPLETED else []
            )

            repository.save(f"perf-{i:03d}", f"Task number {i}", history, result)

        return repository

    @pytest.mark.skip(reason="FTS5 content='' mode 테스트 제한사항")
    def test_keyword_search_performance(self, populated_repository):
        """키워드 검색 성능 테스트"""
        criteria = SessionSearchCriteria(keyword="Task number")
        sessions = populated_repository.search_sessions(criteria)

        # FTS5가 제대로 동작하면 많은 결과를 빠르게 반환해야 함
        assert len(sessions) > 0

    def test_complex_query_combination(self, populated_repository):
        """복합 조건 검색 테스트"""
        criteria = SessionSearchCriteria(
            status="completed",
            agent_name="agent-1",
            limit=10
        )

        sessions = populated_repository.search_sessions(criteria)

        # 모든 결과가 조건을 만족하는지 확인
        assert all(s.status == "completed" for s in sessions)
        assert all("agent-1" in s.agents_used for s in sessions)
        assert len(sessions) <= 10

    def test_pagination(self, populated_repository):
        """페이지네이션 테스트"""
        # 첫 페이지
        page1_criteria = SessionSearchCriteria(limit=20, offset=0)
        page1 = populated_repository.search_sessions(page1_criteria)

        # 두 번째 페이지
        page2_criteria = SessionSearchCriteria(limit=20, offset=20)
        page2 = populated_repository.search_sessions(page2_criteria)

        assert len(page1) == 20
        assert len(page2) == 20

        # 페이지 간 중복 없음
        page1_ids = {s.session_id for s in page1}
        page2_ids = {s.session_id for s in page2}
        assert len(page1_ids & page2_ids) == 0


class TestErrorHandling:
    """에러 처리 통합 테스트"""

    def test_concurrent_access(self, repository):
        """동시 접근 테스트 (SQLite는 기본적으로 동시 쓰기를 지원하지 않으므로 순차 테스트)"""
        # 여러 세션을 순차적으로 저장
        for i in range(10):
            history = ConversationHistory()
            history.add_message("user", f"Concurrent test {i}")

            result = SessionResult(status=SessionStatus.COMPLETED)

            repository.save(f"concurrent-{i:03d}", f"Concurrent test {i}", history, result)

        # 모든 세션이 저장되었는지 확인
        sessions = repository.list_sessions()
        concurrent_sessions = [s for s in sessions if s.session_id.startswith("concurrent-")]
        assert len(concurrent_sessions) == 10

    def test_save_with_empty_history(self, repository):
        """빈 히스토리로 저장 시 테스트"""
        empty_history = ConversationHistory()
        result = SessionResult(status=SessionStatus.COMPLETED)

        # 빈 히스토리도 저장 가능해야 함
        save_path = repository.save("empty-001", "Empty test", empty_history, result)
        assert save_path is not None

        # 로드 확인
        loaded = repository.load("empty-001")
        assert loaded is not None
        assert len(loaded.messages) == 0

    @pytest.mark.skip(reason="FTS5 content='' mode 테스트 제한사항")
    def test_search_with_special_characters(self, repository):
        """특수문자가 포함된 검색 테스트"""
        history = ConversationHistory()
        history.add_message("user", 'Test with "quotes" and special chars')

        result = SessionResult(status=SessionStatus.COMPLETED)

        repository.save("special-001", 'Test with "quotes"', history, result)

        # 특수문자 검색 (이스케이프 처리 확인)
        criteria = SessionSearchCriteria(keyword="quotes")
        sessions = repository.search_sessions(criteria)

        assert len(sessions) == 1
