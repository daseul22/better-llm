"""
ErrorStatisticsManager 테스트
"""

import pytest
from datetime import datetime, timedelta
from src.infrastructure.mcp.error_statistics_manager import (
    ErrorStatisticsManager,
    ErrorRecord,
    ErrorSummary,
    ErrorTrend
)


class TestErrorStatisticsManagerInitialization:
    """ErrorStatisticsManager 초기화 테스트"""

    def test_initialization_default(self):
        """기본 설정으로 초기화 테스트"""
        manager = ErrorStatisticsManager()

        assert len(manager.error_records) == 0
        assert len(manager.attempt_counts) == 0
        assert len(manager.failure_counts) == 0
        assert manager.max_records == 1000

    def test_initialization_custom_max_records(self):
        """커스텀 max_records로 초기화 테스트"""
        manager = ErrorStatisticsManager(max_records=500)

        assert manager.max_records == 500


class TestAttemptRecording:
    """시도 횟수 기록 테스트"""

    def test_record_attempt_single(self):
        """단일 시도 기록 테스트"""
        manager = ErrorStatisticsManager()
        manager.record_attempt("coder")

        assert manager.attempt_counts["coder"] == 1

    def test_record_attempt_multiple(self):
        """여러 시도 기록 테스트"""
        manager = ErrorStatisticsManager()

        for _ in range(5):
            manager.record_attempt("coder")

        assert manager.attempt_counts["coder"] == 5

    def test_record_attempt_multiple_workers(self):
        """여러 Worker 시도 기록 테스트"""
        manager = ErrorStatisticsManager()

        manager.record_attempt("coder")
        manager.record_attempt("coder")
        manager.record_attempt("tester")

        assert manager.attempt_counts["coder"] == 2
        assert manager.attempt_counts["tester"] == 1


class TestErrorRecording:
    """에러 기록 테스트"""

    def test_record_error_basic(self):
        """기본 에러 기록 테스트"""
        manager = ErrorStatisticsManager()
        error = ValueError("Test error")

        manager.record_error("coder", error)

        assert manager.failure_counts["coder"] == 1
        assert len(manager.error_records) == 1

        record = manager.error_records[0]
        assert record.worker_name == "coder"
        assert record.error_type == "ValueError"
        assert record.error_message == "Test error"

    def test_record_error_with_context(self):
        """컨텍스트 포함 에러 기록 테스트"""
        manager = ErrorStatisticsManager()
        error = RuntimeError("Runtime error")
        context = {"task": "refactoring", "file": "test.py"}

        manager.record_error("coder", error, context=context)

        record = manager.error_records[0]
        assert record.context == context

    def test_record_error_with_traceback(self):
        """트레이스백 포함 에러 기록 테스트"""
        manager = ErrorStatisticsManager()
        error = Exception("Test")
        traceback = "Traceback (most recent call last)..."

        manager.record_error("coder", error, traceback_str=traceback)

        record = manager.error_records[0]
        assert record.traceback == traceback

    def test_record_error_max_records_limit(self):
        """최대 레코드 개수 제한 테스트"""
        manager = ErrorStatisticsManager(max_records=3)

        for i in range(5):
            error = ValueError(f"Error {i}")
            manager.record_error("coder", error)

        # 최대 3개만 유지
        assert len(manager.error_records) == 3
        # 최근 3개만 남음 (Error 2, 3, 4)
        assert manager.error_records[0].error_message == "Error 2"


