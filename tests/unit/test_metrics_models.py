"""
메트릭 모델 유닛 테스트

WorkerMetrics, SessionMetrics 모델의 정확성을 검증합니다.
"""

import pytest
from datetime import datetime, timedelta

from src.domain.models.metrics import WorkerMetrics, SessionMetrics


class TestWorkerMetrics:
    """WorkerMetrics 모델 테스트"""

    def test_create_worker_metrics_success(self):
        """성공 케이스: WorkerMetrics 생성"""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 10)

        metric = WorkerMetrics(
            worker_name="planner",
            task_description="계획 수립",
            start_time=start_time,
            end_time=end_time,
            execution_time=10.0,
            success=True,
            tokens_used=1000,
        )

        assert metric.worker_name == "planner"
        assert metric.task_description == "계획 수립"
        assert metric.start_time == start_time
        assert metric.end_time == end_time
        assert metric.execution_time == 10.0
        assert metric.success is True
        assert metric.tokens_used == 1000
        assert metric.error_message is None

    def test_create_worker_metrics_failure(self):
        """실패 케이스: WorkerMetrics 생성 (에러 메시지 포함)"""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 5)

        metric = WorkerMetrics(
            worker_name="coder",
            task_description="코드 작성",
            start_time=start_time,
            end_time=end_time,
            execution_time=5.0,
            success=False,
            error_message="Syntax error in generated code",
        )

        assert metric.worker_name == "coder"
        assert metric.success is False
        assert metric.error_message == "Syntax error in generated code"
        assert metric.tokens_used is None

    def test_worker_metrics_to_dict(self):
        """WorkerMetrics.to_dict() 메서드 테스트"""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 10)

        metric = WorkerMetrics(
            worker_name="tester",
            task_description="테스트 실행",
            start_time=start_time,
            end_time=end_time,
            execution_time=10.0,
            success=True,
            tokens_used=500,
        )

        result = metric.to_dict()

        assert result["worker_name"] == "tester"
        assert result["task_description"] == "테스트 실행"
        assert result["start_time"] == start_time.isoformat()
        assert result["end_time"] == end_time.isoformat()
        assert result["execution_time"] == 10.0
        assert result["success"] is True
        assert result["tokens_used"] == 500
        assert result["error_message"] is None

    def test_worker_metrics_optional_fields(self):
        """선택적 필드가 없는 경우 테스트"""
        metric = WorkerMetrics(
            worker_name="planner",
            task_description="분석",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 5),
            execution_time=5.0,
            success=True,
        )

        assert metric.tokens_used is None
        assert metric.error_message is None

        result = metric.to_dict()
        assert result["tokens_used"] is None
        assert result["error_message"] is None


