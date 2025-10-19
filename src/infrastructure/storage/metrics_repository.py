"""
메트릭 저장소 구현

In-Memory 방식으로 메트릭 저장 (추후 파일/DB로 확장 가능)
"""

from typing import Dict, Optional, List
from datetime import datetime

from ...domain.ports import IMetricsRepository
from ...domain.models import WorkerMetrics, SessionMetrics


class InMemoryMetricsRepository(IMetricsRepository):
    """
    In-Memory 메트릭 저장소

    세션별로 메트릭을 메모리에 저장합니다.
    프로세스 종료 시 데이터가 사라지므로, 영구 저장이 필요하면 다른 구현체로 교체 가능
    """

    def __init__(self):
        """초기화"""
        # session_id -> SessionMetrics
        self._sessions: Dict[str, SessionMetrics] = {}

    def save_worker_metric(self, session_id: str, metric: WorkerMetrics) -> None:
        """
        Worker 메트릭 저장

        Args:
            session_id: 세션 ID
            metric: Worker 메트릭
        """
        if session_id not in self._sessions:
            # 새 세션 생성
            self._sessions[session_id] = SessionMetrics(
                session_id=session_id,
                start_time=datetime.now(),
            )

        session_metrics = self._sessions[session_id]
        session_metrics.add_worker_metric(metric)

    def get_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """
        세션 메트릭 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 메트릭 또는 None
        """
        return self._sessions.get(session_id)

    def get_all_sessions(self) -> List[str]:
        """
        모든 세션 ID 목록 조회

        Returns:
            세션 ID 리스트
        """
        return list(self._sessions.keys())

    def clear_session(self, session_id: str) -> None:
        """
        특정 세션 메트릭 삭제

        Args:
            session_id: 세션 ID
        """
        if session_id in self._sessions:
            del self._sessions[session_id]

    def clear_all(self) -> None:
        """모든 메트릭 삭제"""
        self._sessions.clear()