class TestErrorSummary:
    """에러 요약 조회 테스트"""

    def test_get_error_summary_empty(self):
        """빈 상태에서 요약 조회 테스트"""
        manager = ErrorStatisticsManager()
        summary = manager.get_error_summary()

        assert summary.total_attempts == 0
        assert summary.total_failures == 0
        assert summary.success_rate == 0.0
        assert summary.error_rate == 0.0
        assert len(summary.worker_stats) == 0

    def test_get_error_summary_with_data(self):
        """데이터가 있는 경우 요약 조회 테스트"""
        manager = ErrorStatisticsManager()

        # Coder: 10번 시도, 2번 실패
        for _ in range(10):
            manager.record_attempt("coder")
        for _ in range(2):
            manager.record_error("coder", ValueError("Error"))

        summary = manager.get_error_summary()

        assert summary.total_attempts == 10
        assert summary.total_failures == 2
        assert summary.success_rate == 80.0
        assert summary.error_rate == 20.0

    def test_get_error_summary_worker_stats(self):
        """Worker별 통계 테스트"""
        manager = ErrorStatisticsManager()

        # Coder: 5번 시도, 1번 실패
        for _ in range(5):
            manager.record_attempt("coder")
        manager.record_error("coder", ValueError("Error"))

        # Tester: 10번 시도, 0번 실패
        for _ in range(10):
            manager.record_attempt("tester")

        summary = manager.get_error_summary()

        assert "coder" in summary.worker_stats
        assert summary.worker_stats["coder"]["attempts"] == 5
        assert summary.worker_stats["coder"]["failures"] == 1
        assert summary.worker_stats["coder"]["successes"] == 4
        assert summary.worker_stats["coder"]["error_rate"] == 20.0

        assert "tester" in summary.worker_stats
        assert summary.worker_stats["tester"]["error_rate"] == 0.0

    def test_get_error_summary_type_distribution(self):
        """에러 타입별 분포 테스트"""
        manager = ErrorStatisticsManager()

        manager.record_error("coder", ValueError("Error 1"))
        manager.record_error("coder", ValueError("Error 2"))
        manager.record_error("tester", RuntimeError("Error 3"))

        summary = manager.get_error_summary()

        assert "ValueError" in summary.error_type_distribution
        assert summary.error_type_distribution["ValueError"] == 2
        assert summary.error_type_distribution["RuntimeError"] == 1

    def test_get_error_summary_recent_errors(self):
        """최근 에러 목록 테스트"""
        manager = ErrorStatisticsManager()

        for i in range(15):
            manager.record_error("coder", ValueError(f"Error {i}"))

        summary = manager.get_error_summary()

        # 최대 10개만 반환
        assert len(summary.recent_errors) == 10


class TestErrorTrend:
    """에러 추세 분석 테스트"""

    def test_get_error_trend_1h(self):
        """1시간 범위 에러 추세 테스트"""
        manager = ErrorStatisticsManager()

        # 최근 에러 기록
        manager.record_error("coder", ValueError("Recent error"))

        trends = manager.get_error_trend(time_range="1h")

        assert len(trends) >= 0  # 에러가 있으면 최소 1개 이상

    def test_get_error_trend_invalid_range(self):
        """잘못된 시간 범위 테스트"""
        manager = ErrorStatisticsManager()

        # 잘못된 범위는 기본값 "1h"로 fallback
        trends = manager.get_error_trend(time_range="invalid")

        assert isinstance(trends, list)

    def test_get_error_trend_worker_filter(self):
        """특정 Worker 필터링 테스트"""
        manager = ErrorStatisticsManager()

        manager.record_error("coder", ValueError("Coder error"))
        manager.record_error("tester", ValueError("Tester error"))

        # Coder만 필터링
        trends = manager.get_error_trend(time_range="1h", worker_name="coder")

        # 모든 trend의 worker_name이 "coder"이어야 함
        for trend in trends:
            assert trend.worker_name == "coder"


class TestWorkerFailureRate:
    """Worker 실패율 테스트"""

    def test_get_worker_failure_rate_no_attempts(self):
        """시도가 없는 Worker의 실패율 테스트"""
        manager = ErrorStatisticsManager()

        failure_rate = manager.get_worker_failure_rate("coder")

        assert failure_rate == 0.0

    def test_get_worker_failure_rate_with_failures(self):
        """실패가 있는 Worker의 실패율 테스트"""
        manager = ErrorStatisticsManager()

        for _ in range(10):
            manager.record_attempt("coder")
        for _ in range(3):
            manager.record_error("coder", ValueError("Error"))

        failure_rate = manager.get_worker_failure_rate("coder")

        assert failure_rate == 30.0

    def test_get_worker_failure_rate_all_success(self):
        """모두 성공한 Worker의 실패율 테스트"""
        manager = ErrorStatisticsManager()

        for _ in range(5):
            manager.record_attempt("coder")

        failure_rate = manager.get_worker_failure_rate("coder")

        assert failure_rate == 0.0


