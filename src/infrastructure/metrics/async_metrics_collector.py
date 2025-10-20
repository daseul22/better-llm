"""
비동기 메트릭 수집기

백그라운드 스레드에서 메트릭을 비동기적으로 수집하여 메인 워크플로우 블로킹을 방지합니다.
"""

import asyncio
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from queue import Queue, Empty, Full
from dataclasses import dataclass, asdict
import time

from ...domain.models import WorkerMetrics
from ...domain.ports import IMetricsRepository
from ..logging import get_logger

logger = get_logger(__name__, component="AsyncMetricsCollector")


@dataclass
class MetricEvent:
    """
    메트릭 이벤트 데이터 클래스

    Attributes:
        session_id: 세션 ID
        worker_name: Worker 이름
        task_description: 작업 설명
        start_time: 시작 시각
        end_time: 종료 시각
        success: 성공 여부
        tokens_used: 사용한 토큰 수
        error_message: 에러 메시지
    """
    session_id: str
    worker_name: str
    task_description: str
    start_time: datetime
    end_time: datetime
    success: bool
    tokens_used: Optional[int] = None
    error_message: Optional[str] = None


class AsyncMetricsCollector:
    """
    비동기 메트릭 수집기

    백그라운드 스레드에서 메트릭을 버퍼링하고 배치 처리하여
    메인 워크플로우의 성능 영향을 최소화합니다.

    Attributes:
        repository: 메트릭 저장소
        buffer_size: 버퍼 크기 (최대 큐 크기)
        flush_interval: 플러시 간격 (초)
        enabled: 수집 활성화 여부
    """

    def __init__(
        self,
        repository: IMetricsRepository,
        buffer_size: int = 1000,
        flush_interval: float = 5.0,
        enabled: bool = True
    ):
        """
        Args:
            repository: 메트릭 저장소 인터페이스
            buffer_size: 버퍼 크기 (기본: 1000)
            flush_interval: 플러시 간격 (초, 기본: 5.0)
            enabled: 수집 활성화 여부 (기본: True)
        """
        self.repository = repository
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.enabled = enabled

        # 메트릭 큐 (스레드 세이프)
        self._queue: Queue[MetricEvent] = Queue(maxsize=buffer_size)

        # 백그라운드 스레드
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._flush_event = threading.Event()

        # 집계 메트릭을 위한 Lock (Critical 2 수정)
        self._aggregation_lock = threading.Lock()
        self._aggregated_metrics: Dict[str, Dict[str, Any]] = {}

        # 통계
        self._stats = {
            "total_queued": 0,
            "total_processed": 0,
            "total_failed": 0,
            "queue_full_count": 0,
            "dropped_metrics_count": 0,  # Critical 1: 드랍된 메트릭 카운트 추가
            "last_flush_time": None,
        }

        # 자동 시작
        if self.enabled:
            self.start()

        logger.info(
            "AsyncMetricsCollector initialized",
            buffer_size=buffer_size,
            flush_interval=flush_interval,
            enabled=enabled
        )

    def start(self) -> None:
        """백그라운드 워커 스레드 시작"""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            logger.warning("AsyncMetricsCollector already running")
            return

        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="AsyncMetricsWorker",
            daemon=True
        )
        self._worker_thread.start()

        logger.info("AsyncMetricsCollector background worker started")

    def stop(self, timeout: float = 10.0) -> None:
        """
        백그라운드 워커 스레드 중지 및 남은 메트릭 플러시 (Critical 3 수정)

        Args:
            timeout: 종료 대기 시간 (초, 기본: 10.0)
        """
        if self._worker_thread is None or not self._worker_thread.is_alive():
            logger.warning("AsyncMetricsCollector not running")
            return

        logger.info("Stopping AsyncMetricsCollector...")

        # 중지 신호 전송
        self._stop_event.set()

        # 즉시 플러시 요청 (남은 메트릭 강제 플러시)
        self._flush_event.set()

        # 워커 스레드 종료 대기 (타임아웃 적용)
        self._worker_thread.join(timeout=timeout)

        if self._worker_thread.is_alive():
            logger.error(
                "AsyncMetricsCollector failed to stop within timeout",
                timeout=timeout,
                remaining_queue_size=self._queue.qsize()
            )
        else:
            logger.info(
                "AsyncMetricsCollector stopped successfully",
                final_stats=self.get_stats()
            )

    def record_worker_execution(
        self,
        session_id: str,
        worker_name: str,
        task_description: str,
        start_time: datetime,
        end_time: datetime,
        success: bool,
        tokens_used: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Worker 실행 메트릭 기록 (비동기) - Critical 1 수정: 큐 오버플로우 방지

        Args:
            session_id: 세션 ID
            worker_name: Worker 이름
            task_description: 작업 설명
            start_time: 시작 시각
            end_time: 종료 시각
            success: 성공 여부
            tokens_used: 사용한 토큰 수
            error_message: 에러 메시지

        Returns:
            큐 추가 성공 여부
        """
        if not self.enabled:
            return True

        event = MetricEvent(
            session_id=session_id,
            worker_name=worker_name,
            task_description=task_description,
            start_time=start_time,
            end_time=end_time,
            success=success,
            tokens_used=tokens_used,
            error_message=error_message,
        )

        try:
            # 논블로킹 큐 추가 시도 (타임아웃 0.1초)
            self._queue.put(event, block=True, timeout=0.1)
            self._stats["total_queued"] += 1
            return True

        except Full:
            # Critical 1: 큐가 가득 찬 경우 오래된 메트릭 제거 후 재시도
            self._stats["queue_full_count"] += 1

            try:
                # 오래된 메트릭 제거
                old_event = self._queue.get_nowait()
                self._stats["dropped_metrics_count"] += 1

                # 새 메트릭 추가
                self._queue.put_nowait(event)
                self._stats["total_queued"] += 1

                logger.warning(
                    "Metrics queue full, dropped oldest metric",
                    worker_name=worker_name,
                    dropped_worker=old_event.worker_name,
                    queue_size=self._queue.qsize(),
                    total_dropped=self._stats["dropped_metrics_count"]
                )
                return True

            except (Empty, Full) as e:
                # 재시도도 실패한 경우
                logger.error(
                    "Failed to add metric to queue after retry",
                    worker_name=worker_name,
                    error=str(e)
                )
                return False

        except Exception as e:
            # 기타 예외
            logger.error(
                "Unexpected error adding metric to queue",
                worker_name=worker_name,
                error=str(e),
                exc_info=True
            )
            return False

    def flush(self) -> None:
        """즉시 플러시 요청"""
        self._flush_event.set()
        logger.debug("Flush requested")

    def get_stats(self) -> Dict[str, Any]:
        """
        수집기 통계 조회

        Returns:
            통계 딕셔너리
        """
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "is_running": self._worker_thread is not None and self._worker_thread.is_alive(),
        }

    def _aggregate_metrics(self, metric: MetricEvent) -> None:
        """
        메트릭 집계 (스레드 안전) - Critical 2 수정: Race Condition 방지

        Args:
            metric: 집계할 메트릭 이벤트
        """
        key = metric.worker_name
        execution_time = (metric.end_time - metric.start_time).total_seconds()

        # Lock을 사용하여 스레드 안전성 보장
        with self._aggregation_lock:
            if key not in self._aggregated_metrics:
                self._aggregated_metrics[key] = {
                    "count": 0,
                    "total_time": 0.0,
                    "min_time": float('inf'),
                    "max_time": float('-inf'),
                    "success_count": 0,
                    "failure_count": 0,
                    "total_tokens": 0,
                }

            # 집계 데이터 업데이트
            agg = self._aggregated_metrics[key]
            agg["count"] += 1
            agg["total_time"] += execution_time
            agg["min_time"] = min(agg["min_time"], execution_time)
            agg["max_time"] = max(agg["max_time"], execution_time)

            if metric.success:
                agg["success_count"] += 1
            else:
                agg["failure_count"] += 1

            if metric.tokens_used:
                agg["total_tokens"] += metric.tokens_used

    def get_aggregated_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        집계된 메트릭 조회 (스레드 안전) - Critical 2 수정

        Returns:
            Worker별 집계 메트릭 딕셔너리
        """
        with self._aggregation_lock:
            # 평균 계산을 포함한 복사본 반환
            result = {}
            for worker_name, agg in self._aggregated_metrics.items():
                result[worker_name] = {
                    **agg,
                    "avg_time": agg["total_time"] / agg["count"] if agg["count"] > 0 else 0.0,
                    "success_rate": (
                        agg["success_count"] / agg["count"] if agg["count"] > 0 else 0.0
                    ),
                }
            return result

    def _worker_loop(self) -> None:
        """
        백그라운드 워커 루프

        주기적으로 큐에서 메트릭을 꺼내 저장소에 기록합니다.
        """
        logger.info("AsyncMetrics worker loop started")

        last_flush = time.time()
        batch: List[MetricEvent] = []

        while not self._stop_event.is_set():
            try:
                # 큐에서 이벤트 가져오기 (타임아웃 1초)
                try:
                    event = self._queue.get(block=True, timeout=1.0)
                    batch.append(event)
                except Empty:
                    # 큐가 비어있으면 계속 대기
                    pass

                # 플러시 조건 체크
                current_time = time.time()
                should_flush = (
                    self._flush_event.is_set() or
                    (current_time - last_flush >= self.flush_interval) or
                    len(batch) >= 100  # 배치 크기 제한
                )

                if should_flush and batch:
                    self._flush_batch(batch)
                    batch.clear()
                    last_flush = current_time
                    self._flush_event.clear()

            except Exception as e:
                logger.error(
                    "Error in worker loop",
                    error=str(e),
                    exc_info=True
                )
                # 에러가 발생해도 계속 실행
                time.sleep(1.0)

        # 종료 시 남은 배치 플러시
        if batch:
            logger.info(
                "Flushing remaining metrics on shutdown",
                batch_size=len(batch)
            )
            self._flush_batch(batch)

        logger.info("AsyncMetrics worker loop stopped")

    def _flush_batch(self, batch: List[MetricEvent]) -> None:
        """
        배치를 저장소에 플러시 및 집계 메트릭 업데이트

        Args:
            batch: 메트릭 이벤트 리스트
        """
        if not batch:
            return

        logger.debug(f"Flushing batch of {len(batch)} metrics")

        success_count = 0
        fail_count = 0

        for event in batch:
            try:
                # WorkerMetrics 객체 생성
                execution_time = (event.end_time - event.start_time).total_seconds()

                metric = WorkerMetrics(
                    worker_name=event.worker_name,
                    task_description=event.task_description,
                    start_time=event.start_time,
                    end_time=event.end_time,
                    execution_time=execution_time,
                    success=event.success,
                    tokens_used=event.tokens_used,
                    error_message=event.error_message,
                )

                # 저장소에 저장
                self.repository.save_worker_metric(event.session_id, metric)
                success_count += 1

                # 집계 메트릭 업데이트 (Critical 2: 스레드 안전하게)
                self._aggregate_metrics(event)

            except Exception as e:
                fail_count += 1
                logger.error(
                    "Failed to save metric",
                    worker_name=event.worker_name,
                    error=str(e),
                    exc_info=True
                )

        # 통계 업데이트
        self._stats["total_processed"] += success_count
        self._stats["total_failed"] += fail_count
        self._stats["last_flush_time"] = datetime.now().isoformat()

        logger.debug(
            "Batch flush completed",
            success=success_count,
            failed=fail_count
        )

    def __enter__(self):
        """Context manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료 시 자동 정리"""
        self.stop()
        return False

    def __repr__(self) -> str:
        return (
            f"AsyncMetricsCollector(buffer_size={self.buffer_size}, "
            f"flush_interval={self.flush_interval}, enabled={self.enabled})"
        )
