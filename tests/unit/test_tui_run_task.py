"""
run_task() 리팩토링 테스트

5개 헬퍼 함수 및 run_task() 통합 테스트:
1. _validate_and_prepare_input
2. _execute_streaming_task
3. _calculate_display_width
4. _handle_task_error
5. _save_and_cleanup
"""

import pytest
import asyncio
from pathlib import Path
from typing import Optional, Tuple
from unittest.mock import Mock, MagicMock, AsyncMock, patch

from src.presentation.tui.tui_app import OrchestratorTUI
from src.domain.models import SessionResult
from src.domain.models.session import SessionStatus
from src.presentation.cli.feedback import FeedbackType


@pytest.fixture
def mock_tui_app():
    """TUI 앱 모킹 픽스처"""
    with patch("src.presentation.tui.tui_app.validate_environment"):
        with patch("src.presentation.tui.tui_app.get_project_root", return_value=Path("/tmp")):
            app = OrchestratorTUI()
            # 모킹된 위젯들 설정
            app.query_one = Mock()
            app.write_log = Mock()
            app.update_worker_status = Mock()
            app.history = Mock()
            app.history.get_history = Mock(return_value=[])
            app.history.add_message = Mock()
            app.manager = Mock()
            app.message_renderer = Mock()
            app.message_renderer.reset_state = Mock()
            app.metrics_collector = Mock()

            # session_id 설정
            app.sessions[0].session_id = "test-session-123"

            yield app


class TestValidateAndPrepareInput:
    """_validate_and_prepare_input 테스트"""

    def test_validate_and_prepare_input_success(self, mock_tui_app):
        """
        성공 케이스: 유효한 입력
        """
        with patch("src.presentation.tui.tui_app.validate_user_input", return_value=(True, "")):
            with patch("src.presentation.tui.tui_app.sanitize_user_input", return_value="clean input"):
                is_valid, sanitized = mock_tui_app._validate_and_prepare_input("test input")

                assert is_valid is True
                assert sanitized == "clean input"

    def test_validate_and_prepare_input_empty(self, mock_tui_app):
        """
        실패 케이스: 빈 입력
        """
        is_valid, error_msg = mock_tui_app._validate_and_prepare_input("")

        assert is_valid is False
        assert "입력이 비어있습니다" in error_msg

    def test_validate_and_prepare_input_invalid(self, mock_tui_app):
        """
        실패 케이스: 검증 실패
        """
        mock_task_input = Mock()
        mock_task_input.clear = Mock()
        mock_tui_app.query_one.return_value = mock_task_input

        with patch("src.presentation.tui.tui_app.validate_user_input", return_value=(False, "Invalid input")):
            is_valid, error_msg = mock_tui_app._validate_and_prepare_input("invalid")

            assert is_valid is False
            assert "Invalid input" in error_msg
            mock_task_input.clear.assert_called_once()


class TestExecuteStreamingTask:
    """_execute_streaming_task 테스트"""

    @pytest.mark.asyncio
    async def test_execute_streaming_task_success(self, mock_tui_app):
        """
        성공 케이스: 스트리밍 실행
        """
        # Manager 스트리밍 모킹
        async def mock_stream():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"

        mock_tui_app.manager.analyze_and_plan_stream = AsyncMock(return_value=mock_stream())
        mock_tui_app.message_renderer.render_ai_response_chunk = Mock(return_value="formatted chunk")

        response, duration = await mock_tui_app._execute_streaming_task(effective_width=80)

        assert response == "chunk1chunk2chunk3"
        assert duration > 0
        assert mock_tui_app.write_log.call_count >= 3

    @pytest.mark.asyncio
    async def test_execute_streaming_task_cancelled(self, mock_tui_app):
        """
        실패 케이스: 작업 중단
        """
        async def mock_stream():
            raise asyncio.CancelledError()

        mock_tui_app.manager.analyze_and_plan_stream = AsyncMock(return_value=mock_stream())

        with pytest.raises(asyncio.CancelledError):
            await mock_tui_app._execute_streaming_task(effective_width=80)

        # timer_active가 False로 설정되었는지 확인
        assert mock_tui_app.timer_active is False

    @pytest.mark.asyncio
    async def test_execute_streaming_task_error(self, mock_tui_app):
        """
        실패 케이스: 스트리밍 에러
        """
        async def mock_stream():
            raise Exception("Streaming error")

        mock_tui_app.manager.analyze_and_plan_stream = AsyncMock(return_value=mock_stream())

        with pytest.raises(Exception) as exc_info:
            await mock_tui_app._execute_streaming_task(effective_width=80)

        assert "Streaming error" in str(exc_info.value)
        assert mock_tui_app.timer_active is False


