"""
paths.py 모듈의 단위 테스트

get_project_name() 및 get_data_dir() 함수를 테스트합니다.
"""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.utils.paths import get_project_name, get_data_dir


class TestGetProjectName:
    """get_project_name() 함수 테스트"""

    def test_git_remote_https_url(self):
        """Git remote HTTPS URL에서 프로젝트 이름 추출"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/user/my-project.git\n"

        with patch("subprocess.run", return_value=mock_result):
            assert get_project_name() == "my-project"

    def test_git_remote_https_url_without_git_extension(self):
        """Git remote HTTPS URL (.git 확장자 없음)에서 프로젝트 이름 추출"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/user/another-project\n"

        with patch("subprocess.run", return_value=mock_result):
            assert get_project_name() == "another-project"

    def test_git_remote_ssh_url(self):
        """Git remote SSH URL에서 프로젝트 이름 추출"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git@github.com:user/ssh-project.git\n"

        with patch("subprocess.run", return_value=mock_result):
            assert get_project_name() == "ssh-project"

    def test_git_remote_ssh_url_with_port(self):
        """Git remote SSH URL (포트 포함)에서 프로젝트 이름 추출"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ssh://git@github.com:22/user/port-project.git\n"

        with patch("subprocess.run", return_value=mock_result):
            assert get_project_name() == "port-project"

    def test_git_remote_with_query_params(self):
        """Git remote URL (쿼리 파라미터 포함)에서 프로젝트 이름 추출"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/user/query-project.git?foo=bar\n"

        with patch("subprocess.run", return_value=mock_result):
            # .git까지 포함된 채로 추출됨 (쿼리 파라미터는 무시됨)
            result = get_project_name()
            assert "query-project" in result

    def test_git_remote_fails_fallback_to_repo_root(self):
        """Git remote 실패 시 repository root directory name 사용"""
        # 첫 번째 git remote 명령 실패
        mock_result_remote = MagicMock()
        mock_result_remote.returncode = 1

        # 두 번째 git rev-parse 명령 성공
        mock_result_repo = MagicMock()
        mock_result_repo.returncode = 0
        mock_result_repo.stdout = "/Users/test/my-repo\n"

        with patch("subprocess.run", side_effect=[mock_result_remote, mock_result_repo]):
            assert get_project_name() == "my-repo"

    def test_no_git_fallback_to_cwd(self):
        """Git이 없는 경우 현재 작업 디렉토리 이름 사용"""
        # 모든 git 명령 실패
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            # Path.cwd().name을 mock
            with patch("pathlib.Path.cwd") as mock_cwd:
                mock_cwd.return_value = Path("/Users/test/fallback-dir")
                assert get_project_name() == "fallback-dir"

    def test_git_timeout_fallback_to_cwd(self):
        """Git 명령 timeout 시 현재 작업 디렉토리 이름 사용"""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 2)):
            with patch("pathlib.Path.cwd") as mock_cwd:
                mock_cwd.return_value = Path("/Users/test/timeout-dir")
                assert get_project_name() == "timeout-dir"

    def test_git_not_found_fallback_to_cwd(self):
        """Git이 설치되지 않은 경우 현재 작업 디렉토리 이름 사용"""
        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            with patch("pathlib.Path.cwd") as mock_cwd:
                mock_cwd.return_value = Path("/Users/test/no-git-dir")
                assert get_project_name() == "no-git-dir"


class TestGetDataDir:
    """get_data_dir() 함수 테스트"""

    def test_basic_data_dir_format(self, tmp_path):
        """데이터 디렉토리 경로 형식 검증"""
        with patch("src.utils.paths.get_project_name", return_value="test-project"):
            with patch("pathlib.Path.home", return_value=tmp_path):
                data_dir = get_data_dir()

                # 경로 형식: ~/.better-llm/{project-name}/
                assert data_dir == tmp_path / ".better-llm" / "test-project"
                # 디렉토리가 자동으로 생성되는지 확인
                assert data_dir.exists()
                assert data_dir.is_dir()

    def test_data_dir_with_subdir(self, tmp_path):
        """하위 디렉토리 포함 경로 검증"""
        with patch("src.utils.paths.get_project_name", return_value="test-project"):
            with patch("pathlib.Path.home", return_value=tmp_path):
                data_dir = get_data_dir("sessions")

                # 경로 형식: ~/.better-llm/{project-name}/sessions/
                expected = tmp_path / ".better-llm" / "test-project" / "sessions"
                assert data_dir == expected
                assert data_dir.exists()
                assert data_dir.is_dir()

    def test_data_dir_multiple_subdirs(self, tmp_path):
        """여러 하위 디렉토리 생성 검증"""
        with patch("src.utils.paths.get_project_name", return_value="test-project"):
            with patch("pathlib.Path.home", return_value=tmp_path):
                # 여러 하위 디렉토리 생성
                sessions_dir = get_data_dir("sessions")
                logs_dir = get_data_dir("logs")
                cache_dir = get_data_dir("cache")

                # 모두 존재하는지 확인
                assert sessions_dir.exists()
                assert logs_dir.exists()
                assert cache_dir.exists()

                # 각각 올바른 경로인지 확인
                base = tmp_path / ".better-llm" / "test-project"
                assert sessions_dir == base / "sessions"
                assert logs_dir == base / "logs"
                assert cache_dir == base / "cache"

    def test_data_dir_auto_creation(self, tmp_path):
        """디렉토리 자동 생성 확인"""
        with patch("src.utils.paths.get_project_name", return_value="auto-create"):
            with patch("pathlib.Path.home", return_value=tmp_path):
                data_dir = get_data_dir("deep/nested/path")

                # 깊은 경로도 자동으로 생성되는지 확인
                assert data_dir.exists()
                expected = tmp_path / ".better-llm" / "auto-create" / "deep" / "nested" / "path"
                assert data_dir == expected

    def test_data_dir_project_isolation(self, tmp_path):
        """프로젝트별 데이터 격리 확인"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            # 프로젝트 A
            with patch("src.utils.paths.get_project_name", return_value="project-a"):
                dir_a = get_data_dir("sessions")

            # 프로젝트 B
            with patch("src.utils.paths.get_project_name", return_value="project-b"):
                dir_b = get_data_dir("sessions")

            # 두 경로가 서로 다른지 확인
            assert dir_a != dir_b
            assert "project-a" in str(dir_a)
            assert "project-b" in str(dir_b)

            # 각각 존재하는지 확인
            assert dir_a.exists()
            assert dir_b.exists()

    def test_data_dir_empty_subdir(self, tmp_path):
        """빈 문자열 하위 디렉토리 처리"""
        with patch("src.utils.paths.get_project_name", return_value="test-project"):
            with patch("pathlib.Path.home", return_value=tmp_path):
                # 빈 문자열이면 프로젝트 루트 디렉토리 반환
                data_dir = get_data_dir("")

                expected = tmp_path / ".better-llm" / "test-project"
                assert data_dir == expected
                assert data_dir.exists()

    def test_data_dir_idempotent(self, tmp_path):
        """동일한 디렉토리 여러 번 호출 시 문제없는지 확인"""
        with patch("src.utils.paths.get_project_name", return_value="test-project"):
            with patch("pathlib.Path.home", return_value=tmp_path):
                # 같은 디렉토리를 여러 번 호출
                dir1 = get_data_dir("sessions")
                dir2 = get_data_dir("sessions")
                dir3 = get_data_dir("sessions")

                # 모두 같은 경로여야 함
                assert dir1 == dir2 == dir3
                assert dir1.exists()
