"""
설정 포트 (인터페이스)

IConfigLoader: 설정 로드 인터페이스
ISystemConfig: 시스템 설정 인터페이스
"""

from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass

from domain.models import AgentConfig


@dataclass
class ISystemConfig:
    """
    시스템 설정 인터페이스

    Infrastructure 계층에서 구현됨
    """
    # Manager 설정
    manager_model: str = "claude-sonnet-4-5-20250929"
    max_history_messages: int = 20
    max_turns: int = 10

    # 성능 설정
    enable_caching: bool = True
    worker_retry_enabled: bool = True
    worker_retry_max_attempts: int = 3
    worker_retry_base_delay: float = 1.0

    # 보안 설정
    max_input_length: int = 5000
    enable_input_validation: bool = True

    # 로깅 설정
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_structured_logging: bool = False


class IConfigLoader(ABC):
    """
    설정 로더 인터페이스

    Infrastructure 계층에서 구현됨 (JSON, YAML 등)
    """

    @abstractmethod
    def load_agent_configs(self) -> List[AgentConfig]:
        """
        에이전트 설정 로드

        Returns:
            AgentConfig 리스트

        Raises:
            Exception: 로드 실패 시
        """
        pass

    @abstractmethod
    def load_system_config(self) -> ISystemConfig:
        """
        시스템 설정 로드

        Returns:
            시스템 설정 객체

        Raises:
            Exception: 로드 실패 시
        """
        pass