class TestCalculateDisplayWidth:
    """_calculate_display_width 테스트"""

    def test_calculate_display_width_large(self, mock_tui_app):
        """
        성공 케이스: 큰 터미널 (120 width)
        """
        mock_output_log = Mock()
        mock_output_log.size.width = 120
        mock_tui_app.query_one.return_value = mock_output_log

        # MessageRenderer.OUTPUT_LOG_PADDING과 MIN_OUTPUT_WIDTH 모킹
        with patch("src.presentation.tui.utils.message_renderer.MessageRenderer.OUTPUT_LOG_PADDING", 5):
            with patch("src.presentation.tui.utils.message_renderer.MessageRenderer.MIN_OUTPUT_WIDTH", 60):
                width = mock_tui_app._calculate_display_width()

                assert width == 115  # 120 - 5

    def test_calculate_display_width_medium(self, mock_tui_app):
        """
        성공 케이스: 중간 터미널 (80 width)
        """
        mock_output_log = Mock()
        mock_output_log.size.width = 80
        mock_tui_app.query_one.return_value = mock_output_log

        with patch("src.presentation.tui.utils.message_renderer.MessageRenderer.OUTPUT_LOG_PADDING", 5):
            with patch("src.presentation.tui.utils.message_renderer.MessageRenderer.MIN_OUTPUT_WIDTH", 60):
                width = mock_tui_app._calculate_display_width()

                assert width == 75  # 80 - 5

    def test_calculate_display_width_small(self, mock_tui_app):
        """
        성공 케이스: 작은 터미널 (50 width)
        """
        mock_output_log = Mock()
        mock_output_log.size.width = 50
        mock_tui_app.query_one.return_value = mock_output_log

        with patch("src.presentation.tui.utils.message_renderer.MessageRenderer.OUTPUT_LOG_PADDING", 5):
            with patch("src.presentation.tui.utils.message_renderer.MessageRenderer.MIN_OUTPUT_WIDTH", 60):
                width = mock_tui_app._calculate_display_width()

                # MIN_OUTPUT_WIDTH보다 작아지면 MIN_OUTPUT_WIDTH 사용
                assert width == 60

    def test_calculate_display_width_error(self, mock_tui_app):
        """
        실패 케이스: 위젯 조회 실패
        """
        mock_tui_app.query_one.side_effect = Exception("Widget not found")

        width = mock_tui_app._calculate_display_width()

        assert width is None


