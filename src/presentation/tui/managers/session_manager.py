"""
SessionManager 모듈

TUI 세션 관리 책임:
- 세션 시작/중지/재시작
- 세션 상태 조회
- 세션 데이터 관리
"""

import time
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from src.domain.models import SessionStatus
from src.domain.services import ConversationHistory, MetricsCollector
from src.infrastructure.storage import InMemoryMetricsRepository
from src.infrastructure.logging import get_logger

logger = get_logger(__name__, component="SessionManager")


@dataclass
class SessionConfig:
    """
    세션 설정 정보

    Attributes:
        session_id: 세션 고유 ID
        user_request: 사용자 요청 내용
        max_turns: 최대 턴 수 (기본값: 50)
        timeout: 세션 타임아웃 (초 단위, 기본값: 3600)
    """
    session_id: str
    user_request: str
    max_turns: int = 50
    timeout: int = 3600


@dataclass
class SessionData:
    """
    세션별 데이터 저장 클래스

    Attributes:
        session_id: 세션 고유 ID
        history: 대화 히스토리
        log_lines: 로그 라인 목록
        start_time: 세션 시작 시간
        metrics_repository: 메트릭 저장소
        metrics_collector: 메트릭 수집기
        status: 세션 상태
        end_time: 세션 종료 시간 (옵셔널)
    """
    session_id: str
    history: ConversationHistory
    log_lines: list[str]
    start_time: float
    metrics_repository: InMemoryMetricsRepository
    metrics_collector: MetricsCollector
    status: SessionStatus = SessionStatus.COMPLETED
    end_time: Optional[float] = None

    def __repr__(self) -> str:
        return f"SessionData(id={self.session_id}, status={self.status})"


