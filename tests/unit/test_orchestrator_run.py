"""
orchestrator.py run() 메서드 리팩토링 테스트

6개 헬퍼 함수 및 run() 통합 테스트:
1. _validate_and_prepare_input
2. _print_session_header
3. _execute_manager_turn
4. _check_completion_condition
5. _handle_max_turns_reached
6. _finalize_session
"""

import pytest
import asyncio
import time
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call

from src.presentation.cli.orchestrator import Orchestrator
from src.domain.models import SessionResult
from src.domain.models.session import SessionStatus


@pytest.fixture
def mock_orchestrator():
    """Orchestrator 모킹 픽스처"""
    with patch("src.presentation.cli.orchestrator.validate_environment"):
        with patch("src.presentation.cli.orchestrator.setup_logging"):
            with patch("src.presentation.cli.orchestrator.initialize_workers"):
                with patch("src.presentation.cli.orchestrator.create_worker_tools_server"):
                    with patch("src.presentation.cli.orchestrator.ManagerAgent"):
                        with patch("src.presentation.cli.orchestrator.load_system_config") as mock_config:
                            # 시스템 설정 모킹
                            mock_config.return_value = {
                                "manager_model": "claude-sonnet-4",
                                "max_history_messages": 10,
                                "max_turns": 5,
                                "workflow": {
                                    "auto_commit_enabled": False
                                }
                            }

                            orchestrator = Orchestrator(
                                config_path=Path("/tmp/config.json"),
                                verbose=False
                            )

                            # 모킹된 의존성 설정
                            orchestrator.manager = Mock()
                            orchestrator.history = Mock()
                            orchestrator.history.get_history = Mock(return_value=[])
                            orchestrator.history.add_message = Mock()
                            orchestrator.feedback = Mock()
                            orchestrator.renderer = Mock()
                            orchestrator.renderer.console = Mock()
                            orchestrator.renderer.console.print = Mock()
                            orchestrator.system_config = MagicMock()
                            orchestrator.system_config.max_turns = 5

                            yield orchestrator


class TestValidateAndPrepareInput:
    """_validate_and_prepare_input 테스트"""

    def test_validate_and_prepare_input_success(self, mock_orchestrator):
        """
        성공 케이스: 유효한 입력
        """
        with patch(
            "src.presentation.cli.orchestrator.validate_user_input",
            return_value=(True, "")
        ):
            with patch(
                "src.presentation.cli.orchestrator.sanitize_user_input",
                return_value="clean input"
            ):
                is_valid, error_msg, sanitized = mock_orchestrator._validate_and_prepare_input(
                    "test input"
                )

                assert is_valid is True
                assert error_msg == ""
                assert sanitized == "clean input"

    def test_validate_and_prepare_input_invalid(self, mock_orchestrator):
        """
        실패 케이스: 검증 실패
        """
        with patch(
            "src.presentation.cli.orchestrator.validate_user_input",
            return_value=(False, "Invalid input")
        ):
            is_valid, error_msg, sanitized = mock_orchestrator._validate_and_prepare_input(
                "invalid"
            )

            assert is_valid is False
            assert error_msg == "Invalid input"
            assert sanitized == ""

    def test_validate_and_prepare_input_empty(self, mock_orchestrator):
        """
        실패 케이스: 빈 입력
        """
        with patch(
            "src.presentation.cli.orchestrator.validate_user_input",
            return_value=(False, "입력이 비어있습니다")
        ):
            is_valid, error_msg, sanitized = mock_orchestrator._validate_and_prepare_input("")

            assert is_valid is False
            assert "입력이 비어있습니다" in error_msg
            assert sanitized == ""


class TestPrintSessionHeader:
    """_print_session_header 테스트"""

    def test_print_session_header_success(self, mock_orchestrator):
        """
        성공 케이스: 세션 헤더 출력
        """
        mock_orchestrator._print_session_header("test request")

        # renderer 메서드 호출 확인
        mock_orchestrator.renderer.print_header.assert_called_once_with(
            "Group Chat Orchestration v3.0",
            f"Worker Tools Architecture - Session {mock_orchestrator.session_id}"
        )
        mock_orchestrator.renderer.print_task_info.assert_called_once()

        # print_task_info 호출 인자 검증
        call_args = mock_orchestrator.renderer.print_task_info.call_args
        assert call_args.kwargs["task"] == "test request"
        assert call_args.kwargs["session_id"] == mock_orchestrator.session_id

    def test_print_session_header_with_long_request(self, mock_orchestrator):
        """
        성공 케이스: 긴 요청 텍스트 처리
        """
        long_request = "A" * 500
        mock_orchestrator._print_session_header(long_request)

        # 호출 확인
        mock_orchestrator.renderer.print_header.assert_called_once()
        mock_orchestrator.renderer.print_task_info.assert_called_once()


