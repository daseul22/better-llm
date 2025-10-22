"""
메트릭 수집 서비스

Worker Agent 실행 메트릭 수집 및 통계 조회
"""

from datetime import datetime
from typing import Optional, Dict, Any

from ..models import WorkerMetrics, SessionMetrics
from ..ports import IMetricsRepository


class MetricsCollector:
    """
    메트릭 수집 및 조회 서비스

    Attributes:
        repository: 메트릭 저장소
    """

    def __init__(self, repository: IMetricsRepository):
        """
        Args:
            repository: 메트릭 저장소 인터페이스
        """
        self.repository = repository

    def record_worker_execution(
        self,
        session_id: str,
        worker_name: str,
        task_description: str,
        start_time: datetime,
        end_time: datetime,
        success: bool,
        tokens_used: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        cache_read_tokens: Optional[int] = None,
        cache_creation_tokens: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> WorkerMetrics:
        """
        Worker 실행 메트릭 기록

        Args:
            session_id: 세션 ID
            worker_name: Worker 이름
            task_description: 작업 설명
            start_time: 시작 시각
            end_time: 종료 시각
            success: 성공 여부
            tokens_used: 사용한 토큰 수 (선택적, 하위 호환성)
            input_tokens: 입력 토큰 수 (선택적)
            output_tokens: 출력 토큰 수 (선택적)
            cache_read_tokens: 캐시 읽기 토큰 수 (선택적)
            cache_creation_tokens: 캐시 생성 토큰 수 (선택적)
            error_message: 에러 메시지 (선택적)

        Returns:
            생성된 WorkerMetrics 객체
        """
        execution_time = (end_time - start_time).total_seconds()

        metric = WorkerMetrics(
            worker_name=worker_name,
            task_description=task_description,
            start_time=start_time,
            end_time=end_time,
            execution_time=execution_time,
            success=success,
            tokens_used=tokens_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_creation_tokens=cache_creation_tokens,
            error_message=error_message,
        )

        self.repository.save_worker_metric(session_id, metric)

        return metric

    def get_session_summary(self, session_id: str) -> Optional[SessionMetrics]:
        """
        세션 전체 메트릭 요약 조회

        Args:
            session_id: 세션 ID

        Returns:
            SessionMetrics 또는 None
        """
        return self.repository.get_session_metrics(session_id)

    def get_worker_statistics(
        self, session_id: str, worker_name: str
    ) -> Dict[str, Any]:
        """
        특정 Worker의 통계 조회

        Args:
            session_id: 세션 ID
            worker_name: Worker 이름

        Returns:
            Worker 통계 딕셔너리
        """
        session_metrics = self.repository.get_session_metrics(session_id)

        if not session_metrics:
            return {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "total_tokens": 0,
            }

        return session_metrics.get_worker_statistics(worker_name)

    def get_all_workers_statistics(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        """
        모든 Worker의 통계 조회

        Args:
            session_id: 세션 ID

        Returns:
            Worker별 통계 딕셔너리
        """
        session_metrics = self.repository.get_session_metrics(session_id)

        if not session_metrics:
            return {}

        # 세션에 등장한 모든 unique worker_name 추출
        worker_names = set(m.worker_name for m in session_metrics.workers_metrics)

        statistics = {}
        for worker_name in worker_names:
            statistics[worker_name] = session_metrics.get_worker_statistics(worker_name)

        return statistics

    def clear_session_metrics(self, session_id: str) -> None:
        """
        특정 세션의 메트릭 삭제

        Args:
            session_id: 세션 ID
        """
        self.repository.clear_session(session_id)

    def clear_all_metrics(self) -> None:
        """모든 메트릭 삭제"""
        self.repository.clear_all()
