"""
메트릭 저장소 포트

Domain Layer의 인터페이스 정의 - Clean Architecture의 의존성 역전 원칙(DIP) 준수
Infrastructure Layer가 이 인터페이스를 구현합니다.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from ..models import WorkerMetrics, SessionMetrics


class IMetricsRepository(ABC):
    """메트릭 저장소 인터페이스"""

    @abstractmethod
    def save_worker_metric(self, session_id: str, metric: WorkerMetrics) -> None:
        """
        Worker 메트릭 저장

        Args:
            session_id: 세션 ID
            metric: Worker 메트릭
        """
        pass

    @abstractmethod
    def get_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """
        세션 메트릭 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 메트릭 또는 None
        """
        pass

    @abstractmethod
    def get_all_sessions(self) -> List[str]:
        """
        모든 세션 ID 목록 조회

        Returns:
            세션 ID 리스트
        """
        pass

    @abstractmethod
    def clear_session(self, session_id: str) -> None:
        """
        특정 세션 메트릭 삭제

        Args:
            session_id: 세션 ID
        """
        pass

    @abstractmethod
    def clear_all(self) -> None:
        """모든 메트릭 삭제"""
        pass