class TestExecuteManagerTurn:
    """_execute_manager_turn 테스트"""

    @pytest.mark.asyncio
    async def test_execute_manager_turn_success(self, mock_orchestrator):
        """
        성공 케이스: Manager 턴 실행
        """
        # 스트리밍 모킹
        async def mock_stream():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"

        mock_orchestrator.manager.analyze_and_plan_stream = AsyncMock(
            return_value=mock_stream()
        )

        response = await mock_orchestrator._execute_manager_turn(turn=1)

        assert response == "chunk1chunk2chunk3"
        mock_orchestrator.renderer.print_turn_header.assert_called_once_with(1, "ManagerAgent")
        assert mock_orchestrator.renderer.console.print.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_manager_turn_empty_response(self, mock_orchestrator):
        """
        경계 케이스: 빈 응답
        """
        async def mock_stream():
            return
            yield  # Never reached

        mock_orchestrator.manager.analyze_and_plan_stream = AsyncMock(
            return_value=mock_stream()
        )

        response = await mock_orchestrator._execute_manager_turn(turn=1)

        assert response == ""
        mock_orchestrator.renderer.print_turn_header.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_manager_turn_error(self, mock_orchestrator):
        """
        실패 케이스: 스트리밍 에러
        """
        async def mock_stream():
            raise Exception("Streaming error")

        mock_orchestrator.manager.analyze_and_plan_stream = AsyncMock(
            return_value=mock_stream()
        )

        with pytest.raises(Exception) as exc_info:
            await mock_orchestrator._execute_manager_turn(turn=1)

        assert "Streaming error" in str(exc_info.value)


class TestCheckCompletionCondition:
    """_check_completion_condition 테스트"""

    def test_check_completion_condition_completed_1(self, mock_orchestrator):
        """
        성공 케이스: "작업이 완료되었습니다" 포함
        """
        response = "작업이 완료되었습니다. 모든 파일을 생성했습니다."
        result = mock_orchestrator._check_completion_condition(response)

        assert result is True

    def test_check_completion_condition_completed_2(self, mock_orchestrator):
        """
        성공 케이스: "작업 완료" 포함
        """
        response = "작업 완료. 테스트를 통과했습니다."
        result = mock_orchestrator._check_completion_condition(response)

        assert result is True

    def test_check_completion_condition_not_completed(self, mock_orchestrator):
        """
        실패 케이스: 완료 키워드 없음
        """
        response = "진행 중입니다. 다음 단계로 넘어갑니다."
        result = mock_orchestrator._check_completion_condition(response)

        assert result is False

    def test_check_completion_condition_empty(self, mock_orchestrator):
        """
        경계 케이스: 빈 응답
        """
        response = ""
        result = mock_orchestrator._check_completion_condition(response)

        assert result is False

    def test_check_completion_condition_partial_match(self, mock_orchestrator):
        """
        경계 케이스: 부분 매칭 (완료되지 않음)
        """
        response = "작업을 시작했습니다."
        result = mock_orchestrator._check_completion_condition(response)

        assert result is False


class TestHandleMaxTurnsReached:
    """_handle_max_turns_reached 테스트"""

    def test_handle_max_turns_reached(self, mock_orchestrator):
        """
        성공 케이스: 최대 턴 도달 처리
        """
        result = mock_orchestrator._handle_max_turns_reached(max_turns=5)

        # 피드백 호출 확인
        mock_orchestrator.feedback.warning.assert_called_once_with(
            "최대 턴 수(5)에 도달했습니다",
            use_panel=False
        )

        # 결과 상태 확인
        assert result.status == SessionStatus.MAX_TURNS_REACHED

    def test_handle_max_turns_reached_different_values(self, mock_orchestrator):
        """
        성공 케이스: 다양한 max_turns 값
        """
        for max_turns in [1, 10, 20]:
            result = mock_orchestrator._handle_max_turns_reached(max_turns=max_turns)
            assert result.status == SessionStatus.MAX_TURNS_REACHED


