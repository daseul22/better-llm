"""
Error Statistics Manager - 에러 통계 수집 및 분석

Worker 실행 중 발생하는 에러를 수집하고 통계를 생성합니다.
에러 타입별 빈도, Worker별 실패율, 시간대별 에러 분포 등을 분석합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import logging

from src.infrastructure.logging import get_logger

logger = get_logger(__name__, component="ErrorStatisticsManager")


@dataclass
class ErrorRecord:
    """에러 기록"""
    worker_name: str
    error_type: str
    error_message: str
    context: Dict[str, Any]
    timestamp: datetime
    traceback: Optional[str] = None


@dataclass
class ErrorSummary:
    """에러 요약"""
    total_attempts: int
    total_failures: int
    success_rate: float
    error_rate: float
    worker_stats: Dict[str, Dict[str, Any]]
    error_type_distribution: Dict[str, int]
    recent_errors: List[ErrorRecord] = field(default_factory=list)


@dataclass
class ErrorTrend:
    """에러 추세 데이터"""
    time_bucket: str
    error_count: int
    worker_name: Optional[str] = None


class ErrorStatisticsManager:
    """
    에러 통계 관리자

    Worker 실행 중 발생하는 에러를 기록하고 통계를 생성합니다.
    에러 타입별 빈도, Worker별 실패율, 시간대별 에러 분포 등을 분석합니다.

    Attributes:
        error_records: 에러 기록 리스트
        attempt_counts: Worker별 시도 횟수
        failure_counts: Worker별 실패 횟수
        metrics_repository: 메트릭 저장소 (선택적)

    Example:
        >>> manager = ErrorStatisticsManager()
        >>> manager.record_error(
        ...     worker_name="coder",
        ...     error=ValueError("Invalid input"),
        ...     context={"task": "refactoring"}
        ... )
        >>> summary = manager.get_error_summary()
        >>> print(f"Error rate: {summary.error_rate}%")
    """

    def __init__(self, metrics_repository=None, max_records: int = 1000):
        """
        ErrorStatisticsManager 초기화

        Args:
            metrics_repository: 메트릭 저장소 (선택적)
            max_records: 최대 에러 기록 개수
        """
        self.error_records: List[ErrorRecord] = []
        self.attempt_counts: Dict[str, int] = defaultdict(int)
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.metrics_repository = metrics_repository
        self.max_records = max_records

        logger.info("ErrorStatisticsManager initialized")

    def record_attempt(self, worker_name: str) -> None:
        """
        Worker 실행 시도 기록

        Args:
            worker_name: Worker 이름
        """
        self.attempt_counts[worker_name] += 1
        logger.debug(f"Attempt recorded for {worker_name}")

    def record_failure(self, worker_name: str, error_message: str = "") -> None:
        """
        Worker 실행 실패 기록 (간단한 실패 카운트)

        Args:
            worker_name: Worker 이름
            error_message: 에러 메시지 (선택적)
        """
        self.failure_counts[worker_name] += 1
        logger.debug(f"Failure recorded for {worker_name}: {error_message}")

    def record_error(
        self,
        worker_name: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        traceback_str: Optional[str] = None
    ) -> None:
        """
        에러 발생 기록

        Args:
            worker_name: Worker 이름
            error: 발생한 예외
            context: 에러 발생 컨텍스트
            traceback_str: 스택 트레이스 (선택적)
        """
        self.failure_counts[worker_name] += 1

        error_record = ErrorRecord(
            worker_name=worker_name,
            error_type=type(error).__name__,
            error_message=str(error),
            context=context or {},
            timestamp=datetime.now(),
            traceback=traceback_str
        )

        self.error_records.append(error_record)

        # 레코드 개수 제한
        if len(self.error_records) > self.max_records:
            self.error_records = self.error_records[-self.max_records:]

        logger.error(
            f"Error recorded for {worker_name}",
            error_type=error_record.error_type,
            error_message=error_record.error_message
        )

        # 메트릭 저장소가 있으면 저장
        if self.metrics_repository:
            try:
                self._save_to_repository(error_record)
            except Exception as e:
                logger.warning(f"Failed to save error to repository: {e}")

    def _save_to_repository(self, error_record: ErrorRecord) -> None:
        """
        메트릭 저장소에 에러 기록 저장

        Note:
            현재는 placeholder로 구현되어 있습니다.
            향후 MetricsRepository 인터페이스가 정의되면 다음과 같이 구현할 수 있습니다:
            - self.metrics_repository.save_error(error_record)
            - 데이터베이스, 파일 시스템, 또는 외부 API로 저장
        """
        pass

    def get_error_summary(self) -> ErrorSummary:
        """
        에러 통계 요약 조회

        Returns:
            ErrorSummary: 전체 에러 통계 요약
        """
        total_attempts = sum(self.attempt_counts.values())
        total_failures = sum(self.failure_counts.values())
        success_rate = (
            (total_attempts - total_failures) / total_attempts * 100
            if total_attempts > 0 else 0.0
        )
        error_rate = (
            total_failures / total_attempts * 100
            if total_attempts > 0 else 0.0
        )

        # Worker별 통계
        worker_stats = {}
        for worker_name in set(list(self.attempt_counts.keys()) + list(self.failure_counts.keys())):
            attempts = self.attempt_counts.get(worker_name, 0)
            failures = self.failure_counts.get(worker_name, 0)
            successes = attempts - failures
            worker_error_rate = (failures / attempts * 100) if attempts > 0 else 0.0

            worker_stats[worker_name] = {
                "attempts": attempts,
                "failures": failures,
                "successes": successes,
                "error_rate": round(worker_error_rate, 2)
            }

        # 에러 타입별 분포
        error_type_distribution = defaultdict(int)
        for record in self.error_records:
            error_type_distribution[record.error_type] += 1

        # 최근 에러 (최대 10개)
        recent_errors = self.error_records[-10:]

        return ErrorSummary(
            total_attempts=total_attempts,
            total_failures=total_failures,
            success_rate=round(success_rate, 2),
            error_rate=round(error_rate, 2),
            worker_stats=worker_stats,
            error_type_distribution=dict(error_type_distribution),
            recent_errors=recent_errors
        )

    def get_error_trend(
        self,
        time_range: str = "1h",
        worker_name: Optional[str] = None
    ) -> List[ErrorTrend]:
        """
        시간대별 에러 추세 조회

        Args:
            time_range: 시간 범위 ("1h", "6h", "24h", "7d")
            worker_name: 특정 Worker만 필터링 (None이면 전체)

        Returns:
            시간대별 에러 추세 리스트
        """
        # 시간 범위 파싱
        time_delta_map = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7)
        }

        if time_range not in time_delta_map:
            logger.warning(f"Invalid time_range: {time_range}. Using default '1h'")
            time_range = "1h"

        time_delta = time_delta_map[time_range]
        cutoff_time = datetime.now() - time_delta

        # 필터링
        filtered_records = [
            record for record in self.error_records
            if record.timestamp >= cutoff_time
            and (worker_name is None or record.worker_name == worker_name)
        ]

        # 시간대별 버킷 크기 결정
        bucket_size_map = {
            "1h": timedelta(minutes=10),
            "6h": timedelta(minutes=30),
            "24h": timedelta(hours=2),
            "7d": timedelta(hours=12)
        }
        bucket_size = bucket_size_map[time_range]

        # 버킷별 에러 수 집계
        buckets: Dict[str, int] = defaultdict(int)
        for record in filtered_records:
            # 시간을 버킷 단위로 내림
            bucket_time = record.timestamp - (
                record.timestamp - datetime.min
            ) % bucket_size
            bucket_key = bucket_time.strftime("%Y-%m-%d %H:%M:%S")
            buckets[bucket_key] += 1

        # ErrorTrend 리스트 생성
        trends = [
            ErrorTrend(
                time_bucket=bucket_key,
                error_count=count,
                worker_name=worker_name
            )
            for bucket_key, count in sorted(buckets.items())
        ]

        return trends

    def get_worker_failure_rate(self, worker_name: str) -> float:
        """
        특정 Worker의 실패율 조회

        Args:
            worker_name: Worker 이름

        Returns:
            실패율 (0.0 ~ 100.0)
        """
        attempts = self.attempt_counts.get(worker_name, 0)
        failures = self.failure_counts.get(worker_name, 0)

        if attempts == 0:
            return 0.0

        return round(failures / attempts * 100, 2)

    def get_most_common_errors(self, limit: int = 5) -> List[tuple[str, int]]:
        """
        가장 빈번한 에러 타입 조회

        Args:
            limit: 반환할 최대 개수

        Returns:
            (에러 타입, 발생 횟수) 튜플 리스트
        """
        error_type_counts = defaultdict(int)
        for record in self.error_records:
            error_type_counts[record.error_type] += 1

        # 발생 횟수 기준 내림차순 정렬
        sorted_errors = sorted(
            error_type_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_errors[:limit]

    def reset_statistics(self) -> None:
        """통계 초기화"""
        self.error_records.clear()
        self.attempt_counts.clear()
        self.failure_counts.clear()
        logger.info("✅ Error statistics reset")

    def log_error_summary(self) -> None:
        """에러 통계 요약 로그 출력"""
        summary = self.get_error_summary()

        logger.info("=" * 60)
        logger.info("📊 Worker Error Statistics Summary")
        logger.info("=" * 60)
        logger.info(f"Total Attempts: {summary.total_attempts}")
        logger.info(f"Total Failures: {summary.total_failures}")
        logger.info(f"Success Rate: {summary.success_rate}%")
        logger.info(f"Error Rate: {summary.error_rate}%")
        logger.info("")

        logger.info("📈 Worker-specific Statistics:")
        for worker_name, stats in summary.worker_stats.items():
            logger.info(
                f"  [{worker_name.upper()}] "
                f"Attempts: {stats['attempts']}, "
                f"Successes: {stats['successes']}, "
                f"Failures: {stats['failures']}, "
                f"Error Rate: {stats['error_rate']}%"
            )

        logger.info("")
        logger.info("🔍 Error Type Distribution:")
        for error_type, count in summary.error_type_distribution.items():
            logger.info(f"  - {error_type}: {count}")

        logger.info("=" * 60)

    def export_to_dict(self) -> Dict[str, Any]:
        """
        통계를 딕셔너리로 내보내기 (JSON 직렬화 가능)

        Returns:
            통계 데이터 딕셔너리
        """
        summary = self.get_error_summary()

        return {
            "total_attempts": summary.total_attempts,
            "total_failures": summary.total_failures,
            "success_rate": summary.success_rate,
            "error_rate": summary.error_rate,
            "worker_stats": summary.worker_stats,
            "error_type_distribution": summary.error_type_distribution,
            "recent_errors": [
                {
                    "worker_name": record.worker_name,
                    "error_type": record.error_type,
                    "error_message": record.error_message,
                    "timestamp": record.timestamp.isoformat()
                }
                for record in summary.recent_errors
            ]
        }
