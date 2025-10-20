"""
Tests for config loader

src/infrastructure/config/loader.py 테스트
"""
import json
import pytest
from pathlib import Path

from src.infrastructure.config.loader import (
    JsonConfigLoader,
    SystemConfig,
    load_system_config,
)
from src.domain.models import AgentConfig


@pytest.mark.unit
class TestSystemConfig:
    """SystemConfig 데이터클래스 테스트"""

    def test_system_config_default_values(self):
        """기본값으로 SystemConfig 초기화 테스트"""
        config = SystemConfig()

        assert hasattr(config, "_raw_data")
        assert isinstance(config._raw_data, dict)
        assert config.manager_model == "claude-sonnet-4-5-20250929"

    def test_system_config_get_method(self):
        """get() 메서드 테스트"""
        config = SystemConfig()

        # dataclass 필드 접근
        assert config.get("manager_model") == "claude-sonnet-4-5-20250929"

        # 기본값 반환
        assert config.get("nonexistent_key", "default") == "default"

    def test_system_config_getitem(self):
        """__getitem__ 메서드 테스트"""
        config = SystemConfig()

        # dataclass 필드 접근
        assert config["manager_model"] == "claude-sonnet-4-5-20250929"

        # 존재하지 않는 키 접근 시 KeyError
        with pytest.raises(KeyError):
            _ = config["nonexistent_key"]


@pytest.mark.unit
class TestJsonConfigLoader:
    """JsonConfigLoader 테스트"""

    def test_load_agent_configs_success(self, tmp_path: Path):
        """에이전트 설정 로드 성공 테스트"""
        # 설정 파일 생성
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "agent_config.json"

        config_data = {
            "agents": [
                {
                    "name": "planner",
                    "role": "Planning Agent",
                    "system_prompt_file": "prompts/planner.md",
                    "tools": ["read", "glob", "grep"],
                    "model": "claude-sonnet-4"
                },
                {
                    "name": "coder",
                    "role": "Coding Agent",
                    "system_prompt_file": "prompts/coder.md",
                    "tools": ["read", "write", "edit"],
                    "model": "claude-sonnet-4"
                }
            ]
        }
        config_file.write_text(json.dumps(config_data))

        # 로더 생성 및 로드
        loader = JsonConfigLoader(tmp_path)
        configs = loader.load_agent_configs()

        # 검증
        assert len(configs) == 2
        assert configs[0].name == "planner"
        assert configs[0].role == "Planning Agent"
        assert configs[1].name == "coder"
        assert configs[1].tools == ["read", "write", "edit"]

    def test_load_agent_configs_file_not_found(self, tmp_path: Path):
        """설정 파일이 없을 때 FileNotFoundError 발생 테스트"""
        loader = JsonConfigLoader(tmp_path)

        with pytest.raises(FileNotFoundError):
            loader.load_agent_configs()

    def test_load_agent_configs_invalid_json(self, tmp_path: Path):
        """잘못된 JSON 형식 테스트"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "agent_config.json"
        config_file.write_text("{ invalid json }")

        loader = JsonConfigLoader(tmp_path)

        with pytest.raises(ValueError, match="JSON 파싱 실패"):
            loader.load_agent_configs()

    def test_load_agent_configs_missing_agents_field(self, tmp_path: Path):
        """'agents' 필드가 없을 때 ValueError 발생 테스트"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "agent_config.json"
        config_file.write_text(json.dumps({"not_agents": []}))

        loader = JsonConfigLoader(tmp_path)

        with pytest.raises(ValueError, match="'agents' 필드가 없습니다"):
            loader.load_agent_configs()

    def test_load_agent_configs_missing_required_field(self, tmp_path: Path):
        """필수 필드가 없을 때 ValueError 발생 테스트"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "agent_config.json"

        # 'model' 필드 누락
        config_data = {
            "agents": [
                {
                    "name": "planner",
                    "role": "Planning Agent",
                    "system_prompt_file": "prompts/planner.md",
                    "tools": ["read"]
                    # "model" 누락
                }
            ]
        }
        config_file.write_text(json.dumps(config_data))

        loader = JsonConfigLoader(tmp_path)

        with pytest.raises(ValueError, match="필수 필드"):
            loader.load_agent_configs()

    def test_load_system_config_success(self, tmp_path: Path):
        """시스템 설정 로드 성공 테스트"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "system_config.json"

        config_data = {
            "manager": {
                "model": "claude-sonnet-4",
                "max_history_messages": 30,
                "max_turns": 15
            },
            "performance": {
                "enable_caching": True,
                "worker_retry_enabled": True
            },
            "security": {
                "max_input_length": 10000,
                "enable_input_validation": True
            },
            "logging": {
                "level": "DEBUG",
                "enable_structured_logging": True
            }
        }
        config_file.write_text(json.dumps(config_data))

        loader = JsonConfigLoader(tmp_path)
        config = loader.load_system_config()

        # 검증
        assert config.manager_model == "claude-sonnet-4"
        assert config.max_history_messages == 30
        assert config.max_turns == 15
        assert config.enable_caching is True
        assert config.log_level == "DEBUG"

    def test_load_system_config_file_not_found(self, tmp_path: Path):
        """시스템 설정 파일이 없을 때 기본값 사용 테스트"""
        loader = JsonConfigLoader(tmp_path)
        config = loader.load_system_config()

        # 기본값 검증
        assert config.manager_model == "claude-sonnet-4-5-20250929"
        assert isinstance(config, SystemConfig)


@pytest.mark.unit
class TestLoadSystemConfigFunction:
    """load_system_config() 함수 테스트"""

    def test_load_system_config_success(self, tmp_path: Path, monkeypatch):
        """load_system_config 함수 성공 테스트"""
        # get_project_root를 tmp_path로 모킹
        def mock_get_project_root():
            return tmp_path

        monkeypatch.setattr(
            "src.infrastructure.config.loader.get_project_root",
            mock_get_project_root
        )

        # 설정 파일 생성
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "system_config.json"

        config_data = {
            "manager": {"model": "claude-sonnet-4"},
            "test_key": "test_value"
        }
        config_file.write_text(json.dumps(config_data))

        # 로드
        result = load_system_config()

        # 검증
        assert isinstance(result, dict)
        assert result["manager"]["model"] == "claude-sonnet-4"
        assert result["test_key"] == "test_value"

    def test_load_system_config_file_not_found(self, tmp_path: Path, monkeypatch):
        """설정 파일이 없을 때 빈 딕셔너리 반환 테스트"""
        # get_project_root를 tmp_path로 모킹
        def mock_get_project_root():
            return tmp_path

        monkeypatch.setattr(
            "src.infrastructure.config.loader.get_project_root",
            mock_get_project_root
        )

        # 설정 파일 없음
        result = load_system_config()

        # 빈 딕셔너리 반환
        assert result == {}

    def test_load_system_config_invalid_json(self, tmp_path: Path, monkeypatch):
        """잘못된 JSON 파싱 시 JSONDecodeError 발생 테스트"""
        # get_project_root를 tmp_path로 모킹
        def mock_get_project_root():
            return tmp_path

        monkeypatch.setattr(
            "src.infrastructure.config.loader.get_project_root",
            mock_get_project_root
        )

        # 설정 파일 생성 (잘못된 JSON)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "system_config.json"
        config_file.write_text("{ invalid json }")

        # JSONDecodeError 발생
        with pytest.raises(json.JSONDecodeError):
            load_system_config()
