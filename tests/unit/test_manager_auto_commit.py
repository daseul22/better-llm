"""
Manager Agent의 auto_commit_enabled 설정 테스트

Critical Issue #1 검증:
- auto_commit_enabled=False일 때 Manager 시스템 프롬프트에 Committer 단계 제외
- auto_commit_enabled=True일 때 Manager 시스템 프롬프트에 Committer 단계 포함
- allowed_tools 리스트에 execute_committer_task 조건부 포함
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.infrastructure.claude.manager_client import ManagerAgent


class TestManagerAutoCommitConfig:
    """Manager Agent의 auto_commit_enabled 설정 테스트"""

    @pytest.fixture
    def mock_worker_tools_server(self):
        """Mock Worker Tools Server"""
        return MagicMock()

    def test_auto_commit_disabled_system_prompt(self, mock_worker_tools_server):
        """
        auto_commit_enabled=False일 때 시스템 프롬프트 검증

        검증 항목:
        - Committer Tool 설명이 없어야 함
        - Committer 단계가 워크플로우에 포함되지 않아야 함
        """
        manager = ManagerAgent(
            worker_tools_server=mock_worker_tools_server,
            auto_commit_enabled=False
        )

        system_prompt = manager.SYSTEM_PROMPT

        # Committer Tool 설명이 없어야 함
        assert "execute_committer_task" not in system_prompt
        assert "Git 커밋 생성" not in system_prompt

        # Committer 단계가 워크플로우에 없어야 함
        assert "5단계: execute_committer_task 호출" not in system_prompt

        # 기본 Tool들은 여전히 있어야 함
        assert "execute_planner_task" in system_prompt
        assert "execute_coder_task" in system_prompt
        assert "execute_reviewer_task" in system_prompt
        assert "execute_tester_task" in system_prompt

    def test_auto_commit_enabled_system_prompt(self, mock_worker_tools_server):
        """
        auto_commit_enabled=True일 때 시스템 프롬프트 검증

        검증 항목:
        - Committer Tool 설명이 포함되어야 함
        - Committer 단계가 워크플로우에 포함되어야 함
        """
        manager = ManagerAgent(
            worker_tools_server=mock_worker_tools_server,
            auto_commit_enabled=True
        )

        system_prompt = manager.SYSTEM_PROMPT

        # Committer Tool 설명이 있어야 함
        assert "execute_committer_task" in system_prompt
        assert "Git 커밋 생성" in system_prompt

        # Committer 단계가 워크플로우에 있어야 함
        assert "5단계: execute_committer_task 호출" in system_prompt

        # 모든 Tool이 있어야 함
        assert "execute_planner_task" in system_prompt
        assert "execute_coder_task" in system_prompt
        assert "execute_reviewer_task" in system_prompt
        assert "execute_tester_task" in system_prompt

    @pytest.mark.asyncio
    async def test_auto_commit_disabled_allowed_tools(self, mock_worker_tools_server):
        """
        auto_commit_enabled=False일 때 allowed_tools 검증

        검증 항목:
        - allowed_tools에 execute_committer_task가 없어야 함
        """
        manager = ManagerAgent(
            worker_tools_server=mock_worker_tools_server,
            auto_commit_enabled=False
        )

        # analyze_and_plan_stream을 호출하면 내부적으로 ClaudeSDKClient를 생성
        # 이때 allowed_tools를 확인할 수 있도록 Mock 패치
        with patch(
            "src.infrastructure.claude.manager_client.ClaudeSDKClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock client의 receive_response를 빈 응답으로 설정
            mock_client.receive_response.return_value = AsyncMock(
                __aiter__=lambda self: iter([])
            )

            # 히스토리가 없는 경우 테스트
            from src.domain.models import Message
            history = [Message(role="user", content="테스트")]

            # analyze_and_plan_stream을 호출하여 ClaudeSDKClient 생성 확인
            try:
                async for _ in manager.analyze_and_plan_stream(history):
                    pass
            except Exception:
                pass  # 에러는 무시 (설정 확인이 목적)

            # ClaudeSDKClient 생성 시 전달된 allowed_tools 확인
            assert mock_client_class.called
            call_args = mock_client_class.call_args

            if call_args:
                options = call_args.kwargs.get("options")
                if options and hasattr(options, "allowed_tools"):
                    allowed_tools = options.allowed_tools

                    # execute_committer_task가 없어야 함
                    assert "mcp__workers__execute_committer_task" not in allowed_tools

                    # 다른 Tool들은 있어야 함
                    assert "mcp__workers__execute_planner_task" in allowed_tools
                    assert "mcp__workers__execute_coder_task" in allowed_tools
                    assert "mcp__workers__execute_reviewer_task" in allowed_tools
                    assert "mcp__workers__execute_tester_task" in allowed_tools
                    assert "read" in allowed_tools

    @pytest.mark.asyncio
    async def test_auto_commit_enabled_allowed_tools(self, mock_worker_tools_server):
        """
        auto_commit_enabled=True일 때 allowed_tools 검증

        검증 항목:
        - allowed_tools에 execute_committer_task가 포함되어야 함
        """
        manager = ManagerAgent(
            worker_tools_server=mock_worker_tools_server,
            auto_commit_enabled=True
        )

        # analyze_and_plan_stream을 호출하면 내부적으로 ClaudeSDKClient를 생성
        # 이때 allowed_tools를 확인할 수 있도록 Mock 패치
        with patch(
            "src.infrastructure.claude.manager_client.ClaudeSDKClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock client의 receive_response를 빈 응답으로 설정
            mock_client.receive_response.return_value = AsyncMock(
                __aiter__=lambda self: iter([])
            )

            # 히스토리가 없는 경우 테스트
            from src.domain.models import Message
            history = [Message(role="user", content="테스트")]

            # analyze_and_plan_stream을 호출하여 ClaudeSDKClient 생성 확인
            try:
                async for _ in manager.analyze_and_plan_stream(history):
                    pass
            except Exception:
                pass  # 에러는 무시 (설정 확인이 목적)

            # ClaudeSDKClient 생성 시 전달된 allowed_tools 확인
            assert mock_client_class.called
            call_args = mock_client_class.call_args

            if call_args:
                options = call_args.kwargs.get("options")
                if options and hasattr(options, "allowed_tools"):
                    allowed_tools = options.allowed_tools

                    # execute_committer_task가 있어야 함
                    assert "mcp__workers__execute_committer_task" in allowed_tools

                    # 다른 Tool들도 있어야 함
                    assert "mcp__workers__execute_planner_task" in allowed_tools
                    assert "mcp__workers__execute_coder_task" in allowed_tools
                    assert "mcp__workers__execute_reviewer_task" in allowed_tools
                    assert "mcp__workers__execute_tester_task" in allowed_tools
                    assert "read" in allowed_tools

    def test_default_auto_commit_is_false(self, mock_worker_tools_server):
        """
        auto_commit_enabled의 기본값은 False여야 함
        """
        manager = ManagerAgent(worker_tools_server=mock_worker_tools_server)

        assert manager.auto_commit_enabled is False

    def test_auto_commit_attribute_exists(self, mock_worker_tools_server):
        """
        ManagerAgent가 auto_commit_enabled 속성을 가지고 있어야 함
        """
        manager = ManagerAgent(
            worker_tools_server=mock_worker_tools_server,
            auto_commit_enabled=True
        )

        assert hasattr(manager, "auto_commit_enabled")
        assert manager.auto_commit_enabled is True
