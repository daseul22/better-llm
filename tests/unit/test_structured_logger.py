"""
Tests for structured logging

src/infrastructure/logging/structured_logger.py 테스트
"""
import pytest
import logging
from pathlib import Path
import json
import structlog

from src.infrastructure.logging.structured_logger import (
    configure_structlog,
    get_logger,
)


@pytest.mark.unit
class TestStructuredLogger:
    """구조화된 로깅 테스트"""

    def test_configure_structlog_creates_log_dir(self, tmp_path: Path):
        """configure_structlog이 로그 디렉토리를 생성하는지 테스트"""
        log_dir = tmp_path / "logs"

        configure_structlog(
            log_dir=str(log_dir),
            log_level="INFO",
            enable_json=True
        )

        assert log_dir.exists()
        assert (log_dir / "better-llm.log").exists()

    def test_configure_structlog_creates_error_log(self, tmp_path: Path):
        """configure_structlog이 에러 로그 파일을 생성하는지 테스트"""
        log_dir = tmp_path / "logs"

        configure_structlog(
            log_dir=str(log_dir),
            log_level="INFO",
            enable_json=True
        )

        assert (log_dir / "better-llm-error.log").exists()

    def test_configure_structlog_debug_mode(self, tmp_path: Path):
        """DEBUG 모드에서 디버그 로그 파일이 생성되는지 테스트"""
        log_dir = tmp_path / "logs"

        configure_structlog(
            log_dir=str(log_dir),
            log_level="DEBUG",
            enable_json=True
        )

        assert (log_dir / "better-llm-debug.log").exists()

    def test_configure_structlog_with_json(self, tmp_path: Path):
        """JSON 출력 모드 테스트"""
        log_dir = tmp_path / "logs"

        configure_structlog(
            log_dir=str(log_dir),
            log_level="INFO",
            enable_json=True
        )

        logger = get_logger(__name__)
        logger.info("test message", key="value")

        # 로그 파일 읽기
        log_file = log_dir / "better-llm.log"
        log_content = log_file.read_text()

        # JSON 형식인지 확인 (파싱 가능한지)
        # 로그는 여러 줄일 수 있으므로 각 줄 확인
        for line in log_content.strip().split("\n"):
            if line:
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    pytest.fail(f"Log line is not valid JSON: {line}")

    def test_configure_structlog_with_console(self, tmp_path: Path):
        """콘솔 출력 모드 테스트"""
        log_dir = tmp_path / "logs"

        configure_structlog(
            log_dir=str(log_dir),
            log_level="INFO",
            enable_json=False
        )

        logger = get_logger(__name__)
        logger.info("test message", key="value")

        # 로그 파일이 생성되었는지 확인
        log_file = log_dir / "better-llm.log"
        assert log_file.exists()

    def test_get_logger_without_context(self):
        """컨텍스트 없이 로거 가져오기 테스트"""
        logger = get_logger(__name__)

        assert logger is not None
        assert isinstance(logger, structlog.stdlib.BoundLogger)

    def test_get_logger_with_context(self):
        """컨텍스트와 함께 로거 가져오기 테스트"""
        logger = get_logger(
            __name__,
            session_id="test-123",
            worker_name="planner"
        )

        assert logger is not None
        assert isinstance(logger, structlog.stdlib.BoundLogger)

    def test_get_logger_context_binding(self, tmp_path: Path):
        """로거 컨텍스트 바인딩 테스트"""
        log_dir = tmp_path / "logs"

        configure_structlog(
            log_dir=str(log_dir),
            log_level="INFO",
            enable_json=True
        )

        logger = get_logger(
            __name__,
            session_id="session-123",
            worker_name="coder"
        )

        logger.info("Task started", task_id="task-001")

        # 로그 파일 읽기
        log_file = log_dir / "better-llm.log"
        log_content = log_file.read_text()

        # JSON 파싱
        log_lines = [json.loads(line) for line in log_content.strip().split("\n") if line]

        # 최소 1개 이상의 로그가 있어야 함
        assert len(log_lines) > 0

        # 마지막 로그 확인 (우리가 방금 작성한 로그)
        last_log = log_lines[-1]
        assert last_log["event"] == "Task started"
        assert last_log.get("session_id") == "session-123"
        assert last_log.get("worker_name") == "coder"
        assert last_log.get("task_id") == "task-001"

    def test_logger_log_levels(self, tmp_path: Path):
        """로그 레벨 테스트"""
        log_dir = tmp_path / "logs"

        configure_structlog(
            log_dir=str(log_dir),
            log_level="DEBUG",
            enable_json=True
        )

        logger = get_logger(__name__)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # 로그 파일 읽기
        log_file = log_dir / "better-llm.log"
        log_content = log_file.read_text()

        # 모든 레벨의 로그가 기록되었는지 확인
        assert "Debug message" in log_content
        assert "Info message" in log_content
        assert "Warning message" in log_content
        assert "Error message" in log_content

    def test_error_log_file_only_errors(self, tmp_path: Path):
        """에러 로그 파일에 ERROR 이상만 기록되는지 테스트"""
        log_dir = tmp_path / "logs"

        configure_structlog(
            log_dir=str(log_dir),
            log_level="DEBUG",
            enable_json=True
        )

        logger = get_logger(__name__)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # 에러 로그 파일 읽기
        error_log_file = log_dir / "better-llm-error.log"
        error_log_content = error_log_file.read_text()

        # ERROR 이상만 기록되어야 함
        assert "Error message" in error_log_content
        assert "Critical message" in error_log_content
        assert "Debug message" not in error_log_content
        assert "Info message" not in error_log_content
        assert "Warning message" not in error_log_content


@pytest.mark.unit
class TestLoggerEdgeCases:
    """로거 엣지 케이스 테스트"""

    def test_logger_with_unicode(self, tmp_path: Path):
        """유니코드 문자 로깅 테스트"""
        log_dir = tmp_path / "logs"

        configure_structlog(
            log_dir=str(log_dir),
            log_level="INFO",
            enable_json=True
        )

        logger = get_logger(__name__)
        logger.info("한글 메시지", description="테스트 설명 🔥")

        # 로그 파일 읽기
        log_file = log_dir / "better-llm.log"
        log_content = log_file.read_text()

        assert "한글 메시지" in log_content
        assert "테스트 설명 🔥" in log_content

    def test_logger_with_exception(self, tmp_path: Path):
        """예외 로깅 테스트"""
        log_dir = tmp_path / "logs"

        configure_structlog(
            log_dir=str(log_dir),
            log_level="INFO",
            enable_json=True
        )

        logger = get_logger(__name__)

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Exception occurred")

        # 로그 파일 읽기
        log_file = log_dir / "better-llm.log"
        log_content = log_file.read_text()

        assert "Exception occurred" in log_content
        assert "ValueError" in log_content
        assert "Test exception" in log_content

    def test_logger_with_special_characters(self, tmp_path: Path):
        """특수 문자 로깅 테스트"""
        log_dir = tmp_path / "logs"

        configure_structlog(
            log_dir=str(log_dir),
            log_level="INFO",
            enable_json=True
        )

        logger = get_logger(__name__)
        logger.info("Special chars: \n\t\r")

        # 로그 파일이 생성되었는지만 확인
        log_file = log_dir / "better-llm.log"
        assert log_file.exists()
