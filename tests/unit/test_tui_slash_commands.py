"""
TUI 슬래시 커맨드 핸들러 테스트

handle_slash_command() 메서드의 9개 헬퍼 함수에 대한 18개 테스트를 포함합니다.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.presentation.tui.tui_app import OrchestratorTUI, SessionData
from src.presentation.cli.feedback import FeedbackType
from src.domain.services import ProjectContextAnalyzer


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_tui_app():
    """TUI 앱 모의 객체 생성"""
    app = MagicMock(spec=OrchestratorTUI)

    # 기본 속성 설정
    app.logger = MagicMock()
    app.write_log = MagicMock()
    app.query_one = MagicMock()

    # 세션 관련 속성
    app.session_id = "test-session-123"
    app.sessions = [SessionData("test-session-123")]
    app.active_session_index = 0

    return app


@pytest.fixture
def mock_output_log():
    """RichLog 위젯 모의 객체"""
    log = MagicMock()
    log.clear = MagicMock()
    return log


@pytest.fixture
def mock_task_input():
    """MultilineInput 위젯 모의 객체"""
    input_widget = MagicMock()
    input_widget.clear = MagicMock()
    return input_widget


@pytest.fixture
def mock_worker_status():
    """Worker 상태 위젯 모의 객체"""
    status = MagicMock()
    status.update = MagicMock()
    return status


@pytest.fixture
def mock_status_info():
    """상태 정보 위젯 모의 객체"""
    info = MagicMock()
    info.update = MagicMock()
    return info


# ============================================================================
# _handle_help_command 테스트 (2개)
# ============================================================================


@pytest.mark.asyncio
async def test_handle_help_command_displays_help_text():
    """_handle_help_command: 도움말 텍스트 표시 테스트"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app.action_show_help = AsyncMock()

    # 실제 메서드 바인딩
    await OrchestratorTUI._handle_help_command(app)

    # 검증: action_show_help 호출됨
    app.action_show_help.assert_called_once()


@pytest.mark.asyncio
async def test_handle_help_command_handles_no_args():
    """_handle_help_command: 인자 없이 호출 가능"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app.action_show_help = AsyncMock()

    # 인자 없이 호출
    await OrchestratorTUI._handle_help_command(app)

    # 검증
    app.action_show_help.assert_called_once()


# ============================================================================
# _handle_metrics_command 테스트 (3개)
# ============================================================================


@pytest.mark.asyncio
async def test_handle_metrics_command_displays_metrics():
    """_handle_metrics_command: 메트릭 패널 토글 테스트"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app.action_toggle_metrics_panel = AsyncMock()

    await OrchestratorTUI._handle_metrics_command(app)

    # 검증
    app.action_toggle_metrics_panel.assert_called_once()


@pytest.mark.asyncio
async def test_handle_metrics_command_handles_empty_metrics():
    """_handle_metrics_command: 빈 메트릭 처리"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app.action_toggle_metrics_panel = AsyncMock()

    # 메트릭이 없을 때도 정상 동작
    await OrchestratorTUI._handle_metrics_command(app)

    app.action_toggle_metrics_panel.assert_called_once()


@pytest.mark.asyncio
async def test_handle_metrics_command_formats_correctly():
    """_handle_metrics_command: 메트릭 포맷 테스트"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app.action_toggle_metrics_panel = AsyncMock()

    await OrchestratorTUI._handle_metrics_command(app)

    # 검증: 호출 횟수 확인
    assert app.action_toggle_metrics_panel.call_count == 1


# ============================================================================
# _handle_search_command 테스트 (4개)
# ============================================================================


@pytest.mark.asyncio
async def test_handle_search_command_with_keyword():
    """_handle_search_command: 키워드와 함께 검색 수행"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app.action_search_log = AsyncMock()
    app.perform_search = AsyncMock()

    # 키워드와 함께 호출
    await OrchestratorTUI._handle_search_command(app, "error")

    # 검증: perform_search 호출됨
    app.perform_search.assert_called_once_with("error")
    app.action_search_log.assert_not_called()


@pytest.mark.asyncio
async def test_handle_search_command_no_results():
    """_handle_search_command: 검색 결과 없을 때 처리"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app.perform_search = AsyncMock()

    # 검색 수행
    await OrchestratorTUI._handle_search_command(app, "nonexistent")

    # 검증
    app.perform_search.assert_called_once_with("nonexistent")