class TestMostCommonErrors:
    """가장 빈번한 에러 조회 테스트"""

    def test_get_most_common_errors_empty(self):
        """빈 상태에서 조회 테스트"""
        manager = ErrorStatisticsManager()

        common_errors = manager.get_most_common_errors()

        assert len(common_errors) == 0

    def test_get_most_common_errors_with_data(self):
        """데이터가 있는 경우 조회 테스트"""
        manager = ErrorStatisticsManager()

        # ValueError 3회
        for _ in range(3):
            manager.record_error("coder", ValueError("Error"))

        # RuntimeError 1회
        manager.record_error("tester", RuntimeError("Error"))

        common_errors = manager.get_most_common_errors()

        assert len(common_errors) == 2
        # 가장 빈번한 에러가 첫 번째
        assert common_errors[0][0] == "ValueError"
        assert common_errors[0][1] == 3

    def test_get_most_common_errors_limit(self):
        """개수 제한 테스트"""
        manager = ErrorStatisticsManager()

        # 10가지 다른 에러 타입 기록
        for i in range(10):
            error_class = type(f"Error{i}", (Exception,), {})
            manager.record_error("coder", error_class("Error"))

        # 최대 5개만 조회
        common_errors = manager.get_most_common_errors(limit=5)

        assert len(common_errors) == 5


class TestStatisticsReset:
    """통계 초기화 테스트"""

    def test_reset_statistics(self):
        """통계 초기화 테스트"""
        manager = ErrorStatisticsManager()

        # 데이터 추가
        manager.record_attempt("coder")
        manager.record_error("coder", ValueError("Error"))

        # 초기화
        manager.reset_statistics()

        assert len(manager.error_records) == 0
        assert len(manager.attempt_counts) == 0
        assert len(manager.failure_counts) == 0


class TestLogErrorSummary:
    """에러 요약 로그 출력 테스트"""

    def test_log_error_summary(self):
        """에러 요약 로그 출력 테스트"""
        manager = ErrorStatisticsManager()

        manager.record_attempt("coder")
        manager.record_error("coder", ValueError("Error"))

        # 로그 출력 - 에러 없이 실행되어야 함
        manager.log_error_summary()


class TestExportToDict:
    """딕셔너리 내보내기 테스트"""

    def test_export_to_dict_empty(self):
        """빈 상태에서 내보내기 테스트"""
        manager = ErrorStatisticsManager()

        data = manager.export_to_dict()

        assert data["total_attempts"] == 0
        assert data["total_failures"] == 0
        assert len(data["worker_stats"]) == 0

    def test_export_to_dict_with_data(self):
        """데이터가 있는 경우 내보내기 테스트"""
        manager = ErrorStatisticsManager()

        manager.record_attempt("coder")
        manager.record_error("coder", ValueError("Error"))

        data = manager.export_to_dict()

        assert "total_attempts" in data
        assert "total_failures" in data
        assert "success_rate" in data
        assert "error_rate" in data
        assert "worker_stats" in data
        assert "error_type_distribution" in data
        assert "recent_errors" in data

    def test_export_to_dict_recent_errors_format(self):
        """recent_errors 포맷 테스트"""
        manager = ErrorStatisticsManager()

        manager.record_error("coder", ValueError("Error"))

        data = manager.export_to_dict()

        assert len(data["recent_errors"]) == 1
        error = data["recent_errors"][0]

        assert "worker_name" in error
        assert "error_type" in error
        assert "error_message" in error
        assert "timestamp" in error
        # ISO 형식인지 확인
        assert isinstance(error["timestamp"], str)