class TestSessionMetrics:
    """SessionMetrics 모델 테스트"""

    def test_create_session_metrics(self):
        """SessionMetrics 생성 테스트"""
        session_id = "test_session_001"
        start_time = datetime(2024, 1, 1, 12, 0, 0)

        session = SessionMetrics(
            session_id=session_id,
            start_time=start_time,
        )

        assert session.session_id == session_id
        assert session.start_time == start_time
        assert session.end_time is None
        assert session.workers_metrics == []
        assert session.total_duration == 0.0
        assert session.total_tokens == 0

    def test_add_worker_metric(self):
        """Worker 메트릭 추가 테스트"""
        session = SessionMetrics(
            session_id="test_session_001",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        metric1 = WorkerMetrics(
            worker_name="planner",
            task_description="계획 수립",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            execution_time=10.0,
            success=True,
            tokens_used=1000,
        )

        metric2 = WorkerMetrics(
            worker_name="coder",
            task_description="코드 작성",
            start_time=datetime(2024, 1, 1, 12, 0, 10),
            end_time=datetime(2024, 1, 1, 12, 0, 25),
            execution_time=15.0,
            success=True,
            tokens_used=2000,
        )

        session.add_worker_metric(metric1)
        session.add_worker_metric(metric2)

        assert len(session.workers_metrics) == 2
        assert session.total_duration == 25.0
        assert session.total_tokens == 3000

    def test_get_success_rate_all_success(self):
        """성공률 계산 - 모두 성공"""
        session = SessionMetrics(
            session_id="test_session_001",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        for i in range(5):
            metric = WorkerMetrics(
                worker_name="planner",
                task_description=f"작업 {i}",
                start_time=datetime(2024, 1, 1, 12, 0, i * 10),
                end_time=datetime(2024, 1, 1, 12, 0, i * 10 + 10),
                execution_time=10.0,
                success=True,
            )
            session.add_worker_metric(metric)

        assert session.get_success_rate() == 100.0

    def test_get_success_rate_partial_success(self):
        """성공률 계산 - 일부 성공"""
        session = SessionMetrics(
            session_id="test_session_001",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        # 3개 성공, 2개 실패
        for i in range(3):
            metric = WorkerMetrics(
                worker_name="planner",
                task_description=f"성공 작업 {i}",
                start_time=datetime(2024, 1, 1, 12, 0, i * 10),
                end_time=datetime(2024, 1, 1, 12, 0, i * 10 + 10),
                execution_time=10.0,
                success=True,
            )
            session.add_worker_metric(metric)

        for i in range(2):
            metric = WorkerMetrics(
                worker_name="planner",
                task_description=f"실패 작업 {i}",
                start_time=datetime(2024, 1, 1, 12, 0, (i + 3) * 10),
                end_time=datetime(2024, 1, 1, 12, 0, (i + 3) * 10 + 10),
                execution_time=10.0,
                success=False,
            )
            session.add_worker_metric(metric)

        assert session.get_success_rate() == 60.0  # 3/5 * 100

    def test_get_success_rate_empty(self):
        """성공률 계산 - 메트릭 없음"""
        session = SessionMetrics(
            session_id="test_session_001",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        assert session.get_success_rate() == 0.0

    def test_get_worker_statistics_single_worker(self):
        """특정 Worker 통계 조회"""
        session = SessionMetrics(
            session_id="test_session_001",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        # planner worker: 2 성공, 1 실패
        session.add_worker_metric(
            WorkerMetrics(
                worker_name="planner",
                task_description="작업1",
                start_time=datetime(2024, 1, 1, 12, 0, 0),
                end_time=datetime(2024, 1, 1, 12, 0, 10),
                execution_time=10.0,
                success=True,
                tokens_used=1000,
            )
        )
        session.add_worker_metric(
            WorkerMetrics(
                worker_name="planner",
                task_description="작업2",
                start_time=datetime(2024, 1, 1, 12, 0, 10),
                end_time=datetime(2024, 1, 1, 12, 0, 30),
                execution_time=20.0,
                success=True,
                tokens_used=1500,
            )
        )
        session.add_worker_metric(
            WorkerMetrics(
                worker_name="planner",
                task_description="작업3",
                start_time=datetime(2024, 1, 1, 12, 0, 30),
                end_time=datetime(2024, 1, 1, 12, 0, 35),
                execution_time=5.0,
                success=False,
            )
        )

        stats = session.get_worker_statistics("planner")

        assert stats["attempts"] == 3
        assert stats["successes"] == 2
        assert stats["failures"] == 1
        assert stats["success_rate"] == pytest.approx(66.666, rel=0.01)
        assert stats["avg_execution_time"] == pytest.approx(11.666, rel=0.01)
        assert stats["total_tokens"] == 2500

    def test_get_worker_statistics_no_data(self):
        """존재하지 않는 Worker 통계 조회"""
        session = SessionMetrics(
            session_id="test_session_001",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        stats = session.get_worker_statistics("nonexistent_worker")

        assert stats["attempts"] == 0
        assert stats["successes"] == 0
        assert stats["failures"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_execution_time"] == 0.0
        assert stats["total_tokens"] == 0

    def test_get_worker_statistics_multiple_workers(self):
        """여러 Worker가 있을 때 특정 Worker 통계 조회"""
        session = SessionMetrics(
            session_id="test_session_001",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        # planner worker
        session.add_worker_metric(
            WorkerMetrics(
                worker_name="planner",
                task_description="계획",
                start_time=datetime(2024, 1, 1, 12, 0, 0),
                end_time=datetime(2024, 1, 1, 12, 0, 10),
                execution_time=10.0,
                success=True,
                tokens_used=1000,
            )
        )

        # coder worker
        session.add_worker_metric(
            WorkerMetrics(
                worker_name="coder",
                task_description="코딩",
                start_time=datetime(2024, 1, 1, 12, 0, 10),
                end_time=datetime(2024, 1, 1, 12, 0, 30),
                execution_time=20.0,
                success=True,
                tokens_used=2000,
            )
        )

        planner_stats = session.get_worker_statistics("planner")
        coder_stats = session.get_worker_statistics("coder")

        assert planner_stats["attempts"] == 1
        assert planner_stats["total_tokens"] == 1000
        assert coder_stats["attempts"] == 1
        assert coder_stats["total_tokens"] == 2000

    def test_session_metrics_to_dict(self):
        """SessionMetrics.to_dict() 메서드 테스트"""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 1, 0)

        session = SessionMetrics(
            session_id="test_session_001",
            start_time=start_time,
            end_time=end_time,
        )

        session.add_worker_metric(
            WorkerMetrics(
                worker_name="planner",
                task_description="계획",
                start_time=datetime(2024, 1, 1, 12, 0, 0),
                end_time=datetime(2024, 1, 1, 12, 0, 10),
                execution_time=10.0,
                success=True,
                tokens_used=1000,
            )
        )

        result = session.to_dict()

        assert result["session_id"] == "test_session_001"
        assert result["start_time"] == start_time.isoformat()
        assert result["end_time"] == end_time.isoformat()
        assert len(result["workers_metrics"]) == 1
        assert result["total_duration"] == 10.0
        assert result["total_tokens"] == 1000
        assert result["success_rate"] == 100.0

    def test_add_worker_metric_without_tokens(self):
        """토큰 정보가 없는 메트릭 추가"""
        session = SessionMetrics(
            session_id="test_session_001",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        metric = WorkerMetrics(
            worker_name="planner",
            task_description="계획",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            execution_time=10.0,
            success=True,
            tokens_used=None,
        )

        session.add_worker_metric(metric)

        assert session.total_tokens == 0
        assert session.total_duration == 10.0
