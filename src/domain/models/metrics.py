"""
성능 메트릭 모델

Agent 실행 성능 측정을 위한 도메인 모델
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class WorkerMetrics:
    """
    개별 Worker Agent 실행 메트릭

    Attributes:
        worker_name: Worker 이름 (예: "planner", "coder")
        task_description: 실행한 작업 설명
        start_time: 작업 시작 시각
        end_time: 작업 종료 시각
        execution_time: 실행 시간 (초)
        success: 성공 여부
        tokens_used: 사용한 토큰 수 (선택적)
        error_message: 에러 메시지 (실패 시)
    """
    worker_name: str
    task_description: str
    start_time: datetime
    end_time: datetime
    execution_time: float
    success: bool
    tokens_used: Optional[int] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "worker_name": self.worker_name,
            "task_description": self.task_description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "execution_time": self.execution_time,
            "success": self.success,
            "tokens_used": self.tokens_used,
            "error_message": self.error_message,
        }


@dataclass
class SessionMetrics:
    """
    세션 전체 메트릭

    Attributes:
        session_id: 세션 ID
        start_time: 세션 시작 시각
        end_time: 세션 종료 시각 (선택적)
        workers_metrics: Worker 실행 메트릭 리스트
        total_duration: 총 실행 시간 (초)
        total_tokens: 총 사용 토큰 수
    """
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    workers_metrics: List[WorkerMetrics] = field(default_factory=list)
    total_duration: float = 0.0
    total_tokens: int = 0

    def add_worker_metric(self, metric: WorkerMetrics) -> None:
        """Worker 메트릭 추가"""
        self.workers_metrics.append(metric)
        self.total_duration += metric.execution_time
        if metric.tokens_used:
            self.total_tokens += metric.tokens_used

    def get_success_rate(self) -> float:
        """성공률 계산 (0.0 ~ 100.0)"""
        if not self.workers_metrics:
            return 0.0

        successes = sum(1 for m in self.workers_metrics if m.success)
        return (successes / len(self.workers_metrics)) * 100.0

    def get_worker_statistics(self, worker_name: str) -> Dict[str, Any]:
        """특정 Worker의 통계 계산"""
        worker_metrics = [m for m in self.workers_metrics if m.worker_name == worker_name]

        if not worker_metrics:
            return {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "total_tokens": 0,
            }

        successes = sum(1 for m in worker_metrics if m.success)
        failures = len(worker_metrics) - successes
        avg_execution_time = sum(m.execution_time for m in worker_metrics) / len(worker_metrics)
        total_tokens = sum(m.tokens_used or 0 for m in worker_metrics)

        return {
            "attempts": len(worker_metrics),
            "successes": successes,
            "failures": failures,
            "success_rate": (successes / len(worker_metrics)) * 100.0,
            "avg_execution_time": avg_execution_time,
            "total_tokens": total_tokens,
        }

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "workers_metrics": [m.to_dict() for m in self.workers_metrics],
            "total_duration": self.total_duration,
            "total_tokens": self.total_tokens,
            "success_rate": self.get_success_rate(),
        }
