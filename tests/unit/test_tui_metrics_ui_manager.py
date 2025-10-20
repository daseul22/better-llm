"""MetricsUIManager 단위 테스트."""

import pytest
from datetime import datetime
from collections import deque

from src.presentation.tui.managers.metrics_ui_manager import (
    MetricsUIManager,
    MetricEntry,
)


class TestMetricEntry:
    """MetricEntry 테스트."""

    def test_create_metric_entry(self):
        """메트릭 항목 생성 테스트."""
        timestamp = datetime(2025, 1, 1, 12, 0, 0)
        entry = MetricEntry(
            name="test_metric",
            value=100,
            timestamp=timestamp,
            unit="ms"
        )

        assert entry.name == "test_metric"
        assert entry.value == 100
        assert entry.timestamp == timestamp
        assert entry.unit == "ms"

    def test_metric_entry_without_unit(self):
        """단위 없는 메트릭 항목 테스트."""
        timestamp = datetime.now()
        entry = MetricEntry(
            name="counter",
            value=42,
            timestamp=timestamp
        )

        assert entry.name == "counter"
        assert entry.value == 42
        assert entry.unit is None

    def test_metric_entry_str_with_unit(self):
        """단위가 있는 메트릭 항목 문자열 변환 테스트."""
        timestamp = datetime(2025, 1, 1, 12, 0, 0)
        entry = MetricEntry(
            name="latency",
            value=50,
            timestamp=timestamp,
            unit="ms"
        )

        result = str(entry)
        assert "latency" in result
        assert "50" in result
        assert "ms" in result
        assert "12:00:00" in result

    def test_metric_entry_str_without_unit(self):
        """단위가 없는 메트릭 항목 문자열 변환 테스트."""
        timestamp = datetime(2025, 1, 1, 14, 30, 45)
        entry = MetricEntry(
            name="count",
            value=10,
            timestamp=timestamp
        )

        result = str(entry)
        assert "count" in result
        assert "10" in result
        assert "14:30:45" in result


