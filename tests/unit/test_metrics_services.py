"""
메트릭 서비스 유닛 테스트

MetricsCollector, MetricsReporter 서비스의 정확성을 검증합니다.
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from src.domain.models.metrics import WorkerMetrics, SessionMetrics
from src.domain.services.metrics_collector import MetricsCollector
from src.domain.services.metrics_reporter import MetricsReporter
from src.infrastructure.storage.metrics_repository import InMemoryMetricsRepository


class TestMetricsCollector:
    """MetricsCollector 서비스 테스트"""

    @pytest.fixture
    def repository(self):
        """InMemoryMetricsRepository fixture"""
        return InMemoryMetricsRepository()

    @pytest.fixture
    def collector(self, repository):
        """MetricsCollector fixture"""
        return MetricsCollector(repository)

    def test_record_worker_execution_success(self, collector):
        """Worker 실행 메트릭 기록 - 성공 케이스"""
        session_id = "test_session_001"
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 10)

        metric = collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획 수립",
            start_time=start_time,
            end_time=end_time,
            success=True,
            tokens_used=1000,
        )

        assert metric.worker_name == "planner"
        assert metric.task_description == "계획 수립"
        assert metric.execution_time == 10.0
        assert metric.success is True
        assert metric.tokens_used == 1000

        # 저장소에 저장되었는지 확인
        session_metrics = collector.get_session_summary(session_id)
        assert session_metrics is not None
        assert len(session_metrics.workers_metrics) == 1

    def test_record_worker_execution_failure(self, collector):
        """Worker 실행 메트릭 기록 - 실패 케이스"""
        session_id = "test_session_002"
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 5)

        metric = collector.record_worker_execution(
            session_id=session_id,
            worker_name="coder",
            task_description="코드 작성",
            start_time=start_time,
            end_time=end_time,
            success=False,
            error_message="Syntax error",
        )

        assert metric.success is False
        assert metric.error_message == "Syntax error"
        assert metric.execution_time == 5.0

    def test_record_multiple_workers(self, collector):
        """여러 Worker 메트릭 기록"""
        session_id = "test_session_003"

        # Planner
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            success=True,
            tokens_used=1000,
        )

        # Coder
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="coder",
            task_description="코딩",
            start_time=datetime(2024, 1, 1, 12, 0, 10),
            end_time=datetime(2024, 1, 1, 12, 0, 30),
            success=True,
            tokens_used=2000,
        )

        # Tester
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="tester",
            task_description="테스트",
            start_time=datetime(2024, 1, 1, 12, 0, 30),
            end_time=datetime(2024, 1, 1, 12, 0, 40),
            success=True,
            tokens_used=500,
        )

        session_metrics = collector.get_session_summary(session_id)
        assert len(session_metrics.workers_metrics) == 3
        assert session_metrics.total_duration == 40.0  # 10 + 20 + 10
        assert session_metrics.total_tokens == 3500

    def test_get_session_summary_nonexistent(self, collector):
        """존재하지 않는 세션 조회"""
        summary = collector.get_session_summary("nonexistent_session")
        assert summary is None

    def test_get_worker_statistics(self, collector):
        """특정 Worker 통계 조회"""
        session_id = "test_session_004"

        # Planner 2회 실행 (1 성공, 1 실패)
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획1",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            success=True,
            tokens_used=1000,
        )

        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획2",
            start_time=datetime(2024, 1, 1, 12, 0, 10),
            end_time=datetime(2024, 1, 1, 12, 0, 15),
            success=False,
            error_message="Failed",
        )

        stats = collector.get_worker_statistics(session_id, "planner")

        assert stats["attempts"] == 2
        assert stats["successes"] == 1
        assert stats["failures"] == 1
        assert stats["success_rate"] == 50.0
        assert stats["avg_execution_time"] == 7.5
        assert stats["total_tokens"] == 1000

    def test_get_worker_statistics_nonexistent_session(self, collector):
        """존재하지 않는 세션의 Worker 통계 조회"""
        stats = collector.get_worker_statistics("nonexistent_session", "planner")

        assert stats["attempts"] == 0
        assert stats["successes"] == 0
        assert stats["failures"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_execution_time"] == 0.0
        assert stats["total_tokens"] == 0

    def test_get_all_workers_statistics(self, collector):
        """모든 Worker 통계 조회"""
        session_id = "test_session_005"

        # Planner
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            success=True,
            tokens_used=1000,
        )

        # Coder
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="coder",
            task_description="코딩",
            start_time=datetime(2024, 1, 1, 12, 0, 10),
            end_time=datetime(2024, 1, 1, 12, 0, 30),
            success=True,
            tokens_used=2000,
        )

        all_stats = collector.get_all_workers_statistics(session_id)

        assert "planner" in all_stats
        assert "coder" in all_stats
        assert all_stats["planner"]["attempts"] == 1
        assert all_stats["coder"]["attempts"] == 1

    def test_get_all_workers_statistics_empty_session(self, collector):
        """메트릭이 없는 세션의 통계 조회"""
        all_stats = collector.get_all_workers_statistics("nonexistent_session")
        assert all_stats == {}

    def test_clear_session_metrics(self, collector):
        """특정 세션 메트릭 삭제"""
        session_id = "test_session_006"

        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            success=True,
        )

        assert collector.get_session_summary(session_id) is not None

        collector.clear_session_metrics(session_id)

        assert collector.get_session_summary(session_id) is None

    def test_clear_all_metrics(self, collector):
        """모든 메트릭 삭제"""
        # 여러 세션 생성
        for i in range(3):
            collector.record_worker_execution(
                session_id=f"session_{i}",
                worker_name="planner",
                task_description="계획",
                start_time=datetime(2024, 1, 1, 12, 0, 0),
                end_time=datetime(2024, 1, 1, 12, 0, 10),
                success=True,
            )

        # 모든 세션이 존재하는지 확인
        for i in range(3):
            assert collector.get_session_summary(f"session_{i}") is not None

        # 전체 삭제
        collector.clear_all_metrics()

        # 모든 세션이 삭제되었는지 확인
        for i in range(3):
            assert collector.get_session_summary(f"session_{i}") is None


class TestMetricsReporter:
    """MetricsReporter 서비스 테스트"""

    @pytest.fixture
    def sample_session_metrics(self):
        """샘플 SessionMetrics fixture"""
        session = SessionMetrics(
            session_id="test_session_001",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 1, 0),
        )

        # Planner (성공)
        session.add_worker_metric(
            WorkerMetrics(
                worker_name="planner",
                task_description="계획 수립 작업",
                start_time=datetime(2024, 1, 1, 12, 0, 0),
                end_time=datetime(2024, 1, 1, 12, 0, 10),
                execution_time=10.0,
                success=True,
                tokens_used=1000,
            )
        )

        # Coder (성공)
        session.add_worker_metric(
            WorkerMetrics(
                worker_name="coder",
                task_description="코드 작성 작업",
                start_time=datetime(2024, 1, 1, 12, 0, 10),
                end_time=datetime(2024, 1, 1, 12, 0, 30),
                execution_time=20.0,
                success=True,
                tokens_used=2000,
            )
        )

        # Tester (실패)
        session.add_worker_metric(
            WorkerMetrics(
                worker_name="tester",
                task_description="테스트 실행 작업",
                start_time=datetime(2024, 1, 1, 12, 0, 30),
                end_time=datetime(2024, 1, 1, 12, 0, 35),
                execution_time=5.0,
                success=False,
                error_message="Test failed",
            )
        )

        return session

    def test_generate_text_report(self, sample_session_metrics):
        """텍스트 리포트 생성 테스트"""
        report = MetricsReporter.generate_text_report(sample_session_metrics)

        assert "Agent 성능 메트릭 리포트" in report
        assert "test_session_001" in report
        assert "총 소요 시간: 35.00초" in report
        assert "총 토큰 사용량: 3000" in report
        assert "PLANNER" in report
        assert "CODER" in report
        assert "TESTER" in report
        assert "✅" in report  # 성공 아이콘
        assert "❌" in report  # 실패 아이콘

    def test_generate_json_report(self, sample_session_metrics):
        """JSON 리포트 생성 테스트"""
        report = MetricsReporter.generate_json_report(sample_session_metrics)

        # JSON 파싱 가능한지 확인
        data = json.loads(report)

        assert data["session_id"] == "test_session_001"
        assert data["total_duration"] == 35.0
        assert data["total_tokens"] == 3000
        assert len(data["workers_metrics"]) == 3
        assert "worker_statistics" in data
        assert "planner" in data["worker_statistics"]
        assert "coder" in data["worker_statistics"]
        assert "tester" in data["worker_statistics"]

    def test_generate_markdown_report(self, sample_session_metrics):
        """Markdown 리포트 생성 테스트"""
        report = MetricsReporter.generate_markdown_report(sample_session_metrics)

        assert "# 📊 Agent 성능 메트릭 리포트" in report
        assert "## 세션 정보" in report
        assert "## Worker별 통계" in report
        assert "## 개별 실행 기록" in report
        assert "| Worker | 시도 | 성공 | 실패 | 성공률 | 평균 시간 | 토큰 |" in report
        assert "test_session_001" in report

    def test_save_text_report(self, sample_session_metrics, tmp_path):
        """텍스트 리포트 파일 저장 테스트"""
        output_path = tmp_path / "reports"

        filepath = MetricsReporter.save_report(
            sample_session_metrics, output_path, format="text"
        )

        assert filepath.exists()
        assert filepath.name == "test_session_001_metrics.txt"

        content = filepath.read_text(encoding="utf-8")
        assert "Agent 성능 메트릭 리포트" in content

    def test_save_json_report(self, sample_session_metrics, tmp_path):
        """JSON 리포트 파일 저장 테스트"""
        output_path = tmp_path / "reports"

        filepath = MetricsReporter.save_report(
            sample_session_metrics, output_path, format="json"
        )

        assert filepath.exists()
        assert filepath.name == "test_session_001_metrics.json"

        content = filepath.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["session_id"] == "test_session_001"

    def test_save_markdown_report(self, sample_session_metrics, tmp_path):
        """Markdown 리포트 파일 저장 테스트"""
        output_path = tmp_path / "reports"

        filepath = MetricsReporter.save_report(
            sample_session_metrics, output_path, format="markdown"
        )

        assert filepath.exists()
        assert filepath.name == "test_session_001_metrics.md"

        content = filepath.read_text(encoding="utf-8")
        assert "# 📊 Agent 성능 메트릭 리포트" in content

    def test_save_report_invalid_format(self, sample_session_metrics, tmp_path):
        """잘못된 형식으로 리포트 저장 시 에러"""
        output_path = tmp_path / "reports"

        with pytest.raises(ValueError, match="지원하지 않는 형식"):
            MetricsReporter.save_report(
                sample_session_metrics, output_path, format="invalid"
            )

    def test_save_report_creates_directory(self, sample_session_metrics, tmp_path):
        """디렉토리가 없을 때 자동 생성"""
        output_path = tmp_path / "non_existent" / "reports"

        assert not output_path.exists()

        filepath = MetricsReporter.save_report(
            sample_session_metrics, output_path, format="text"
        )

        assert output_path.exists()
        assert filepath.exists()