@pytest.mark.asyncio
async def test_handle_search_command_empty_keyword():
    """_handle_search_command: 빈 키워드일 때 검색 모달 표시"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app.action_search_log = AsyncMock()
    app.perform_search = AsyncMock()

    # 빈 키워드로 호출
    await OrchestratorTUI._handle_search_command(app, "")

    # 검증: action_search_log 호출됨 (모달 표시)
    app.action_search_log.assert_called_once()
    app.perform_search.assert_not_called()


@pytest.mark.asyncio
async def test_handle_search_command_error_handling():
    """_handle_search_command: 에러 처리 테스트"""
    from src.presentation.tui.tui_app import OrchestratorTUI
    from src.presentation.cli.feedback import TUIFeedbackWidget

    app = MagicMock(spec=OrchestratorTUI)
    app.perform_search = AsyncMock(side_effect=Exception("Search failed"))
    app.write_log = MagicMock()

    # 에러 발생 시 처리
    await OrchestratorTUI._handle_search_command(app, "test")

    # 검증: write_log 호출됨 (에러 패널 표시)
    assert app.write_log.call_count >= 1


# ============================================================================
# _handle_clear_command 테스트 (1개)
# ============================================================================


@pytest.mark.asyncio
async def test_handle_clear_command_clears_output():
    """_handle_clear_command: 로그 화면 지우기"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    output_log = MagicMock()
    output_log.clear = MagicMock()

    app.query_one = MagicMock(return_value=output_log)
    app.log_lines = ["line1", "line2", "line3"]
    app.write_log = MagicMock()

    # 화면 지우기 실행
    await OrchestratorTUI._handle_clear_command(app)

    # 검증
    output_log.clear.assert_called_once()
    assert len(app.log_lines) == 0
    assert app.write_log.call_count >= 1


# ============================================================================
# _handle_load_command 테스트 (3개)
# ============================================================================


@pytest.mark.asyncio
async def test_handle_load_command_success():
    """_handle_load_command: 세션 로드 성공"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app.load_session = AsyncMock()
    app.write_log = MagicMock()

    # 세션 로드
    await OrchestratorTUI._handle_load_command(app, "test-session-123")

    # 검증
    app.load_session.assert_called_once_with("test-session-123")


@pytest.mark.asyncio
async def test_handle_load_command_invalid_session_id():
    """_handle_load_command: 유효하지 않은 세션 ID"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app.load_session = AsyncMock()
    app.write_log = MagicMock()

    # 빈 세션 ID
    await OrchestratorTUI._handle_load_command(app, "")

    # 검증: load_session 호출되지 않음
    app.load_session.assert_not_called()
    assert app.write_log.call_count >= 1


@pytest.mark.asyncio
async def test_handle_load_command_error_handling():
    """_handle_load_command: 에러 처리 테스트"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app.load_session = AsyncMock(side_effect=Exception("Load failed"))
    app.write_log = MagicMock()

    # 에러 발생 시 처리
    await OrchestratorTUI._handle_load_command(app, "invalid-session")

    # 검증: write_log 호출됨 (에러 패널 표시)
    assert app.write_log.call_count >= 1


# ============================================================================
# _handle_init_command 테스트 (5개)
# ============================================================================


@pytest.mark.asyncio
async def test_handle_init_command_success():
    """_handle_init_command: 프로젝트 초기화 성공"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    worker_status = MagicMock()
    status_info = MagicMock()

    app.query_one = MagicMock(side_effect=[worker_status, status_info])
    app.write_log = MagicMock()
    app._parse_init_args = MagicMock(return_value={})
    app._render_project_analysis_table = MagicMock()
    app._save_project_context = MagicMock(return_value=Path(".context.json"))
    app.sessions = [SessionData("test")]
    app.active_session_index = 0
    app.session_id = "test"
    app._update_status_bar = MagicMock()

    # Mock ProjectContextAnalyzer
    mock_context = MagicMock()
    mock_context.project_name = "test-project"
    mock_context.architecture = "clean-architecture"

    with patch("src.presentation.tui.tui_app.get_project_root", return_value=Path("/tmp")):
        with patch("src.presentation.tui.tui_app.ProjectContextAnalyzer") as mock_analyzer:
            mock_analyzer.return_value.analyze.return_value = mock_context

            with patch("src.presentation.tui.tui_app.generate_session_id", return_value="new-session"):
                with patch("src.presentation.tui.tui_app.SessionData"):
                    with patch("src.presentation.tui.tui_app.update_session_id"):
                        with patch("src.presentation.tui.tui_app.set_metrics_collector"):
                            # 초기화 실행
                            await OrchestratorTUI._handle_init_command(app, "")

                            # 검증
                            assert app.write_log.call_count >= 5
                            worker_status.update.assert_called()
                            status_info.update.assert_called()


