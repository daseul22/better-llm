"""
WorkerOutputManager 단위 테스트
"""

import re
import pytest

from src.presentation.tui.managers.worker_output_manager import (
    WorkerOutputManager,
    OutputLine,
)


class TestWorkerOutputManager:
    """WorkerOutputManager 테스트 클래스"""

    def test_init(self):
        """초기화 테스트"""
        manager = WorkerOutputManager(max_history_size=500)
        assert manager is not None
        assert len(manager.get_worker_list()) == 0

    def test_stream_output(self):
        """출력 스트리밍 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Test output")

        history = manager.get_output_history("coder")
        assert len(history) == 1
        assert history[0] == "Test output"

    def test_stream_output_empty(self):
        """빈 출력 스트리밍 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "")

        history = manager.get_output_history("coder")
        assert len(history) == 0

    def test_filter_output_with_pattern(self):
        """정규 표현식 패턴으로 출력 필터링 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Error: File not found")
        manager.stream_output("coder", "Success: Implementation done")
        manager.stream_output("coder", "Error: Invalid syntax")

        errors = manager.filter_output(r"Error:")
        assert len(errors) == 2

    def test_filter_output_invalid_pattern(self):
        """잘못된 정규 표현식 패턴으로 필터링 시 에러 발생 테스트"""
        manager = WorkerOutputManager()

        with pytest.raises(re.error):
            manager.filter_output(r"[invalid")

    def test_filter_output_by_worker(self):
        """특정 Worker의 출력만 필터링 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Coder error")
        manager.stream_output("tester", "Tester error")

        filtered = manager.filter_output(r"error", worker_id="coder")
        assert len(filtered) == 1
        assert "Coder" in filtered[0]

    def test_filter_output_nonexistent_worker(self):
        """존재하지 않는 Worker 필터링 테스트"""
        manager = WorkerOutputManager()

        filtered = manager.filter_output(r"test", worker_id="nonexistent")
        assert len(filtered) == 0

    def test_get_output_history(self):
        """출력 히스토리 조회 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Line 1")
        manager.stream_output("coder", "Line 2")
        manager.stream_output("coder", "Line 3")

        history = manager.get_output_history("coder", limit=2)
        assert len(history) == 2

    def test_get_output_history_nonexistent_worker(self):
        """존재하지 않는 Worker의 히스토리 조회 테스트"""
        manager = WorkerOutputManager()

        history = manager.get_output_history("nonexistent")
        assert len(history) == 0

    def test_get_all_output_history(self):
        """모든 출력 히스토리 조회 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Coder output")
        manager.stream_output("tester", "Tester output")

        all_history = manager.get_all_output_history()
        assert len(all_history) == 2

    def test_clear_worker_output(self):
        """Worker 출력 삭제 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Test output")

        manager.clear_worker_output("coder")

        history = manager.get_output_history("coder")
        assert len(history) == 0

    def test_clear_worker_output_nonexistent(self):
        """존재하지 않는 Worker 출력 삭제 테스트"""
        manager = WorkerOutputManager()
        # 에러 없이 실행되어야 함
        manager.clear_worker_output("nonexistent")

    def test_clear_all_output(self):
        """모든 출력 삭제 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Test 1")
        manager.stream_output("tester", "Test 2")

        manager.clear_all_output()

        all_history = manager.get_all_output_history()
        assert len(all_history) == 0
        assert len(manager.get_worker_list()) == 0

    def test_get_worker_list(self):
        """Worker 목록 조회 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Output 1")
        manager.stream_output("tester", "Output 2")
        manager.stream_output("reviewer", "Output 3")

        workers = manager.get_worker_list()
        assert len(workers) == 3
        assert "coder" in workers
        assert "tester" in workers
        assert "reviewer" in workers

    def test_get_worker_output_count(self):
        """Worker 출력 라인 수 조회 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Line 1")
        manager.stream_output("coder", "Line 2")
        manager.stream_output("coder", "Line 3")

        count = manager.get_worker_output_count("coder")
        assert count == 3

    def test_get_worker_output_count_nonexistent(self):
        """존재하지 않는 Worker 출력 라인 수 조회 테스트"""
        manager = WorkerOutputManager()

        count = manager.get_worker_output_count("nonexistent")
        assert count == 0

    def test_subscribe(self):
        """출력 구독 테스트"""
        manager = WorkerOutputManager()
        received_lines = []

        def callback(line: OutputLine):
            received_lines.append(line.content)

        manager.subscribe("coder", callback)
        manager.stream_output("coder", "Test output")

        assert len(received_lines) == 1
        assert received_lines[0] == "Test output"

    def test_unsubscribe(self):
        """출력 구독 취소 테스트"""
        manager = WorkerOutputManager()
        received_lines = []

        def callback(line: OutputLine):
            received_lines.append(line.content)

        manager.subscribe("coder", callback)
        manager.unsubscribe("coder", callback)
        manager.stream_output("coder", "Test output")

        assert len(received_lines) == 0

    def test_search_output(self):
        """출력 검색 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Error occurred")
        manager.stream_output("coder", "Success")
        manager.stream_output("coder", "Another error")

        results = manager.search_output("error")
        assert len(results) == 2

    def test_search_output_case_sensitive(self):
        """대소문자 구분 검색 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Error occurred")
        manager.stream_output("coder", "error occurred")

        results = manager.search_output("Error", case_sensitive=True)
        assert len(results) == 1

    def test_search_output_by_worker(self):
        """특정 Worker 출력 검색 테스트"""
        manager = WorkerOutputManager()
        manager.stream_output("coder", "Coder error")
        manager.stream_output("tester", "Tester error")

        results = manager.search_output("error", worker_id="coder")
        assert len(results) == 1
        assert results[0].worker_id == "coder"

    def test_get_latest_output(self):
        """최신 출력 조회 테스트"""
        manager = WorkerOutputManager()

        for i in range(20):
            manager.stream_output("coder", f"Line {i}")

        latest = manager.get_latest_output("coder", count=5)
        assert len(latest) == 5
        assert "Line 19" in latest[-1]

    def test_get_latest_output_nonexistent_worker(self):
        """존재하지 않는 Worker의 최신 출력 조회 테스트"""
        manager = WorkerOutputManager()

        latest = manager.get_latest_output("nonexistent", count=5)
        assert len(latest) == 0

    def test_max_history_size(self):
        """최대 히스토리 크기 제한 테스트"""
        manager = WorkerOutputManager(max_history_size=10)

        # 15개 출력 추가
        for i in range(15):
            manager.stream_output("coder", f"Line {i}")

        all_history = manager.get_all_output_history(limit=100)
        # 최대 10개만 저장되어야 함
        assert len(all_history) <= 10

    def test_multiple_workers(self):
        """여러 Worker 동시 관리 테스트"""
        manager = WorkerOutputManager()

        manager.stream_output("coder", "Coder line 1")
        manager.stream_output("tester", "Tester line 1")
        manager.stream_output("coder", "Coder line 2")
        manager.stream_output("reviewer", "Reviewer line 1")

        assert len(manager.get_worker_list()) == 3
        assert manager.get_worker_output_count("coder") == 2
        assert manager.get_worker_output_count("tester") == 1
        assert manager.get_worker_output_count("reviewer") == 1

    def test_output_line_ordering(self):
        """출력 라인 순서 테스트"""
        manager = WorkerOutputManager()

        for i in range(5):
            manager.stream_output("coder", f"Line {i}")

        history = manager.get_output_history("coder", limit=10)
        # 최신 순으로 반환되어야 함
        assert "Line 4" in history[0]
        assert "Line 0" in history[-1]
