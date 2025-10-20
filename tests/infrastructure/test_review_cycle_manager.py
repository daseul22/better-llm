"""
ReviewCycleManager 테스트
"""

import pytest
from datetime import datetime
from src.infrastructure.mcp.review_cycle_manager import (
    ReviewCycleManager,
    ReviewResult,
    ReviewCycleSummary
)


class TestReviewCycleManager:
    """ReviewCycleManager 기본 기능 테스트"""

    def test_initialization(self):
        """초기화 테스트"""
        manager = ReviewCycleManager(max_cycles=3)
        assert manager.max_cycles == 3
        assert manager.cycle_count == 0
        assert len(manager.review_history) == 0
        assert manager.last_reviewer_call_time is None
        assert manager.coder_called_after_reviewer is False

    def test_default_max_cycles(self):
        """기본 max_cycles 값 테스트"""
        manager = ReviewCycleManager()
        assert manager.max_cycles == 3

    def test_reset(self):
        """reset() 메서드 테스트"""
        manager = ReviewCycleManager(max_cycles=3)
        manager.cycle_count = 2
        manager.mark_reviewer_called()
        manager.mark_coder_called()
        manager.record_review_result(critical_issues=["issue1"])

        manager.reset()

        assert manager.cycle_count == 0
        assert len(manager.review_history) == 0
        assert manager.last_reviewer_call_time is None
        assert manager.coder_called_after_reviewer is False


class TestReviewCycleTracking:
    """Review cycle 추적 기능 테스트"""

    def test_mark_reviewer_called(self):
        """Reviewer 호출 기록 테스트"""
        manager = ReviewCycleManager()
        manager.mark_reviewer_called()

        assert manager.last_reviewer_call_time is not None
        assert isinstance(manager.last_reviewer_call_time, datetime)

    def test_mark_coder_called(self):
        """Coder 호출 기록 테스트 (Reviewer 호출 이후)"""
        manager = ReviewCycleManager()
        manager.mark_reviewer_called()
        manager.mark_coder_called()

        assert manager.coder_called_after_reviewer is True

    def test_mark_coder_called_without_reviewer(self):
        """Reviewer 호출 없이 Coder 호출 시 플래그 설정 안 됨"""
        manager = ReviewCycleManager()
        manager.mark_coder_called()

        assert manager.coder_called_after_reviewer is False

    def test_should_continue_review_initial(self):
        """초기 상태에서 should_continue_review() 테스트"""
        manager = ReviewCycleManager(max_cycles=3)
        can_continue, error_msg = manager.should_continue_review()

        assert can_continue is True
        assert error_msg is None

    def test_should_continue_review_increment_cycle(self):
        """Coder 호출 후 cycle count 증가 테스트"""
        manager = ReviewCycleManager(max_cycles=3)
        manager.mark_reviewer_called()
        manager.mark_coder_called()

        can_continue, error_msg = manager.should_continue_review()

        assert can_continue is True
        assert manager.cycle_count == 1

    def test_should_continue_review_max_cycles_exceeded(self):
        """최대 cycle 초과 시 중단 테스트"""
        manager = ReviewCycleManager(max_cycles=2)

        # Cycle 1
        manager.mark_reviewer_called()
        manager.mark_coder_called()
        manager.should_continue_review()

        # Cycle 2
        manager.mark_reviewer_called()
        manager.mark_coder_called()
        manager.should_continue_review()

        # Cycle 3 (초과)
        manager.mark_reviewer_called()
        manager.mark_coder_called()
        can_continue, error_msg = manager.should_continue_review()

        assert can_continue is False
        assert error_msg is not None
        assert "최대 횟수" in error_msg


class TestReviewResultRecording:
    """Review 결과 기록 테스트"""

    def test_record_review_result_basic(self):
        """기본 review 결과 기록 테스트"""
        manager = ReviewCycleManager()
        manager.record_review_result(
            critical_issues=["issue1", "issue2"],
            reviewer_output="Review output"
        )

        assert len(manager.review_history) == 1
        result = manager.review_history[0]
        assert result.cycle_number == 0
        assert len(result.critical_issues) == 2
        assert result.reviewer_output == "Review output"

    def test_record_review_result_empty_issues(self):
        """빈 이슈 리스트 기록 테스트"""
        manager = ReviewCycleManager()
        manager.record_review_result()

        assert len(manager.review_history) == 1
        result = manager.review_history[0]
        assert len(result.critical_issues) == 0

    def test_record_multiple_results(self):
        """여러 review 결과 기록 테스트"""
        manager = ReviewCycleManager()

        for i in range(3):
            manager.record_review_result(
                critical_issues=[f"issue{i}"],
                reviewer_output=f"output{i}"
            )

        assert len(manager.review_history) == 3

    def test_record_with_coder_response(self):
        """Coder 응답 포함 기록 테스트"""
        manager = ReviewCycleManager()
        manager.record_review_result(
            critical_issues=["issue"],
            reviewer_output="review",
            coder_response="fixed"
        )

        result = manager.review_history[0]
        assert result.coder_response == "fixed"