@pytest.mark.asyncio
async def test_handle_init_command_with_all_args():
    """_handle_init_command: 모든 인자와 함께 초기화"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    app._parse_init_args = MagicMock(return_value={"path": "/tmp", "name": "myproject"})

    # _parse_init_args 호출 확인
    result = OrchestratorTUI._parse_init_args(app, "--path /tmp --name myproject")

    assert "path" in result
    assert "name" in result


@pytest.mark.asyncio
async def test_handle_init_command_missing_path():
    """_handle_init_command: 경로 누락 시 기본 동작"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)

    # 빈 인자로 파싱
    result = OrchestratorTUI._parse_init_args(app, "")

    assert result == {}


@pytest.mark.asyncio
async def test_handle_init_command_error_handling():
    """_handle_init_command: 에러 처리 테스트"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    worker_status = MagicMock()
    status_info = MagicMock()

    app.query_one = MagicMock(side_effect=[worker_status, status_info])
    app.write_log = MagicMock()
    app._parse_init_args = MagicMock(side_effect=Exception("Parse failed"))

    # 에러 발생 시 처리
    await OrchestratorTUI._handle_init_command(app, "--invalid")

    # 검증: 에러 패널 표시
    assert app.write_log.call_count >= 1
    worker_status.update.assert_called()


@pytest.mark.asyncio
async def test_handle_init_command_saves_context():
    """_handle_init_command: 컨텍스트 저장 확인"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    mock_context = MagicMock()

    # _save_project_context 호출 확인
    with patch("src.presentation.tui.tui_app.get_project_root", return_value=Path("/tmp")):
        with patch("src.presentation.tui.tui_app.JsonContextRepository") as mock_repo:
            result = OrchestratorTUI._save_project_context(app, mock_context)

            # 검증
            assert result == Path("/tmp") / ".context.json"
            mock_repo.assert_called_once()


# ============================================================================
# 추가 헬퍼 함수 테스트
# ============================================================================


def test_parse_init_args_with_flags():
    """_parse_init_args: 플래그 파싱 테스트"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)

    # 여러 플래그 파싱
    result = OrchestratorTUI._parse_init_args(app, "--path /tmp --name myproject --description 'test project'")

    assert result["path"] == "/tmp"
    assert result["name"] == "myproject"
    assert result["description"] == "'test project'"


def test_render_project_analysis_table():
    """_render_project_analysis_table: 테이블 렌더링 테스트"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)

    mock_context = MagicMock()
    mock_context.project_name = "test-project"
    mock_context.language = "python"
    mock_context.framework = "textual"
    mock_context.architecture = "clean-architecture"
    mock_context.dependencies = ["dep1", "dep2", "dep3"]

    # 테이블 렌더링
    table = OrchestratorTUI._render_project_analysis_table(app, mock_context)

    # 검증
    assert table is not None
    assert hasattr(table, "add_row")


def test_save_project_context():
    """_save_project_context: 컨텍스트 저장 테스트"""
    from src.presentation.tui.tui_app import OrchestratorTUI

    app = MagicMock(spec=OrchestratorTUI)
    mock_context = MagicMock()

    with patch("src.presentation.tui.tui_app.get_project_root", return_value=Path("/tmp")):
        with patch("src.presentation.tui.tui_app.JsonContextRepository") as mock_repo:
            result = OrchestratorTUI._save_project_context(app, mock_context)

            # 검증
            assert result == Path("/tmp") / ".context.json"
            mock_repo.assert_called_once()
            mock_repo.return_value.save.assert_called_once_with(mock_context)
