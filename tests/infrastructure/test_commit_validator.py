"""
CommitSafetyValidator 테스트
"""

import pytest
import tempfile
import os
from pathlib import Path
from src.infrastructure.mcp.commit_validator import (
    CommitSafetyValidator,
    SecretPatternChecker,
    GitConflictChecker,
    LargeFileChecker,
    SafetyCheckResult,
    ValidationResult
)


class TestSecretPatternChecker:
    """SecretPatternChecker 테스트"""

    @pytest.mark.asyncio
    async def test_no_sensitive_files(self, tmp_path):
        """민감한 파일이 없는 경우 테스트"""
        # 일반 파일 생성
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        checker = SecretPatternChecker()
        result = await checker.check([str(test_file)])

        assert result.passed is True
        assert result.check_name == "SecretPatternChecker"

    @pytest.mark.asyncio
    async def test_sensitive_filename_detected(self, tmp_path):
        """민감한 파일명 감지 테스트"""
        # .env 파일 생성
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=test")

        checker = SecretPatternChecker()
        result = await checker.check([str(env_file)])

        assert result.passed is False
        assert "민감한 파일명" in result.error_message
        assert ".env" in result.error_message

    @pytest.mark.asyncio
    async def test_credentials_file_detected(self, tmp_path):
        """credentials 파일명 감지 테스트"""
        cred_file = tmp_path / "credentials.json"
        cred_file.write_text("{}")

        checker = SecretPatternChecker()
        result = await checker.check([str(cred_file)])

        assert result.passed is False
        assert "credentials.json" in result.error_message

    @pytest.mark.asyncio
    async def test_sensitive_content_detected(self, tmp_path):
        """파일 내용에서 민감 정보 감지 테스트"""
        test_file = tmp_path / "config.py"
        test_file.write_text('api_key = "sk-1234567890abcdefghijklmnop"')

        checker = SecretPatternChecker()
        result = await checker.check([str(test_file)])

        assert result.passed is False
        assert "민감한 정보가 파일 내용에서 감지" in result.error_message

    @pytest.mark.asyncio
    async def test_password_in_content_detected(self, tmp_path):
        """비밀번호 패턴 감지 테스트"""
        test_file = tmp_path / "settings.py"
        test_file.write_text('password = "mysecretpass123"')

        checker = SecretPatternChecker()
        result = await checker.check([str(test_file)])

        assert result.passed is False

    @pytest.mark.asyncio
    async def test_binary_file_skipped(self, tmp_path):
        """바이너리 파일 스킵 테스트"""
        binary_file = tmp_path / "image.png"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")

        checker = SecretPatternChecker()
        result = await checker.check([str(binary_file)])

        # 바이너리 파일은 스캔 스킵되므로 통과
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_large_file_skipped(self, tmp_path):
        """대용량 파일 스캔 스킵 테스트"""
        large_file = tmp_path / "large.txt"
        # 11MB 파일 생성
        large_file.write_text("x" * (11 * 1024 * 1024))

        checker = SecretPatternChecker()
        result = await checker.check([str(large_file)])

        # 10MB 이상은 스캔 스킵
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_multiple_files_one_sensitive(self, tmp_path):
        """여러 파일 중 하나만 민감한 경우 테스트"""
        safe_file = tmp_path / "safe.py"
        safe_file.write_text("print('hello')")

        sensitive_file = tmp_path / "secrets.txt"
        sensitive_file.write_text("api_key = 'sk-12345678901234567890'")

        checker = SecretPatternChecker()
        result = await checker.check([str(safe_file), str(sensitive_file)])

        assert result.passed is False


class TestGitConflictChecker:
    """GitConflictChecker 테스트"""

    @pytest.mark.asyncio
    async def test_no_conflicts(self, tmp_path):
        """충돌 마커가 없는 경우 테스트"""
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo():\n    return True")

        checker = GitConflictChecker()
        result = await checker.check([str(test_file)])

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_conflict_marker_detected(self, tmp_path):
        """병합 충돌 마커 감지 테스트"""
        conflict_file = tmp_path / "conflicted.py"
        content = """
def foo():
<<<<<<< HEAD
    return True
=======
    return False
>>>>>>> branch
"""
        conflict_file.write_text(content)

        checker = GitConflictChecker()
        result = await checker.check([str(conflict_file)])

        assert result.passed is False
        assert "병합 충돌 마커" in result.error_message

    @pytest.mark.asyncio
    async def test_binary_file_skipped_for_conflicts(self, tmp_path):
        """바이너리 파일은 충돌 검사 스킵"""
        binary_file = tmp_path / "binary.dat"
        binary_file.write_bytes(b"\x00\x01\x02")

        checker = GitConflictChecker()
        result = await checker.check([str(binary_file)])

        assert result.passed is True


