"""
Review Cycle Manager - Review 사이클 관리 및 무한 루프 방지

Reviewer → Coder → Reviewer 패턴의 무한 루프를 방지하기 위해
Review cycle을 추적하고 최대 횟수를 제한합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from infrastructure.logging import get_logger

logger = get_logger(__name__, component="ReviewCycleManager")


@dataclass
class ReviewResult:
    """Review 결과 데이터 클래스"""
    cycle_number: int
    timestamp: datetime
    critical_issues: List[str] = field(default_factory=list)
    reviewer_output: str = ""
    coder_response: Optional[str] = None


@dataclass
class ReviewCycleSummary:
    """Review cycle 요약 정보"""
    total_cycles: int
    exceeded_limit: bool
    max_cycles: int
    review_history: List[ReviewResult]
    first_review_time: Optional[datetime]
    last_review_time: Optional[datetime]

    @property
    def duration_seconds(self) -> Optional[float]:
        """전체 Review 소요 시간 (초)"""
        if self.first_review_time and self.last_review_time:
            return (self.last_review_time - self.first_review_time).total_seconds()
        return None


class ReviewCycleManager:
    """
    Review cycle 관리자

    Reviewer → Coder → Reviewer 패턴의 무한 루프를 방지하기 위해
    Review cycle을 추적하고 최대 횟수를 제한합니다.

    Attributes:
        max_cycles: 최대 Review cycle 횟수
        cycle_count: 현재 Review cycle 수
        review_history: Review 결과 히스토리
        last_reviewer_call_time: 마지막 Reviewer 호출 시각
        coder_called_after_reviewer: Reviewer 호출 후 Coder 호출 여부

    Example:
        >>> manager = ReviewCycleManager(max_cycles=3)
        >>> should_continue, message = manager.should_continue_review()
        >>> if should_continue:
        ...     # Review 진행
        ...     manager.record_review_result(critical_issues=["issue1"])
    """

    def __init__(self, max_cycles: int = 3):
        """
        ReviewCycleManager 초기화

        Args:
            max_cycles: 최대 Review cycle 횟수 (기본값: 3)
        """
        self.max_cycles = max_cycles
        self.cycle_count = 0
        self.review_history: List[ReviewResult] = []
        self.last_reviewer_call_time: Optional[datetime] = None
        self.coder_called_after_reviewer = False

        logger.info(f"ReviewCycleManager initialized with max_cycles={max_cycles}")

    def reset(self) -> None:
        """Review cycle 초기화"""
        self.cycle_count = 0
        self.review_history.clear()
        self.last_reviewer_call_time = None
        self.coder_called_after_reviewer = False
        logger.info("🔄 Review cycle has been reset")

    def mark_reviewer_called(self) -> None:
        """Reviewer 호출 기록"""
        self.last_reviewer_call_time = datetime.now()
        logger.debug("Reviewer call marked", timestamp=self.last_reviewer_call_time)

    def mark_coder_called(self) -> None:
        """
        Coder 호출 기록

        Reviewer 호출 후 Coder가 호출되면 플래그 설정
        다음 Reviewer 호출 시 cycle count 증가 트리거
        """
        if self.last_reviewer_call_time is not None:
            self.coder_called_after_reviewer = True
            logger.debug("Coder called after Reviewer - cycle increment will occur on next Reviewer call")

    def should_continue_review(self) -> tuple[bool, Optional[str]]:
        """
        Review 진행 여부 판단

        Returns:
            tuple[bool, Optional[str]]: (진행 가능 여부, 에러 메시지)
                - (True, None): Review 진행 가능
                - (False, "에러 메시지"): Review 중단 필요

        Note:
            Reviewer 호출 후 Coder가 호출된 경우에만 cycle count를 증가시킵니다.
        """
        # Coder 호출 후인 경우에만 cycle count 증가
        if self.coder_called_after_reviewer:
            self.cycle_count += 1
            self.coder_called_after_reviewer = False
            logger.info(
                f"🔄 Review cycle incremented: {self.cycle_count}/{self.max_cycles}"
            )

        # 최대 횟수 초과 체크
        if self.cycle_count > self.max_cycles:
            error_msg = (
                f"⚠️  Review Cycle이 최대 횟수 ({self.max_cycles}회)를 초과했습니다.\n\n"
                f"무한 루프를 방지하기 위해 Reviewer 실행을 중단합니다.\n"
                f"수동으로 코드를 검토하고 수정하거나, 요구사항을 조정해주세요.\n\n"
                f"(Tip: system_config.json의 'workflow_limits.max_review_iterations'로 "
                f"최대 횟수를 조정할 수 있습니다.)"
            )
            logger.error(error_msg)
            return False, error_msg

        return True, None

    def record_review_result(
        self,
        critical_issues: Optional[List[str]] = None,
        reviewer_output: str = "",
        coder_response: Optional[str] = None
    ) -> None:
        """
        Review 결과 기록

        Args:
            critical_issues: 발견된 중요 이슈 목록
            reviewer_output: Reviewer 출력 전문
            coder_response: Coder 응답 (있는 경우)
        """
        result = ReviewResult(
            cycle_number=self.cycle_count,
            timestamp=datetime.now(),
            critical_issues=critical_issues or [],
            reviewer_output=reviewer_output,
            coder_response=coder_response
        )
        self.review_history.append(result)

        logger.info(
            f"Review result recorded",
            cycle_number=result.cycle_number,
            critical_issues_count=len(result.critical_issues)
        )

    def generate_summary_report(self) -> ReviewCycleSummary:
        """
        Review cycle 요약 리포트 생성

        Returns:
            ReviewCycleSummary: Review cycle 요약 정보
        """
        first_review_time = self.review_history[0].timestamp if self.review_history else None
        last_review_time = self.review_history[-1].timestamp if self.review_history else None

        summary = ReviewCycleSummary(
            total_cycles=self.cycle_count,
            exceeded_limit=self.cycle_count > self.max_cycles,
            max_cycles=self.max_cycles,
            review_history=self.review_history.copy(),
            first_review_time=first_review_time,
            last_review_time=last_review_time
        )

        logger.info(
            f"Review cycle summary generated",
            total_cycles=summary.total_cycles,
            exceeded_limit=summary.exceeded_limit,
            duration=summary.duration_seconds
        )

        return summary

    def format_critical_issues_summary(self) -> str:
        """
        전체 Review cycle에서 발견된 중요 이슈 요약

        Returns:
            포맷된 이슈 요약 문자열
        """
        if not self.review_history:
            return "No review history available."

        lines = [f"📋 Review Cycle Summary ({self.cycle_count} cycles)"]
        lines.append("=" * 60)

        for result in self.review_history:
            lines.append(f"\n🔍 Cycle #{result.cycle_number} ({result.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")

            if result.critical_issues:
                lines.append(f"   Critical Issues ({len(result.critical_issues)}):")
                for i, issue in enumerate(result.critical_issues, 1):
                    lines.append(f"      {i}. {issue}")
            else:
                lines.append("   ✅ No critical issues found")

        lines.append("\n" + "=" * 60)

        return "\n".join(lines)

    def get_cycle_state(self) -> Dict[str, Any]:
        """
        현재 cycle 상태 반환 (디버깅용)

        Returns:
            현재 상태를 담은 딕셔너리
        """
        return {
            "cycle_count": self.cycle_count,
            "max_cycles": self.max_cycles,
            "exceeded": self.cycle_count > self.max_cycles,
            "last_reviewer_call": self.last_reviewer_call_time.isoformat() if self.last_reviewer_call_time else None,
            "coder_called_after_reviewer": self.coder_called_after_reviewer,
            "review_history_count": len(self.review_history)
        }
