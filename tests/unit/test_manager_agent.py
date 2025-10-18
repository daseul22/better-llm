"""
ManagerAgent 단위 테스트

ManagerAgent의 기능을 독립적으로 테스트합니다.
Claude Agent SDK는 mock으로 대체합니다.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from src.manager_agent import ManagerAgent
from src.models import Message, Role


class TestManagerAgent:
    """ManagerAgent 클래스 테스트"""

    def test_manager_agent_initialization(self):
        """매니저 에이전트 초기화 테스트"""
        manager = ManagerAgent()

        assert manager.model == "claude-sonnet-4-5-20250929"
        assert ManagerAgent.SYSTEM_PROMPT is not None
        assert "매니저" in ManagerAgent.SYSTEM_PROMPT

    def test_manager_agent_custom_model(self):
        """커스텀 모델로 초기화 테스트"""
        manager = ManagerAgent(model="claude-opus-4")

        assert manager.model == "claude-opus-4"

    def test_repr(self):
        """__repr__ 테스트"""
        manager = ManagerAgent()
        repr_str = repr(manager)

        assert "ManagerAgent" in repr_str
        assert "claude-sonnet-4-5-20250929" in repr_str


class TestBuildPromptFromHistory:
    """_build_prompt_from_history 메서드 테스트"""

    def test_build_prompt_empty_history(self):
        """빈 히스토리로 프롬프트 생성 테스트"""
        manager = ManagerAgent()
        prompt = manager._build_prompt_from_history([])

        assert ManagerAgent.SYSTEM_PROMPT in prompt
        assert "대화 히스토리" in prompt
        assert "다음 단계를 계획해주세요" in prompt

    def test_build_prompt_with_user_message(self):
        """사용자 메시지가 있는 히스토리로 프롬프트 생성 테스트"""
        manager = ManagerAgent()
        history = [
            Message(role=Role.USER, content="FastAPI로 API 만들어줘")
        ]

        prompt = manager._build_prompt_from_history(history)

        assert "[사용자]" in prompt
        assert "FastAPI로 API 만들어줘" in prompt

    def test_build_prompt_with_multiple_messages(self, sample_messages):
        """여러 메시지가 있는 히스토리로 프롬프트 생성 테스트"""
        manager = ManagerAgent()
        prompt = manager._build_prompt_from_history(sample_messages)

        assert "[사용자]" in prompt
        assert "[매니저 (당신)]" in prompt
        assert "[planner 작업 완료]" in prompt
        assert "사용자 요청" in prompt
        assert "작업 계획" in prompt
        assert "작업 완료" in prompt

    def test_build_prompt_preserves_order(self):
        """메시지 순서가 유지되는지 테스트"""
        manager = ManagerAgent()
        history = [
            Message(role=Role.USER, content="첫 번째"),
            Message(role=Role.MANAGER, content="두 번째"),
            Message(role=Role.AGENT, content="세 번째", agent_name="planner")
        ]

        prompt = manager._build_prompt_from_history(history)

        # 순서 확인
        first_idx = prompt.find("첫 번째")
        second_idx = prompt.find("두 번째")
        third_idx = prompt.find("세 번째")

        assert first_idx < second_idx < third_idx


class TestAnalyzeAndPlan:
    """analyze_and_plan 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_analyze_and_plan_success(self, mock_claude_agent_sdk):
        """작업 분석 및 계획 성공 테스트"""
        manager = ManagerAgent()
        history = [
            Message(role=Role.USER, content="API 만들어줘")
        ]

        response = await manager.analyze_and_plan(history)

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

        # SDK가 호출되었는지 확인
        mock_claude_agent_sdk.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_and_plan_with_empty_history(self, mock_claude_agent_sdk):
        """빈 히스토리로 분석 및 계획 테스트"""
        manager = ManagerAgent()

        response = await manager.analyze_and_plan([])

        assert response is not None
        mock_claude_agent_sdk.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_and_plan_sdk_options(self, mock_claude_agent_sdk):
        """SDK 옵션이 올바르게 전달되는지 테스트"""
        manager = ManagerAgent(model="claude-opus-4")
        history = [Message(role=Role.USER, content="테스트")]

        await manager.analyze_and_plan(history)

        # call_args로 전달된 인자 확인
        call_args = mock_claude_agent_sdk.call_args

        # options 인자 확인
        assert call_args is not None
        assert "options" in call_args.kwargs
        options = call_args.kwargs["options"]

        assert options.model == "claude-opus-4"
        assert options.allowed_tools == []  # 매니저는 툴을 사용하지 않음
        assert options.permission_mode == "bypassPermissions"

    @pytest.mark.asyncio
    async def test_analyze_and_plan_streaming_response(self):
        """스트리밍 응답을 올바르게 처리하는지 테스트"""
        manager = ManagerAgent()
        history = [Message(role=Role.USER, content="테스트")]

        # 여러 청크로 나뉜 스트리밍 응답 mock
        async def mock_streaming():
            responses = [
                Mock(content=[Mock(text="**작업 분석:**\n")]),
                Mock(content=[Mock(text="테스트 작업입니다.\n")]),
                Mock(content=[Mock(text="\n**다음 단계:**\n")]),
                Mock(content=[Mock(text="@planner 계획 수립")])
            ]
            for resp in responses:
                yield resp

        with patch('claude_agent_sdk.query', return_value=mock_streaming()):
            response = await manager.analyze_and_plan(history)

            # 모든 청크가 합쳐졌는지 확인
            assert "**작업 분석:**" in response
            assert "테스트 작업입니다." in response
            assert "**다음 단계:**" in response
            assert "@planner 계획 수립" in response

    @pytest.mark.asyncio
    async def test_analyze_and_plan_error_handling(self):
        """SDK 호출 실패 시 예외 처리 테스트"""
        manager = ManagerAgent()
        history = [Message(role=Role.USER, content="테스트")]

        # SDK 호출 시 에러 발생
        with patch('claude_agent_sdk.query', side_effect=Exception("SDK Error")):
            with pytest.raises(Exception) as exc_info:
                await manager.analyze_and_plan(history)

            assert "SDK Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_and_plan_response_text_extraction(self):
        """다양한 응답 형식에서 텍스트 추출 테스트"""
        manager = ManagerAgent()
        history = [Message(role=Role.USER, content="테스트")]

        # 1. content 속성이 있는 경우
        async def mock_with_content():
            yield Mock(content=[Mock(text="Response with content")])

        with patch('claude_agent_sdk.query', return_value=mock_with_content()):
            response = await manager.analyze_and_plan(history)
            assert response == "Response with content"

        # 2. text 속성이 직접 있는 경우
        async def mock_with_text():
            yield Mock(text="Direct text response", spec=['text'])

        with patch('claude_agent_sdk.query', return_value=mock_with_text()):
            response = await manager.analyze_and_plan(history)
            assert response == "Direct text response"

        # 3. 그 외의 경우 (문자열 변환)
        async def mock_other():
            yield "String response"

        with patch('claude_agent_sdk.query', return_value=mock_other()):
            response = await manager.analyze_and_plan(history)
            assert response == "String response"


