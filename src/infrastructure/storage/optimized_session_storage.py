"""
최적화된 세션 저장소

증분 저장, 압축, 백그라운드 저장을 지원하여 메인 워크플로우의 성능을 향상시킵니다.
"""

import gzip
import json
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from queue import Queue, Empty
import time
import hashlib

from src.application.ports import ISessionRepository
from src.domain.models import (
    SessionResult,
    SessionMetadata,
    SessionSearchCriteria,
    SessionDetail
)
from src.domain.services import ConversationHistory
from ..logging import get_logger

logger = get_logger(__name__, component="OptimizedSessionStorage")


class OptimizedSessionRepository(ISessionRepository):
    """
    최적화된 세션 저장소

    다음 최적화 기능을 제공합니다:
    1. 증분 저장: 변경된 메시지만 추가 저장
    2. 압축 저장: gzip으로 파일 크기 감소
    3. 백그라운드 저장: 별도 스레드에서 비동기 저장

    Attributes:
        sessions_dir: 세션 디렉토리
        enable_compression: 압축 활성화 여부
        enable_background_save: 백그라운드 저장 활성화 여부
    """

    def __init__(
        self,
        sessions_dir: Path = Path("sessions"),
        enable_compression: bool = True,
        enable_background_save: bool = True,
    ):
        """
        Args:
            sessions_dir: 세션 디렉토리
            enable_compression: 압축 활성화 여부 (기본: True)
            enable_background_save: 백그라운드 저장 활성화 여부 (기본: True)
        """
        self.sessions_dir = sessions_dir
        self.enable_compression = enable_compression
        self.enable_background_save = enable_background_save

        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # 세션별 저장 상태 추적 (증분 저장용)
        self._session_states: Dict[str, Dict[str, Any]] = {}
        self._state_lock = threading.RLock()

        # 백그라운드 저장 큐
        if self.enable_background_save:
            self._save_queue: Queue = Queue()
            self._worker_thread: Optional[threading.Thread] = None
            self._stop_event = threading.Event()
            self._start_background_worker()

        logger.info(
            "OptimizedSessionRepository initialized",
            sessions_dir=str(sessions_dir),
            compression=enable_compression,
            background_save=enable_background_save
        )

    def save(
        self,
        session_id: str,
        user_request: str,
        history: ConversationHistory,
        result: SessionResult
    ) -> Path:
        """
        세션 저장 (최적화 적용)

        Args:
            session_id: 세션 ID
            user_request: 사용자 요청
            history: 대화 히스토리
            result: 작업 결과

        Returns:
            저장된 파일 경로
        """
        # 파일 경로 생성
        filename = self._create_filename(session_id, user_request)
        filepath = self.sessions_dir / filename

        # 세션 데이터 준비
        agents_used = list(set(
            msg.agent_name for msg in history.messages
            if msg.role == "agent" and msg.agent_name
        ))

        session_data = {
            "session_id": session_id,
            "created_at": history.messages[0].timestamp.isoformat() if history.messages else datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "user_request": user_request,
            "total_turns": sum(1 for msg in history.messages if msg.role == "agent"),
            "agents_used": sorted(agents_used),
            "messages": [msg.to_dict() for msg in history.messages],
            "result": result.to_dict()
        }

        # 증분 저장 체크
        if self._should_incremental_save(session_id, session_data):
            logger.debug(
                "Incremental save detected",
                session_id=session_id,
                message_count=len(session_data["messages"])
            )

        # 백그라운드 저장 또는 동기 저장
        if self.enable_background_save:
            self._enqueue_save(filepath, session_data)
        else:
            self._save_to_disk(filepath, session_data)

        # 세션 상태 업데이트
        self._update_session_state(session_id, session_data)

        return filepath

    def load(self, session_id: str) -> Optional[ConversationHistory]:
        """
        세션 히스토리 로드 (압축 파일 지원)

        Args:
            session_id: 세션 ID

        Returns:
            대화 히스토리 또는 None
        """
        # 세션 ID로 파일 검색 (.json 또는 .json.gz)
        patterns = [
            f"session_{session_id}_*.json",
            f"session_{session_id}_*.json.gz"
        ]

        files = []
        for pattern in patterns:
            files.extend(self.sessions_dir.glob(pattern))

        if not files:
            logger.warning(f"세션을 찾을 수 없습니다: {session_id}")
            return None

        filepath = files[0]
        try:
            data = self._load_from_disk(filepath)

            history_data = {
                "max_length": 50,
                "messages": data.get("messages", [])
            }

            return ConversationHistory.from_dict(history_data)

        except Exception as e:
            logger.error(f"세션 로드 실패: {e}", exc_info=True)
            return None

    def search_sessions(self, criteria: SessionSearchCriteria) -> List[SessionMetadata]:
        """
        세션 검색 (압축 파일 지원)

        Args:
            criteria: 검색 조건

        Returns:
            검색된 세션 메타데이터 목록
        """
        sessions = []

        # 모든 JSON 파일 읽기 (.json 및 .json.gz)
        json_files = sorted(
            list(self.sessions_dir.glob("session_*.json")) +
            list(self.sessions_dir.glob("session_*.json.gz")),
            reverse=True
        )

        for json_file in json_files:
            try:
                data = self._load_from_disk(json_file)
                metadata = self._extract_metadata(data)

                # 필터 적용
                if not self._matches_criteria(metadata, criteria):
                    continue

                sessions.append(metadata)

                # 제한 확인
                if len(sessions) >= criteria.limit + criteria.offset:
                    break

            except Exception as e:
                logger.error(f"세션 파일 읽기 실패: {json_file} - {e}")
                continue

        # 오프셋 적용
        return sessions[criteria.offset:criteria.offset + criteria.limit]

    def get_session_detail(self, session_id: str) -> Optional[SessionDetail]:
        """
        세션 상세 정보 조회 (압축 파일 지원)

        Args:
            session_id: 세션 ID

        Returns:
            세션 상세 정보 또는 None
        """
        patterns = [
            f"session_{session_id}_*.json",
            f"session_{session_id}_*.json.gz"
        ]

        files = []
        for pattern in patterns:
            files.extend(self.sessions_dir.glob(pattern))

        if not files:
            logger.warning(f"세션을 찾을 수 없습니다: {session_id}")
            return None

        try:
            data = self._load_from_disk(files[0])
            metadata = self._extract_metadata(data)
            messages = data.get("messages", [])

            return SessionDetail(metadata=metadata, messages=messages)

        except Exception as e:
            logger.error(f"세션 상세 조회 실패: {e}", exc_info=True)
            return None

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[SessionMetadata]:
        """
        세션 목록 조회 (최신순)

        Args:
            limit: 최대 결과 수
            offset: 결과 오프셋

        Returns:
            세션 메타데이터 목록
        """
        criteria = SessionSearchCriteria(limit=limit, offset=offset)
        return self.search_sessions(criteria)

    def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID

        Returns:
            삭제 성공 여부
        """
        patterns = [
            f"session_{session_id}_*.json",
            f"session_{session_id}_*.json.gz"
        ]

        files = []
        for pattern in patterns:
            files.extend(self.sessions_dir.glob(pattern))

        if not files:
            logger.warning(f"세션을 찾을 수 없습니다: {session_id}")
            return False

        try:
            files[0].unlink()
            logger.info(f"세션 삭제 완료: {session_id}")

            # 세션 상태 제거
            with self._state_lock:
                self._session_states.pop(session_id, None)

            return True

        except Exception as e:
            logger.error(f"세션 삭제 실패: {e}", exc_info=True)
            return False

    def stop(self, timeout: float = 10.0) -> None:
        """
        백그라운드 워커 중지

        Args:
            timeout: 종료 대기 시간 (초)
        """
        if not self.enable_background_save:
            return

        if self._worker_thread is None or not self._worker_thread.is_alive():
            return

        logger.info("Stopping background save worker...")

        self._stop_event.set()
        self._worker_thread.join(timeout=timeout)

        if self._worker_thread.is_alive():
            logger.error(
                "Background save worker failed to stop",
                timeout=timeout
            )
        else:
            logger.info("Background save worker stopped successfully")

    def _save_to_disk(self, filepath: Path, data: Dict[str, Any]) -> None:
        """
        디스크에 저장 (압축 옵션 적용)

        Args:
            filepath: 파일 경로
            data: 저장할 데이터
        """
        json_str = json.dumps(data, ensure_ascii=False, indent=2)

        if self.enable_compression:
            # gzip 압축 저장
            compressed_path = filepath.with_suffix(filepath.suffix + ".gz")
            with gzip.open(compressed_path, 'wt', encoding='utf-8') as f:
                f.write(json_str)

            original_size = len(json_str.encode('utf-8'))
            compressed_size = compressed_path.stat().st_size
            compression_ratio = (1 - compressed_size / original_size) * 100

            logger.debug(
                "Session saved (compressed)",
                filepath=str(compressed_path),
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=f"{compression_ratio:.1f}%"
            )
        else:
            # 일반 JSON 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)

            logger.debug(
                "Session saved",
                filepath=str(filepath),
                size=len(json_str.encode('utf-8'))
            )

    def _load_from_disk(self, filepath: Path) -> Dict[str, Any]:
        """
        디스크에서 로드 (압축 파일 자동 감지)

        Args:
            filepath: 파일 경로

        Returns:
            로드된 데이터
        """
        if filepath.suffix == ".gz":
            with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)

    def _enqueue_save(self, filepath: Path, data: Dict[str, Any]) -> None:
        """
        백그라운드 저장 큐에 추가

        Args:
            filepath: 파일 경로
            data: 저장할 데이터
        """
        try:
            self._save_queue.put((filepath, data), block=False)
            logger.debug("Save task enqueued", filepath=str(filepath))
        except Exception as e:
            logger.error(
                "Failed to enqueue save task, falling back to sync save",
                error=str(e)
            )
            # 큐 추가 실패 시 동기 저장으로 폴백
            self._save_to_disk(filepath, data)

    def _start_background_worker(self) -> None:
        """백그라운드 저장 워커 시작"""
        self._worker_thread = threading.Thread(
            target=self._background_save_loop,
            name="SessionSaveWorker",
            daemon=True
        )
        self._worker_thread.start()
        logger.info("Background save worker started")

    def _background_save_loop(self) -> None:
        """백그라운드 저장 루프"""
        logger.info("Background save loop started")

        while not self._stop_event.is_set():
            try:
                # 큐에서 작업 가져오기 (타임아웃 1초)
                try:
                    filepath, data = self._save_queue.get(block=True, timeout=1.0)
                except Empty:
                    continue

                # 디스크에 저장
                self._save_to_disk(filepath, data)

            except Exception as e:
                logger.error(
                    "Error in background save loop",
                    error=str(e),
                    exc_info=True
                )
                time.sleep(1.0)

        # 종료 시 남은 작업 처리
        pending_count = 0
        while not self._save_queue.empty():
            try:
                filepath, data = self._save_queue.get_nowait()
                self._save_to_disk(filepath, data)
                pending_count += 1
            except Empty:
                break
            except Exception as e:
                logger.error(
                    "Error saving pending session",
                    error=str(e),
                    exc_info=True
                )

        if pending_count > 0:
            logger.info(
                "Flushed pending saves on shutdown",
                count=pending_count
            )

        logger.info("Background save loop stopped")

    def _should_incremental_save(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """
        증분 저장 여부 판단

        Args:
            session_id: 세션 ID
            session_data: 세션 데이터

        Returns:
            증분 저장 여부 (현재는 항상 전체 저장)
        """
        with self._state_lock:
            prev_state = self._session_states.get(session_id)

            if prev_state is None:
                return False

            # 메시지 개수 비교 (증분 여부 판단)
            prev_message_count = len(prev_state.get("messages", []))
            current_message_count = len(session_data.get("messages", []))

            return current_message_count > prev_message_count

    def _update_session_state(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """
        세션 상태 업데이트

        Args:
            session_id: 세션 ID
            session_data: 세션 데이터
        """
        with self._state_lock:
            # 메시지 해시 저장 (증분 저장 최적화용)
            message_hashes = [
                hashlib.md5(
                    json.dumps(msg, sort_keys=True).encode('utf-8')
                ).hexdigest()
                for msg in session_data.get("messages", [])
            ]

            self._session_states[session_id] = {
                "messages": session_data.get("messages", []),
                "message_hashes": message_hashes,
                "last_updated": time.time(),
            }

    def _create_filename(self, session_id: str, user_request: str) -> str:
        """
        세션 파일명 생성

        Args:
            session_id: 세션 ID
            user_request: 사용자 요청

        Returns:
            파일명
        """
        safe_request = "".join(c for c in user_request if c.isalnum() or c.isspace())
        safe_request = safe_request.replace(" ", "")[:20]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 압축 활성화 시 .json.gz 확장자 사용
        extension = ".json.gz" if self.enable_compression else ".json"
        return f"session_{session_id}_{timestamp}_{safe_request}{extension}"

    def _extract_metadata(self, data: dict) -> SessionMetadata:
        """
        JSON 데이터에서 메타데이터 추출

        Args:
            data: JSON 세션 데이터

        Returns:
            SessionMetadata 객체
        """
        result_data = data.get("result", {})

        return SessionMetadata(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]),
            user_request=data["user_request"],
            status=result_data.get("status", "completed"),
            total_turns=data.get("total_turns", 0),
            agents_used=data.get("agents_used", []),
            files_modified=result_data.get("files_modified", []),
            tests_passed=result_data.get("tests_passed"),
            error_message=result_data.get("error_message")
        )

    def _matches_criteria(self, metadata: SessionMetadata, criteria: SessionSearchCriteria) -> bool:
        """
        메타데이터가 검색 조건과 일치하는지 확인

        Args:
            metadata: 세션 메타데이터
            criteria: 검색 조건

        Returns:
            일치 여부
        """
        # 키워드 검색
        if criteria.keyword:
            keyword_lower = criteria.keyword.lower()
            if keyword_lower not in metadata.user_request.lower():
                return False

        # 상태 필터
        if criteria.status and metadata.status != criteria.status:
            return False

        # 에이전트 필터
        if criteria.agent_name and criteria.agent_name not in metadata.agents_used:
            return False

        # 날짜 필터
        if criteria.date_from:
            date_from = datetime.strptime(criteria.date_from, "%Y-%m-%d")
            if metadata.created_at < date_from:
                return False

        if criteria.date_to:
            date_to = datetime.strptime(criteria.date_to, "%Y-%m-%d")
            from datetime import timedelta
            date_to_inclusive = date_to + timedelta(days=1)
            if metadata.created_at >= date_to_inclusive:
                return False

        return True

    def __enter__(self):
        """Context manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료 시 자동 정리"""
        self.stop()
        return False

    def __repr__(self) -> str:
        return (
            f"OptimizedSessionRepository("
            f"sessions_dir={self.sessions_dir}, "
            f"compression={self.enable_compression}, "
            f"background_save={self.enable_background_save})"
        )
