"""
메트릭 수집 통합 테스트

실제 메트릭 수집 플로우를 엔드투엔드로 검증합니다.
"""

import pytest
import json
from datetime import datetime
from pathlib import Path

from src.domain.models.metrics import WorkerMetrics, SessionMetrics
from src.domain.services.metrics_collector import MetricsCollector
from src.domain.services.metrics_reporter import MetricsReporter
from src.infrastructure.storage.metrics_repository import InMemoryMetricsRepository


class TestMetricsCollectionFlow:
    """메트릭 수집 플로우 통합 테스트"""

    @pytest.fixture
    def metrics_system(self):
        """메트릭 시스템 fixture (repository + collector + reporter)"""
        repository = InMemoryMetricsRepository()
        collector = MetricsCollector(repository)
        reporter = MetricsReporter()

        return {
            "repository": repository,
            "collector": collector,
            "reporter": reporter,
        }

    def test_full_workflow_single_worker(self, metrics_system):
        """전체 워크플로우 - 단일 Worker 실행"""
        collector = metrics_system["collector"]
        reporter = metrics_system["reporter"]
        session_id = "integration_test_001"

        # 1. Worker 실행 메트릭 기록
        metric = collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="요구사항 분석 및 계획 수립",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 15),
            success=True,
            tokens_used=1500,
        )

        # 2. 메트릭 검증
        assert metric.worker_name == "planner"
        assert metric.execution_time == 15.0
        assert metric.success is True

        # 3. 세션 요약 조회
        summary = collector.get_session_summary(session_id)
        assert summary is not None
        assert len(summary.workers_metrics) == 1
        assert summary.total_duration == 15.0
        assert summary.total_tokens == 1500

        # 4. 리포트 생성
        text_report = reporter.generate_text_report(summary)
        assert "planner" in text_report.lower()
        assert "15.00초" in text_report

    def test_full_workflow_multiple_workers(self, metrics_system):
        """전체 워크플로우 - 여러 Worker 순차 실행"""
        collector = metrics_system["collector"]
        reporter = metrics_system["reporter"]
        session_id = "integration_test_002"

        # 1. Planner 실행
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="요구사항 분석",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            success=True,
            tokens_used=1000,
        )

        # 2. Coder 실행
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="coder",
            task_description="기능 구현",
            start_time=datetime(2024, 1, 1, 12, 0, 10),
            end_time=datetime(2024, 1, 1, 12, 0, 40),
            success=True,
            tokens_used=3000,
        )

        # 3. Tester 실행
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="tester",
            task_description="테스트 실행",
            start_time=datetime(2024, 1, 1, 12, 0, 40),
            end_time=datetime(2024, 1, 1, 12, 0, 50),
            success=True,
            tokens_used=500,
        )

        # 4. 세션 요약 검증
        summary = collector.get_session_summary(session_id)
        assert len(summary.workers_metrics) == 3
        assert summary.total_duration == 50.0
        assert summary.total_tokens == 4500
        assert summary.get_success_rate() == 100.0

        # 5. Worker별 통계 검증
        all_stats = collector.get_all_workers_statistics(session_id)
        assert len(all_stats) == 3
        assert all_stats["planner"]["attempts"] == 1
        assert all_stats["coder"]["attempts"] == 1
        assert all_stats["tester"]["attempts"] == 1

    def test_workflow_with_failures(self, metrics_system):
        """실패 케이스를 포함한 워크플로우"""
        collector = metrics_system["collector"]
        session_id = "integration_test_003"

        # Planner 성공
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획 수립",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            success=True,
            tokens_used=1000,
        )

        # Coder 실패 (1차 시도)
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="coder",
            task_description="코드 작성 (1차)",
            start_time=datetime(2024, 1, 1, 12, 0, 10),
            end_time=datetime(2024, 1, 1, 12, 0, 30),
            success=False,
            error_message="Syntax error in generated code",
        )

        # Coder 성공 (2차 시도)
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="coder",
            task_description="코드 작성 (2차)",
            start_time=datetime(2024, 1, 1, 12, 0, 30),
            end_time=datetime(2024, 1, 1, 12, 0, 50),
            success=True,
            tokens_used=2500,
        )

        # 세션 요약 검증
        summary = collector.get_session_summary(session_id)
        assert len(summary.workers_metrics) == 3
        assert summary.get_success_rate() == pytest.approx(66.666, rel=0.01)

        # Coder 통계 검증
        coder_stats = collector.get_worker_statistics(session_id, "coder")
        assert coder_stats["attempts"] == 2
        assert coder_stats["successes"] == 1
        assert coder_stats["failures"] == 1
        assert coder_stats["success_rate"] == 50.0

    def test_workflow_with_retry_pattern(self, metrics_system):
        """재시도 패턴 워크플로우"""
        collector = metrics_system["collector"]
        session_id = "integration_test_004"

        # Planner가 3번 시도 (2 실패, 1 성공)
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획 수립 (1차 시도)",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 5),
            success=False,
            error_message="Insufficient context",
        )

        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획 수립 (2차 시도)",
            start_time=datetime(2024, 1, 1, 12, 0, 5),
            end_time=datetime(2024, 1, 1, 12, 0, 12),
            success=False,
            error_message="Plan too vague",
        )

        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획 수립 (3차 시도)",
            start_time=datetime(2024, 1, 1, 12, 0, 12),
            end_time=datetime(2024, 1, 1, 12, 0, 25),
            success=True,
            tokens_used=2000,
        )

        # 통계 검증
        planner_stats = collector.get_worker_statistics(session_id, "planner")
        assert planner_stats["attempts"] == 3
        assert planner_stats["successes"] == 1
        assert planner_stats["failures"] == 2
        assert planner_stats["success_rate"] == pytest.approx(33.333, rel=0.01)
        assert planner_stats["avg_execution_time"] == pytest.approx(8.333, rel=0.01)

    def test_report_generation_and_saving(self, metrics_system, tmp_path):
        """리포트 생성 및 저장 통합 테스트"""
        collector = metrics_system["collector"]
        reporter = metrics_system["reporter"]
        session_id = "integration_test_005"

        # 메트릭 수집
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            success=True,
            tokens_used=1000,
        )

        collector.record_worker_execution(
            session_id=session_id,
            worker_name="coder",
            task_description="코딩",
            start_time=datetime(2024, 1, 1, 12, 0, 10),
            end_time=datetime(2024, 1, 1, 12, 0, 30),
            success=True,
            tokens_used=2000,
        )

        # 세션 요약 조회
        summary = collector.get_session_summary(session_id)

        # 텍스트 리포트 저장
        text_path = reporter.save_report(summary, tmp_path, format="text")
        assert text_path.exists()
        text_content = text_path.read_text(encoding="utf-8")
        assert "Agent 성능 메트릭 리포트" in text_content

        # JSON 리포트 저장
        json_path = reporter.save_report(summary, tmp_path, format="json")
        assert json_path.exists()
        json_data = json.loads(json_path.read_text(encoding="utf-8"))
        assert json_data["session_id"] == session_id

        # Markdown 리포트 저장
        md_path = reporter.save_report(summary, tmp_path, format="markdown")
        assert md_path.exists()
        md_content = md_path.read_text(encoding="utf-8")
        assert "# 📊 Agent 성능 메트릭 리포트" in md_content

    def test_multiple_sessions_isolation(self, metrics_system):
        """여러 세션이 독립적으로 관리되는지 확인"""
        collector = metrics_system["collector"]

        # 세션 A
        collector.record_worker_execution(
            session_id="session_A",
            worker_name="planner",
            task_description="세션A 계획",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            success=True,
            tokens_used=1000,
        )

        # 세션 B
        collector.record_worker_execution(
            session_id="session_B",
            worker_name="coder",
            task_description="세션B 코딩",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 20),
            success=True,
            tokens_used=2000,
        )

        # 세션 A 검증
        summary_a = collector.get_session_summary("session_A")
        assert len(summary_a.workers_metrics) == 1
        assert summary_a.total_tokens == 1000

        # 세션 B 검증
        summary_b = collector.get_session_summary("session_B")
        assert len(summary_b.workers_metrics) == 1
        assert summary_b.total_tokens == 2000

    def test_clear_session_workflow(self, metrics_system):
        """세션 삭제 워크플로우"""
        collector = metrics_system["collector"]
        session_id = "integration_test_006"

        # 메트릭 기록
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            success=True,
        )

        assert collector.get_session_summary(session_id) is not None

        # 세션 삭제
        collector.clear_session_metrics(session_id)

        assert collector.get_session_summary(session_id) is None

    def test_realistic_development_workflow(self, metrics_system):
        """실제 개발 워크플로우 시뮬레이션"""
        collector = metrics_system["collector"]
        reporter = metrics_system["reporter"]
        session_id = "realistic_workflow_001"

        # 1. Planner: 요구사항 분석
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="사용자 요구사항 분석 및 작업 계획 수립",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 15),
            success=True,
            tokens_used=1800,
        )

        # 2. Coder: 코드 작성 (1차 시도 실패)
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="coder",
            task_description="기능 구현 (1차 시도)",
            start_time=datetime(2024, 1, 1, 12, 0, 15),
            end_time=datetime(2024, 1, 1, 12, 0, 45),
            success=False,
            error_message="Type error in implementation",
        )

        # 3. Planner: 오류 분석 및 재계획
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="오류 분석 및 수정 방향 제시",
            start_time=datetime(2024, 1, 1, 12, 0, 45),
            end_time=datetime(2024, 1, 1, 12, 0, 55),
            success=True,
            tokens_used=1200,
        )

        # 4. Coder: 코드 작성 (2차 시도 성공)
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="coder",
            task_description="기능 구현 (2차 시도, 수정)",
            start_time=datetime(2024, 1, 1, 12, 0, 55),
            end_time=datetime(2024, 1, 1, 12, 1, 25),
            success=True,
            tokens_used=3500,
        )

        # 5. Tester: 테스트 실행
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="tester",
            task_description="단위 테스트 및 통합 테스트 실행",
            start_time=datetime(2024, 1, 1, 12, 1, 25),
            end_time=datetime(2024, 1, 1, 12, 1, 40),
            success=True,
            tokens_used=800,
        )

        # 검증
        summary = collector.get_session_summary(session_id)
        assert len(summary.workers_metrics) == 5
        assert summary.get_success_rate() == 80.0  # 4/5 성공

        # Worker별 통계
        all_stats = collector.get_all_workers_statistics(session_id)

        # Planner: 2회 실행, 모두 성공
        assert all_stats["planner"]["attempts"] == 2
        assert all_stats["planner"]["successes"] == 2
        assert all_stats["planner"]["success_rate"] == 100.0

        # Coder: 2회 실행, 1회 성공
        assert all_stats["coder"]["attempts"] == 2
        assert all_stats["coder"]["successes"] == 1
        assert all_stats["coder"]["success_rate"] == 50.0

        # Tester: 1회 실행, 성공
        assert all_stats["tester"]["attempts"] == 1
        assert all_stats["tester"]["successes"] == 1

        # 리포트 생성
        text_report = reporter.generate_text_report(summary)
        assert "PLANNER" in text_report
        assert "CODER" in text_report
        assert "TESTER" in text_report
        assert "80.0%" in text_report  # 전체 성공률

    def test_zero_token_usage_handling(self, metrics_system):
        """토큰 사용량이 없는 경우 처리"""
        collector = metrics_system["collector"]
        session_id = "integration_test_007"

        # 토큰 정보 없이 메트릭 기록
        collector.record_worker_execution(
            session_id=session_id,
            worker_name="planner",
            task_description="계획",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 10),
            success=True,
            tokens_used=None,
        )

        collector.record_worker_execution(
            session_id=session_id,
            worker_name="coder",
            task_description="코딩",
            start_time=datetime(2024, 1, 1, 12, 0, 10),
            end_time=datetime(2024, 1, 1, 12, 0, 30),
            success=True,
            tokens_used=1000,
        )

        summary = collector.get_session_summary(session_id)
        assert summary.total_tokens == 1000  # planner의 None은 무시됨

        # Worker별 통계
        planner_stats = collector.get_worker_statistics(session_id, "planner")
        assert planner_stats["total_tokens"] == 0
