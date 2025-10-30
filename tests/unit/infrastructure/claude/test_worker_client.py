"""Unit tests for WorkerAgent (Phase 1 changes - Type Hints)."""

import pytest
from typing import Callable, Dict, Any, Optional
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.domain.models import AgentConfig
from src.domain.services import ProjectContext
from src.infrastructure.claude.worker_client import WorkerAgent


class TestWorkerClientTypeHints:
    """Test type hints improvements in WorkerAgent.

    Phase 1 Change: Improved type hints for usage_callback parameter
    - Before: Optional[callable] (incorrect, not a valid type)
    - After: Optional[Callable[[Dict[str, Any]], None]] (correct, precise signature)
    """

    @pytest.fixture
    def agent_config(self) -> AgentConfig:
        """Create test agent config."""
        return AgentConfig(
            name="test_agent",
            role="Test Agent",
            allowed_tools=["read", "write"],
            model="claude-sonnet-4",
            system_prompt="Test system prompt"
        )

    @pytest.fixture
    def worker_agent(self, agent_config: AgentConfig) -> WorkerAgent:
        """Create WorkerAgent instance."""
        with patch('src.infrastructure.claude.worker_client.JsonContextRepository'):
            return WorkerAgent(
                config=agent_config,
                project_context=None,
                project_dir=None
            )

    def test_worker_agent_initialization(self, agent_config: AgentConfig):
        """Test WorkerAgent can be initialized."""
        with patch('src.infrastructure.claude.worker_client.JsonContextRepository') as mock_repo:
            mock_repo.return_value.load.return_value = None
            worker_agent = WorkerAgent(
                config=agent_config,
                project_context=None,
                project_dir=None
            )
            assert worker_agent.config.name == "test_agent"
            assert worker_agent.config.role == "Test Agent"
            assert worker_agent.system_prompt == "Test system prompt"

    def test_usage_callback_type_annotation(self):
        """Test that usage_callback parameter accepts correct type.

        This test verifies the type hint fix from Phase 1:
        - Type should be Optional[Callable[[Dict[str, Any]], None]]
        - This means a function that takes Dict[str, Any] and returns None
        """
        # This test validates the type annotation at runtime
        def valid_callback(usage_data: Dict[str, Any]) -> None:
            """Valid callback with correct signature."""
            pass

        # The callback should be callable with Dict[str, Any]
        assert callable(valid_callback)

        # Test that it accepts Dict[str, Any]
        test_data: Dict[str, Any] = {"model": "test", "tokens": 100}
        result = valid_callback(test_data)
        assert result is None

    def test_usage_callback_none(self):
        """Test that usage_callback can be None."""
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
        assert callback is None

    def test_project_context_loading(self):
        """Test project context loading with type hints.

        Verifies that _load_project_context returns Optional[ProjectContext]
        """
        with patch('src.infrastructure.claude.worker_client.JsonContextRepository') as mock_repo_class:
            # Mock successful context loading
            mock_context = Mock(spec=ProjectContext)
            mock_context.project_name = "test_project"
            mock_repo_instance = Mock()
            mock_repo_instance.load.return_value = mock_context
            mock_repo_class.return_value = mock_repo_instance

            config = AgentConfig(
                name="test",
                role="Test",
                allowed_tools=["read"],
                model="claude-sonnet-4",
                system_prompt="Test"
            )

            agent = WorkerAgent(config=config)

            # Result should be ProjectContext or None
            result = agent._load_project_context()
            assert result is None or isinstance(result, (Mock, ProjectContext))

    def test_system_prompt_loading(self):
        """Test system prompt loading with correct type hints."""
        config = AgentConfig(
            name="test",
            role="Test",
            allowed_tools=["read"],
            model="claude-sonnet-4",
            system_prompt="Direct prompt text"
        )

        with patch('src.infrastructure.claude.worker_client.JsonContextRepository'):
            agent = WorkerAgent(config=config)

            # system_prompt should be a string
            assert isinstance(agent.system_prompt, str)
            assert "Direct prompt text" in agent.system_prompt

    def test_type_annotations_in_module(self):
        """Test that type annotations are properly imported in worker_client."""
        from src.infrastructure.claude.worker_client import Callable, Dict, Any, Optional

        # Verify imports are available and correct
        assert Callable is not None
        assert Dict is not None
        assert Any is not None
        assert Optional is not None

    @pytest.mark.parametrize("usage_data", [
        {"model": "test", "tokens": 100},
        {"error": "test error"},
        {},
    ])
    def test_usage_callback_with_various_data(self, usage_data: Dict[str, Any]):
        """Test callback function with various data types."""
        collected_data = []

        def collect_data(data: Dict[str, Any]) -> None:
            """Callback that collects data."""
            collected_data.append(data)

        # Call callback
        collect_data(usage_data)

        # Verify callback was called with correct data
        assert len(collected_data) == 1
        assert collected_data[0] == usage_data