class TestFinalizeSession:
    """_finalize_session 테스트"""

    def test_finalize_session_success(self, mock_orchestrator):
        """
        성공 케이스: 세션 종료 처리
        """
        with patch("src.presentation.cli.orchestrator.log_error_summary"):
            with patch(
                "src.presentation.cli.orchestrator.save_session_history",
                return_value=Path("/tmp/session.json")
            ):
                result = SessionResult(status=SessionStatus.COMPLETED)
                mock_orchestrator._finalize_session("test request", result)

                # 렌더러 호출 확인
                mock_orchestrator.renderer.console.print.assert_called()
                mock_orchestrator.renderer.print_footer.assert_called_once()

                # print_footer 인자 검증
                call_args = mock_orchestrator.renderer.print_footer.call_args[0]
                assert call_args[0] == mock_orchestrator.session_id

    def test_finalize_session_with_history(self, mock_orchestrator):
        """
        성공 케이스: 히스토리 포함 세션 종료
        """
        # 히스토리 설정
        mock_orchestrator.history.get_history.return_value = [
            Mock(role="user"),
            Mock(role="manager"),
            Mock(role="manager"),
        ]

        with patch("src.presentation.cli.orchestrator.log_error_summary"):
            with patch(
                "src.presentation.cli.orchestrator.save_session_history",
                return_value=Path("/tmp/session.json")
            ):
                result = SessionResult(status=SessionStatus.COMPLETED)
                mock_orchestrator._finalize_session("test request", result)

                # print_footer 호출 시 manager 메시지 카운트 확인
                call_args = mock_orchestrator.renderer.print_footer.call_args[0]
                # call_args[1]은 manager 메시지 수 (2개)
                assert call_args[1] == 2

    def test_finalize_session_save_error(self, mock_orchestrator):
        """
        실패 케이스: 세션 저장 실패
        """
        with patch("src.presentation.cli.orchestrator.log_error_summary"):
            with patch(
                "src.presentation.cli.orchestrator.save_session_history",
                side_effect=IOError("Save failed")
            ):
                result = SessionResult(status=SessionStatus.COMPLETED)

                # 에러가 발생해도 렌더러는 호출되어야 함
                with pytest.raises(IOError):
                    mock_orchestrator._finalize_session("test request", result)


