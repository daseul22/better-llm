"""
메트릭 저장소 유닛 테스트

InMemoryMetricsRepository의 정확성을 검증합니다.
"""

import pytest
from datetime import datetime

from src.domain.models.metrics import WorkerMetrics, SessionMetrics
from src.infrastructure.storage.metrics_repository import InMemoryMetricsRepository


class TestInMemoryMetricsRepository:
    """InMemoryMetricsRepository 테스트"""

    @pytest.fixture
    def repository(self):
        """Repository fixture"""
        return InMemoryMetricsRepository()

    @pytest.fixture
    def sample_worker_metric(self):
        """샘플 WorkerMetrics fixture"""
        return WorkerMetrics(
            worker_name="planner",
            task_description="계획 수립",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            execution_time=10.0,
            success=True,
            tokens_used=1000,
        )

    def test_save_worker_metric_new_session(self, repository, sample_worker_metric):
        """새 세션에 Worker 메트릭 저장"""
        session_id = "test_session_001"

        repository.save_worker_metric(session_id, sample_worker_metric)

        session_metrics = repository.get_session_metrics(session_id)
        assert session_metrics is not None
        assert session_metrics.session_id == session_id
        assert len(session_metrics.workers_metrics) == 1
        assert session_metrics.workers_metrics[0].worker_name == "planner"

    def test_save_worker_metric_existing_session(self, repository, sample_worker_metric):
        """기존 세션에 Worker 메트릭 추가"""
        session_id = "test_session_002"

        # 첫 번째 메트릭
        repository.save_worker_metric(session_id, sample_worker_metric)

        # 두 번째 메트릭
        metric2 = WorkerMetrics(
            worker_name="coder",
            task_description="코드 작성",
            start_time=datetime(2024, 1, 1, 12, 0, 10),
            end_time=datetime(2024, 1, 1, 12, 0, 30),
            execution_time=20.0,
            success=True,
            tokens_used=2000,
        )
        repository.save_worker_metric(session_id, metric2)

        session_metrics = repository.get_session_metrics(session_id)
        assert len(session_metrics.workers_metrics) == 2
        assert session_metrics.total_duration == 30.0
        assert session_metrics.total_tokens == 3000

    def test_get_session_metrics_nonexistent(self, repository):
        """존재하지 않는 세션 조회"""
        session_metrics = repository.get_session_metrics("nonexistent_session")
        assert session_metrics is None

    def test_get_all_sessions(self, repository, sample_worker_metric):
        """모든 세션 ID 조회"""
        # 여러 세션 생성
        session_ids = ["session_1", "session_2", "session_3"]

        for session_id in session_ids:
            repository.save_worker_metric(session_id, sample_worker_metric)

        all_sessions = repository.get_all_sessions()
        assert len(all_sessions) == 3
        assert set(all_sessions) == set(session_ids)

    def test_get_all_sessions_empty(self, repository):
        """빈 저장소에서 세션 조회"""
        all_sessions = repository.get_all_sessions()
        assert all_sessions == []

    def test_clear_session(self, repository, sample_worker_metric):
        """특정 세션 삭제"""
        session_id = "test_session_003"

        repository.save_worker_metric(session_id, sample_worker_metric)
        assert repository.get_session_metrics(session_id) is not None

        repository.clear_session(session_id)
        assert repository.get_session_metrics(session_id) is None

    def test_clear_session_nonexistent(self, repository):
        """존재하지 않는 세션 삭제 시 에러 없음"""
        # 에러 없이 실행되어야 함
        repository.clear_session("nonexistent_session")

    def test_clear_all(self, repository, sample_worker_metric):
        """모든 세션 삭제"""
        # 여러 세션 생성
        for i in range(5):
            repository.save_worker_metric(f"session_{i}", sample_worker_metric)

        assert len(repository.get_all_sessions()) == 5

        repository.clear_all()

        assert len(repository.get_all_sessions()) == 0
        for i in range(5):
            assert repository.get_session_metrics(f"session_{i}") is None

    def test_session_start_time_auto_creation(self, repository, sample_worker_metric):
        """세션 자동 생성 시 start_time이 설정되는지 확인"""
        session_id = "test_session_004"

        repository.save_worker_metric(session_id, sample_worker_metric)

        session_metrics = repository.get_session_metrics(session_id)
        assert session_metrics.start_time is not None
        assert isinstance(session_metrics.start_time, datetime)

    def test_multiple_sessions_isolation(self, repository):
        """여러 세션이 서로 독립적인지 확인"""
        metric1 = WorkerMetrics(
            worker_name="planner",
            task_description="계획1",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            execution_time=10.0,
            success=True,
            tokens_used=1000,
        )

        metric2 = WorkerMetrics(
            worker_name="coder",
            task_description="코딩2",
            start_time=datetime(2024, 1, 1, 12, 0, 10),
            end_time=datetime(2024, 1, 1, 12, 0, 30),
            execution_time=20.0,
            success=True,
            tokens_used=2000,
        )

        repository.save_worker_metric("session_A", metric1)
        repository.save_worker_metric("session_B", metric2)

        session_a = repository.get_session_metrics("session_A")
        session_b = repository.get_session_metrics("session_B")

        assert len(session_a.workers_metrics) == 1
        assert len(session_b.workers_metrics) == 1
        assert session_a.total_tokens == 1000
        assert session_b.total_tokens == 2000

    def test_worker_metric_accumulation(self, repository):
        """같은 Worker가 여러 번 실행될 때 메트릭 누적 확인"""
        session_id = "test_session_005"

        # Planner 3회 실행
        for i in range(3):
            metric = WorkerMetrics(
                worker_name="planner",
                task_description=f"계획 {i + 1}",
                start_time=datetime(2024, 1, 1, 12, 0, i * 10),
                end_time=datetime(2024, 1, 1, 12, 0, i * 10 + 10),
                execution_time=10.0,
                success=True,
                tokens_used=1000,
            )
            repository.save_worker_metric(session_id, metric)

        session_metrics = repository.get_session_metrics(session_id)
        assert len(session_metrics.workers_metrics) == 3
        assert session_metrics.total_duration == 30.0
        assert session_metrics.total_tokens == 3000

        # Worker 통계 확인
        planner_stats = session_metrics.get_worker_statistics("planner")
        assert planner_stats["attempts"] == 3
        assert planner_stats["successes"] == 3
