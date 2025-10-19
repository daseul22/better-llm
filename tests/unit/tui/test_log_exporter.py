"""
LogExporter 클래스 단위 테스트

테스트 항목:
- 로그 파일 저장 (텍스트)
- 로그 파일 저장 (Markdown)
- Rich 마크업 제거
- 보안: Path Traversal 공격 차단
- 빈 session_id 처리
- 특수문자 sanitization
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from src.presentation.tui.utils.log_exporter import LogExporter


class TestLogExporter:
    """LogExporter 클래스 테스트"""

    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리 생성"""
        temp = Path(tempfile.mkdtemp())
        yield temp
        # 테스트 후 정리
        if temp.exists():
            shutil.rmtree(temp)

    @pytest.fixture
    def sample_logs(self):
        """샘플 로그 데이터"""
        return [
            "[bold]Session started[/bold]",
            "User: hello",
            "[green]Manager:[/green] Processing...",
            "[red]Error:[/red] Something went wrong",
            "Plain text line",
        ]

    def test_export_to_file_basic(self, temp_dir, sample_logs):
        """기본 파일 저장 테스트"""
        filepath = LogExporter.export_to_file(
            lines=sample_logs,
            session_id="test_session",
            output_dir=temp_dir,
        )

        assert filepath is not None
        assert filepath.exists()
        assert filepath.suffix == ".log"
        assert "session_test_session_" in filepath.name

        # 파일 내용 확인
        content = filepath.read_text(encoding="utf-8")
        assert "Session started" in content
        assert "User: hello" in content
        assert "[bold]" not in content  # 마크업 제거됨
        assert "[green]" not in content

    def test_export_to_markdown_basic(self, temp_dir, sample_logs):
        """기본 Markdown 저장 테스트"""
        filepath = LogExporter.export_to_markdown(
            lines=sample_logs,
            session_id="test_session",
            output_dir=temp_dir,
        )

        assert filepath is not None
        assert filepath.exists()
        assert filepath.suffix == ".md"

        # 파일 내용 확인
        content = filepath.read_text(encoding="utf-8")
        assert "# AI Orchestration Session Log" in content
        assert "**Session ID:** `test_session`" in content
        assert "Session started" in content
        assert "[bold]" not in content  # 마크업 제거됨

    def test_clean_markup(self):
        """Rich 마크업 제거 테스트"""
        test_cases = [
            ("[bold]Hello[/bold]", "Hello"),
            ("[red]Error[/red] message", "Error message"),
            ("[bold blue on white]Text[/bold blue on white]", "Text"),
            ("Plain text", "Plain text"),
            ("[link=url]Link[/link]", "Link"),
            ("Multiple [red]colored[/red] [green]words[/green]", "Multiple colored words"),
        ]

        for input_text, expected in test_cases:
            result = LogExporter._clean_markup(input_text)
            assert result == expected, f"Failed for input: {input_text}"

    @pytest.mark.security
    def test_path_traversal_protection(self, temp_dir):
        """Path Traversal 공격 차단 테스트"""
        malicious_session_ids = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "../../sensitive_data",
            "../config",
            "test/../../../etc/passwd",
        ]

        for malicious_id in malicious_session_ids:
            filepath = LogExporter.export_to_file(
                lines=["test log"],
                session_id=malicious_id,
                output_dir=temp_dir,
            )

            # 파일이 저장되어야 함 (하지만 안전한 경로에)
            assert filepath is not None
            assert filepath.exists()

            # 파일이 output_dir 내부에 있는지 확인
            assert filepath.parent == temp_dir, (
                f"Path traversal detected! File saved at: {filepath}"
            )

            # 파일명에 '..' 또는 '/' 가 없는지 확인
            assert ".." not in filepath.name
            assert "/" not in filepath.name
            assert "\\" not in filepath.name

    @pytest.mark.security
    def test_empty_session_id(self, temp_dir):
        """빈 session_id 처리 테스트"""
        # 빈 문자열
        result = LogExporter.export_to_file(
            lines=["test"],
            session_id="",
            output_dir=temp_dir,
        )
        assert result is None

        # 특수문자만 있는 경우
        result = LogExporter.export_to_file(
            lines=["test"],
            session_id="!@#$%^&*()",
            output_dir=temp_dir,
        )
        assert result is None

    @pytest.mark.security
    def test_special_characters_sanitization(self, temp_dir):
        """특수문자 sanitization 테스트"""
        test_cases = [
            ("test/session", "testsession"),
            ("test\\session", "testsession"),
            ("test:session", "testsession"),
            ("test*session", "testsession"),
            ("test?session", "testsession"),
            ("test<session>", "testsession"),
            ("test|session", "testsession"),
            ("test session", "testsession"),  # 공백
            ("test.session", "testsession"),  # 점
        ]

        for input_id, expected_safe_id in test_cases:
            filepath = LogExporter.export_to_file(
                lines=["test"],
                session_id=input_id,
                output_dir=temp_dir,
            )

            assert filepath is not None
            # 안전한 ID가 파일명에 포함되어야 함
            assert expected_safe_id in filepath.name

    def test_valid_session_ids(self, temp_dir):
        """유효한 session_id 테스트"""
        valid_ids = [
            "session123",
            "test-session",
            "test_session",
            "SESSION_123",
            "a1b2c3",
        ]

        for session_id in valid_ids:
            filepath = LogExporter.export_to_file(
                lines=["test"],
                session_id=session_id,
                output_dir=temp_dir,
            )

            assert filepath is not None
            assert filepath.exists()
            assert session_id in filepath.name

    def test_directory_creation(self, temp_dir):
        """출력 디렉토리 자동 생성 테스트"""
        nested_dir = temp_dir / "nested" / "logs"

        filepath = LogExporter.export_to_file(
            lines=["test"],
            session_id="test",
            output_dir=nested_dir,
        )

        assert filepath is not None
        assert filepath.exists()
        assert nested_dir.exists()

    def test_empty_logs(self, temp_dir):
        """빈 로그 리스트 테스트"""
        filepath = LogExporter.export_to_file(
            lines=[],
            session_id="empty_session",
            output_dir=temp_dir,
        )

        assert filepath is not None
        assert filepath.exists()

        # 파일이 비어있거나 빈 줄만 있어야 함
        content = filepath.read_text(encoding="utf-8")
        assert content.strip() == ""

    def test_unicode_content(self, temp_dir):
        """유니코드 내용 테스트"""
        unicode_logs = [
            "한글 로그",
            "日本語ログ",
            "中文日志",
            "Emoji test: 🚀 🎉 ✅",
        ]

        filepath = LogExporter.export_to_file(
            lines=unicode_logs,
            session_id="unicode_test",
            output_dir=temp_dir,
        )

        assert filepath is not None
        content = filepath.read_text(encoding="utf-8")

        for line in unicode_logs:
            assert line in content

    def test_markdown_format_structure(self, temp_dir):
        """Markdown 포맷 구조 테스트"""
        logs = ["Line 1", "Line 2", "Line 3"]

        filepath = LogExporter.export_to_markdown(
            lines=logs,
            session_id="md_test",
            output_dir=temp_dir,
        )

        content = filepath.read_text(encoding="utf-8")

        # Markdown 헤더 구조 확인
        assert content.startswith("# AI Orchestration Session Log")
        assert "**Session ID:**" in content
        assert "**Exported:**" in content
        assert "---" in content

        # 로그 내용 확인
        for line in logs:
            assert line in content

    def test_export_error_handling(self):
        """에러 처리 테스트 (잘못된 경로)"""
        # 쓰기 권한이 없는 경로 (Unix 시스템)
        invalid_path = Path("/root/forbidden/logs")

        result = LogExporter.export_to_file(
            lines=["test"],
            session_id="test",
            output_dir=invalid_path,
        )

        # 실패 시 None 반환
        assert result is None