class TestSummaryGeneration:
    """요약 리포트 생성 테스트"""

    def test_generate_summary_empty(self):
        """빈 히스토리에서 summary 생성 테스트"""
        manager = ReviewCycleManager()
        summary = manager.generate_summary_report()

        assert summary.total_cycles == 0
        assert summary.exceeded_limit is False
        assert len(summary.review_history) == 0
        assert summary.first_review_time is None
        assert summary.last_review_time is None

    def test_generate_summary_with_history(self):
        """히스토리가 있는 경우 summary 생성 테스트"""
        manager = ReviewCycleManager(max_cycles=3)
        manager.cycle_count = 2

        manager.record_review_result(critical_issues=["issue1"])
        manager.record_review_result(critical_issues=["issue2"])

        summary = manager.generate_summary_report()

        assert summary.total_cycles == 2
        assert summary.exceeded_limit is False
        assert len(summary.review_history) == 2
        assert summary.first_review_time is not None
        assert summary.last_review_time is not None

    def test_generate_summary_exceeded(self):
        """최대 횟수 초과 시 summary 테스트"""
        manager = ReviewCycleManager(max_cycles=2)
        manager.cycle_count = 3

        summary = manager.generate_summary_report()

        assert summary.exceeded_limit is True

    def test_summary_duration_calculation(self):
        """summary duration 계산 테스트"""
        manager = ReviewCycleManager()
        manager.record_review_result(critical_issues=["issue1"])
        # 약간의 시간 지연 시뮬레이션
        import time
        time.sleep(0.1)
        manager.record_review_result(critical_issues=["issue2"])

        summary = manager.generate_summary_report()
        duration = summary.duration_seconds

        assert duration is not None
        assert duration > 0


class TestCriticalIssuesSummary:
    """중요 이슈 요약 테스트"""

    def test_format_critical_issues_empty(self):
        """빈 히스토리 포맷 테스트"""
        manager = ReviewCycleManager()
        formatted = manager.format_critical_issues_summary()

        assert "No review history available" in formatted

    def test_format_critical_issues_with_data(self):
        """이슈가 있는 경우 포맷 테스트"""
        manager = ReviewCycleManager()
        manager.cycle_count = 1
        manager.record_review_result(critical_issues=["issue1", "issue2"])

        formatted = manager.format_critical_issues_summary()

        assert "Review Cycle Summary" in formatted
        assert "issue1" in formatted
        assert "issue2" in formatted

    def test_format_no_critical_issues(self):
        """이슈가 없는 경우 포맷 테스트"""
        manager = ReviewCycleManager()
        manager.record_review_result(critical_issues=[])

        formatted = manager.format_critical_issues_summary()

        assert "No critical issues found" in formatted


class TestCycleState:
    """Cycle 상태 조회 테스트"""

    def test_get_cycle_state_initial(self):
        """초기 상태 조회 테스트"""
        manager = ReviewCycleManager(max_cycles=3)
        state = manager.get_cycle_state()

        assert state["cycle_count"] == 0
        assert state["max_cycles"] == 3
        assert state["exceeded"] is False
        assert state["last_reviewer_call"] is None
        assert state["coder_called_after_reviewer"] is False
        assert state["review_history_count"] == 0

    def test_get_cycle_state_with_data(self):
        """데이터가 있는 경우 상태 조회 테스트"""
        manager = ReviewCycleManager(max_cycles=3)
        manager.cycle_count = 2
        manager.mark_reviewer_called()
        manager.mark_coder_called()
        manager.record_review_result(critical_issues=["issue"])

        state = manager.get_cycle_state()

        assert state["cycle_count"] == 2
        assert state["exceeded"] is False
        assert state["last_reviewer_call"] is not None
        assert state["coder_called_after_reviewer"] is True
        assert state["review_history_count"] == 1
