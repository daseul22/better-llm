"""
Worker Tools의 Committer 보안 검증 테스트

Critical Issue #2 검증:
- Git 환경 검증 (_verify_git_environment)
- 민감 정보 검증 (_validate_commit_safety)
- execute_committer_task의 보안 게이트
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from src.infrastructure.mcp import worker_tools
from src.infrastructure.mcp.worker_tools import (
    _verify_git_environment,
    _validate_commit_safety,
    SENSITIVE_FILE_PATTERNS,
    SENSITIVE_CONTENT_PATTERNS,
)


class TestGitEnvironmentVerification:
    """Git 환경 검증 테스트"""

    @pytest.mark.asyncio
    async def test_verify_git_not_installed(self):
        """
        Git이 설치되지 않은 경우 검증 실패

        git --version 명령이 실패하면 False 반환
        """
        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            # git --version 실패 시뮬레이션
            mock_proc = AsyncMock()
            mock_proc.returncode = 127  # 명령어를 찾을 수 없음
            mock_proc.communicate = AsyncMock(
                return_value=(b"", b"command not found: git")
            )
            mock_subprocess.return_value = mock_proc

            is_valid, error_msg = await _verify_git_environment()

            assert is_valid is False
            assert "Git이 설치되어 있지 않습니다" in error_msg

    @pytest.mark.asyncio
    async def test_verify_not_git_repository(self):
        """
        Git 저장소가 아닌 경우 검증 실패

        git rev-parse --is-inside-work-tree 명령이 실패하면 False 반환
        """
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

            is_valid, error_msg = await _verify_git_environment()

            assert is_valid is False
            assert "Git 저장소가 아닙니다" in error_msg

    @pytest.mark.asyncio
    async def test_verify_git_valid_environment(self):
        """
        Git이 설치되어 있고 저장소인 경우 검증 성공

        git --version, git rev-parse 모두 성공하면 True 반환
        """
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

            is_valid, error_msg = await _verify_git_environment()

            assert is_valid is True
            assert error_msg is None


class TestCommitSafetyValidation:
    """커밋 안전성 검증 테스트"""

    @pytest.mark.asyncio
    async def test_validate_no_changes(self):
        """
        변경 사항이 없는 경우 검증 실패

        git status --porcelain이 빈 출력이면 False 반환
        """
        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            # git status --porcelain이 빈 출력
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(
                return_value=(b"", b"")
            )
            mock_subprocess.return_value = mock_proc

            is_safe, error_msg = await _validate_commit_safety()

            assert is_safe is False
            assert "커밋할 변경 사항이 없습니다" in error_msg

    @pytest.mark.asyncio
    async def test_validate_sensitive_filename_env(self):
        """
        민감한 파일명 검증 (.env)

        .env 파일이 변경 사항에 포함되면 False 반환
        """
        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            # git status에 .env 파일 포함
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(
                return_value=(b" M .env\n M src/main.py", b"")
            )
            mock_subprocess.return_value = mock_proc

            is_safe, error_msg = await _validate_commit_safety()

            assert is_safe is False
            assert "민감한 파일명이 감지되었습니다" in error_msg
            assert ".env" in error_msg

    @pytest.mark.asyncio
    async def test_validate_sensitive_filename_credentials(self):
        """
        민감한 파일명 검증 (credentials.json)

        credentials 파일이 변경 사항에 포함되면 False 반환
        """
        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            # git status에 credentials 파일 포함
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(
                return_value=(b" M config/credentials.json", b"")
            )
            mock_subprocess.return_value = mock_proc

            is_safe, error_msg = await _validate_commit_safety()

            assert is_safe is False
            assert "민감한 파일명이 감지되었습니다" in error_msg
            assert "credentials.json" in error_msg

    @pytest.mark.asyncio
    async def test_validate_sensitive_content_api_key(self):
        """
        민감한 내용 검증 (API 키)

        파일 내용에 API 키 패턴이 있으면 False 반환
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 임시 파일 생성
            test_file = Path(tmpdir) / "config.py"
            test_file.write_text('api_key = "sk-1234567890abcdefghijklmnopqrst"')

            with patch("asyncio.create_subprocess_shell") as mock_subprocess:
                # git status에 config.py 포함
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(
                    return_value=(f" M {test_file}".encode(), b"")
                )
                mock_subprocess.return_value = mock_proc

                # Path 객체를 mock하여 실제 파일 경로 반환
                with patch("pathlib.Path") as mock_path:
                    mock_path.return_value = test_file

                    is_safe, error_msg = await _validate_commit_safety()

                    assert is_safe is False
                    assert "민감한 정보가 파일 내용에서 감지되었습니다" in error_msg

    @pytest.mark.asyncio
    async def test_validate_safe_files(self):
        """
        안전한 파일들만 있는 경우 검증 성공

        민감한 정보가 없는 일반 코드 파일이면 True 반환
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 안전한 임시 파일 생성
            test_file = Path(tmpdir) / "main.py"
            test_file.write_text('print("Hello, World!")')

            with patch("asyncio.create_subprocess_shell") as mock_subprocess:
                # git status에 안전한 파일만 포함
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(
                    return_value=(f" M {test_file}".encode(), b"")
                )
                mock_subprocess.return_value = mock_proc

                # Path 객체를 mock하여 실제 파일 경로 반환
                with patch("pathlib.Path") as mock_path:
                    mock_path.return_value = test_file

                    is_safe, error_msg = await _validate_commit_safety()

                    # 파일이 실제로 존재하는 경우만 검증 성공
                    if test_file.exists():
                        assert is_safe is True
                        assert error_msg is None


class TestExecuteCommitterTask:
    """execute_committer_task 통합 테스트"""

    @pytest.mark.asyncio
    async def test_execute_committer_git_not_installed(self):
        """
        Git이 설치되지 않은 경우 Committer 실행 거부

        _verify_git_environment가 False를 반환하면 에러 메시지 반환
        """
        with patch(
            "src.infrastructure.mcp.worker_tools._verify_git_environment"
        ) as mock_verify:
            mock_verify.return_value = (False, "Git이 설치되어 있지 않습니다.")

            # Tool 데코레이터가 적용된 함수의 handler 속성으로 원본 함수 호출
            result = await worker_tools.execute_committer_task.handler(
                {"task_description": "커밋 생성"}
            )

            assert "content" in result
            assert len(result["content"]) > 0
            assert "Git 환경 오류" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_committer_not_git_repo(self):
        """
        Git 저장소가 아닌 경우 Committer 실행 거부

        _verify_git_environment가 False를 반환하면 에러 메시지 반환
        """
        with patch(
            "src.infrastructure.mcp.worker_tools._verify_git_environment"
        ) as mock_verify:
            mock_verify.return_value = (False, "현재 디렉토리가 Git 저장소가 아닙니다.")

            result = await worker_tools.execute_committer_task.handler(
                {"task_description": "커밋 생성"}
            )

            assert "content" in result
            assert len(result["content"]) > 0
            assert "Git 환경 오류" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_committer_sensitive_file(self):
        """
        민감한 파일이 포함된 경우 Committer 실행 거부

        _validate_commit_safety가 False를 반환하면 에러 메시지 반환
        """
        with patch(
            "src.infrastructure.mcp.worker_tools._verify_git_environment"
        ) as mock_verify, patch(
            "src.infrastructure.mcp.worker_tools._validate_commit_safety"
        ) as mock_validate:
            # Git 환경은 정상
            mock_verify.return_value = (True, None)
            # 민감 정보 감지
            mock_validate.return_value = (
                False,
                "민감한 파일명이 감지되었습니다:\n  - .env"
            )

            result = await worker_tools.execute_committer_task.handler(
                {"task_description": "커밋 생성"}
            )

            assert "content" in result
            assert len(result["content"]) > 0
            assert "커밋 거부" in result["content"][0]["text"]
            assert "보안 검증 실패" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_committer_all_checks_pass(self):
        """
        모든 검증 통과 시 Committer Agent 실행

        _verify_git_environment, _validate_commit_safety 모두 True 반환 시
        _execute_worker_task("committer", ...) 호출
        """
        with patch(
            "src.infrastructure.mcp.worker_tools._verify_git_environment"
        ) as mock_verify, patch(
            "src.infrastructure.mcp.worker_tools._validate_commit_safety"
        ) as mock_validate, patch(
            "src.infrastructure.mcp.worker_tools._execute_worker_task"
        ) as mock_execute:
            # 모든 검증 통과
            mock_verify.return_value = (True, None)
            mock_validate.return_value = (True, None)

            # _execute_worker_task가 성공 응답 반환
            mock_execute.return_value = {
                "content": [
                    {"type": "text", "text": "커밋이 성공적으로 생성되었습니다."}
                ]
            }

            result = await worker_tools.execute_committer_task.handler(
                {"task_description": "feat: 새 기능 추가"}
            )

            # _execute_worker_task가 호출되었는지 확인
            mock_execute.assert_called_once_with(
                "committer",
                "feat: 새 기능 추가",
                use_retry=False
            )

            # 결과 확인
            assert "content" in result
            assert len(result["content"]) > 0
            assert "커밋이 성공적으로 생성되었습니다" in result["content"][0]["text"]


class TestSensitivePatterns:
    """민감 정보 패턴 테스트"""

    def test_sensitive_file_patterns_match_env(self):
        """
        .env 파일명 패턴 매칭 테스트
        """
        import re
        test_files = [
            ".env",
            ".env.local",
            ".env.production",
            ".env.development",
        ]

        pattern = SENSITIVE_FILE_PATTERNS[0]  # \.env.*

        for file in test_files:
            assert re.match(pattern, file, re.IGNORECASE), \
                f"파일 {file}이 패턴 {pattern}에 매칭되지 않음"

    def test_sensitive_file_patterns_match_credentials(self):
        """
        credentials 파일명 패턴 매칭 테스트
        """
        import re
        test_files = [
            "credentials.json",
            "aws-credentials",
            "google_credentials.yaml",
        ]

        pattern = SENSITIVE_FILE_PATTERNS[1]  # .*credentials.*

        for file in test_files:
            assert re.match(pattern, file, re.IGNORECASE), \
                f"파일 {file}이 패턴 {pattern}에 매칭되지 않음"

    def test_sensitive_content_patterns_match_api_key(self):
        """
        API 키 내용 패턴 매칭 테스트
        """
        import re
        test_contents = [
            'api_key = "sk-1234567890abcdefghijklmnopqrst"',
            "api-key: sk-1234567890abcdefghijklmnopqrst",
            "ANTHROPIC_API_KEY=sk-ant-1234567890abcdefghijklmnopqrst",
        ]

        # API 키 패턴들
        api_key_patterns = [
            SENSITIVE_CONTENT_PATTERNS[0],  # api[_-]?key\s*[:=]
            SENSITIVE_CONTENT_PATTERNS[3],  # aws[_-]?access[_-]?key
            SENSITIVE_CONTENT_PATTERNS[4],  # anthropic[_-]?api[_-]?key
        ]

        matched = False
        for content in test_contents:
            for pattern in api_key_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    matched = True
                    break

        assert matched, "API 키 패턴이 매칭되지 않음"