class TestMetricsUIManager:
    """MetricsUIManager 테스트."""

    @pytest.fixture
    def manager(self):
        """MetricsUIManager 픽스처."""
        return MetricsUIManager(max_history_size=10)

    def test_initialization(self, manager):
        """초기화 테스트."""
        assert manager._max_history_size == 10
        assert len(manager._metrics) == 0
        assert len(manager._metric_history) == 0

    def test_render_dashboard_empty(self, manager):
        """빈 대시보드 렌더링 테스트."""
        result = manager.render_dashboard({})
        assert "No metrics available" in result

    def test_render_dashboard_with_metrics(self, manager):
        """메트릭이 있는 대시보드 렌더링 테스트."""
        metrics = {
            "total_turns": 10,
            "tokens_used": 5000,
            "success_rate": 0.95
        }

        result = manager.render_dashboard(metrics)

        assert "Metrics Dashboard" in result
        assert "total_turns" in result
        assert "tokens_used" in result
        assert "success_rate" in result

    def test_format_metric_value_float(self, manager):
        """float 메트릭 포맷팅 테스트."""
        result = manager._format_metric_value("rate", 0.956789)
        assert result == "0.96"

    def test_format_metric_value_int(self, manager):
        """int 메트릭 포맷팅 테스트."""
        result = manager._format_metric_value("count", 1234567)
        assert "1,234,567" in result

    def test_format_metric_value_string(self, manager):
        """string 메트릭 포맷팅 테스트."""
        result = manager._format_metric_value("status", "active")
        assert result == "active"

    def test_update_metric(self, manager):
        """메트릭 업데이트 테스트."""
        manager.update_metric("counter", 10)

        assert manager.get_current_metric("counter") == 10
        assert "counter" in manager._metric_history
        assert len(manager._metric_history["counter"]) == 1

    def test_update_metric_multiple_times(self, manager):
        """메트릭 여러 번 업데이트 테스트."""
        manager.update_metric("value", 1)
        manager.update_metric("value", 2)
        manager.update_metric("value", 3)

        assert manager.get_current_metric("value") == 3
        assert len(manager._metric_history["value"]) == 3

    def test_get_metric_history(self, manager):
        """메트릭 히스토리 조회 테스트."""
        manager.update_metric("tokens", 100)
        manager.update_metric("tokens", 200)
        manager.update_metric("tokens", 300)

        history = manager.get_metric_history("tokens")

        # 최신 순으로 반환
        assert len(history) == 3
        assert history[0] == 300
        assert history[1] == 200
        assert history[2] == 100

    def test_get_metric_history_with_limit(self, manager):
        """제한된 개수로 메트릭 히스토리 조회 테스트."""
        for i in range(5):
            manager.update_metric("count", i)

        history = manager.get_metric_history("count", limit=3)

        assert len(history) == 3
        assert history[0] == 4  # 최신
        assert history[1] == 3
        assert history[2] == 2

    def test_get_metric_history_nonexistent(self, manager):
        """존재하지 않는 메트릭 히스토리 조회 테스트."""
        history = manager.get_metric_history("nonexistent")
        assert history == []

    def test_get_current_metric(self, manager):
        """현재 메트릭 값 조회 테스트."""
        manager.update_metric("score", 95)

        assert manager.get_current_metric("score") == 95
        assert manager.get_current_metric("nonexistent") is None

    def test_get_all_metrics(self, manager):
        """모든 메트릭 조회 테스트."""
        manager.update_metric("metric1", 10)
        manager.update_metric("metric2", 20)
        manager.update_metric("metric3", 30)

        all_metrics = manager.get_all_metrics()

        assert len(all_metrics) == 3
        assert all_metrics["metric1"] == 10
        assert all_metrics["metric2"] == 20
        assert all_metrics["metric3"] == 30

    def test_clear_metric(self, manager):
        """메트릭 삭제 테스트."""
        manager.update_metric("temp", 50)
        assert manager.get_current_metric("temp") == 50

        manager.clear_metric("temp")
        assert manager.get_current_metric("temp") is None
        assert "temp" not in manager._metric_history

    def test_clear_all_metrics(self, manager):
        """모든 메트릭 삭제 테스트."""
        manager.update_metric("metric1", 10)
        manager.update_metric("metric2", 20)

        manager.clear_all_metrics()

        assert len(manager.get_all_metrics()) == 0
        assert len(manager._metric_history) == 0

    def test_set_metric_unit(self, manager):
        """메트릭 단위 설정 테스트."""
        manager.set_metric_unit("latency", "ms")
        manager.update_metric("latency", 100)

        # 히스토리에서 단위 확인
        assert manager._metric_units["latency"] == "ms"

    def test_set_metric_formatter(self, manager):
        """메트릭 포맷터 설정 테스트."""
        manager.set_metric_formatter("percentage", lambda x: f"{x * 100:.1f}%")

        result = manager._format_metric_value("percentage", 0.855)
        assert result == "85.5%"

    def test_set_metric_formatter_error_handling(self, manager):
        """메트릭 포맷터 에러 처리 테스트."""
        # 에러를 발생시키는 포맷터
        manager.set_metric_formatter("bad", lambda x: x / 0)

        # 에러가 발생해도 기본 포맷팅으로 대체
        result = manager._format_metric_value("bad", 100)
        assert result == "100"

    def test_list_metrics(self, manager):
        """메트릭 목록 조회 테스트."""
        manager.update_metric("a", 1)
        manager.update_metric("b", 2)
        manager.update_metric("c", 3)

        metrics = manager.list_metrics()

        assert len(metrics) == 3
        assert "a" in metrics
        assert "b" in metrics
        assert "c" in metrics

    def test_get_metric_count(self, manager):
        """메트릭 개수 조회 테스트."""
        assert manager.get_metric_count() == 0

        manager.update_metric("m1", 1)
        assert manager.get_metric_count() == 1

        manager.update_metric("m2", 2)
        assert manager.get_metric_count() == 2

    def test_increment_metric(self, manager):
        """메트릭 증가 테스트."""
        manager.update_metric("counter", 0)

        manager.increment_metric("counter")
        assert manager.get_current_metric("counter") == 1

        manager.increment_metric("counter", 5)
        assert manager.get_current_metric("counter") == 6

    def test_increment_metric_nonexistent(self, manager):
        """존재하지 않는 메트릭 증가 테스트."""
        manager.increment_metric("new_counter")
        assert manager.get_current_metric("new_counter") == 1

    def test_increment_metric_non_numeric(self, manager):
        """숫자가 아닌 메트릭 증가 테스트 (에러 처리)."""
        manager.update_metric("text", "hello")

        # 숫자가 아니므로 증가하지 않음
        manager.increment_metric("text")
        assert manager.get_current_metric("text") == "hello"

    def test_decrement_metric(self, manager):
        """메트릭 감소 테스트."""
        manager.update_metric("counter", 10)

        manager.decrement_metric("counter")
        assert manager.get_current_metric("counter") == 9

        manager.decrement_metric("counter", 3)
        assert manager.get_current_metric("counter") == 6

    def test_decrement_metric_nonexistent(self, manager):
        """존재하지 않는 메트릭 감소 테스트."""
        manager.decrement_metric("new_counter")
        assert manager.get_current_metric("new_counter") == -1

    def test_decrement_metric_non_numeric(self, manager):
        """숫자가 아닌 메트릭 감소 테스트 (에러 처리)."""
        manager.update_metric("text", "world")

        # 숫자가 아니므로 감소하지 않음
        manager.decrement_metric("text")
        assert manager.get_current_metric("text") == "world"

    def test_get_metric_summary(self, manager):
        """메트릭 요약 통계 테스트."""
        manager.update_metric("values", 10)
        manager.update_metric("values", 20)
        manager.update_metric("values", 30)

        summary = manager.get_metric_summary("values")

        assert summary is not None
        assert summary["min"] == 10
        assert summary["max"] == 30
        assert summary["avg"] == 20.0
        assert summary["count"] == 3
        assert summary["latest"] == 30

    def test_get_metric_summary_nonexistent(self, manager):
        """존재하지 않는 메트릭 요약 조회 테스트."""
        summary = manager.get_metric_summary("nonexistent")
        assert summary is None

    def test_get_metric_summary_non_numeric(self, manager):
        """숫자가 아닌 메트릭 요약 조회 테스트."""
        manager.update_metric("text", "hello")
        manager.update_metric("text", "world")

        summary = manager.get_metric_summary("text")
        assert summary is None

    def test_render_metric_chart(self, manager):
        """메트릭 차트 렌더링 테스트."""
        for i in range(10):
            manager.update_metric("value", i * 10)

        chart = manager.render_metric_chart("value", width=20, height=5)

        assert "value" in chart
        assert len(chart) > 0
        assert "Max:" in chart
        assert "Min:" in chart

    def test_render_metric_chart_nonexistent(self, manager):
        """존재하지 않는 메트릭 차트 렌더링 테스트."""
        chart = manager.render_metric_chart("nonexistent")
        assert "No data" in chart

    def test_render_metric_chart_non_numeric(self, manager):
        """숫자가 아닌 메트릭 차트 렌더링 테스트."""
        manager.update_metric("text", "hello")
        chart = manager.render_metric_chart("text")
        assert "No numeric data" in chart

    def test_render_metric_chart_same_values(self, manager):
        """같은 값으로 차트 렌더링 테스트 (range = 0)."""
        for _ in range(5):
            manager.update_metric("constant", 50)

        chart = manager.render_metric_chart("constant", width=10, height=5)

        assert "constant" in chart
        assert len(chart) > 0

    def test_history_max_size(self):
        """히스토리 최대 크기 제한 테스트."""
        manager = MetricsUIManager(max_history_size=5)

        # 10개 추가하면 최근 5개만 유지
        for i in range(10):
            manager.update_metric("limited", i)

        history = manager.get_metric_history("limited")

        assert len(history) == 5
        # 최신 5개: 9, 8, 7, 6, 5
        assert history[0] == 9
        assert history[4] == 5

    def test_multiple_metrics_independence(self, manager):
        """여러 메트릭의 독립성 테스트."""
        manager.update_metric("metric_a", 100)
        manager.update_metric("metric_b", 200)

        manager.increment_metric("metric_a")
        manager.decrement_metric("metric_b")

        assert manager.get_current_metric("metric_a") == 101
        assert manager.get_current_metric("metric_b") == 199

    def test_render_dashboard_updates_internal_state(self, manager):
        """대시보드 렌더링이 내부 상태를 업데이트하는지 테스트."""
        metrics = {
            "new_metric": 42
        }

        manager.render_dashboard(metrics)

        # render_dashboard가 _metrics를 업데이트해야 함
        assert manager.get_current_metric("new_metric") == 42
