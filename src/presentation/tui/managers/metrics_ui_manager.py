"""
MetricsUIManager 모듈

메트릭 UI 관리 책임:
- 실시간 메트릭 대시보드 렌더링
- 메트릭 업데이트
- 메트릭 히스토리 관리
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import deque

from infrastructure.logging import get_logger

logger = get_logger(__name__, component="MetricsUIManager")


@dataclass
class MetricEntry:
    """
    메트릭 항목

    Attributes:
        name: 메트릭 이름
        value: 메트릭 값
        timestamp: 타임스탬프
        unit: 단위 (옵셔널)
    """
    name: str
    value: Any
    timestamp: datetime
    unit: Optional[str] = None

    def __str__(self) -> str:
        unit_str = f" {self.unit}" if self.unit else ""
        time_str = self.timestamp.strftime("%H:%M:%S")
        return f"[{time_str}] {self.name}: {self.value}{unit_str}"


class MetricsUIManager:
    """
    메트릭 UI 관리자

    실시간 메트릭 데이터를 대시보드 형식으로 렌더링하고 관리합니다.

    Example:
        >>> manager = MetricsUIManager()
        >>> metrics = {
        ...     "total_turns": 10,
        ...     "tokens_used": 5000,
        ...     "success_rate": 0.95
        ... }
        >>> dashboard = manager.render_dashboard(metrics)
        >>> manager.update_metric("total_turns", 11)
    """

    def __init__(self, max_history_size: int = 100) -> None:
        """
        MetricsUIManager 초기화

        Args:
            max_history_size: 각 메트릭별 최대 히스토리 크기 (기본값: 100)
        """
        self._metrics: Dict[str, Any] = {}
        self._metric_history: Dict[str, deque[MetricEntry]] = {}
        self._max_history_size = max_history_size
        self._metric_units: Dict[str, str] = {}
        self._metric_formatters: Dict[str, callable] = {}
        logger.info(f"MetricsUIManager initialized (max_history: {max_history_size})")

    def render_dashboard(self, metrics: Dict[str, Any]) -> str:
        """
        메트릭 데이터를 대시보드 형식으로 렌더링합니다.

        Args:
            metrics: 렌더링할 메트릭 딕셔너리

        Returns:
            렌더링된 대시보드 문자열

        Example:
            >>> manager = MetricsUIManager()
            >>> metrics = {"total_turns": 10, "tokens_used": 5000}
            >>> dashboard = manager.render_dashboard(metrics)
            >>> print(len(dashboard) > 0)
            True
        """
        if not metrics:
            return "No metrics available"

        # 메트릭을 현재 상태로 업데이트
        for name, value in metrics.items():
            self._metrics[name] = value

        # 대시보드 렌더링
        lines = ["=== Metrics Dashboard ===", ""]

        for name, value in sorted(metrics.items()):
            formatted_value = self._format_metric_value(name, value)
            unit = self._metric_units.get(name, "")
            unit_str = f" {unit}" if unit else ""

            lines.append(f"  {name}: {formatted_value}{unit_str}")

        lines.append("")
        dashboard = "\n".join(lines)

        logger.debug(f"Dashboard rendered with {len(metrics)} metrics")

        return dashboard

    def _format_metric_value(self, name: str, value: Any) -> str:
        """
        메트릭 값을 포맷팅합니다.

        Args:
            name: 메트릭 이름
            value: 메트릭 값

        Returns:
            포맷팅된 값 문자열
        """
        # 커스텀 포맷터 사용
        if name in self._metric_formatters:
            try:
                return self._metric_formatters[name](value)
            except Exception as e:
                logger.error(f"Error formatting metric {name}: {e}")
                return str(value)

        # 기본 포맷팅
        if isinstance(value, float):
            return f"{value:.2f}"
        elif isinstance(value, int):
            return f"{value:,}"
        else:
            return str(value)

    def update_metric(self, metric_name: str, value: Any) -> None:
        """
        메트릭을 업데이트하고 히스토리에 기록합니다.

        Args:
            metric_name: 메트릭 이름
            value: 새로운 값

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.update_metric("total_turns", 10)
            >>> manager.update_metric("total_turns", 11)
            >>> history = manager.get_metric_history("total_turns")
            >>> print(len(history))
            2
        """
        # 메트릭 업데이트
        self._metrics[metric_name] = value

        # 히스토리 초기화
        if metric_name not in self._metric_history:
            self._metric_history[metric_name] = deque(maxlen=self._max_history_size)

        # 히스토리에 추가
        entry = MetricEntry(
            name=metric_name,
            value=value,
            timestamp=datetime.now(),
            unit=self._metric_units.get(metric_name)
        )
        self._metric_history[metric_name].append(entry)

        logger.debug(f"Metric updated: {metric_name} = {value}")

    def get_metric_history(
        self,
        metric_name: str,
        limit: int = 100
    ) -> List[Any]:
        """
        메트릭 히스토리를 조회합니다.

        Args:
            metric_name: 메트릭 이름
            limit: 최대 반환 개수 (기본값: 100)

        Returns:
            메트릭 값 리스트 (최신순)

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.update_metric("tokens", 100)
            >>> manager.update_metric("tokens", 200)
            >>> history = manager.get_metric_history("tokens")
            >>> print(len(history))
            2
        """
        if metric_name not in self._metric_history:
            logger.warning(f"Metric not found: {metric_name}")
            return []

        entries = list(self._metric_history[metric_name])
        # 최신 순으로 정렬
        entries.sort(key=lambda x: x.timestamp, reverse=True)

        result = [entry.value for entry in entries[:limit]]
        logger.debug(f"Retrieved metric history: {metric_name} ({len(result)} entries)")

        return result

    def get_current_metric(self, metric_name: str) -> Optional[Any]:
        """
        현재 메트릭 값을 조회합니다.

        Args:
            metric_name: 메트릭 이름

        Returns:
            현재 메트릭 값 (없으면 None)

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.update_metric("tokens", 500)
            >>> value = manager.get_current_metric("tokens")
            >>> print(value)
            500
        """
        return self._metrics.get(metric_name)

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        모든 메트릭을 조회합니다.

        Returns:
            메트릭 딕셔너리

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.update_metric("turns", 10)
            >>> manager.update_metric("tokens", 500)
            >>> metrics = manager.get_all_metrics()
            >>> print(len(metrics))
            2
        """
        return self._metrics.copy()

    def clear_metric(self, metric_name: str) -> None:
        """
        특정 메트릭을 삭제합니다.

        Args:
            metric_name: 메트릭 이름

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.update_metric("tokens", 500)
            >>> manager.clear_metric("tokens")
            >>> value = manager.get_current_metric("tokens")
            >>> print(value)
            None
        """
        if metric_name in self._metrics:
            del self._metrics[metric_name]

        if metric_name in self._metric_history:
            del self._metric_history[metric_name]

        logger.info(f"Metric cleared: {metric_name}")

    def clear_all_metrics(self) -> None:
        """
        모든 메트릭을 삭제합니다.

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.update_metric("turns", 10)
            >>> manager.update_metric("tokens", 500)
            >>> manager.clear_all_metrics()
            >>> metrics = manager.get_all_metrics()
            >>> print(len(metrics))
            0
        """
        self._metrics.clear()
        self._metric_history.clear()
        logger.info("All metrics cleared")

    def set_metric_unit(self, metric_name: str, unit: str) -> None:
        """
        메트릭의 단위를 설정합니다.

        Args:
            metric_name: 메트릭 이름
            unit: 단위 (예: "tokens", "ms", "%")

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.set_metric_unit("tokens_used", "tokens")
            >>> manager.update_metric("tokens_used", 1000)
        """
        self._metric_units[metric_name] = unit
        logger.debug(f"Metric unit set: {metric_name} -> {unit}")

    def set_metric_formatter(
        self,
        metric_name: str,
        formatter: callable
    ) -> None:
        """
        메트릭의 포맷터를 설정합니다.

        Args:
            metric_name: 메트릭 이름
            formatter: 값을 문자열로 변환하는 함수

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.set_metric_formatter("success_rate", lambda x: f"{x*100:.1f}%")
            >>> manager.update_metric("success_rate", 0.95)
        """
        self._metric_formatters[metric_name] = formatter
        logger.debug(f"Metric formatter set: {metric_name}")

    def list_metrics(self) -> List[str]:
        """
        모든 메트릭 이름 목록을 반환합니다.

        Returns:
            메트릭 이름 리스트

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.update_metric("turns", 10)
            >>> manager.update_metric("tokens", 500)
            >>> metrics = manager.list_metrics()
            >>> print(sorted(metrics))
            ['tokens', 'turns']
        """
        return list(self._metrics.keys())

    def get_metric_count(self) -> int:
        """
        메트릭 개수를 반환합니다.

        Returns:
            메트릭 개수

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.update_metric("turns", 10)
            >>> count = manager.get_metric_count()
            >>> print(count)
            1
        """
        return len(self._metrics)

    def increment_metric(self, metric_name: str, amount: int = 1) -> None:
        """
        메트릭을 증가시킵니다.

        Args:
            metric_name: 메트릭 이름
            amount: 증가량 (기본값: 1)

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.update_metric("counter", 0)
            >>> manager.increment_metric("counter")
            >>> manager.increment_metric("counter", 5)
            >>> value = manager.get_current_metric("counter")
            >>> print(value)
            6
        """
        current_value = self._metrics.get(metric_name, 0)

        if not isinstance(current_value, (int, float)):
            logger.error(
                f"Cannot increment non-numeric metric: {metric_name} "
                f"(type: {type(current_value).__name__})"
            )
            return

        new_value = current_value + amount
        self.update_metric(metric_name, new_value)

    def decrement_metric(self, metric_name: str, amount: int = 1) -> None:
        """
        메트릭을 감소시킵니다.

        Args:
            metric_name: 메트릭 이름
            amount: 감소량 (기본값: 1)

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.update_metric("counter", 10)
            >>> manager.decrement_metric("counter")
            >>> manager.decrement_metric("counter", 3)
            >>> value = manager.get_current_metric("counter")
            >>> print(value)
            6
        """
        current_value = self._metrics.get(metric_name, 0)

        if not isinstance(current_value, (int, float)):
            logger.error(
                f"Cannot decrement non-numeric metric: {metric_name} "
                f"(type: {type(current_value).__name__})"
            )
            return

        new_value = current_value - amount
        self.update_metric(metric_name, new_value)

    def get_metric_summary(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """
        메트릭의 요약 통계를 반환합니다.

        Args:
            metric_name: 메트릭 이름

        Returns:
            요약 통계 딕셔너리 (min, max, avg, count) 또는 None

        Example:
            >>> manager = MetricsUIManager()
            >>> manager.update_metric("tokens", 100)
            >>> manager.update_metric("tokens", 200)
            >>> manager.update_metric("tokens", 300)
            >>> summary = manager.get_metric_summary("tokens")
            >>> print(summary["avg"])
            200.0
        """
        if metric_name not in self._metric_history:
            logger.warning(f"Metric not found: {metric_name}")
            return None

        entries = list(self._metric_history[metric_name])
        if not entries:
            return None

        # 숫자형 값만 처리
        numeric_values = [
            entry.value for entry in entries
            if isinstance(entry.value, (int, float))
        ]

        if not numeric_values:
            return None

        summary = {
            "min": min(numeric_values),
            "max": max(numeric_values),
            "avg": sum(numeric_values) / len(numeric_values),
            "count": len(numeric_values),
            "latest": numeric_values[-1] if numeric_values else None
        }

        return summary

    def render_metric_chart(
        self,
        metric_name: str,
        width: int = 40,
        height: int = 10
    ) -> str:
        """
        메트릭을 간단한 ASCII 차트로 렌더링합니다.

        Args:
            metric_name: 메트릭 이름
            width: 차트 너비 (기본값: 40)
            height: 차트 높이 (기본값: 10)

        Returns:
            ASCII 차트 문자열

        Example:
            >>> manager = MetricsUIManager()
            >>> for i in range(10):
            ...     manager.update_metric("value", i * 10)
            >>> chart = manager.render_metric_chart("value", width=20, height=5)
            >>> print(len(chart) > 0)
            True
        """
        if metric_name not in self._metric_history:
            return f"No data for metric: {metric_name}"

        entries = list(self._metric_history[metric_name])
        if not entries:
            return f"No data for metric: {metric_name}"

        # 숫자형 값만 처리
        numeric_values = [
            entry.value for entry in entries
            if isinstance(entry.value, (int, float))
        ]

        if not numeric_values:
            return f"No numeric data for metric: {metric_name}"

        # 값 정규화
        min_val = min(numeric_values)
        max_val = max(numeric_values)
        value_range = max_val - min_val

        if value_range == 0:
            # 모든 값이 같은 경우
            normalized = [height // 2] * len(numeric_values)
        else:
            normalized = [
                int((v - min_val) / value_range * (height - 1))
                for v in numeric_values
            ]

        # 차트 생성
        lines = [f"=== {metric_name} ==="]
        lines.append(f"Max: {max_val:.2f}")

        # 그래프 렌더링 (위에서 아래로)
        for y in range(height - 1, -1, -1):
            line = ""
            for i, norm_value in enumerate(normalized[-width:]):
                if norm_value >= y:
                    line += "█"
                else:
                    line += " "
            lines.append(line)

        lines.append(f"Min: {min_val:.2f}")

        return "\n".join(lines)
