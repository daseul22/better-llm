"""
메트릭 리포터

성능 메트릭 리포트 생성 및 저장
"""

from typing import Optional
from pathlib import Path
import json

from ..models import SessionMetrics


class MetricsReporter:
    """
    메트릭 리포트 생성기

    세션 메트릭을 다양한 형식으로 리포트 생성
    """

    @staticmethod
    def generate_text_report(session_metrics: SessionMetrics) -> str:
        """
        텍스트 형식 리포트 생성

        Args:
            session_metrics: 세션 메트릭

        Returns:
            텍스트 리포트 문자열
        """
        lines = []
        lines.append("=" * 80)
        lines.append("📊 Agent 성능 메트릭 리포트")
        lines.append("=" * 80)
        lines.append("")

        # 세션 정보
        lines.append(f"Session ID: {session_metrics.session_id}")
        lines.append(f"시작 시각: {session_metrics.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if session_metrics.end_time:
            lines.append(
                f"종료 시각: {session_metrics.end_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        lines.append(f"총 소요 시간: {session_metrics.total_duration:.2f}초")
        lines.append(f"총 토큰 사용량: {session_metrics.total_tokens}")
        lines.append(f"전체 성공률: {session_metrics.get_success_rate():.1f}%")
        lines.append("")

        # Worker별 통계
        lines.append("-" * 80)
        lines.append("Worker별 상세 통계")
        lines.append("-" * 80)
        lines.append("")

        # 세션에 등장한 모든 unique worker_name 추출
        worker_names = set(m.worker_name for m in session_metrics.workers_metrics)

        for worker_name in sorted(worker_names):
            stats = session_metrics.get_worker_statistics(worker_name)

            lines.append(f"[{worker_name.upper()}]")
            lines.append(f"  시도: {stats['attempts']}회")
            lines.append(f"  성공: {stats['successes']}회")
            lines.append(f"  실패: {stats['failures']}회")
            lines.append(f"  성공률: {stats['success_rate']:.1f}%")
            lines.append(f"  평균 실행 시간: {stats['avg_execution_time']:.2f}초")
            lines.append(f"  총 토큰 사용량: {stats['total_tokens']}")
            lines.append("")

        # 개별 실행 기록
        lines.append("-" * 80)
        lines.append("개별 실행 기록")
        lines.append("-" * 80)
        lines.append("")

        for i, metric in enumerate(session_metrics.workers_metrics, 1):
            status_icon = "✅" if metric.success else "❌"
            lines.append(f"{i}. {status_icon} [{metric.worker_name.upper()}]")
            lines.append(f"   작업: {metric.task_description[:80]}...")
            lines.append(
                f"   시간: {metric.start_time.strftime('%H:%M:%S')} - "
                f"{metric.end_time.strftime('%H:%M:%S')} "
                f"({metric.execution_time:.2f}초)"
            )
            if metric.tokens_used:
                lines.append(f"   토큰: {metric.tokens_used}")
            if metric.error_message:
                lines.append(f"   오류: {metric.error_message}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    @staticmethod
    def generate_json_report(session_metrics: SessionMetrics) -> str:
        """
        JSON 형식 리포트 생성

        Args:
            session_metrics: 세션 메트릭

        Returns:
            JSON 리포트 문자열
        """
        report_data = session_metrics.to_dict()

        # Worker별 통계 추가
        worker_names = set(m.worker_name for m in session_metrics.workers_metrics)
        worker_statistics = {}
        for worker_name in worker_names:
            worker_statistics[worker_name] = session_metrics.get_worker_statistics(
                worker_name
            )

        report_data["worker_statistics"] = worker_statistics

        return json.dumps(report_data, indent=2, ensure_ascii=False)

    @staticmethod
    def generate_markdown_report(session_metrics: SessionMetrics) -> str:
        """
        Markdown 형식 리포트 생성

        Args:
            session_metrics: 세션 메트릭

        Returns:
            Markdown 리포트 문자열
        """
        lines = []
        lines.append("# 📊 Agent 성능 메트릭 리포트")
        lines.append("")

        # 세션 정보
        lines.append("## 세션 정보")
        lines.append("")
        lines.append(f"- **Session ID**: `{session_metrics.session_id}`")
        lines.append(
            f"- **시작 시각**: {session_metrics.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        if session_metrics.end_time:
            lines.append(
                f"- **종료 시각**: "
                f"{session_metrics.end_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        lines.append(f"- **총 소요 시간**: {session_metrics.total_duration:.2f}초")
        lines.append(f"- **총 토큰 사용량**: {session_metrics.total_tokens}")
        lines.append(f"- **전체 성공률**: {session_metrics.get_success_rate():.1f}%")
        lines.append("")

        # Worker별 통계 (테이블 형식)
        lines.append("## Worker별 통계")
        lines.append("")
        lines.append("| Worker | 시도 | 성공 | 실패 | 성공률 | 평균 시간 | 토큰 |")
        lines.append("|--------|------|------|------|--------|-----------|------|")

        worker_names = set(m.worker_name for m in session_metrics.workers_metrics)

        for worker_name in sorted(worker_names):
            stats = session_metrics.get_worker_statistics(worker_name)
            lines.append(
                f"| {worker_name.upper()} "
                f"| {stats['attempts']} "
                f"| {stats['successes']} "
                f"| {stats['failures']} "
                f"| {stats['success_rate']:.1f}% "
                f"| {stats['avg_execution_time']:.2f}s "
                f"| {stats['total_tokens']} |"
            )

        lines.append("")

        # 개별 실행 기록
        lines.append("## 개별 실행 기록")
        lines.append("")

        for i, metric in enumerate(session_metrics.workers_metrics, 1):
            status_icon = "✅" if metric.success else "❌"
            lines.append(f"### {i}. {status_icon} [{metric.worker_name.upper()}]")
            lines.append("")
            lines.append(f"- **작업**: {metric.task_description}")
            lines.append(
                f"- **시간**: {metric.start_time.strftime('%H:%M:%S')} - "
                f"{metric.end_time.strftime('%H:%M:%S')} "
                f"({metric.execution_time:.2f}초)"
            )
            if metric.tokens_used:
                lines.append(f"- **토큰**: {metric.tokens_used}")
            if metric.error_message:
                lines.append(f"- **오류**: `{metric.error_message}`")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def save_report(
        session_metrics: SessionMetrics,
        output_path: Path,
        format: str = "text",
    ) -> Path:
        """
        리포트를 파일로 저장

        Args:
            session_metrics: 세션 메트릭
            output_path: 출력 경로 (디렉토리)
            format: 리포트 형식 ("text", "json", "markdown")

        Returns:
            저장된 파일 경로
        """
        output_path.mkdir(parents=True, exist_ok=True)

        # 파일명 생성
        session_id = session_metrics.session_id
        if format == "text":
            filename = f"{session_id}_metrics.txt"
            content = MetricsReporter.generate_text_report(session_metrics)
        elif format == "json":
            filename = f"{session_id}_metrics.json"
            content = MetricsReporter.generate_json_report(session_metrics)
        elif format == "markdown":
            filename = f"{session_id}_metrics.md"
            content = MetricsReporter.generate_markdown_report(session_metrics)
        else:
            raise ValueError(f"지원하지 않는 형식: {format}")

        filepath = output_path / filename
        filepath.write_text(content, encoding="utf-8")

        return filepath
