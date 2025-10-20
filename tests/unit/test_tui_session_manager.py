"""
SessionManager 단위 테스트
"""

import time
import pytest

from src.presentation.tui.managers.session_manager import (
    SessionManager,
    SessionConfig,
    SessionData,
)
from src.domain.models import SessionStatus


class TestSessionManager:
    """SessionManager 테스트 클래스"""

    def test_init(self):
        """초기화 테스트"""
        manager = SessionManager()
        assert manager is not None
        assert manager.get_active_session_id() is None
        assert len(manager.list_sessions()) == 0

    def test_start_session(self):
        """세션 시작 테스트"""
        manager = SessionManager()
        config = SessionConfig(
            session_id="test-001",
            user_request="Test request"
        )

        session_id = manager.start_session(config)

        assert session_id == "test-001"
        assert manager.get_active_session_id() == "test-001"
        assert "test-001" in manager.list_sessions()

    def test_start_session_with_duplicate_id(self):
        """중복 세션 ID로 시작 시 에러 발생 테스트"""
        manager = SessionManager()
        config = SessionConfig(
            session_id="test-001",
            user_request="Test request"
        )

        manager.start_session(config)

        with pytest.raises(ValueError) as exc_info:
            manager.start_session(config)

        assert "already exists" in str(exc_info.value).lower()

    def test_stop_session(self):
        """세션 중지 테스트"""
        manager = SessionManager()
        config = SessionConfig(
            session_id="test-001",
            user_request="Test request"
        )

        session_id = manager.start_session(config)
        manager.stop_session(session_id)

        status = manager.get_session_status(session_id)
        assert status == SessionStatus.TERMINATED
        assert manager.get_active_session_id() is None

    def test_stop_nonexistent_session(self):
        """존재하지 않는 세션 중지 시 에러 발생 테스트"""
        manager = SessionManager()

        with pytest.raises(KeyError) as exc_info:
            manager.stop_session("nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_restart_session(self):
        """세션 재시작 테스트"""
        manager = SessionManager()
        config = SessionConfig(
            session_id="test-001",
            user_request="Test request"
        )

        session_id = manager.start_session(config)
        manager.stop_session(session_id)
        manager.restart_session(session_id)

        status = manager.get_session_status(session_id)
        assert status == SessionStatus.COMPLETED
        assert manager.get_active_session_id() == session_id

    def test_restart_nonexistent_session(self):
        """존재하지 않는 세션 재시작 시 에러 발생 테스트"""
        manager = SessionManager()

        with pytest.raises(KeyError) as exc_info:
            manager.restart_session("nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_get_session_status(self):
        """세션 상태 조회 테스트"""
        manager = SessionManager()
        config = SessionConfig(
            session_id="test-001",
            user_request="Test request"
        )

        session_id = manager.start_session(config)
        status = manager.get_session_status(session_id)

        assert status == SessionStatus.COMPLETED

    def test_get_session_status_nonexistent(self):
        """존재하지 않는 세션 상태 조회 시 에러 발생 테스트"""
        manager = SessionManager()

        with pytest.raises(KeyError) as exc_info:
            manager.get_session_status("nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_get_session_data(self):
        """세션 데이터 조회 테스트"""
        manager = SessionManager()
        config = SessionConfig(
            session_id="test-001",
            user_request="Test request"
        )

        session_id = manager.start_session(config)
        data = manager.get_session_data(session_id)

        assert isinstance(data, SessionData)
        assert data.session_id == session_id
        assert data.history is not None

    def test_get_active_session_id(self):
        """활성 세션 ID 조회 테스트"""
        manager = SessionManager()
        config = SessionConfig(
            session_id="test-001",
            user_request="Test request"
        )

        assert manager.get_active_session_id() is None

        session_id = manager.start_session(config)
        assert manager.get_active_session_id() == session_id

    def test_list_sessions(self):
        """세션 목록 조회 테스트"""
        manager = SessionManager()

        config1 = SessionConfig(session_id="test-001", user_request="Request 1")
        config2 = SessionConfig(session_id="test-002", user_request="Request 2")

        manager.start_session(config1)
        manager.start_session(config2)

        sessions = manager.list_sessions()
        assert len(sessions) == 2
        assert "test-001" in sessions
        assert "test-002" in sessions

    def test_delete_session(self):
        """세션 삭제 테스트"""
        manager = SessionManager()
        config = SessionConfig(
            session_id="test-001",
            user_request="Test request"
        )

        session_id = manager.start_session(config)
        manager.delete_session(session_id)

        assert session_id not in manager.list_sessions()
        assert manager.get_active_session_id() is None

    def test_delete_nonexistent_session(self):
        """존재하지 않는 세션 삭제 시 에러 발생 테스트"""
        manager = SessionManager()

        with pytest.raises(KeyError) as exc_info:
            manager.delete_session("nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_clear_all_sessions(self):
        """모든 세션 삭제 테스트"""
        manager = SessionManager()

        config1 = SessionConfig(session_id="test-001", user_request="Request 1")
        config2 = SessionConfig(session_id="test-002", user_request="Request 2")

        manager.start_session(config1)
        manager.start_session(config2)

        manager.clear_all_sessions()

        assert len(manager.list_sessions()) == 0
        assert manager.get_active_session_id() is None

    def test_update_session_status(self):
        """세션 상태 업데이트 테스트"""
        manager = SessionManager()
        config = SessionConfig(
            session_id="test-001",
            user_request="Test request"
        )

        session_id = manager.start_session(config)
        manager.update_session_status(session_id, SessionStatus.ERROR)

        status = manager.get_session_status(session_id)
        assert status == SessionStatus.ERROR

    def test_update_session_status_nonexistent(self):
        """존재하지 않는 세션 상태 업데이트 시 에러 발생 테스트"""
        manager = SessionManager()

        with pytest.raises(KeyError) as exc_info:
            manager.update_session_status("nonexistent", SessionStatus.ERROR)

        assert "not found" in str(exc_info.value).lower()

    def test_get_session_duration(self):
        """세션 실행 시간 조회 테스트"""
        manager = SessionManager()
        config = SessionConfig(
            session_id="test-001",
            user_request="Test request"
        )

        session_id = manager.start_session(config)
        time.sleep(0.1)  # 0.1초 대기

        duration = manager.get_session_duration(session_id)
        assert duration >= 0.1

    def test_get_session_duration_nonexistent(self):
        """존재하지 않는 세션 실행 시간 조회 시 에러 발생 테스트"""
        manager = SessionManager()

        with pytest.raises(KeyError) as exc_info:
            manager.get_session_duration("nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_session_config_defaults(self):
        """SessionConfig 기본값 테스트"""
        config = SessionConfig(
            session_id="test-001",
            user_request="Test request"
        )

        assert config.max_turns == 50
        assert config.timeout == 3600

    def test_multiple_sessions(self):
        """여러 세션 동시 관리 테스트"""
        manager = SessionManager()

        # 3개 세션 생성
        for i in range(3):
            config = SessionConfig(
                session_id=f"test-{i:03d}",
                user_request=f"Request {i}"
            )
            manager.start_session(config)

        # 모든 세션이 존재하는지 확인
        sessions = manager.list_sessions()
        assert len(sessions) == 3

        # 마지막 세션이 활성화되어 있는지 확인
        assert manager.get_active_session_id() == "test-002"
