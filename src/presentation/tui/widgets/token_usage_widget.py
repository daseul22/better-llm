"""
토큰 사용량 시각화 위젯

실시간 토큰 사용량을 프로그레스 바와 색상 경고로 표시합니다.
"""

from typing import Optional, Dict, Any
from textual.widgets import Static, ProgressBar
from textual.containers import Vertical, Horizontal
from rich.text import Text

from src.infrastructure.logging import get_logger

logger = get_logger(__name__, component="TokenUsageWidget")


class TokenUsageWidget(Static):
    """
    토큰 사용량 시각화 위젯 (매니저 토큰 기준)

    색상 경고 + 예산 설정으로 토큰 사용량을 직관적으로 표시합니다.

    Features:
        - 현재 사용량 / 예산 표시 (예: 15,234 / 150,000 tokens)
        - **퍼센트 계산은 매니저 토큰만 기준** (워커 토큰 제외)
        - 캐시 토큰 정보 (괄호로 표시: +3,456 cache read)
        - 색상 변화: 녹색 < 70% < 노랑 < 90% < 빨강
        - 실시간 업데이트 (1초마다)
        - 워커 토큰은 별도 표시 (M:xxx W:yyy 형태)

    Example:
        >>> widget = TokenUsageWidget(token_budget=150000)
        >>> session_summary = metrics_collector.get_session_summary(session_id)
        >>> widget.update_token_info(manager_usage, session_summary)
    """

    def __init__(
        self,
        token_budget: int = 150000,
        warn_threshold: float = 0.7,
        alert_threshold: float = 0.9,
        **kwargs
    ) -> None:
        """
        TokenUsageWidget 초기화

        Args:
            token_budget: 토큰 예산 (기본값: 150,000)
            warn_threshold: 경고 시작 임계값 (기본값: 0.7 = 70%)
            alert_threshold: 긴급 경고 임계값 (기본값: 0.9 = 90%)
            **kwargs: Static 위젯 추가 인자
        """
        super().__init__(**kwargs)
        self.token_budget = token_budget
        self.warn_threshold = warn_threshold
        self.alert_threshold = alert_threshold

        # 초기 상태
        self._total_tokens = 0
        self._manager_tokens = 0
        self._worker_tokens = 0
        self._cache_read_tokens = 0
        self._cache_creation_tokens = 0

        logger.info(
            f"TokenUsageWidget initialized (budget: {token_budget}, "
            f"warn: {warn_threshold:.0%}, alert: {alert_threshold:.0%})"
        )

    def update_token_info(
        self,
        manager_usage: Dict[str, int],
        session_summary: Optional[Any] = None
    ) -> None:
        """
        토큰 사용량 정보 업데이트

        Args:
            manager_usage: Manager Agent 토큰 사용량 딕셔너리
                - total_tokens: 전체 토큰 수
                - input_tokens: 입력 토큰 수
                - output_tokens: 출력 토큰 수
            session_summary: SessionMetrics 객체 (Worker 토큰 정보)

        Example:
            >>> manager_usage = {
            ...     "total_tokens": 10000,
            ...     "input_tokens": 8000,
            ...     "output_tokens": 2000
            ... }
            >>> widget.update_token_info(manager_usage, session_metrics)
        """
        try:
            # Manager 토큰 정보
            self._manager_tokens = manager_usage.get("total_tokens", 0)

            # Worker 토큰 정보 계산
            worker_input = 0
            worker_output = 0
            cache_read = 0
            cache_creation = 0

            if session_summary:
                for metric in session_summary.workers_metrics:
                    worker_input += metric.input_tokens or 0
                    worker_output += metric.output_tokens or 0
                    cache_read += metric.cache_read_tokens or 0
                    cache_creation += metric.cache_creation_tokens or 0

            self._worker_tokens = worker_input + worker_output
            self._cache_read_tokens = cache_read
            self._cache_creation_tokens = cache_creation

            # 전체 토큰 계산 (매니저 토큰만 - 워커 제외)
            self._total_tokens = self._manager_tokens

            # UI 렌더링
            self._render_token_display()

            logger.debug(
                f"Token info updated: total={self._total_tokens}, "
                f"manager={self._manager_tokens}, worker={self._worker_tokens}, "
                f"cache_read={self._cache_read_tokens}"
            )

        except Exception as e:
            logger.error(f"Failed to update token info: {e}")
            self.update("[red]토큰 정보 업데이트 실패[/red]")

    def _render_token_display(self) -> None:
        """
        토큰 정보를 Rich 마크업으로 렌더링 (한 줄 표시)

        형식:
            🟢 15.2K / 150.0K tokens (10.1%) • M: 10,234 W: 5,000 (+3,456 cache)
        """
        # 사용률 계산
        usage_ratio = self._total_tokens / self.token_budget if self.token_budget > 0 else 0
        usage_percent = usage_ratio * 100

        # 색상 및 이모지 결정
        if usage_ratio < self.warn_threshold:
            color = "green"
            emoji = "🟢"
        elif usage_ratio < self.alert_threshold:
            color = "yellow"
            emoji = "🟡"
        else:
            color = "red"
            emoji = "🔴"

        # 토큰 수 포맷팅 (1,000 이상이면 K 단위)
        def format_tokens(tokens: int) -> str:
            if tokens >= 1000:
                return f"{tokens / 1000:.1f}K"
            return str(tokens)

        total_display = format_tokens(self._total_tokens)
        budget_display = format_tokens(self.token_budget)

        # 첫 번째 줄: 요약 정보
        summary_line = (
            f"[{color}]{emoji} {total_display} / {budget_display} tokens "
            f"({usage_percent:.1f}%)[/{color}] "
            f"[dim]• M:{self._manager_tokens:,} W:{self._worker_tokens:,}"
        )

        # 캐시 정보 추가 (있는 경우만)
        if self._cache_read_tokens > 0:
            summary_line += f" (+{self._cache_read_tokens:,} cache)"

        summary_line += "[/dim]"

        # 최종 출력 (프로그레스바 제거, 한 줄로 표시)
        self.update(summary_line)

    def set_budget(self, budget: int) -> None:
        """
        토큰 예산 설정

        Args:
            budget: 새로운 토큰 예산

        Example:
            >>> widget.set_budget(100000)
        """
        if budget < 1000:
            logger.warning(f"Token budget too low: {budget} (minimum: 1,000)")
            return

        self.token_budget = budget
        logger.info(f"Token budget updated: {budget:,}")

        # UI 즉시 재렌더링
        self._render_token_display()

    def set_thresholds(self, warn: float, alert: float) -> None:
        """
        경고 임계값 설정

        Args:
            warn: 경고 시작 임계값 (0.0 ~ 1.0)
            alert: 긴급 경고 임계값 (0.0 ~ 1.0)

        Example:
            >>> widget.set_thresholds(0.6, 0.8)  # 60% 경고, 80% 긴급
        """
        if not (0.0 <= warn <= 1.0 and 0.0 <= alert <= 1.0):
            logger.error(f"Invalid thresholds: warn={warn}, alert={alert} (must be 0.0~1.0)")
            return

        if warn >= alert:
            logger.error(f"Warn threshold ({warn}) must be less than alert ({alert})")
            return

        self.warn_threshold = warn
        self.alert_threshold = alert
        logger.info(f"Thresholds updated: warn={warn:.0%}, alert={alert:.0%}")

        # UI 즉시 재렌더링
        self._render_token_display()

    def get_usage_summary(self) -> Dict[str, Any]:
        """
        현재 토큰 사용량 요약 정보 반환

        Returns:
            사용량 요약 딕셔너리

        Example:
            >>> summary = widget.get_usage_summary()
            >>> print(summary["usage_percent"])
            30.5
        """
        usage_ratio = self._total_tokens / self.token_budget if self.token_budget > 0 else 0

        return {
            "total_tokens": self._total_tokens,
            "manager_tokens": self._manager_tokens,
            "worker_tokens": self._worker_tokens,
            "cache_read_tokens": self._cache_read_tokens,
            "cache_creation_tokens": self._cache_creation_tokens,
            "budget": self.token_budget,
            "usage_ratio": usage_ratio,
            "usage_percent": usage_ratio * 100,
            "is_warning": usage_ratio >= self.warn_threshold,
            "is_alert": usage_ratio >= self.alert_threshold,
        }