class SessionManager:
    """
    TUI 세션 관리자

    세션의 생명주기를 관리하고 상태를 추적합니다.

    Example:
        >>> manager = SessionManager()
        >>> config = SessionConfig(
        ...     session_id="test-001",
        ...     user_request="Implement feature X"
        ... )
        >>> session_id = manager.start_session(config)
        >>> status = manager.get_session_status(session_id)
        >>> manager.stop_session(session_id)
    """

    def __init__(self) -> None:
        """SessionManager 초기화"""
        self._sessions: Dict[str, SessionData] = {}
        self._active_session_id: Optional[str] = None
        logger.info("SessionManager initialized")

    def start_session(self, session_config: SessionConfig) -> str:
        """
        새로운 세션을 시작합니다.

        Args:
            session_config: 세션 설정 정보

        Returns:
            생성된 세션 ID

        Raises:
            ValueError: 이미 존재하는 세션 ID인 경우

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(
            ...     session_id="test-001",
            ...     user_request="Implement feature X"
            ... )
            >>> session_id = manager.start_session(config)
            >>> print(session_id)
            test-001
        """
        session_id = session_config.session_id

        if session_id in self._sessions:
            logger.error(f"Session already exists: {session_id}")
            raise ValueError(f"Session with ID '{session_id}' already exists")

        # 세션 데이터 생성
        metrics_repository = InMemoryMetricsRepository()
        metrics_collector = MetricsCollector(metrics_repository)

        session_data = SessionData(
            session_id=session_id,
            history=ConversationHistory(),
            log_lines=[],
            start_time=time.time(),
            metrics_repository=metrics_repository,
            metrics_collector=metrics_collector,
            status=SessionStatus.COMPLETED,
        )

        self._sessions[session_id] = session_data
        self._active_session_id = session_id

        logger.info(
            f"Session started: {session_id} "
            f"(request: {session_config.user_request[:50]}...)"
        )

        return session_id

    def stop_session(self, session_id: str) -> None:
        """
        세션을 중지합니다.

        Args:
            session_id: 중지할 세션 ID

        Raises:
            KeyError: 존재하지 않는 세션 ID인 경우

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> session_id = manager.start_session(config)
            >>> manager.stop_session(session_id)
        """
        if session_id not in self._sessions:
            logger.error(f"Session not found: {session_id}")
            raise KeyError(f"Session with ID '{session_id}' not found")

        session_data = self._sessions[session_id]
        session_data.end_time = time.time()
        session_data.status = SessionStatus.TERMINATED

        if self._active_session_id == session_id:
            self._active_session_id = None

        logger.info(f"Session stopped: {session_id}")

    def restart_session(self, session_id: str) -> None:
        """
        세션을 재시작합니다.

        기존 세션 데이터는 유지하되, 상태를 초기화합니다.

        Args:
            session_id: 재시작할 세션 ID

        Raises:
            KeyError: 존재하지 않는 세션 ID인 경우

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> session_id = manager.start_session(config)
            >>> manager.stop_session(session_id)
            >>> manager.restart_session(session_id)
        """
        if session_id not in self._sessions:
            logger.error(f"Session not found: {session_id}")
            raise KeyError(f"Session with ID '{session_id}' not found")

        session_data = self._sessions[session_id]
        session_data.start_time = time.time()
        session_data.end_time = None
        session_data.status = SessionStatus.COMPLETED

        self._active_session_id = session_id

        logger.info(f"Session restarted: {session_id}")

    def get_session_status(self, session_id: str) -> SessionStatus:
        """
        세션의 현재 상태를 조회합니다.

        Args:
            session_id: 조회할 세션 ID

        Returns:
            세션 상태 (SessionStatus Enum)

        Raises:
            KeyError: 존재하지 않는 세션 ID인 경우

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> session_id = manager.start_session(config)
            >>> status = manager.get_session_status(session_id)
            >>> print(status)
            SessionStatus.COMPLETED
        """
        if session_id not in self._sessions:
            logger.error(f"Session not found: {session_id}")
            raise KeyError(f"Session with ID '{session_id}' not found")

        return self._sessions[session_id].status

    def get_session_data(self, session_id: str) -> SessionData:
        """
        세션 데이터를 조회합니다.

        Args:
            session_id: 조회할 세션 ID

        Returns:
            세션 데이터 객체

        Raises:
            KeyError: 존재하지 않는 세션 ID인 경우

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> session_id = manager.start_session(config)
            >>> data = manager.get_session_data(session_id)
            >>> print(data.session_id)
            test-001
        """
        if session_id not in self._sessions:
            logger.error(f"Session not found: {session_id}")
            raise KeyError(f"Session with ID '{session_id}' not found")

        return self._sessions[session_id]

    def get_active_session_id(self) -> Optional[str]:
        """
        현재 활성화된 세션 ID를 반환합니다.

        Returns:
            활성 세션 ID (없으면 None)

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> session_id = manager.start_session(config)
            >>> active_id = manager.get_active_session_id()
            >>> print(active_id)
            test-001
        """
        return self._active_session_id

    def list_sessions(self) -> list[str]:
        """
        모든 세션 ID 목록을 반환합니다.

        Returns:
            세션 ID 리스트

        Example:
            >>> manager = SessionManager()
            >>> config1 = SessionConfig(session_id="test-001", user_request="Test 1")
            >>> config2 = SessionConfig(session_id="test-002", user_request="Test 2")
            >>> manager.start_session(config1)
            >>> manager.start_session(config2)
            >>> sessions = manager.list_sessions()
            >>> print(len(sessions))
            2
        """
        return list(self._sessions.keys())

    def delete_session(self, session_id: str) -> None:
        """
        세션을 삭제합니다.

        Args:
            session_id: 삭제할 세션 ID

        Raises:
            KeyError: 존재하지 않는 세션 ID인 경우

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> session_id = manager.start_session(config)
            >>> manager.delete_session(session_id)
        """
        if session_id not in self._sessions:
            logger.error(f"Session not found: {session_id}")
            raise KeyError(f"Session with ID '{session_id}' not found")

        if self._active_session_id == session_id:
            self._active_session_id = None

        del self._sessions[session_id]
        logger.info(f"Session deleted: {session_id}")

    def clear_all_sessions(self) -> None:
        """
        모든 세션을 삭제합니다.

        Example:
            >>> manager = SessionManager()
            >>> config1 = SessionConfig(session_id="test-001", user_request="Test 1")
            >>> config2 = SessionConfig(session_id="test-002", user_request="Test 2")
            >>> manager.start_session(config1)
            >>> manager.start_session(config2)
            >>> manager.clear_all_sessions()
            >>> print(len(manager.list_sessions()))
            0
        """
        self._sessions.clear()
        self._active_session_id = None
        logger.info("All sessions cleared")

    def update_session_status(
        self,
        session_id: str,
        status: SessionStatus
    ) -> None:
        """
        세션 상태를 업데이트합니다.

        Args:
            session_id: 세션 ID
            status: 새로운 세션 상태

        Raises:
            KeyError: 존재하지 않는 세션 ID인 경우

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> session_id = manager.start_session(config)
            >>> manager.update_session_status(session_id, SessionStatus.ERROR)
            >>> status = manager.get_session_status(session_id)
            >>> print(status)
            SessionStatus.ERROR
        """
        if session_id not in self._sessions:
            logger.error(f"Session not found: {session_id}")
            raise KeyError(f"Session with ID '{session_id}' not found")

        self._sessions[session_id].status = status
        logger.info(f"Session status updated: {session_id} -> {status}")

    def get_session_duration(self, session_id: str) -> float:
        """
        세션의 실행 시간을 초 단위로 반환합니다.

        Args:
            session_id: 세션 ID

        Returns:
            세션 실행 시간 (초)

        Raises:
            KeyError: 존재하지 않는 세션 ID인 경우

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> session_id = manager.start_session(config)
            >>> import time
            >>> time.sleep(0.1)
            >>> duration = manager.get_session_duration(session_id)
            >>> print(duration > 0)
            True
        """
        if session_id not in self._sessions:
            logger.error(f"Session not found: {session_id}")
            raise KeyError(f"Session with ID '{session_id}' not found")

        session_data = self._sessions[session_id]
        end_time = session_data.end_time or time.time()
        return end_time - session_data.start_time
