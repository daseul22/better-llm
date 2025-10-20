"""
WorkerOutputManager 모듈

Worker 출력 관리 책임:
- 실시간 출력 스트리밍
- 로그 필터링
- 출력 히스토리 관리
"""

import re
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass
from datetime import datetime

from infrastructure.logging import get_logger

logger = get_logger(__name__, component="WorkerOutputManager")


@dataclass
class OutputLine:
    """
    출력 라인 데이터

    Attributes:
        worker_id: Worker ID
        content: 출력 내용
        timestamp: 타임스탬프
        line_number: 라인 번호
    """
    worker_id: str
    content: str
    timestamp: datetime
    line_number: int

    def __str__(self) -> str:
        time_str = self.timestamp.strftime("%H:%M:%S")
        return f"[{time_str}] {self.worker_id}: {self.content}"


class WorkerOutputManager:
    """
    Worker 출력 관리자

    여러 Worker의 출력을 실시간으로 스트리밍하고 필터링합니다.

    Example:
        >>> manager = WorkerOutputManager()
        >>> manager.stream_output("coder", "Starting implementation...")
        >>> manager.stream_output("tester", "Running tests...")
        >>> history = manager.get_output_history("coder")
        >>> filtered = manager.filter_output("test")
    """

    def __init__(self, max_history_size: int = 1000) -> None:
        """
        WorkerOutputManager 초기화

        Args:
            max_history_size: 각 Worker별 최대 히스토리 크기 (기본값: 1000)
        """
        self._output_history: Dict[str, deque[OutputLine]] = {}
        self._all_output: deque[OutputLine] = deque(maxlen=max_history_size)
        self._max_history_size = max_history_size
        self._line_counter: Dict[str, int] = {}
        self._subscribers: Dict[str, List[callable]] = {}
        logger.info(f"WorkerOutputManager initialized (max_history: {max_history_size})")

    def stream_output(self, worker_id: str, output: str) -> None:
        """
        Worker 출력을 실시간으로 스트리밍합니다.

        Args:
            worker_id: Worker ID
            output: 출력 내용

        Example:
            >>> manager = WorkerOutputManager()
            >>> manager.stream_output("coder", "Implementation started")
            >>> manager.stream_output("coder", "Function foo() created")
        """
        if not output:
            return

        # Worker별 히스토리 초기화
        if worker_id not in self._output_history:
            self._output_history[worker_id] = deque(maxlen=self._max_history_size)
            self._line_counter[worker_id] = 0

        # 라인 번호 증가
        self._line_counter[worker_id] += 1
        line_number = self._line_counter[worker_id]

        # OutputLine 생성
        output_line = OutputLine(
            worker_id=worker_id,
            content=output,
            timestamp=datetime.now(),
            line_number=line_number
        )

        # 히스토리에 추가
        self._output_history[worker_id].append(output_line)
        self._all_output.append(output_line)

        # 구독자에게 알림
        self._notify_subscribers(worker_id, output_line)

        logger.debug(f"Output streamed: {worker_id} (line {line_number})")

    def filter_output(self, pattern: str, worker_id: Optional[str] = None) -> List[str]:
        """
        정규 표현식 패턴으로 출력을 필터링합니다.

        Args:
            pattern: 정규 표현식 패턴
            worker_id: 특정 Worker ID (None이면 전체 검색)

        Returns:
            필터링된 출력 라인 목록

        Raises:
            re.error: 잘못된 정규 표현식 패턴

        Example:
            >>> manager = WorkerOutputManager()
            >>> manager.stream_output("coder", "Error: File not found")
            >>> manager.stream_output("coder", "Success: Implementation done")
            >>> errors = manager.filter_output(r"Error:")
            >>> print(len(errors))
            1
        """
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            logger.error(f"Invalid regex pattern: {pattern} - {e}")
            raise

        # 검색 대상 선택
        if worker_id:
            if worker_id not in self._output_history:
                logger.warning(f"Worker not found: {worker_id}")
                return []
            output_lines = self._output_history[worker_id]
        else:
            output_lines = self._all_output

        # 필터링
        filtered = [
            line.content
            for line in output_lines
            if regex.search(line.content)
        ]

        logger.debug(
            f"Filtered output: pattern='{pattern}', worker={worker_id}, "
            f"results={len(filtered)}"
        )

        return filtered

    def get_output_history(
        self,
        worker_id: str,
        limit: int = 100
    ) -> List[str]:
        """
        특정 Worker의 출력 히스토리를 조회합니다.

        Args:
            worker_id: Worker ID
            limit: 최대 반환 개수 (기본값: 100)

        Returns:
            출력 라인 목록 (최신순)

        Example:
            >>> manager = WorkerOutputManager()
            >>> manager.stream_output("coder", "Line 1")
            >>> manager.stream_output("coder", "Line 2")
            >>> history = manager.get_output_history("coder", limit=10)
            >>> print(len(history))
            2
        """
        if worker_id not in self._output_history:
            logger.warning(f"Worker not found: {worker_id}")
            return []

        output_lines = list(self._output_history[worker_id])
        # 최신 순으로 정렬
        output_lines.sort(key=lambda x: x.timestamp, reverse=True)

        result = [line.content for line in output_lines[:limit]]
        logger.debug(f"Retrieved history: {worker_id} ({len(result)} lines)")

        return result

    def get_all_output_history(self, limit: int = 100) -> List[str]:
        """
        모든 Worker의 출력 히스토리를 조회합니다.

        Args:
            limit: 최대 반환 개수 (기본값: 100)

        Returns:
            출력 라인 목록 (최신순)

        Example:
            >>> manager = WorkerOutputManager()
            >>> manager.stream_output("coder", "Coder output")
            >>> manager.stream_output("tester", "Tester output")
            >>> all_history = manager.get_all_output_history()
            >>> print(len(all_history))
            2
        """
        output_lines = list(self._all_output)
        # 최신 순으로 정렬
        output_lines.sort(key=lambda x: x.timestamp, reverse=True)

        result = [line.content for line in output_lines[:limit]]
        logger.debug(f"Retrieved all history ({len(result)} lines)")

        return result

    def clear_worker_output(self, worker_id: str) -> None:
        """
        특정 Worker의 출력을 삭제합니다.

        Args:
            worker_id: Worker ID

        Example:
            >>> manager = WorkerOutputManager()
            >>> manager.stream_output("coder", "Test output")
            >>> manager.clear_worker_output("coder")
            >>> history = manager.get_output_history("coder")
            >>> print(len(history))
            0
        """
        if worker_id in self._output_history:
            self._output_history[worker_id].clear()
            self._line_counter[worker_id] = 0
            logger.info(f"Cleared output for worker: {worker_id}")
        else:
            logger.warning(f"Worker not found: {worker_id}")

    def clear_all_output(self) -> None:
        """
        모든 Worker의 출력을 삭제합니다.

        Example:
            >>> manager = WorkerOutputManager()
            >>> manager.stream_output("coder", "Test 1")
            >>> manager.stream_output("tester", "Test 2")
            >>> manager.clear_all_output()
            >>> all_history = manager.get_all_output_history()
            >>> print(len(all_history))
            0
        """
        self._output_history.clear()
        self._all_output.clear()
        self._line_counter.clear()
        logger.info("Cleared all output")

    def get_worker_list(self) -> List[str]:
        """
        출력 히스토리가 있는 모든 Worker ID 목록을 반환합니다.

        Returns:
            Worker ID 리스트

        Example:
            >>> manager = WorkerOutputManager()
            >>> manager.stream_output("coder", "Output 1")
            >>> manager.stream_output("tester", "Output 2")
            >>> workers = manager.get_worker_list()
            >>> print(sorted(workers))
            ['coder', 'tester']
        """
        return list(self._output_history.keys())

    def get_worker_output_count(self, worker_id: str) -> int:
        """
        특정 Worker의 총 출력 라인 수를 반환합니다.

        Args:
            worker_id: Worker ID

        Returns:
            출력 라인 수

        Example:
            >>> manager = WorkerOutputManager()
            >>> manager.stream_output("coder", "Line 1")
            >>> manager.stream_output("coder", "Line 2")
            >>> count = manager.get_worker_output_count("coder")
            >>> print(count)
            2
        """
        if worker_id not in self._output_history:
            return 0
        return len(self._output_history[worker_id])

    def subscribe(
        self,
        worker_id: str,
        callback: callable
    ) -> None:
        """
        특정 Worker의 출력을 실시간으로 구독합니다.

        Args:
            worker_id: Worker ID
            callback: 출력 발생 시 호출될 콜백 함수 (OutputLine을 인자로 받음)

        Example:
            >>> manager = WorkerOutputManager()
            >>> def on_output(line):
            ...     print(f"Received: {line.content}")
            >>> manager.subscribe("coder", on_output)
            >>> manager.stream_output("coder", "New output")
        """
        if worker_id not in self._subscribers:
            self._subscribers[worker_id] = []

        self._subscribers[worker_id].append(callback)
        logger.debug(f"Subscribed to worker: {worker_id}")

    def unsubscribe(
        self,
        worker_id: str,
        callback: callable
    ) -> None:
        """
        Worker 출력 구독을 취소합니다.

        Args:
            worker_id: Worker ID
            callback: 등록된 콜백 함수

        Example:
            >>> manager = WorkerOutputManager()
            >>> def on_output(line):
            ...     print(line.content)
            >>> manager.subscribe("coder", on_output)
            >>> manager.unsubscribe("coder", on_output)
        """
        if worker_id in self._subscribers:
            try:
                self._subscribers[worker_id].remove(callback)
                logger.debug(f"Unsubscribed from worker: {worker_id}")
            except ValueError:
                logger.warning(f"Callback not found for worker: {worker_id}")

    def _notify_subscribers(
        self,
        worker_id: str,
        output_line: OutputLine
    ) -> None:
        """
        구독자들에게 새로운 출력을 알립니다.

        Args:
            worker_id: Worker ID
            output_line: 출력 라인 데이터
        """
        if worker_id not in self._subscribers:
            return

        for callback in self._subscribers[worker_id]:
            try:
                callback(output_line)
            except Exception as e:
                logger.error(
                    f"Error in subscriber callback for {worker_id}: {e}",
                    exc_info=True
                )

    def search_output(
        self,
        keyword: str,
        worker_id: Optional[str] = None,
        case_sensitive: bool = False
    ) -> List[OutputLine]:
        """
        키워드로 출력을 검색합니다.

        Args:
            keyword: 검색 키워드
            worker_id: 특정 Worker ID (None이면 전체 검색)
            case_sensitive: 대소문자 구분 여부 (기본값: False)

        Returns:
            검색 결과 OutputLine 리스트

        Example:
            >>> manager = WorkerOutputManager()
            >>> manager.stream_output("coder", "Error occurred")
            >>> manager.stream_output("coder", "Success")
            >>> results = manager.search_output("error")
            >>> print(len(results))
            1
        """
        # 검색 대상 선택
        if worker_id:
            if worker_id not in self._output_history:
                logger.warning(f"Worker not found: {worker_id}")
                return []
            output_lines = self._output_history[worker_id]
        else:
            output_lines = self._all_output

        # 검색
        search_keyword = keyword if case_sensitive else keyword.lower()
        results = []

        for line in output_lines:
            content = line.content if case_sensitive else line.content.lower()
            if search_keyword in content:
                results.append(line)

        logger.debug(
            f"Searched output: keyword='{keyword}', worker={worker_id}, "
            f"results={len(results)}"
        )

        return results

    def get_latest_output(
        self,
        worker_id: str,
        count: int = 10
    ) -> List[str]:
        """
        특정 Worker의 최신 출력을 조회합니다.

        Args:
            worker_id: Worker ID
            count: 반환할 라인 수 (기본값: 10)

        Returns:
            최신 출력 라인 목록

        Example:
            >>> manager = WorkerOutputManager()
            >>> for i in range(20):
            ...     manager.stream_output("coder", f"Line {i}")
            >>> latest = manager.get_latest_output("coder", count=5)
            >>> print(len(latest))
            5
        """
        if worker_id not in self._output_history:
            logger.warning(f"Worker not found: {worker_id}")
            return []

        output_lines = list(self._output_history[worker_id])
        # 최신 N개만 반환
        latest_lines = output_lines[-count:] if len(output_lines) > count else output_lines

        result = [line.content for line in latest_lines]
        logger.debug(f"Retrieved latest output: {worker_id} ({len(result)} lines)")

        return result
