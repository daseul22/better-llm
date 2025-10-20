"""
Tests for error tracking

src/infrastructure/logging/error_tracker.py 테스트
"""
import pytest
import threading
from datetime import datetime

from src.infrastructure.logging.error_tracker import (
    track_error,
    get_error_stats,
    reset_error_stats,
    get_error_summary,
    _error_counts,
    _recent_errors,
)


@pytest.mark.unit
class TestErrorTracker:
    """Error tracking 기능 테스트"""

    def setup_method(self):
        """각 테스트 전에 에러 통계 초기화"""
        reset_error_stats()

    def test_track_error_basic(self):
        """기본 에러 추적 테스트"""
        error = ValueError("Test error")

        track_error(error, "test_context", worker_name="planner")

        stats = get_error_stats()
        assert stats["total_errors"] == 1
        assert stats["error_counts"]["ValueError"] == 1
        assert len(stats["recent_errors"]) == 1

        # 최근 에러 정보 확인
        recent = stats["recent_errors"][0]
        assert recent["error_type"] == "ValueError"
        assert recent["error_message"] == "Test error"
        assert recent["context"] == "test_context"
        assert recent["worker_name"] == "planner"
        assert "timestamp" in recent

    def test_track_multiple_errors(self):
        """여러 에러 추적 테스트"""
        errors = [
            ValueError("Error 1"),
            TypeError("Error 2"),
            ValueError("Error 3"),
        ]

        for error in errors:
            track_error(error, "test_context")

        stats = get_error_stats()
        assert stats["total_errors"] == 3
        assert stats["error_counts"]["ValueError"] == 2
        assert stats["error_counts"]["TypeError"] == 1

    def test_track_error_with_metadata(self):
        """메타데이터를 포함한 에러 추적 테스트"""
        error = RuntimeError("Runtime error")
        metadata = {
            "worker_name": "coder",
            "task_id": "task-123",
            "user_id": "user-456"
        }

        track_error(error, "task_execution", **metadata)

        stats = get_error_stats()
        recent = stats["recent_errors"][0]

        assert recent["worker_name"] == "coder"
        assert recent["task_id"] == "task-123"
        assert recent["user_id"] == "user-456"

    def test_track_error_thread_safety(self):
        """에러 추적 스레드 안전성 테스트"""
        num_threads = 10
        errors_per_thread = 100

        def track_many_errors():
            for i in range(errors_per_thread):
                error = RuntimeError(f"Error {i}")
                track_error(error, "thread_test")

        threads = [threading.Thread(target=track_many_errors) for _ in range(num_threads)]

        # 모든 스레드 시작
        for t in threads:
            t.start()

        # 모든 스레드 종료 대기
        for t in threads:
            t.join()

        # 검증
        stats = get_error_stats()
        expected_total = num_threads * errors_per_thread
        assert stats["total_errors"] == expected_total
        assert stats["error_counts"]["RuntimeError"] == expected_total

    def test_recent_errors_limit(self):
        """최근 에러 버퍼 제한 테스트"""
        # MAX_RECENT_ERRORS = 100이므로 150개 에러 추적
        for i in range(150):
            error = ValueError(f"Error {i}")
            track_error(error, "limit_test")

        # _recent_errors는 최대 100개만 유지
        from src.infrastructure.logging.error_tracker import _recent_errors, MAX_RECENT_ERRORS
        assert len(_recent_errors) == MAX_RECENT_ERRORS

        # get_error_stats()는 최근 10개만 반환
        stats = get_error_stats()
        assert len(stats["recent_errors"]) == 10
        assert stats["total_errors"] == 150

    def test_reset_error_stats(self):
        """에러 통계 초기화 테스트"""
        # 에러 추적
        for i in range(5):
            track_error(ValueError(f"Error {i}"), "test")

        # 초기화 전 확인
        stats = get_error_stats()
        assert stats["total_errors"] == 5

        # 초기화
        reset_error_stats()

        # 초기화 후 확인
        stats = get_error_stats()
        assert stats["total_errors"] == 0
        assert len(stats["error_counts"]) == 0
        assert len(stats["recent_errors"]) == 0

    def test_get_error_summary_no_errors(self):
        """에러가 없을 때 요약 테스트"""
        summary = get_error_summary()
        assert summary == "No errors recorded"

    def test_get_error_summary_with_errors(self):
        """에러가 있을 때 요약 테스트"""
        # 여러 에러 추적
        track_error(ValueError("Error 1"), "test")
        track_error(ValueError("Error 2"), "test")
        track_error(TypeError("Error 3"), "test")
        track_error(RuntimeError("Error 4"), "test")

        summary = get_error_summary(limit=3)

        # 요약 내용 확인
        assert "Total errors: 4" in summary
        assert "ValueError: 2" in summary
        assert "TypeError: 1" in summary
        assert "RuntimeError: 1" in summary

    def test_get_error_summary_limit(self):
        """에러 요약 제한 테스트"""
        # 10가지 다른 에러 타입 추적
        error_types = [
            ValueError, TypeError, RuntimeError, KeyError, AttributeError,
            IndexError, ZeroDivisionError, FileNotFoundError, ImportError, OSError
        ]

        for error_type in error_types:
            track_error(error_type("Test"), "test")

        # 상위 5개만 요청
        summary = get_error_summary(limit=5)

        # 5개만 포함되어야 함
        lines = summary.split("\n")
        error_lines = [line for line in lines if line.strip().startswith("-")]
        assert len(error_lines) == 5

    def test_error_stats_return_copy(self):
        """get_error_stats()가 복사본을 반환하는지 테스트"""
        track_error(ValueError("Test"), "test")

        # 통계 가져오기
        stats1 = get_error_stats()
        stats2 = get_error_stats()

        # 복사본이므로 다른 객체여야 함
        assert stats1 is not stats2
        assert stats1["recent_errors"] is not stats2["recent_errors"]

        # 값은 같아야 함
        assert stats1["total_errors"] == stats2["total_errors"]


@pytest.mark.unit
class TestErrorTrackerEdgeCases:
    """Error tracker 엣지 케이스 테스트"""

    def setup_method(self):
        """각 테스트 전에 에러 통계 초기화"""
        reset_error_stats()

    def test_track_error_with_long_message(self):
        """긴 에러 메시지 추적 테스트"""
        long_message = "A" * 10000
        error = ValueError(long_message)

        track_error(error, "test")

        stats = get_error_stats()
        assert stats["total_errors"] == 1
        assert stats["recent_errors"][0]["error_message"] == long_message

    def test_track_error_with_special_characters(self):
        """특수 문자가 포함된 에러 메시지 테스트"""
        special_message = "Error: \n\t\r\x00 special chars 한글 🔥"
        error = RuntimeError(special_message)

        track_error(error, "test")

        stats = get_error_stats()
        assert stats["recent_errors"][0]["error_message"] == special_message

    def test_track_error_with_nested_exception(self):
        """중첩된 예외 추적 테스트"""
        try:
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise RuntimeError("Outer error") from e
        except RuntimeError as outer:
            track_error(outer, "nested_test")

        stats = get_error_stats()
        assert stats["total_errors"] == 1
        assert stats["error_counts"]["RuntimeError"] == 1