class TestRunIntegration:
    """run() 통합 테스트"""

    @pytest.mark.asyncio
    async def test_run_integration_single_turn_completion(self, mock_orchestrator):
        """
        통합 테스트: 단일 턴에서 완료
        """
        # 스트리밍 모킹
        async def mock_stream():
            yield "작업이 완료되었습니다."

        mock_orchestrator.manager.analyze_and_plan_stream = AsyncMock(
            return_value=mock_stream()
        )

        with patch(
            "src.presentation.cli.orchestrator.validate_user_input",
            return_value=(True, "")
        ):
            with patch(
                "src.presentation.cli.orchestrator.sanitize_user_input",
                return_value="test request"
            ):
                with patch("src.presentation.cli.orchestrator.log_error_summary"):
                    with patch(
                        "src.presentation.cli.orchestrator.save_session_history",
                        return_value=Path("/tmp/session.json")
                    ):
                        result = await mock_orchestrator.run("test request")

        # 결과 확인
        assert result.status == SessionStatus.COMPLETED
        mock_orchestrator.feedback.success.assert_called_once()
        mock_orchestrator.history.add_message.assert_called()

    @pytest.mark.asyncio
    async def test_run_integration_multiple_turns(self, mock_orchestrator):
        """
        통합 테스트: 여러 턴 실행 후 완료
        """
        # 3턴 후 완료
        turn_count = 0

        async def mock_stream():
            nonlocal turn_count
            turn_count += 1
            if turn_count < 3:
                yield "진행 중입니다."
            else:
                yield "작업이 완료되었습니다."

        mock_orchestrator.manager.analyze_and_plan_stream = AsyncMock(
            side_effect=lambda _: mock_stream()
        )

        with patch(
            "src.presentation.cli.orchestrator.validate_user_input",
            return_value=(True, "")
        ):
            with patch(
                "src.presentation.cli.orchestrator.sanitize_user_input",
                return_value="test request"
            ):
                with patch("src.presentation.cli.orchestrator.log_error_summary"):
                    with patch(
                        "src.presentation.cli.orchestrator.save_session_history",
                        return_value=Path("/tmp/session.json")
                    ):
                        result = await mock_orchestrator.run("test request")

        # 결과 확인
        assert result.status == SessionStatus.COMPLETED
        assert turn_count == 3
        mock_orchestrator.feedback.success.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_integration_max_turns_reached(self, mock_orchestrator):
        """
        통합 테스트: 최대 턴 도달
        """
        # 완료되지 않는 응답
        async def mock_stream():
            yield "진행 중입니다."

        mock_orchestrator.manager.analyze_and_plan_stream = AsyncMock(
            return_value=mock_stream()
        )

        with patch(
            "src.presentation.cli.orchestrator.validate_user_input",
            return_value=(True, "")
        ):
            with patch(
                "src.presentation.cli.orchestrator.sanitize_user_input",
                return_value="test request"
            ):
                with patch("src.presentation.cli.orchestrator.log_error_summary"):
                    with patch(
                        "src.presentation.cli.orchestrator.save_session_history",
                        return_value=Path("/tmp/session.json")
                    ):
                        result = await mock_orchestrator.run("test request")

        # 결과 확인
        assert result.status == SessionStatus.MAX_TURNS_REACHED
        mock_orchestrator.feedback.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_integration_invalid_input(self, mock_orchestrator):
        """
        통합 테스트: 잘못된 입력
        """
        with patch(
            "src.presentation.cli.orchestrator.validate_user_input",
            return_value=(False, "Invalid input")
        ):
            result = await mock_orchestrator.run("invalid")

        # 결과 확인
        assert result.status == SessionStatus.INVALID_INPUT
        mock_orchestrator.feedback.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_integration_empty_input(self, mock_orchestrator):
        """
        통합 테스트: 빈 입력
        """
        with patch(
            "src.presentation.cli.orchestrator.validate_user_input",
            return_value=(False, "입력이 비어있습니다")
        ):
            result = await mock_orchestrator.run("")

        # 결과 확인
        assert result.status == SessionStatus.INVALID_INPUT
        mock_orchestrator.feedback.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_integration_streaming_error(self, mock_orchestrator):
        """
        통합 테스트: 스트리밍 에러
        """
        async def mock_stream():
            raise Exception("Streaming error")

        mock_orchestrator.manager.analyze_and_plan_stream = AsyncMock(
            return_value=mock_stream()
        )

        with patch(
            "src.presentation.cli.orchestrator.validate_user_input",
            return_value=(True, "")
        ):
            with patch(
                "src.presentation.cli.orchestrator.sanitize_user_input",
                return_value="test request"
            ):
                with patch("src.presentation.cli.orchestrator.log_error_summary"):
                    with patch(
                        "src.presentation.cli.orchestrator.save_session_history",
                        return_value=Path("/tmp/session.json")
                    ):
                        with pytest.raises(Exception) as exc_info:
                            await mock_orchestrator.run("test request")

        assert "Streaming error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_integration_finalize_always_called(self, mock_orchestrator):
        """
        통합 테스트: finally 블록이 항상 실행됨
        """
        # 에러 발생 시에도 finalize가 호출되는지 확인
        async def mock_stream():
            raise Exception("Test error")

        mock_orchestrator.manager.analyze_and_plan_stream = AsyncMock(
            return_value=mock_stream()
        )

        with patch(
            "src.presentation.cli.orchestrator.validate_user_input",
            return_value=(True, "")
        ):
            with patch(
                "src.presentation.cli.orchestrator.sanitize_user_input",
                return_value="test request"
            ):
                with patch("src.presentation.cli.orchestrator.log_error_summary") as mock_log:
                    with patch(
                        "src.presentation.cli.orchestrator.save_session_history",
                        return_value=Path("/tmp/session.json")
                    ):
                        with pytest.raises(Exception):
                            await mock_orchestrator.run("test request")

                        # log_error_summary가 호출되었는지 확인 (finalize 실행 증거)
                        mock_log.assert_called_once()
                        mock_orchestrator.renderer.print_footer.assert_called_once()
