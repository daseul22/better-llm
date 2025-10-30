"""
설정 로더 구현

JsonConfigLoader: JSON 파일에서 설정 로드
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from src.domain.models import AgentConfig
from src.infrastructure.logging import get_logger

logger = get_logger(__name__, component="ConfigLoader")


@dataclass
class SystemConfig:
    """
    시스템 설정 구현

    JSON 파일에서 로드된 설정
    딕셔너리 접근도 지원 (하위 호환성)
    """
    # Manager 설정
    manager_model: str = "claude-sonnet-4-5-20250929"
    max_history_messages: int = 20
    max_turns: int = 10

    # Performance 설정
    enable_caching: bool = True
    worker_retry_enabled: bool = True
    worker_retry_max_attempts: int = 3
    worker_retry_base_delay: float = 1.0

    # Security 설정
    max_input_length: int = 5000
    enable_input_validation: bool = True

    # Logging 설정
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_structured_logging: bool = False

    _raw_data: dict = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        """dataclass 초기화 후 처리"""
        # _raw_data는 field로 정의되어 자동 초기화됨
        # 추가 초기화 로직이 필요하면 여기에 작성
        pass

    def get(self, key: str, default=None):
        """
        딕셔너리처럼 get() 메서드 제공

        Args:
            key: 설정 키
            default: 기본값

        Returns:
            설정 값 또는 기본값
        """
        # 먼저 dataclass 필드 확인
        if hasattr(self, key):
            return getattr(self, key)

        # _raw_data에서 확인
        return self._raw_data.get(key, default)

    def __getitem__(self, key: str):
        """
        딕셔너리처럼 [] 접근 제공

        Args:
            key: 설정 키

        Returns:
            설정 값

        Raises:
            KeyError: 키가 없을 경우
        """
        if hasattr(self, key):
            return getattr(self, key)

        if key in self._raw_data:
            return self._raw_data[key]
        raise KeyError(f"설정 키를 찾을 수 없습니다: {key}")


class JsonConfigLoader:
    """
    JSON 설정 로더

    config/agent_config.json, config/system_config.json에서 설정 로드
    """

    def __init__(self, project_root: Path):
        """
        Args:
            project_root: 프로젝트 루트 디렉토리
        """
        self.project_root = project_root
        self.agent_config_path = project_root / "config" / "agent_config.json"
        self.system_config_path = project_root / "config" / "system_config.json"

    def load_agent_configs(self) -> List[AgentConfig]:
        """
        에이전트 설정 로드

        Returns:
            AgentConfig 리스트

        Raises:
            FileNotFoundError: 설정 파일이 없을 경우
            ValueError: 설정 파일 형식이 잘못된 경우
        """
        if not self.agent_config_path.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {self.agent_config_path}")

        try:
            with open(self.agent_config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 유효성 검증
            if "agents" not in data:
                raise ValueError("설정 파일에 'agents' 필드가 없습니다")

            agents_data = data["agents"]
            if not isinstance(agents_data, list):
                raise ValueError("'agents'는 리스트여야 합니다")

            # AgentConfig 객체 생성
            agent_configs = []
            for agent_data in agents_data:
                # 필수 필드 검증
                required_fields = ["name", "role", "system_prompt_file", "allowed_tools", "model"]
                for field in required_fields:
                    if field not in agent_data:
                        raise ValueError(f"에이전트 설정에 필수 필드 '{field}'가 없습니다: {agent_data}")

                # system_prompt_file을 system_prompt로 변환
                agent_data_copy = agent_data.copy()
                agent_data_copy["system_prompt"] = agent_data_copy.pop("system_prompt_file")

                config = AgentConfig.from_dict(agent_data_copy)
                agent_configs.append(config)

            logger.info("Agent configs loaded", count=len(agent_configs))
            return agent_configs

        except json.JSONDecodeError as e:
            logger.error("JSON parsing failed", config_path=str(self.agent_config_path), error=str(e))
            raise ValueError(f"JSON 파싱 실패: {e}")
        except Exception as e:
            logger.error("Config loading failed", config_path=str(self.agent_config_path), error=str(e))
            raise ValueError(f"설정 파일 로드 실패: {e}")

    def load_system_config(self) -> SystemConfig:
        """
        시스템 설정 로드

        Returns:
            시스템 설정 객체

        Raises:
            Exception: 로드 실패 시 (기본값 사용)
        """
        if not self.system_config_path.exists():
            logger.warning(f"시스템 설정 파일이 없습니다: {self.system_config_path}. 기본값 사용.")
            return SystemConfig()

        try:
            with open(self.system_config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            manager = data.get("manager", {})
            performance = data.get("performance", {})
            security = data.get("security", {})
            logging_config = data.get("logging", {})

            config = SystemConfig(
                manager_model=manager.get("model", "claude-sonnet-4-5-20250929"),
                max_history_messages=manager.get("max_history_messages", 20),
                max_turns=manager.get("max_turns", 10),
                enable_caching=performance.get("enable_caching", True),
                worker_retry_enabled=performance.get("worker_retry_enabled", True),
                worker_retry_max_attempts=performance.get("worker_retry_max_attempts", 3),
                worker_retry_base_delay=performance.get("worker_retry_base_delay", 1.0),
                max_input_length=security.get("max_input_length", 5000),
                enable_input_validation=security.get("enable_input_validation", True),
                log_level=logging_config.get("level", "INFO"),
                log_format=logging_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                enable_structured_logging=logging_config.get("enable_structured_logging", False)
            )

            # 원본 데이터 저장 (딕셔너리 접근용)
            config._raw_data = data

            return config

        except Exception as e:
            logger.error(f"시스템 설정 로드 실패: {e}. 기본값 사용.")
            return SystemConfig()


def load_system_config() -> SystemConfig:
    """
    시스템 설정을 SystemConfig 객체로 로드 (간편 함수)

    Returns:
        SystemConfig: 설정 객체 (파일이 없으면 기본 설정 반환)

    Raises:
        json.JSONDecodeError: JSON 파싱 실패 시
        OSError: 파일 읽기 실패 시 (권한 문제 등)
    """
    from .validator import get_project_root

    config_path = get_project_root() / "config" / "system_config.json"

    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}. Using default config.")
        return SystemConfig()

    try:
        # JsonConfigLoader를 사용하여 SystemConfig 객체 생성
        loader = JsonConfigLoader(get_project_root())
        return loader.load_system_config()
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config JSON: {config_path} - {e}")
        raise
    except OSError as e:
        logger.error(f"Failed to read config file: {config_path} - {e}")
        raise