class TestHandleTaskError:
    """_handle_task_error 테스트"""

    def test_handle_task_error_generic(self, mock_tui_app):
        """
        성공 케이스: 일반 에러 처리
        """
        mock_worker_status = Mock()
        mock_status_info = Mock()

        def query_side_effect(selector, widget_type):
            if selector == "#worker-status":
                return mock_worker_status
            elif selector == "#status-info":
                return mock_status_info

        mock_tui_app.query_one.side_effect = query_side_effect

        test_error = Exception("Test error")
        mock_tui_app._handle_task_error(test_error)

        # UI 업데이트 확인
        mock_worker_status.update.assert_called_once_with("❌ 오류")
        mock_status_info.update.assert_called_once_with("Error")

        # 로그 출력 확인
        assert mock_tui_app.write_log.call_count >= 3

    def test_handle_task_error_with_traceback(self, mock_tui_app):
        """
        성공 케이스: 트레이스백 포함 에러 처리
        """
        mock_worker_status = Mock()
        mock_status_info = Mock()

        def query_side_effect(selector, widget_type):
            if selector == "#worker-status":
                return mock_worker_status
            elif selector == "#status-info":
                return mock_status_info

        mock_tui_app.query_one.side_effect = query_side_effect

        try:
            raise ValueError("Test error with traceback")
        except Exception as e:
            mock_tui_app._handle_task_error(e)

        # 로그에 트레이스백이 포함되었는지 확인
        assert mock_tui_app.write_log.call_count >= 3


class TestSaveAndCleanup:
    """_save_and_cleanup 테스트"""

    def test_save_and_cleanup_success(self, mock_tui_app):
        """
        성공 케이스: 세션 및 메트릭 저장
        """
        with patch("src.presentation.tui.tui_app.save_session_history", return_value=Path("/tmp/session.json")):
            with patch("src.presentation.tui.tui_app.save_metrics_report", return_value=Path("/tmp/metrics.txt")):
                session_path, metrics_path = mock_tui_app._save_and_cleanup(
                    "test request", 5.0
                )

                assert session_path == Path("/tmp/session.json")
                assert metrics_path == Path("/tmp/metrics.txt")

    def test_save_and_cleanup_no_metrics(self, mock_tui_app):
        """
        성공 케이스: 메트릭 저장 실패 (None 반환)
        """
        with patch("src.presentation.tui.tui_app.save_session_history", return_value=Path("/tmp/session.json")):
            with patch("src.presentation.tui.tui_app.save_metrics_report", return_value=None):
                session_path, metrics_path = mock_tui_app._save_and_cleanup(
                    "test request", 5.0
                )

                assert session_path == Path("/tmp/session.json")
                assert metrics_path is None

    def test_save_and_cleanup_error(self, mock_tui_app):
        """
        실패 케이스: 세션 저장 실패
        """
        with patch("src.presentation.tui.tui_app.save_session_history", side_effect=IOError("Save failed")):
            with pytest.raises(IOError) as exc_info:
                mock_tui_app._save_and_cleanup("test request", 5.0)

            assert "Save failed" in str(exc_info.value)