class TestManagerAgentIntegration:
    """ManagerAgent의 통합 동작 테스트"""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, mock_claude_agent_sdk):
        """전체 대화 흐름 테스트"""
        manager = ManagerAgent()

        # 1단계: 사용자 요청
        history = [
            Message(role=Role.USER, content="FastAPI로 CRUD API 만들어줘")
        ]

        response1 = await manager.analyze_and_plan(history)
        assert response1 is not None

        # 2단계: 워커 작업 완료 후 매니저에게 보고
        history.append(Message(role=Role.MANAGER, content=response1))
        history.append(Message(
            role=Role.AGENT,
            content="계획 수립 완료",
            agent_name="planner"
        ))

        response2 = await manager.analyze_and_plan(history)
        assert response2 is not None

        # 매니저가 두 번 호출되었는지 확인
        assert mock_claude_agent_sdk.call_count == 2

    @pytest.mark.asyncio
    async def test_manager_with_complex_history(self, sample_messages, mock_claude_agent_sdk):
        """복잡한 히스토리를 처리하는 테스트"""
        manager = ManagerAgent()

        # 여러 턴의 대화가 있는 복잡한 히스토리
        complex_history = sample_messages + [
            Message(role=Role.USER, content="추가 요청"),
            Message(role=Role.MANAGER, content="추가 계획"),
            Message(role=Role.AGENT, content="추가 작업 완료", agent_name="coder")
        ]

        response = await manager.analyze_and_plan(complex_history)

        assert response is not None

        # SDK 호출 시 프롬프트에 모든 메시지가 포함되었는지 확인
        call_args = mock_claude_agent_sdk.call_args
        prompt = call_args.kwargs["prompt"]

        assert "사용자 요청" in prompt
        assert "작업 계획" in prompt
        assert "작업 완료" in prompt
        assert "추가 요청" in prompt