class TestLargeFileChecker:
    """LargeFileChecker 테스트"""

    @pytest.mark.asyncio
    async def test_small_file(self, tmp_path):
        """작은 파일 테스트"""
        small_file = tmp_path / "small.txt"
        small_file.write_text("x" * 1024)  # 1KB

        checker = LargeFileChecker(max_size_mb=50)
        result = await checker.check([str(small_file)])

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_large_file_detected(self, tmp_path):
        """대용량 파일 감지 테스트"""
        large_file = tmp_path / "large.bin"
        # 51MB 파일 생성
        large_file.write_bytes(b"x" * (51 * 1024 * 1024))

        checker = LargeFileChecker(max_size_mb=50)
        result = await checker.check([str(large_file)])

        assert result.passed is False
        assert "대용량 파일" in result.error_message

    @pytest.mark.asyncio
    async def test_custom_size_limit(self, tmp_path):
        """커스텀 크기 제한 테스트"""
        file = tmp_path / "file.txt"
        file.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB

        # 1MB 제한
        checker = LargeFileChecker(max_size_mb=1)
        result = await checker.check([str(file)])

        assert result.passed is False

        # 10MB 제한
        checker = LargeFileChecker(max_size_mb=10)
        result = await checker.check([str(file)])

        assert result.passed is True


class TestCommitSafetyValidator:
    """CommitSafetyValidator 통합 테스트"""

    @pytest.mark.asyncio
    async def test_initialization_default_checkers(self):
        """기본 체커로 초기화 테스트"""
        validator = CommitSafetyValidator()

        assert len(validator.checkers) == 3
        assert any(isinstance(c, SecretPatternChecker) for c in validator.checkers)
        assert any(isinstance(c, GitConflictChecker) for c in validator.checkers)
        assert any(isinstance(c, LargeFileChecker) for c in validator.checkers)

    @pytest.mark.asyncio
    async def test_add_checker(self):
        """체커 추가 테스트"""
        validator = CommitSafetyValidator(checkers=[])
        assert len(validator.checkers) == 0

        validator.add_checker(SecretPatternChecker())
        assert len(validator.checkers) == 1

    @pytest.mark.asyncio
    async def test_update_allowed_paths(self):
        """화이트리스트 경로 업데이트 테스트"""
        validator = CommitSafetyValidator()
        validator.update_allowed_paths(["docs/", "tests/"])

        assert "docs/" in validator.allowed_paths
        assert "tests/" in validator.allowed_paths

    @pytest.mark.asyncio
    async def test_verify_git_environment_no_git(self):
        """Git이 없는 환경 테스트 (시뮬레이션)"""
        # 실제 환경에서는 Git이 설치되어 있으므로 스킵
        pytest.skip("Git is installed in test environment")

    @pytest.mark.asyncio
    async def test_get_changed_files_no_git_repo(self, tmp_path, monkeypatch):
        """Git 저장소가 아닌 경우 테스트"""
        # 임시 디렉토리로 이동
        monkeypatch.chdir(tmp_path)

        validator = CommitSafetyValidator()
        success, files, error = await validator.get_changed_files()

        # Git 저장소가 아니므로 실패
        assert success is False
        assert error is not None


class TestValidationWorkflow:
    """전체 검증 워크플로우 테스트"""

    @pytest.mark.asyncio
    async def test_validate_all_no_changes(self, tmp_path, monkeypatch):
        """변경 사항이 없는 경우 테스트"""
        # Git 저장소가 아니므로 실패할 것으로 예상
        monkeypatch.chdir(tmp_path)

        validator = CommitSafetyValidator()
        result = await validator.validate_all()

        assert result.is_safe is False

    @pytest.mark.asyncio
    async def test_custom_checkers(self, tmp_path):
        """커스텀 체커 설정 테스트"""
        # SecretPatternChecker만 사용
        validator = CommitSafetyValidator(
            checkers=[SecretPatternChecker()]
        )

        assert len(validator.checkers) == 1


class TestSafetyCheckResult:
    """SafetyCheckResult 데이터클래스 테스트"""

    def test_passed_result(self):
        """통과 결과 생성 테스트"""
        result = SafetyCheckResult(
            passed=True,
            check_name="TestChecker"
        )

        assert result.passed is True
        assert result.check_name == "TestChecker"
        assert result.error_message is None
        assert result.details is None

    def test_failed_result_with_details(self):
        """실패 결과 생성 테스트"""
        result = SafetyCheckResult(
            passed=False,
            check_name="TestChecker",
            error_message="Test error",
            details={"files": ["test.py"]}
        )

        assert result.passed is False
        assert result.error_message == "Test error"
        assert "files" in result.details


class TestValidationResult:
    """ValidationResult 데이터클래스 테스트"""

    def test_safe_result(self):
        """안전한 결과 생성 테스트"""
        result = ValidationResult(is_safe=True)

        assert result.is_safe is True
        assert result.error_message is None
        assert result.check_results == []

    def test_unsafe_result_with_checks(self):
        """안전하지 않은 결과 생성 테스트"""
        check_result = SafetyCheckResult(
            passed=False,
            check_name="TestChecker",
            error_message="Test error"
        )

        result = ValidationResult(
            is_safe=False,
            error_message="Validation failed",
            check_results=[check_result]
        )

        assert result.is_safe is False
        assert result.error_message == "Validation failed"
        assert len(result.check_results) == 1
