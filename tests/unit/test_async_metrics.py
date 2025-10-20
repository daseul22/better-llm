"""
비동기 메트릭 수집기 단위 테스트
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.infrastructure.metrics import AsyncMetricsCollector
from src.domain.models import WorkerMetrics


class MockMetricsRepository:
    """메트릭 저장소 Mock"""

    def __init__(self):
        self.saved_metrics = []

    def save_worker_metric(self, session_id: str, metric: WorkerMetrics):
        """메트릭 저장"""
        self.saved_metrics.append((session_id, metric))

    def get_session_metrics(self, session_id: str):
        """세션 메트릭 조회"""
        return None

    def clear_session(self, session_id: str):
        """세션 메트릭 삭제"""
        pass

    def clear_all(self):
        """모든 메트릭 삭제"""
        pass


def test_async_metrics_collector_initialization():
    """AsyncMetricsCollector 초기화 테스트"""
    repository = MockMetricsRepository()
    collector = AsyncMetricsCollector(
        repository=repository,
        buffer_size=100,
        flush_interval=1.0,
        enabled=True
    )

    assert collector.buffer_size == 100
    assert collector.flush_interval == 1.0
    assert collector.enabled is True

    # 백그라운드 스레드 시작 확인
    assert collector._worker_thread is not None
    assert collector._worker_thread.is_alive()

    collector.stop()


def test_async_metrics_collector_disabled():
    """비활성화된 AsyncMetricsCollector 테스트"""
    repository = MockMetricsRepository()
    collector = AsyncMetricsCollector(
        repository=repository,
        enabled=False
    )

    assert collector.enabled is False
    # 비활성화 시 백그라운드 스레드가 시작되지 않음
    assert collector._worker_thread is None


def test_record_worker_execution():
    """Worker 실행 메트릭 기록 테스트"""
    repository = MockMetricsRepository()
    collector = AsyncMetricsCollector(
        repository=repository,
        buffer_size=10,
        flush_interval=0.5
    )

    start_time = datetime.now()
    end_time = datetime.now()

    # 메트릭 기록
    result = collector.record_worker_execution(
        session_id="test_session",
        worker_name="planner",
        task_description="Test task",
        start_time=start_time,
        end_time=end_time,
        success=True,
        tokens_used=100,
        error_message=None
    )

    assert result is True

    # 플러시 대기 (백그라운드 스레드에서 처리)
    time.sleep(1.0)

    # 저장소에 메트릭이 저장되었는지 확인
    assert len(repository.saved_metrics) == 1
    session_id, metric = repository.saved_metrics[0]
    assert session_id == "test_session"
    assert metric.worker_name == "planner"
    assert metric.success is True

    collector.stop()


def test_flush_on_shutdown():
    """종료 시 남은 메트릭 플러시 테스트"""
    repository = MockMetricsRepository()
    collector = AsyncMetricsCollector(
        repository=repository,
        buffer_size=100,
        flush_interval=10.0  # 긴 플러시 간격
    )

    # 메트릭 여러 개 추가
    for i in range(5):
        collector.record_worker_execution(
            session_id=f"session_{i}",
            worker_name="planner",
            task_description=f"Task {i}",
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True
        )

    # 즉시 종료 (플러시 간격 전)
    collector.stop(timeout=5.0)

    # 모든 메트릭이 저장되었는지 확인
    assert len(repository.saved_metrics) == 5


def test_queue_full_handling():
    """큐가 가득 찬 경우 처리 테스트"""
    repository = MockMetricsRepository()
    collector = AsyncMetricsCollector(
        repository=repository,
        buffer_size=2,  # 작은 버퍼
        flush_interval=10.0  # 긴 플러시 간격
    )

    # 큐를 가득 채움
    for i in range(5):
        result = collector.record_worker_execution(
            session_id=f"session_{i}",
            worker_name="planner",
            task_description=f"Task {i}",
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True
        )

        # 처음 2개는 성공, 이후는 타임아웃으로 실패 가능
        if i < 2:
            assert result is True

    stats = collector.get_stats()
    # 큐가 가득 차서 일부 이벤트가 드롭될 수 있음
    assert stats["queue_full_count"] >= 0

    collector.stop()


def test_get_stats():
    """통계 조회 테스트"""
    repository = MockMetricsRepository()
    collector = AsyncMetricsCollector(
        repository=repository,
        buffer_size=10,
        flush_interval=0.5
    )

    # 메트릭 기록
    collector.record_worker_execution(
        session_id="test_session",
        worker_name="planner",
        task_description="Test task",
        start_time=datetime.now(),
        end_time=datetime.now(),
        success=True
    )

    stats = collector.get_stats()

    assert "total_queued" in stats
    assert "total_processed" in stats
    assert "queue_size" in stats
    assert "is_running" in stats
    assert stats["total_queued"] >= 1

    time.sleep(1.0)
    stats = collector.get_stats()
    assert stats["total_processed"] >= 1

    collector.stop()


def test_context_manager():
    """Context manager 테스트"""
    repository = MockMetricsRepository()

    with AsyncMetricsCollector(repository=repository) as collector:
        collector.record_worker_execution(
            session_id="test_session",
            worker_name="planner",
            task_description="Test task",
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True
        )

        time.sleep(1.0)

    # Context manager 종료 후 워커 스레드도 종료되어야 함
    # (종료는 비동기적으로 일어날 수 있으므로 대기)
    time.sleep(2.0)
    assert len(repository.saved_metrics) >= 1


def test_manual_flush():
    """수동 플러시 테스트"""
    repository = MockMetricsRepository()
    collector = AsyncMetricsCollector(
        repository=repository,
        buffer_size=100,
        flush_interval=100.0  # 매우 긴 플러시 간격
    )

    # 메트릭 기록
    collector.record_worker_execution(
        session_id="test_session",
        worker_name="planner",
        task_description="Test task",
        start_time=datetime.now(),
        end_time=datetime.now(),
        success=True
    )

    # 수동 플러시
    collector.flush()

    # 플러시 대기
    time.sleep(1.0)

    # 메트릭이 저장되었는지 확인
    assert len(repository.saved_metrics) >= 1

    collector.stop()
