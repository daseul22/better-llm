"""
SessionManager 모듈

TUI 세션 관리 책임:
- 세션 시작/중지/재시작
- 세션 상태 조회
- 세션 데이터 관리
"""

import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

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
        log_lines: 로그 라인 목록 (thread-safe deque, maxlen=10000)
        start_time: 세션 시작 시간
        metrics_repository: 메트릭 저장소
        metrics_collector: 메트릭 수집기
        status: 세션 상태
        end_time: 세션 종료 시간 (옵셔널)
        input_buffer: 입력 버퍼 (기본값: 빈 문자열)
    """
    session_id: str
    history: ConversationHistory
    log_lines: deque = field(default_factory=lambda: deque(maxlen=10000))
    start_time: float = 0.0
    metrics_repository: InMemoryMetricsRepository = field(default_factory=InMemoryMetricsRepository)
    metrics_collector: MetricsCollector = field(default=None)
    status: SessionStatus = SessionStatus.COMPLETED
    end_time: Optional[float] = None
    input_buffer: str = ""

    def __repr__(self) -> str:
        return f"SessionData(id={self.session_id}, status={self.status})"


class SessionManager:
    """
    TUI 세션 관리자

    세션의 생명주기를 관리하고 상태를 추적합니다.
    멀티 세션을 지원하며 인덱스 기반 세션 전환이 가능합니다.

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
        self._session_list: list[SessionData] = []  # 인덱스 기반 접근을 위한 리스트
        self._active_session_id: Optional[str] = None
        self._active_session_index: int = 0
        logger.info("SessionManager initialized")

    # ============================================================================
    # 헬퍼 메서드 (중복 코드 제거)
    # ============================================================================

    def _ensure_session_exists(self, session_id: str) -> SessionData:
        """
        세션 존재 여부 검증 및 반환 (헬퍼 메서드)

        Args:
            session_id: 조회할 세션 ID

        Returns:
            세션 데이터

        Raises:
            KeyError: 존재하지 않는 세션 ID인 경우
        """
        if session_id not in self._sessions:
            logger.error(f"Session not found: {session_id}")
            raise KeyError(f"Session with ID '{session_id}' not found")
        return self._sessions[session_id]

    def _sync_session_index(
        self,
        index: int,
        old_session: SessionData,
        new_session: SessionData
    ) -> None:
        """
        세션 인덱스/딕셔너리 동기화 헬퍼 (단일 책임)

        Args:
            index: 세션 인덱스
            old_session: 기존 세션 데이터
            new_session: 새로운 세션 데이터
        """
        # 기존 세션을 딕셔너리에서 제거
        if old_session.session_id in self._sessions:
            del self._sessions[old_session.session_id]

        # 새 세션 저장
        self._sessions[new_session.session_id] = new_session
        self._session_list[index] = new_session

        logger.info(
            f"Synced session at index {index}: "
            f"{old_session.session_id} -> {new_session.session_id}"
        )

    # ============================================================================
    # 세션 생명주기 관리
    # ============================================================================

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

        # Phase 1 - Step 1.2: 중앙화된 팩토리 메서드 사용
        session_data = self.create_session_data(
            session_id=session_id,
            user_request=session_config.user_request
        )

        self._sessions[session_id] = session_data
        self._session_list.append(session_data)
        self._active_session_id = session_id
        self._active_session_index = len(self._session_list) - 1

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
        session_data = self._ensure_session_exists(session_id)
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
        session_data = self._ensure_session_exists(session_id)
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
        session_data = self._ensure_session_exists(session_id)
        return session_data.status

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
        return self._ensure_session_exists(session_id)

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
        session_data = self._ensure_session_exists(session_id)

        if self._active_session_id == session_id:
            self._active_session_id = None

        # 딕셔너리에서 삭제
        del self._sessions[session_id]

        # 리스트에서도 삭제 (동기화)
        if session_data in self._session_list:
            self._session_list.remove(session_data)

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
        self._session_list.clear()  # 리스트도 동기화
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
        session_data = self._ensure_session_exists(session_id)
        session_data.status = status
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
        session_data = self._ensure_session_exists(session_id)
        end_time = session_data.end_time or time.time()
        return end_time - session_data.start_time

    # === 멀티 세션 관리 메서드 (Phase 1.4) ===

    def get_all_sessions(self) -> list[SessionData]:
        """
        모든 세션을 리스트로 반환합니다.

        Returns:
            세션 데이터 리스트 (인덱스 순서 유지)

        Example:
            >>> manager = SessionManager()
            >>> config1 = SessionConfig(session_id="test-001", user_request="Test 1")
            >>> config2 = SessionConfig(session_id="test-002", user_request="Test 2")
            >>> manager.start_session(config1)
            >>> manager.start_session(config2)
            >>> sessions = manager.get_all_sessions()
            >>> print(len(sessions))
            2
        """
        return self._session_list

    def get_session_by_index(self, index: int) -> SessionData:
        """
        인덱스로 세션 데이터를 조회합니다.

        Args:
            index: 세션 인덱스

        Returns:
            세션 데이터 객체

        Raises:
            IndexError: 잘못된 인덱스인 경우

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> manager.start_session(config)
            >>> session = manager.get_session_by_index(0)
            >>> print(session.session_id)
            test-001
        """
        if index < 0 or index >= len(self._session_list):
            logger.error(f"Invalid session index: {index}")
            raise IndexError(f"Session index {index} out of range")

        return self._session_list[index]

    def get_session_count(self) -> int:
        """
        세션 개수를 반환합니다.

        Returns:
            세션 개수

        Example:
            >>> manager = SessionManager()
            >>> config1 = SessionConfig(session_id="test-001", user_request="Test 1")
            >>> config2 = SessionConfig(session_id="test-002", user_request="Test 2")
            >>> manager.start_session(config1)
            >>> manager.start_session(config2)
            >>> count = manager.get_session_count()
            >>> print(count)
            2
        """
        return len(self._session_list)

    def get_active_session_index(self) -> int:
        """
        현재 활성화된 세션의 인덱스를 반환합니다.

        Returns:
            활성 세션 인덱스

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> manager.start_session(config)
            >>> index = manager.get_active_session_index()
            >>> print(index)
            0
        """
        return self._active_session_index

    def switch_to_session(self, index: int) -> str:
        """
        세션을 전환합니다.

        Args:
            index: 전환할 세션 인덱스

        Returns:
            전환된 세션 ID

        Raises:
            IndexError: 잘못된 인덱스인 경우

        Example:
            >>> manager = SessionManager()
            >>> config1 = SessionConfig(session_id="test-001", user_request="Test 1")
            >>> config2 = SessionConfig(session_id="test-002", user_request="Test 2")
            >>> manager.start_session(config1)
            >>> manager.start_session(config2)
            >>> session_id = manager.switch_to_session(0)
            >>> print(session_id)
            test-001
        """
        if index < 0 or index >= len(self._session_list):
            logger.error(f"Invalid session index: {index}")
            raise IndexError(f"Session index {index} out of range")

        self._active_session_index = index
        session_data = self._session_list[index]
        self._active_session_id = session_data.session_id

        logger.info(f"Switched to session {index}: {session_data.session_id}")
        return session_data.session_id

    def create_session_at_index(
        self,
        index: int,
        session_id: str,
        user_request: str = ""
    ) -> SessionData:
        """
        특정 인덱스에 세션을 생성합니다.

        인덱스가 현재 세션 개수보다 크면 빈 세션들을 자동으로 생성합니다.

        Args:
            index: 세션 인덱스
            session_id: 세션 ID
            user_request: 사용자 요청 (기본값: "")

        Returns:
            생성된 세션 데이터

        Example:
            >>> manager = SessionManager()
            >>> session = manager.create_session_at_index(2, "test-003")
            >>> print(manager.get_session_count())
            3
        """
        # 인덱스가 현재 세션 개수보다 크면 빈 세션들을 생성
        while len(self._session_list) <= index:
            empty_index = len(self._session_list)
            empty_session_id = f"empty-{empty_index}"

            # Phase 1 - Step 1.2: 중앙화된 팩토리 메서드 사용
            empty_session = self.create_session_data(
                session_id=empty_session_id,
                user_request=""
            )

            self._sessions[empty_session_id] = empty_session
            self._session_list.append(empty_session)
            logger.info(f"Created empty session at index {empty_index}: {empty_session_id}")

        # Phase 1 - Step 1.2: 중앙화된 팩토리 메서드 사용
        session_data = self.create_session_data(
            session_id=session_id,
            user_request=user_request
        )

        # 세션 인덱스 동기화 (헬퍼 메서드 사용)
        old_session = self._session_list[index]
        self._sync_session_index(index, old_session, session_data)

        logger.info(f"Created session at index {index}: {session_id}")
        return session_data

    def update_session_at_index(
        self,
        index: int,
        session_data: SessionData
    ) -> None:
        """
        특정 인덱스의 세션 데이터를 업데이트합니다.

        Args:
            index: 세션 인덱스
            session_data: 새로운 세션 데이터

        Raises:
            IndexError: 잘못된 인덱스인 경우

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> manager.start_session(config)
            >>> new_data = SessionData(...)
            >>> manager.update_session_at_index(0, new_data)
        """
        if index < 0 or index >= len(self._session_list):
            logger.error(f"Invalid session index: {index}")
            raise IndexError(f"Session index {index} out of range")

        old_session = self._session_list[index]
        self._sync_session_index(index, old_session, session_data)

        logger.info(
            f"Updated session at index {index}: "
            f"{old_session.session_id} -> {session_data.session_id}"
        )

    # === Phase 1 - Step 1.2: 세션 생성 로직 중앙화 ===

    def create_session_data(
        self,
        session_id: str,
        user_request: str = "",
        initial_messages: Optional[list[dict]] = None
    ) -> SessionData:
        """
        세션 데이터를 생성합니다 (팩토리 메서드).

        모든 세션 생성이 이 메서드를 통해 이루어져야 합니다.
        metrics, history 등이 일관되게 초기화됩니다.

        Args:
            session_id: 세션 ID
            user_request: 사용자 요청 (기본값: "")
            initial_messages: 초기 메시지 목록 (기본값: None)

        Returns:
            SessionData: 생성된 세션 데이터

        Example:
            >>> manager = SessionManager()
            >>> session = manager.create_session_data(
            ...     session_id="test-001",
            ...     user_request="Implement feature X"
            ... )
            >>> print(session.session_id)
            test-001
        """
        # ConversationHistory 초기화
        history = ConversationHistory()
        if initial_messages:
            for msg in initial_messages:
                history.add_message(msg["role"], msg["content"])

        # Metrics 초기화
        metrics_repository = InMemoryMetricsRepository()
        metrics_collector = MetricsCollector(metrics_repository)

        # SessionData 생성 (log_lines는 deque, maxlen=10000)
        session_data = SessionData(
            session_id=session_id,
            history=history,
            log_lines=deque(maxlen=10000),
            start_time=time.time(),
            metrics_repository=metrics_repository,
            metrics_collector=metrics_collector,
            status=SessionStatus.COMPLETED,
            input_buffer=""
        )

        logger.debug(f"Created session data: {session_id}")
        return session_data

    # === Phase 1 - Step 1.1: 캡슐화 강화 메서드 ===

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        세션을 안전하게 가져옵니다.

        Args:
            session_id: 조회할 세션 ID

        Returns:
            세션 데이터 (없으면 None)

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> manager.start_session(config)
            >>> session = manager.get_session("test-001")
            >>> print(session is not None)
            True
        """
        return self._sessions.get(session_id)

    def update_session_input(self, session_id: str, input_text: str) -> bool:
        """
        세션의 입력 버퍼를 업데이트합니다.

        Args:
            session_id: 세션 ID
            input_text: 업데이트할 입력 텍스트

        Returns:
            bool: 성공 여부

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> manager.start_session(config)
            >>> success = manager.update_session_input("test-001", "Hello")
            >>> print(success)
            True
        """
        session = self.get_session(session_id)
        if session:
            session.input_buffer = input_text
            logger.debug(f"Updated input buffer for session {session_id}")
            return True
        logger.warning(f"Session not found: {session_id}")
        return False

    def add_message_to_session(self, session_id: str, role: str, content: str) -> bool:
        """
        세션에 메시지를 추가합니다.

        Args:
            session_id: 세션 ID
            role: 메시지 역할 (user, assistant, system)
            content: 메시지 내용

        Returns:
            추가 성공 여부

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> manager.start_session(config)
            >>> success = manager.add_message_to_session("test-001", "user", "Hello")
            >>> print(success)
            True
        """
        session = self.get_session(session_id)
        if session:
            session.history.add_message(role, content)
            logger.debug(f"Added {role} message to session {session_id}")
            return True
        logger.warning(f"Session not found: {session_id}")
        return False

    def replace_session_at_index(self, index: int, session_data: SessionData) -> bool:
        """
        특정 인덱스의 세션을 완전히 교체합니다.

        Args:
            index: 세션 인덱스
            session_data: 새로운 세션 데이터

        Returns:
            교체 성공 여부

        Example:
            >>> manager = SessionManager()
            >>> config = SessionConfig(session_id="test-001", user_request="Test")
            >>> manager.start_session(config)
            >>> new_session = SessionData(...)
            >>> success = manager.replace_session_at_index(0, new_session)
            >>> print(success)
            True
        """
        if index < 0 or index >= len(self._session_list):
            logger.error(f"Invalid session index: {index}")
            return False

        old_session = self._session_list[index]
        self._sync_session_index(index, old_session, session_data)

        logger.info(
            f"Replaced session at index {index}: "
            f"{old_session.session_id} -> {session_data.session_id}"
        )
        return True
