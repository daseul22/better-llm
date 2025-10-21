"""
세션 파일 경로 변경 기능 통합 테스트

실제 세션 파일이 새 경로에 저장되고 로드되는지 검증합니다.
"""

from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import pytest

from src.domain.models import SessionResult, SessionStatus
from src.domain.services import ConversationHistory
from src.infrastructure.storage import JsonSessionRepository
from src.utils.paths import get_project_name, get_data_dir


class TestSessionPathIntegration:
    """세션 파일 저장/로드 통합 테스트"""

    def test_session_saved_to_project_specific_path(self, tmp_path):
        """세션 파일이 프로젝트별 경로에 저장되는지 확인"""
        project_name = "integration-test-project"

        with patch("src.infrastructure.config.validator.get_project_name", return_value=project_name):
            with patch("pathlib.Path.home", return_value=tmp_path):
                # 세션 저장소 생성
                repo = JsonSessionRepository()

                # 대화 히스토리 생성
                history = ConversationHistory()
                history.add_message(
                    role="user",
                    content="테스트 요청"
                )
                history.add_message(
                    role="agent",
                    content="작업 완료",
                    agent_name="tester"
                )

                # 세션 결과 생성
                result = SessionResult(
                    status=SessionStatus.COMPLETED,
                    files_modified=["test.py"],
                    tests_passed=True,
                    error_message=None
                )

                # 세션 저장
                session_id = "test123"
                user_request = "통합 테스트"
                saved_path = repo.save(session_id, user_request, history, result)

                # 저장 경로 검증
                expected_dir = tmp_path / ".better-llm" / project_name / "sessions"
                assert saved_path.parent == expected_dir
                assert saved_path.exists()
                assert saved_path.name.startswith(f"session_{session_id}_")

    def test_session_loaded_from_project_specific_path(self, tmp_path):
        """저장된 세션을 프로젝트별 경로에서 로드할 수 있는지 확인"""
        project_name = "load-test-project"

        with patch("src.infrastructure.config.validator.get_project_name", return_value=project_name):
            with patch("pathlib.Path.home", return_value=tmp_path):
                # 세션 저장소 생성
                repo = JsonSessionRepository()

                # 대화 히스토리 생성 및 저장
                history = ConversationHistory()
                history.add_message(
                    role="user",
                    content="로드 테스트 요청"
                )

                result = SessionResult(
                    status=SessionStatus.COMPLETED,
                    files_modified=[],
                    tests_passed=True,
                    error_message=None
                )

                session_id = "load456"
                repo.save(session_id, "로드 테스트", history, result)

                # 세션 로드
                loaded_history = repo.load(session_id)

                # 로드 검증
                assert loaded_history is not None
                assert len(loaded_history.messages) == 1
                assert loaded_history.messages[0].content == "로드 테스트 요청"

    def test_multiple_projects_isolated(self, tmp_path):
        """여러 프로젝트의 세션이 격리되는지 확인"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            # 프로젝트 A에 세션 저장
            with patch("src.infrastructure.config.validator.get_project_name", return_value="project-a"):
                repo_a = JsonSessionRepository()
                history_a = ConversationHistory()
                history_a.add_message(
                    role="user",
                    content="프로젝트 A 요청"
                )
                result_a = SessionResult(
                    status=SessionStatus.COMPLETED,
                    files_modified=[],
                    tests_passed=True,
                    error_message=None
                )
                saved_a = repo_a.save("sessionA", "A 작업", history_a, result_a)

            # 프로젝트 B에 세션 저장
            with patch("src.infrastructure.config.validator.get_project_name", return_value="project-b"):
                repo_b = JsonSessionRepository()
                history_b = ConversationHistory()
                history_b.add_message(
                    role="user",
                    content="프로젝트 B 요청"
                )
                result_b = SessionResult(
                    status=SessionStatus.COMPLETED,
                    files_modified=[],
                    tests_passed=True,
                    error_message=None
                )
                saved_b = repo_b.save("sessionB", "B 작업", history_b, result_b)

            # 경로가 다른지 확인
            assert "project-a" in str(saved_a)
            assert "project-b" in str(saved_b)
            assert saved_a.parent != saved_b.parent

            # 각 프로젝트에서 자신의 세션만 로드할 수 있는지 확인
            with patch("src.infrastructure.config.validator.get_project_name", return_value="project-a"):
                repo_a = JsonSessionRepository()
                loaded_a = repo_a.load("sessionA")
                assert loaded_a is not None
                assert loaded_a.messages[0].content == "프로젝트 A 요청"

                # 프로젝트 B의 세션은 로드 불가
                loaded_b_from_a = repo_a.load("sessionB")
                assert loaded_b_from_a is None

    def test_session_search_in_project_directory(self, tmp_path):
        """세션 검색이 프로젝트별 디렉토리에서 수행되는지 확인"""
        project_name = "search-test-project"

        with patch("src.infrastructure.config.validator.get_project_name", return_value=project_name):
            with patch("pathlib.Path.home", return_value=tmp_path):
                repo = JsonSessionRepository()

                # 여러 세션 저장
                for i in range(3):
                    history = ConversationHistory()
                    history.add_message(
                        role="user",
                        content=f"검색 테스트 {i}"
                    )
                    result = SessionResult(
                        status=SessionStatus.COMPLETED,
                        files_modified=[],
                        tests_passed=True,
                        error_message=None
                    )
                    repo.save(f"search{i}", f"검색 테스트 {i}", history, result)

                # 세션 목록 조회
                sessions = repo.list_sessions(limit=10)

                # 3개의 세션이 검색되는지 확인
                assert len(sessions) == 3

                # 모든 세션이 올바른 프로젝트의 것인지 확인
                for session in sessions:
                    assert session.session_id.startswith("search")

    def test_session_delete_from_project_directory(self, tmp_path):
        """세션 삭제가 프로젝트별 디렉토리에서 수행되는지 확인"""
        project_name = "delete-test-project"

        with patch("src.infrastructure.config.validator.get_project_name", return_value=project_name):
            with patch("pathlib.Path.home", return_value=tmp_path):
                repo = JsonSessionRepository()

                # 세션 저장
                history = ConversationHistory()
                history.add_message(
                    role="user",
                    content="삭제 테스트"
                )
                result = SessionResult(
                    status=SessionStatus.COMPLETED,
                    files_modified=[],
                    tests_passed=True,
                    error_message=None
                )
                session_id = "delete789"
                saved_path = repo.save(session_id, "삭제 테스트", history, result)

                # 파일이 존재하는지 확인
                assert saved_path.exists()

                # 세션 삭제
                deleted = repo.delete_session(session_id)
                assert deleted is True

                # 파일이 삭제되었는지 확인
                assert not saved_path.exists()

                # 로드 시도 시 None 반환
                loaded = repo.load(session_id)
                assert loaded is None

    def test_cli_utils_save_session_uses_correct_path(self, tmp_path):
        """CLI utils의 save_session_history가 올바른 경로를 사용하는지 확인"""
        from src.presentation.cli.utils import save_session_history

        project_name = "cli-test-project"

        with patch("src.infrastructure.config.validator.get_project_name", return_value=project_name):
            with patch("pathlib.Path.home", return_value=tmp_path):
                # 대화 히스토리 생성
                history = ConversationHistory()
                history.add_message(
                    role="user",
                    content="CLI 테스트"
                )

                # 세션 결과 생성
                result = {
                    "status": "completed",
                    "files_modified": ["test.py"],
                    "tests_passed": True,
                    "error_message": None
                }

                # 세션 저장 (output_dir=None으로 자동 경로 사용)
                session_id = "cli999"
                saved_path = save_session_history(
                    session_id=session_id,
                    user_request="CLI 테스트",
                    history=history,
                    result=result,
                    output_dir=None
                )

                # 저장 경로 검증
                expected_dir = tmp_path / ".better-llm" / project_name / "sessions"
                assert saved_path.parent == expected_dir
                assert saved_path.exists()

    def test_backward_compatibility_with_custom_output_dir(self, tmp_path):
        """기존 코드와의 하위 호환성 - 커스텀 output_dir 지정 시"""
        from src.presentation.cli.utils import save_session_history

        custom_dir = tmp_path / "custom_sessions"
        custom_dir.mkdir()

        # 대화 히스토리 생성
        history = ConversationHistory()
        history.add_message(
            role="user",
            content="커스텀 경로 테스트"
        )

        result = {
            "status": "completed",
            "files_modified": [],
            "tests_passed": True,
            "error_message": None
        }

        # 커스텀 경로로 저장
        saved_path = save_session_history(
            session_id="custom123",
            user_request="커스텀 테스트",
            history=history,
            result=result,
            output_dir=custom_dir
        )

        # 커스텀 경로에 저장되었는지 확인
        assert saved_path.parent == custom_dir
        assert saved_path.exists()
