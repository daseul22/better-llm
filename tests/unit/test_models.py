"""
데이터 모델 단위 테스트

Message, AgentConfig, SessionResult 등의 데이터 모델을 테스트합니다.
"""

import pytest
from datetime import datetime

from src.models import Message, AgentConfig, SessionResult, Role


class TestMessage:
    """Message 클래스 테스트"""

    def test_message_creation(self):
        """메시지 생성 테스트"""
        msg = Message(
            role=Role.USER,
            content="Test message"
        )

        assert msg.role == Role.USER
        assert msg.content == "Test message"
        assert msg.agent_name is None
        assert isinstance(msg.timestamp, datetime)

    def test_message_with_agent_name(self):
        """에이전트 이름이 있는 메시지 생성 테스트"""
        msg = Message(
            role=Role.AGENT,
            content="Agent response",
            agent_name="planner"
        )

        assert msg.role == Role.AGENT
        assert msg.agent_name == "planner"

    def test_message_to_dict(self, sample_message):
        """메시지를 딕셔너리로 변환 테스트"""
        msg_dict = sample_message.to_dict()

        assert msg_dict["role"] == Role.USER
        assert msg_dict["content"] == "Hello, world!"
        assert msg_dict["agent_name"] is None
        assert isinstance(msg_dict["timestamp"], str)

    def test_message_from_dict(self):
        """딕셔너리에서 메시지 생성 테스트"""
        data = {
            "role": "user",
            "content": "Test",
            "agent_name": None,
            "timestamp": "2024-01-01T12:00:00"
        }

        msg = Message.from_dict(data)

        assert msg.role == "user"
        assert msg.content == "Test"
        assert isinstance(msg.timestamp, datetime)

    def test_message_serialization_roundtrip(self, sample_message):
        """직렬화/역직렬화 왕복 테스트"""
        msg_dict = sample_message.to_dict()
        restored_msg = Message.from_dict(msg_dict)

        assert restored_msg.role == sample_message.role
        assert restored_msg.content == sample_message.content
        assert restored_msg.agent_name == sample_message.agent_name
        # 타임스탬프는 마이크로초 정밀도가 다를 수 있으므로 날짜만 비교
        assert restored_msg.timestamp.date() == sample_message.timestamp.date()


class TestAgentConfig:
    """AgentConfig 클래스 테스트"""

    def test_agent_config_creation(self):
        """에이전트 설정 생성 테스트"""
        config = AgentConfig(
            name="test_agent",
            role="Test Agent",
            system_prompt="You are a test agent.",
            tools=["read", "write"],
            model="claude-sonnet-4"
        )

        assert config.name == "test_agent"
        assert config.role == "Test Agent"
        assert config.tools == ["read", "write"]
        assert config.model == "claude-sonnet-4"

    def test_agent_config_default_model(self):
        """기본 모델 설정 테스트"""
        config = AgentConfig(
            name="test_agent",
            role="Test Agent",
            system_prompt="Test prompt",
            tools=[]
        )

        assert config.model == "claude-sonnet-4"

    def test_agent_config_to_dict(self, sample_agent_config):
        """에이전트 설정을 딕셔너리로 변환 테스트"""
        config_dict = sample_agent_config.to_dict()

        assert config_dict["name"] == "test_agent"
        assert config_dict["role"] == "Test Agent"
        assert config_dict["tools"] == ["read", "write"]
        assert config_dict["model"] == "claude-sonnet-4"

    def test_agent_config_from_dict(self):
        """딕셔너리에서 에이전트 설정 생성 테스트"""
        data = {
            "name": "planner",
            "role": "Planning Agent",
            "system_prompt": "You are a planner.",
            "tools": ["read", "glob"],
            "model": "claude-sonnet-4"
        }

        config = AgentConfig.from_dict(data)

        assert config.name == "planner"
        assert config.role == "Planning Agent"
        assert config.tools == ["read", "glob"]

    def test_agent_config_serialization_roundtrip(self, sample_agent_config):
        """직렬화/역직렬화 왕복 테스트"""
        config_dict = sample_agent_config.to_dict()
        restored_config = AgentConfig.from_dict(config_dict)

        assert restored_config.name == sample_agent_config.name
        assert restored_config.role == sample_agent_config.role
        assert restored_config.system_prompt == sample_agent_config.system_prompt
        assert restored_config.tools == sample_agent_config.tools
        assert restored_config.model == sample_agent_config.model


class TestSessionResult:
    """SessionResult 클래스 테스트"""

    def test_session_result_creation(self):
        """세션 결과 생성 테스트"""
        result = SessionResult(
            status="completed",
            files_modified=["test.py"],
            tests_passed=True,
            error_message=None
        )

        assert result.status == "completed"
        assert result.files_modified == ["test.py"]
        assert result.tests_passed is True
        assert result.error_message is None

    def test_session_result_with_error(self):
        """에러가 있는 세션 결과 테스트"""
        result = SessionResult(
            status="error",
            error_message="Something went wrong"
        )

        assert result.status == "error"
        assert result.error_message == "Something went wrong"
        assert result.files_modified == []
        assert result.tests_passed is None

    def test_session_result_to_dict(self, sample_session_result):
        """세션 결과를 딕셔너리로 변환 테스트"""
        result_dict = sample_session_result.to_dict()

        assert result_dict["status"] == "completed"
        assert result_dict["files_modified"] == ["test.py", "main.py"]
        assert result_dict["tests_passed"] is True
        assert result_dict["error_message"] is None

    def test_session_result_default_values(self):
        """기본값 테스트"""
        result = SessionResult(status="pending")

        assert result.status == "pending"
        assert result.files_modified == []
        assert result.tests_passed is None
        assert result.error_message is None


class TestRole:
    """Role Enum 테스트"""

    def test_role_values(self):
        """Role enum 값 테스트"""
        assert Role.USER == "user"
        assert Role.AGENT == "agent"
        assert Role.MANAGER == "manager"
        assert Role.SYSTEM == "system"

    def test_role_membership(self):
        """Role enum 멤버십 테스트"""
        assert "user" in [role.value for role in Role]
        assert "agent" in [role.value for role in Role]
        assert "manager" in [role.value for role in Role]
        assert "system" in [role.value for role in Role]

    def test_role_string_comparison(self):
        """Role과 문자열 비교 테스트"""
        msg = Message(role=Role.USER, content="test")

        # Role은 str의 서브클래스이므로 직접 비교 가능
        assert msg.role == "user"
        assert msg.role == Role.USER
