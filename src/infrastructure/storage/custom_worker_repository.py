"""
커스텀 워커 저장소

프로젝트별 커스텀 워커를 .claude-flow/worker/ 폴더에 저장/로드
"""

import json
from pathlib import Path
from typing import List, Optional

from src.domain.models import AgentConfig
from src.infrastructure.logging import get_logger

logger = get_logger(__name__, component="CustomWorkerRepository")


class CustomWorkerRepository:
    """
    커스텀 워커 저장소

    {project_path}/.claude-flow/worker/ 구조:
    - {worker_name}.txt: 시스템 프롬프트
    - ../worker-config.json: 워커 설정 (agent_config.json 형식)
    """

    def __init__(self, project_path: Path):
        """
        Args:
            project_path: 프로젝트 루트 경로
        """
        self.project_path = Path(project_path)
        self.worker_dir = self.project_path / ".claude-flow" / "worker"
        self.config_path = self.project_path / ".claude-flow" / "worker-config.json"

    def _ensure_directories(self):
        """필요한 디렉토리 생성"""
        self.worker_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Worker directory ensured", path=str(self.worker_dir))

    def save_custom_worker(
        self,
        worker_name: str,
        prompt_content: str,
        allowed_tools: List[str],
        model: str = "claude-sonnet-4-5-20250929",
        thinking: bool = False,
        role: Optional[str] = None
    ) -> Path:
        """
        커스텀 워커 저장

        Args:
            worker_name: 워커 이름 (파일명으로 사용)
            prompt_content: 시스템 프롬프트 내용
            allowed_tools: 허용 도구 리스트
            model: 사용 모델
            thinking: thinking 활성화 여부
            role: 워커 역할 설명 (없으면 worker_name 사용)

        Returns:
            저장된 프롬프트 파일 경로

        Raises:
            ValueError: 워커 이름이 유효하지 않은 경우
            OSError: 파일 쓰기 실패
        """
        # 워커 이름 검증
        if not worker_name or not worker_name.replace("_", "").isalnum():
            raise ValueError(f"유효하지 않은 워커 이름: {worker_name} (영문, 숫자, _ 만 가능)")

        self._ensure_directories()

        # 프롬프트 파일 저장
        prompt_path = self.worker_dir / f"{worker_name}.txt"
        try:
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(prompt_content)
            logger.info("Custom worker prompt saved", worker=worker_name, path=str(prompt_path))
        except OSError as e:
            logger.error("Failed to save prompt", worker=worker_name, error=str(e))
            raise

        # 설정 파일 업데이트
        self._update_config(
            worker_name=worker_name,
            allowed_tools=allowed_tools,
            model=model,
            thinking=thinking,
            role=role or worker_name
        )

        return prompt_path

    def _update_config(
        self,
        worker_name: str,
        allowed_tools: List[str],
        model: str,
        thinking: bool,
        role: str
    ):
        """
        worker-config.json 업데이트

        Args:
            worker_name: 워커 이름
            allowed_tools: 허용 도구
            model: 모델
            thinking: thinking 활성화
            role: 역할
        """
        # 기존 설정 로드
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Invalid worker-config.json, creating new", path=str(self.config_path))
                config_data = {"agents": []}
        else:
            config_data = {"agents": []}

        # 기존 워커 찾기
        agents = config_data.get("agents", [])
        existing_index = None
        for i, agent in enumerate(agents):
            if agent.get("name") == worker_name:
                existing_index = i
                break

        # 워커 설정 생성
        worker_config = {
            "name": worker_name,
            "role": role,
            "system_prompt_file": f".claude-flow/worker/{worker_name}.txt",
            "allowed_tools": allowed_tools,
            "model": model,
            "thinking": thinking
        }

        # 업데이트 또는 추가
        if existing_index is not None:
            agents[existing_index] = worker_config
            logger.info("Custom worker config updated", worker=worker_name)
        else:
            agents.append(worker_config)
            logger.info("Custom worker config added", worker=worker_name)

        config_data["agents"] = agents

        # 저장
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            logger.debug("worker-config.json saved", path=str(self.config_path))
        except OSError as e:
            logger.error("Failed to save worker-config.json", error=str(e))
            raise

    def load_custom_workers(self) -> List[AgentConfig]:
        """
        커스텀 워커 설정 로드

        Returns:
            AgentConfig 리스트 (없으면 빈 리스트)
        """
        if not self.config_path.exists():
            logger.debug("No worker-config.json found", path=str(self.config_path))
            return []

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            agents_data = config_data.get("agents", [])
            if not isinstance(agents_data, list):
                logger.warning("Invalid agents format in worker-config.json")
                return []

            # AgentConfig 객체 생성
            agent_configs = []
            for agent_data in agents_data:
                # 필수 필드 검증
                required_fields = ["name", "role", "system_prompt_file", "allowed_tools", "model"]
                if not all(field in agent_data for field in required_fields):
                    logger.warning("Skipping invalid worker config", agent=agent_data.get("name", "unknown"))
                    continue

                # system_prompt_file을 절대 경로로 변환
                prompt_file = agent_data["system_prompt_file"]
                if not prompt_file.startswith("/"):
                    # 상대 경로 → 절대 경로
                    prompt_file = str(self.project_path / prompt_file)

                agent_data_copy = agent_data.copy()
                agent_data_copy["system_prompt"] = prompt_file
                agent_data_copy.pop("system_prompt_file", None)

                try:
                    config = AgentConfig.from_dict(agent_data_copy)
                    agent_configs.append(config)
                except Exception as e:
                    logger.warning("Failed to parse worker config", worker=agent_data.get("name"), error=str(e))
                    continue

            logger.info("Custom workers loaded", count=len(agent_configs))
            return agent_configs

        except json.JSONDecodeError as e:
            logger.error("Failed to parse worker-config.json", error=str(e))
            return []
        except Exception as e:
            logger.error("Failed to load custom workers", error=str(e))
            return []

    def list_custom_workers(self) -> List[str]:
        """
        커스텀 워커 이름 목록 조회

        Returns:
            워커 이름 리스트
        """
        if not self.worker_dir.exists():
            return []

        worker_files = list(self.worker_dir.glob("*.txt"))
        worker_names = [f.stem for f in worker_files]

        logger.debug("Custom workers listed", count=len(worker_names), names=worker_names)
        return worker_names

    def delete_custom_worker(self, worker_name: str) -> bool:
        """
        커스텀 워커 삭제

        Args:
            worker_name: 삭제할 워커 이름

        Returns:
            삭제 성공 여부
        """
        # 프롬프트 파일 삭제
        prompt_path = self.worker_dir / f"{worker_name}.txt"
        if prompt_path.exists():
            try:
                prompt_path.unlink()
                logger.info("Custom worker prompt deleted", worker=worker_name)
            except OSError as e:
                logger.error("Failed to delete prompt", worker=worker_name, error=str(e))
                return False
        else:
            logger.warning("Prompt file not found", worker=worker_name)

        # 설정에서 제거
        if not self.config_path.exists():
            return True

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            agents = config_data.get("agents", [])
            updated_agents = [a for a in agents if a.get("name") != worker_name]

            config_data["agents"] = updated_agents

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            logger.info("Custom worker config deleted", worker=worker_name)
            return True

        except Exception as e:
            logger.error("Failed to delete worker config", worker=worker_name, error=str(e))
            return False
