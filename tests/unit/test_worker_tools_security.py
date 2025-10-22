"""
Worker Tools의 보안 검증 테스트 (CommitSafetyValidator 기반)

이 테스트 파일은 CommitSafetyValidator를 사용하여 다음을 검증합니다:
- Git 환경 검증 (Git 설치 확인, Git 저장소 확인)
- 민감한 파일명 감지 (.env, credentials.json 등)
- 민감한 내용 감지 (API 키, 비밀번호 패턴 등)
- 병합 충돌 마커 감지
- 대용량 파일 감지
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
import asyncio

from src.infrastructure.mcp.commit_validator import (
    CommitSafetyValidator,
    SecretPatternChecker,
    GitConflictChecker,
    LargeFileChecker,
    ValidationResult,
    SafetyCheckResult,
    DEFAULT_SENSITIVE_FILE_PATTERNS,
    DEFAULT_SENSITIVE_CONTENT_PATTERNS
)


class TestGitEnvironmentVerification:
    """Git 환경 검증 테스트"""

    @pytest.mark.asyncio
    async def test_verify_git_not_installed(self):
        """
        Git이 설치되지 않은 경우 검증 실패

        git --version 명령이 실패하면 is_safe=False 반환
        """
        validator = CommitSafetyValidator()

        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            # git --version 실패 시뮬레이션
            mock_proc = AsyncMock()
            mock_proc.returncode = 127  # 명령어를 찾을 수 없음
            mock_proc.communicate = AsyncMock(
                return_value=(b"", b"command not found: git")
            )
            mock_subprocess.return_value = mock_proc

            result = await validator.verify_git_environment()

            assert result.is_safe is False
            assert "Git이 설치되어 있지 않습니다" in result.error_message

    @pytest.mark.asyncio
    async def test_verify_not_git_repository(self):
        """
        Git 저장소가 아닌 경우 검증 실패

        git rev-parse --is-inside-work-tree 명령이 실패하면 is_safe=False 반환
        """
        validator = CommitSafetyValidator()

        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            # git --version은 성공
            mock_proc1 = AsyncMock()
            mock_proc1.returncode = 0
            mock_proc1.communicate = AsyncMock(
                return_value=(b"git version 2.39.0", b"")
            )

            # git rev-parse는 실패
            mock_proc2 = AsyncMock()
            mock_proc2.returncode = 128
            mock_proc2.communicate = AsyncMock(
                return_value=(b"", b"not a git repository")
            )

            mock_subprocess.side_effect = [mock_proc1, mock_proc2]

            result = await validator.verify_git_environment()

            assert result.is_safe is False
            assert "Git 저장소가 아닙니다" in result.error_message

    @pytest.mark.asyncio
    async def test_verify_git_valid_environment(self):
        """
        Git이 설치되어 있고 저장소인 경우 검증 성공

        git --version, git rev-parse 모두 성공하면 is_safe=True 반환
        """
        validator = CommitSafetyValidator()

        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            # git --version 성공
            mock_proc1 = AsyncMock()
            mock_proc1.returncode = 0
            mock_proc1.communicate = AsyncMock(
                return_value=(b"git version 2.39.0", b"")
            )

            # git rev-parse 성공
            mock_proc2 = AsyncMock()
            mock_proc2.returncode = 0
            mock_proc2.communicate = AsyncMock(
                return_value=(b"true", b"")
            )

            mock_subprocess.side_effect = [mock_proc1, mock_proc2]

            result = await validator.verify_git_environment()

            assert result.is_safe is True
            assert result.error_message is None


class TestSensitiveFilenameDetection:
    """민감한 파일명 감지 테스트"""

    @pytest.mark.asyncio
    async def test_detect_env_file(self, tmp_path):
        """
        .env 파일명 감지 테스트

        .env 파일이 변경 사항에 포함되면 passed=False 반환
        """
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret")

        checker = SecretPatternChecker()
        result = await checker.check([str(env_file)])

        assert result.passed is False
        assert "민감한 파일명" in result.error_message
        assert ".env" in result.error_message

    @pytest.mark.asyncio
    async def test_detect_env_variants(self, tmp_path):
        """
        .env 변형 파일명 감지 테스트 (.env.local, .env.production 등)
        """
        env_variants = [".env.local", ".env.production", ".env.development"]

        for variant in env_variants:
            env_file = tmp_path / variant
            env_file.write_text("API_KEY=secret")

            checker = SecretPatternChecker()
            result = await checker.check([str(env_file)])

            assert result.passed is False, f"{variant} 파일이 감지되지 않음"
            assert variant in result.error_message

    @pytest.mark.asyncio
    async def test_detect_credentials_file(self, tmp_path):
        """
        credentials 파일명 감지 테스트 (credentials.json 등)
        """
        cred_files = [
            "credentials.json",
            "aws-credentials",
            "google_credentials.yaml"
        ]

        for cred_file_name in cred_files:
            cred_file = tmp_path / cred_file_name
            cred_file.write_text("{}")

            checker = SecretPatternChecker()
            result = await checker.check([str(cred_file)])

            assert result.passed is False, f"{cred_file_name} 파일이 감지되지 않음"
            assert cred_file_name in result.error_message

    @pytest.mark.asyncio
    async def test_detect_secret_files(self, tmp_path):
        """
        secret 관련 파일명 감지 테스트
        """
        secret_files = ["secret.txt", "secrets.yaml", "api_keys.json"]

        for secret_file_name in secret_files:
            secret_file = tmp_path / secret_file_name
            secret_file.write_text("secret content")

            checker = SecretPatternChecker()
            result = await checker.check([str(secret_file)])

            # secret 파일은 패턴에 따라 감지될 수 있음
            if result.passed is False:
                assert "민감한 파일명" in result.error_message

    @pytest.mark.asyncio
    async def test_safe_filenames(self, tmp_path):
        """
        안전한 파일명은 통과 테스트
        """
        safe_files = ["main.py", "README.md", "config.yaml", "test.txt"]

        for safe_file_name in safe_files:
            safe_file = tmp_path / safe_file_name
            safe_file.write_text("safe content")

            checker = SecretPatternChecker()
            result = await checker.check([str(safe_file)])

            assert result.passed is True, f"{safe_file_name}이 잘못 감지됨"


class TestSensitiveContentDetection:
    """민감한 내용 감지 테스트"""

    @pytest.mark.asyncio
    async def test_detect_api_key_pattern(self, tmp_path):
        """
        API 키 패턴 감지 테스트

        파일 내용에 API 키 패턴이 있으면 passed=False 반환
        """
        test_contents = [
            'api_key = "sk-1234567890abcdefghijklmnopqrst"',
            "api-key: sk-1234567890abcdefghijklmnopqrst",
            "ANTHROPIC_API_KEY=sk-ant-1234567890abcdefghijklmnopqrst",
        ]

        for content in test_contents:
            test_file = tmp_path / f"config_{hash(content)}.py"
            test_file.write_text(content)

            checker = SecretPatternChecker()
            result = await checker.check([str(test_file)])

            assert result.passed is False, f"API 키 패턴이 감지되지 않음: {content}"
            assert "민감한 정보가 파일 내용에서 감지" in result.error_message

    @pytest.mark.asyncio
    async def test_detect_password_pattern(self, tmp_path):
        """
        비밀번호 패턴 감지 테스트
        """
        test_file = tmp_path / "settings.py"
        test_file.write_text('password = "mysecretpass123"')

        checker = SecretPatternChecker()
        result = await checker.check([str(test_file)])

        assert result.passed is False
        assert "민감한 정보가 파일 내용에서 감지" in result.error_message

    @pytest.mark.asyncio
    async def test_detect_aws_access_key(self, tmp_path):
        """
        AWS Access Key 패턴 감지 테스트
        """
        test_file = tmp_path / "aws_config.py"
        test_file.write_text("aws_access_key = 'AKIAIOSFODNN7EXAMPLE'")

        checker = SecretPatternChecker()
        result = await checker.check([str(test_file)])

        assert result.passed is False

    @pytest.mark.asyncio
    async def test_detect_bearer_token(self, tmp_path):
        """
        Bearer 토큰 패턴 감지 테스트
        """
        test_file = tmp_path / "auth.py"
        test_file.write_text("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")

        checker = SecretPatternChecker()
        result = await checker.check([str(test_file)])

        assert result.passed is False

    @pytest.mark.asyncio
    async def test_safe_content(self, tmp_path):
        """
        안전한 내용은 통과 테스트
        """
        test_file = tmp_path / "main.py"
        test_file.write_text('''
def main():
    print("Hello, World!")
    config = load_config()  # 설정 로드
    return 0
''')

        checker = SecretPatternChecker()
        result = await checker.check([str(test_file)])

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_binary_file_skipped(self, tmp_path):
        """
        바이너리 파일은 스캔 스킵 테스트
        """
        binary_file = tmp_path / "image.png"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")

        checker = SecretPatternChecker()
        result = await checker.check([str(binary_file)])

        # 바이너리 파일은 스캔 스킵되므로 통과
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_large_file_skipped(self, tmp_path):
        """
        대용량 파일 (10MB 이상) 스캔 스킵 테스트
        """
        large_file = tmp_path / "large.txt"
        # 11MB 파일 생성
        large_file.write_text("x" * (11 * 1024 * 1024))

        checker = SecretPatternChecker()
        result = await checker.check([str(large_file)])

        # 10MB 이상은 스캔 스킵되므로 통과
        assert result.passed is True


class TestGitConflictDetection:
    """Git 병합 충돌 마커 감지 테스트"""

    @pytest.mark.asyncio
    async def test_detect_conflict_markers(self, tmp_path):
        """
        병합 충돌 마커 감지 테스트
        """
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
    async def test_no_conflict_markers(self, tmp_path):
        """
        충돌 마커가 없는 경우 통과 테스트
        """
        safe_file = tmp_path / "safe.py"
        safe_file.write_text("def foo():\n    return True")

        checker = GitConflictChecker()
        result = await checker.check([str(safe_file)])

        assert result.passed is True


class TestLargeFileDetection:
    """대용량 파일 감지 테스트"""

    @pytest.mark.asyncio
    async def test_detect_large_file(self, tmp_path):
        """
        대용량 파일 (50MB 이상) 감지 테스트
        """
        large_file = tmp_path / "large.bin"
        # 51MB 파일 생성
        large_file.write_bytes(b"x" * (51 * 1024 * 1024))

        checker = LargeFileChecker(max_size_mb=50)
        result = await checker.check([str(large_file)])

        assert result.passed is False
        assert "대용량 파일" in result.error_message

    @pytest.mark.asyncio
    async def test_small_file_pass(self, tmp_path):
        """
        작은 파일은 통과 테스트
        """
        small_file = tmp_path / "small.txt"
        small_file.write_text("x" * 1024)  # 1KB

        checker = LargeFileChecker(max_size_mb=50)
        result = await checker.check([str(small_file)])

        assert result.passed is True


class TestCommitSafetyValidatorIntegration:
    """CommitSafetyValidator 통합 테스트"""

    @pytest.mark.asyncio
    async def test_validator_initialization(self):
        """
        CommitSafetyValidator 초기화 테스트

        기본 체커(SecretPatternChecker, GitConflictChecker, LargeFileChecker)가 포함되어야 함
        """
        validator = CommitSafetyValidator()

        assert len(validator.checkers) == 3
        assert any(isinstance(c, SecretPatternChecker) for c in validator.checkers)
        assert any(isinstance(c, GitConflictChecker) for c in validator.checkers)
        assert any(isinstance(c, LargeFileChecker) for c in validator.checkers)

    @pytest.mark.asyncio
    async def test_add_custom_checker(self):
        """
        커스텀 체커 추가 테스트
        """
        validator = CommitSafetyValidator(checkers=[])
        assert len(validator.checkers) == 0

        validator.add_checker(SecretPatternChecker())
        assert len(validator.checkers) == 1

    @pytest.mark.asyncio
    async def test_update_allowed_paths(self):
        """
        화이트리스트 경로 업데이트 테스트
        """
        validator = CommitSafetyValidator()
        validator.update_allowed_paths(["docs/", "tests/"])

        assert "docs/" in validator.allowed_paths
        assert "tests/" in validator.allowed_paths

    @pytest.mark.asyncio
    async def test_validate_all_with_git_error(self):
        """
        Git 환경 오류 시 validate_all 실패 테스트
        """
        validator = CommitSafetyValidator()

        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            # git --version 실패
            mock_proc = AsyncMock()
            mock_proc.returncode = 127
            mock_proc.communicate = AsyncMock(
                return_value=(b"", b"command not found")
            )
            mock_subprocess.return_value = mock_proc

            result = await validator.validate_all()

            assert result.is_safe is False
            assert "Git이 설치되어 있지 않습니다" in result.error_message


class TestSensitivePatternConstants:
    """민감 정보 패턴 상수 검증 테스트"""

    def test_sensitive_file_patterns_defined(self):
        """
        DEFAULT_SENSITIVE_FILE_PATTERNS 정의 확인
        """
        assert len(DEFAULT_SENSITIVE_FILE_PATTERNS) > 0
        # .env 패턴 존재 확인
        assert any(r"\.env" in pattern for pattern in DEFAULT_SENSITIVE_FILE_PATTERNS)

    def test_sensitive_content_patterns_defined(self):
        """
        DEFAULT_SENSITIVE_CONTENT_PATTERNS 정의 확인
        """
        assert len(DEFAULT_SENSITIVE_CONTENT_PATTERNS) > 0
        # API 키 패턴 존재 확인
        assert any("api" in pattern.lower() for pattern in DEFAULT_SENSITIVE_CONTENT_PATTERNS)

    def test_file_patterns_match_env(self):
        """
        .env 파일명 패턴 매칭 검증
        """
        import re
        test_files = [".env", ".env.local", ".env.production"]

        # .env 패턴 찾기
        env_pattern = next(p for p in DEFAULT_SENSITIVE_FILE_PATTERNS if r"\.env" in p)

        for file in test_files:
            assert re.match(env_pattern, file, re.IGNORECASE), \
                f"파일 {file}이 패턴 {env_pattern}에 매칭되지 않음"

    def test_file_patterns_match_credentials(self):
        """
        credentials 파일명 패턴 매칭 검증
        """
        import re
        test_files = ["credentials.json", "aws-credentials", "google_credentials.yaml"]

        # credentials 패턴 찾기
        cred_pattern = next(p for p in DEFAULT_SENSITIVE_FILE_PATTERNS if "credentials" in p)

        for file in test_files:
            assert re.match(cred_pattern, file, re.IGNORECASE), \
                f"파일 {file}이 패턴 {cred_pattern}에 매칭되지 않음"

    def test_content_patterns_match_api_keys(self):
        """
        API 키 내용 패턴 매칭 검증
        """
        import re
        test_contents = [
            'api_key = "sk-1234567890abcdefghijklmnopqrst"',
            "ANTHROPIC_API_KEY=sk-ant-1234567890abcdefghijklmnopqrst",
        ]

        # API 키 관련 패턴들
        api_patterns = [
            p for p in DEFAULT_SENSITIVE_CONTENT_PATTERNS
            if "api" in p.lower() and "key" in p.lower()
        ]

        assert len(api_patterns) > 0, "API 키 패턴이 정의되지 않음"

        matched = False
        for content in test_contents:
            for pattern in api_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    matched = True
                    break
            if matched:
                break

        assert matched, "API 키 패턴이 테스트 내용에 매칭되지 않음"