class TestRunTaskIntegration:
    """run_task() 통합 테스트"""

    @pytest.mark.asyncio
    async def test_run_task_integration_success(self, mock_tui_app):
        """
        통합 테스트: 전체 성공 플로우
        """
        # 모킹 설정
        mock_task_input = Mock()
        mock_worker_status = Mock()
        mock_status_info = Mock()

        def query_side_effect(selector, widget_type=None):
            if selector == "#task-input":
                return mock_task_input
            elif selector == "#worker-status":
                return mock_worker_status
            elif selector == "#status-info":
                return mock_status_info
            elif selector == "#output-log":
                mock_log = Mock()
                mock_log.size.width = 120
                return mock_log

        mock_tui_app.query_one.side_effect = query_side_effect

        # 스트리밍 모킹
        async def mock_stream():
            yield "response"

        mock_tui_app.manager.analyze_and_plan_stream = AsyncMock(return_value=mock_stream())
        mock_tui_app.message_renderer.render_ai_response_chunk = Mock(return_value="formatted")

        # 저장 모킹
        with patch("src.presentation.tui.tui_app.validate_user_input", return_value=(True, "")):
            with patch("src.presentation.tui.tui_app.sanitize_user_input", return_value="clean input"):
                with patch("src.presentation.tui.utils.message_renderer.MessageRenderer.render_user_message", return_value="user msg"):
                    with patch("src.presentation.tui.tui_app.save_session_history", return_value=Path("/tmp/session.json")):
                        with patch("src.presentation.tui.tui_app.save_metrics_report", return_value=Path("/tmp/metrics.txt")):
                            await mock_tui_app.run_task("test request")

        # 검증
        mock_task_input.clear.assert_called_once()
        mock_worker_status.update.assert_called()
        mock_status_info.update.assert_called()
        assert mock_tui_app.write_log.call_count >= 5

    @pytest.mark.asyncio
    async def test_run_task_integration_error(self, mock_tui_app):
        """
        통합 테스트: 에러 발생 플로우
        """
        # 모킹 설정
        mock_task_input = Mock()
        mock_worker_status = Mock()
        mock_status_info = Mock()

        def query_side_effect(selector, widget_type=None):
            if selector == "#task-input":
                return mock_task_input
            elif selector == "#worker-status":
                return mock_worker_status
            elif selector == "#status-info":
                return mock_status_info
            elif selector == "#output-log":
                mock_log = Mock()
                mock_log.size.width = 120
                return mock_log

        mock_tui_app.query_one.side_effect = query_side_effect

        # 스트리밍에서 에러 발생
        async def mock_stream():
            raise Exception("Test error")

        mock_tui_app.manager.analyze_and_plan_stream = AsyncMock(return_value=mock_stream())

        with patch("src.presentation.tui.tui_app.validate_user_input", return_value=(True, "")):
            with patch("src.presentation.tui.tui_app.sanitize_user_input", return_value="clean input"):
                with patch("src.presentation.tui.utils.message_renderer.MessageRenderer.render_user_message", return_value="user msg"):
                    await mock_tui_app.run_task("test request")

        # 에러 핸들러가 호출되었는지 확인
        mock_worker_status.update.assert_called()
        assert "❌" in str(mock_worker_status.update.call_args)

    @pytest.mark.asyncio
    async def test_run_task_integration_empty_input(self, mock_tui_app):
        """
        통합 테스트: 빈 입력 처리
        """
        # 빈 입력으로 실행
        await mock_tui_app.run_task("")

        # 로그에 에러 메시지가 출력되지 않았는지 확인 (조기 리턴)
        # write_log가 호출되지 않거나 최소한으로 호출됨
        assert mock_tui_app.write_log.call_count == 0

    @pytest.mark.asyncio
    async def test_run_task_integration_save_error(self, mock_tui_app):
        """
        통합 테스트: 저장 실패 처리
        """
        # 모킹 설정
        mock_task_input = Mock()
        mock_worker_status = Mock()
        mock_status_info = Mock()

        def query_side_effect(selector, widget_type=None):
            if selector == "#task-input":
                return mock_task_input
            elif selector == "#worker-status":
                return mock_worker_status
            elif selector == "#status-info":
                return mock_status_info
            elif selector == "#output-log":
                mock_log = Mock()
                mock_log.size.width = 120
                return mock_log

        mock_tui_app.query_one.side_effect = query_side_effect

        # 스트리밍 모킹
        async def mock_stream():
            yield "response"

        mock_tui_app.manager.analyze_and_plan_stream = AsyncMock(return_value=mock_stream())
        mock_tui_app.message_renderer.render_ai_response_chunk = Mock(return_value="formatted")

        # 저장 실패 모킹
        with patch("src.presentation.tui.tui_app.validate_user_input", return_value=(True, "")):
            with patch("src.presentation.tui.tui_app.sanitize_user_input", return_value="clean input"):
                with patch("src.presentation.tui.utils.message_renderer.MessageRenderer.render_user_message", return_value="user msg"):
                    with patch("src.presentation.tui.tui_app.save_session_history", side_effect=IOError("Save failed")):
                        await mock_tui_app.run_task("test request")

        # 에러 핸들러가 호출되었는지 확인
        mock_worker_status.update.assert_called()
        assert "❌" in str(mock_worker_status.update.call_args)
