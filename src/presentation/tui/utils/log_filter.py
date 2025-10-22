"""
로그 필터링 유틸리티

로그 레벨, Worker, 시간대별 실시간 필터링을 제공합니다.
"""

import re
from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Optional, Set


@dataclass
class LogEntry:
    """
    파싱된 로그 엔트리.

    Attributes:
        raw_line: 원본 로그 라인
        timestamp: 타임스탬프 (HH:MM:SS 형식에서 추출)
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
        worker: Worker 이름 (예: Coder, Reviewer, None)
        message: 로그 메시지 본문
        line_number: 원본 로그에서의 라인 번호
    """
    raw_line: str
    timestamp: Optional[time]
    level: Optional[str]
    worker: Optional[str]
    message: str
    line_number: int


class LogFilter:
    """
    로그 필터링 엔진.

    로그 레벨, Worker, 시간대별 필터링을 수행하며, 성능 최적화를 위해
    최대 라인 수 제한을 적용합니다.
    """

    # 로그 파싱 정규식 패턴
    # 예: "2024-01-23 14:30:45 [INFO] [Coder] 코드 작성 완료"
    # 또는: "14:30:45 | INFO | [Coder] 코드 작성 완료"
    # ReDoS 방지: .*? 대신 구체적인 패턴 사용
    LOG_PATTERN = re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})?'  # 시간 (선택적)
        r'[^\[\]]*?'  # 중간 구분자 (대괄호 제외, ReDoS 방지)
        r'(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)?'  # 로그 레벨 (선택적)
        r'[^\[\]]*?'  # 중간 구분자 (대괄호 제외, ReDoS 방지)
        r'(?:\[(?P<worker>\w+)\])?'  # Worker 이름 (선택적, 대괄호)
        r'(?P<message>.*)',  # 나머지 메시지
        re.IGNORECASE
    )

    # 성능 최적화: 최근 N줄만 메모리 유지
    MAX_LINES = 1000

    # ReDoS 방지: 최대 로그 라인 길이 제한 (10KB)
    MAX_LOG_LINE_LENGTH = 10000

    def parse_log_line(self, line: str, line_number: int) -> LogEntry:
        """
        로그 라인을 파싱하여 LogEntry 객체 생성.

        Args:
            line: 원본 로그 라인
            line_number: 라인 번호

        Returns:
            파싱된 LogEntry 객체 (파싱 실패 시 raw_line만 설정)
        """
        # 빈 라인 처리
        if not line.strip():
            return LogEntry(
                raw_line=line,
                timestamp=None,
                level=None,
                worker=None,
                message=line,
                line_number=line_number
            )

        # ReDoS 방지: 최대 라인 길이 검증 및 truncation
        if len(line) > self.MAX_LOG_LINE_LENGTH:
            line = line[:self.MAX_LOG_LINE_LENGTH] + "... [truncated]"

        match = self.LOG_PATTERN.match(line)

        if not match:
            # 파싱 실패 시 raw_line만 설정 (fallback)
            return LogEntry(
                raw_line=line,
                timestamp=None,
                level=None,
                worker=None,
                message=line,
                line_number=line_number
            )

        # 타임스탬프 파싱
        timestamp = None
        if match.group('time'):
            try:
                timestamp = datetime.strptime(match.group('time'), '%H:%M:%S').time()
            except ValueError:
                # 타임스탬프 파싱 실패 시 None
                pass

        # 로그 레벨 정규화 (대문자)
        level = match.group('level')
        if level:
            level = level.upper()

        return LogEntry(
            raw_line=line,
            timestamp=timestamp,
            level=level,
            worker=match.group('worker'),
            message=match.group('message') or line,
            line_number=line_number
        )

    def filter_by_level(self, lines: List[str], levels: Set[str]) -> List[str]:
        """
        로그 레벨로 필터링.

        Args:
            lines: 로그 라인 리스트
            levels: 필터링할 로그 레벨 집합 (예: {"DEBUG", "INFO"})

        Returns:
            필터링된 로그 라인 리스트
        """
        if not levels:
            # 레벨 필터가 비어있으면 모든 라인 반환
            return lines

        # 최근 MAX_LINES만 처리 (성능 최적화)
        lines_to_process = lines[-self.MAX_LINES:] if len(lines) > self.MAX_LINES else lines

        filtered = []
        for i, line in enumerate(lines_to_process):
            entry = self.parse_log_line(line, i)
            # 레벨이 없는 라인은 포함 (일반 메시지일 수 있음)
            if entry.level is None or entry.level in levels:
                filtered.append(line)

        return filtered

    def filter_by_worker(self, lines: List[str], worker_name: Optional[str]) -> List[str]:
        """
        Worker 이름으로 필터링.

        Args:
            lines: 로그 라인 리스트
            worker_name: Worker 이름 (None 또는 "All"이면 모든 라인 반환)

        Returns:
            필터링된 로그 라인 리스트
        """
        if not worker_name or worker_name.lower() == "all":
            # Worker 필터가 비어있거나 "All"이면 모든 라인 반환
            return lines

        # 최근 MAX_LINES만 처리 (성능 최적화)
        lines_to_process = lines[-self.MAX_LINES:] if len(lines) > self.MAX_LINES else lines

        filtered = []
        for i, line in enumerate(lines_to_process):
            entry = self.parse_log_line(line, i)
            # Worker가 없는 라인은 포함 (일반 메시지일 수 있음)
            # 또는 Worker 이름이 일치하면 포함 (대소문자 무시)
            if entry.worker is None or \
               (entry.worker and entry.worker.lower() == worker_name.lower()):
                filtered.append(line)

        return filtered

    def filter_by_time_range(
        self,
        lines: List[str],
        start_time: Optional[time],
        end_time: Optional[time]
    ) -> List[str]:
        """
        시간대별 필터링.

        Args:
            lines: 로그 라인 리스트
            start_time: 시작 시각 (None이면 시작 제한 없음)
            end_time: 종료 시각 (None이면 종료 제한 없음)

        Returns:
            필터링된 로그 라인 리스트
        """
        if start_time is None and end_time is None:
            # 시간 필터가 비어있으면 모든 라인 반환
            return lines

        # 최근 MAX_LINES만 처리 (성능 최적화)
        lines_to_process = lines[-self.MAX_LINES:] if len(lines) > self.MAX_LINES else lines

        filtered = []
        for i, line in enumerate(lines_to_process):
            entry = self.parse_log_line(line, i)

            # 타임스탬프가 없는 라인은 포함 (일반 메시지일 수 있음)
            if entry.timestamp is None:
                filtered.append(line)
                continue

            # 시간 범위 체크
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue

            filtered.append(line)

        return filtered

    def apply_filters(
        self,
        lines: List[str],
        levels: Optional[Set[str]] = None,
        worker: Optional[str] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None
    ) -> List[str]:
        """
        복합 필터 적용 (레벨 + Worker + 시간대).

        Args:
            lines: 로그 라인 리스트
            levels: 필터링할 로그 레벨 집합 (None이면 모든 레벨)
            worker: Worker 이름 (None 또는 "All"이면 모든 Worker)
            start_time: 시작 시각 (None이면 시작 제한 없음)
            end_time: 종료 시각 (None이면 종료 제한 없음)

        Returns:
            필터링된 로그 라인 리스트
        """
        # 필터링 수행 (순차 적용)
        filtered = lines

        # 1. 레벨 필터
        if levels:
            filtered = self.filter_by_level(filtered, levels)

        # 2. Worker 필터
        if worker and worker.lower() != "all":
            filtered = self.filter_by_worker(filtered, worker)

        # 3. 시간대 필터
        if start_time or end_time:
            filtered = self.filter_by_time_range(filtered, start_time, end_time)

        return filtered

    def extract_workers(self, lines: List[str]) -> List[str]:
        """
        로그에서 Worker 이름 목록 추출.

        Args:
            lines: 로그 라인 리스트

        Returns:
            고유한 Worker 이름 리스트 (정렬됨)
        """
        workers = set()

        # 최근 MAX_LINES만 처리 (성능 최적화)
        lines_to_process = lines[-self.MAX_LINES:] if len(lines) > self.MAX_LINES else lines

        for i, line in enumerate(lines_to_process):
            entry = self.parse_log_line(line, i)
            if entry.worker:
                workers.add(entry.worker)

        return sorted(workers)
