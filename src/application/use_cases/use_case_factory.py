"""
Use Case Factory

의존성 주입을 관리하고 Use Case 인스턴스를 생성합니다.
Circuit Breaker, Retry Policy 등 탄력성 기능을 통합합니다.
"""

import json
import logging
from pathlib import Path
from typing import Callable, Dict, Optional

from .execute_planner_use_case import ExecutePlannerUseCase
from .execute_coder_use_case import ExecuteCoderUseCase
from .execute_reviewer_use_case import ExecuteReviewerUseCase
from .execute_tester_use_case import ExecuteTesterUseCase
from ..resilience import CircuitBreaker, ExponentialBackoffRetryPolicy
from src.domain.interfaces.use_cases import IExecuteWorkerUseCase
from src.domain.interfaces.circuit_breaker import ICircuitBreaker
from src.domain.interfaces.retry_policy import IRetryPolicy
from src.domain.models import AgentConfig
from src.domain.exceptions import WorkerNotFoundError
from ..ports.agent_port import IAgentClient
from src.infrastructure.config import JsonConfigLoader, get_project_root


logger = logging.getLogger(__name__)


class UseCaseFactory:
    """
    Use Case 팩토리

    의존성 주입을 관리하고 Use Case 인스턴스를 생성합니다.

    특징:
    - 설정 파일에서 Worker 설정 로드
    - Worker Client Factory를 통한 의존성 주입 (DIP 준수)
    - Use Case 인스턴스 생성 및 캐싱
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        worker_client_factory: Optional[Callable[[AgentConfig], IAgentClient]] = None
    ):
        """
        Use Case Factory

        Args:
            config_path: 설정 파일 경로 (기본: 프로젝트 루트)
            worker_client_factory: Worker Client 생성 팩토리 함수.
                                  AgentConfig를 받아 IAgentClient를 반환하는 Callable.
                                  필수 파라미터입니다.

        Raises:
            ValueError: worker_client_factory가 None인 경우
        """
        self.config_path = config_path or get_project_root()
        self.config_loader = JsonConfigLoader(self.config_path)

        # Worker Client Factory 저장 (필수)
        if worker_client_factory is None:
            raise ValueError(
                "worker_client_factory is required. "
                "Pass a factory function that creates IAgentClient instances."
            )
        self.worker_client_factory = worker_client_factory

        # System Config 로드
        self.system_config = self._load_system_config()

        # Worker 설정 로드
        self.worker_configs: Dict[str, AgentConfig] = {}
        self._load_worker_configs()

        # Worker Client 캐시
        self._worker_clients: Dict[str, IAgentClient] = {}

        # Use Case 캐시
        self._use_cases: Dict[str, IExecuteWorkerUseCase] = {}

        # Circuit Breaker 캐시 (Worker별)
        self._circuit_breakers: Dict[str, ICircuitBreaker] = {}
        self._initialize_circuit_breakers()

    def _load_system_config(self) -> Dict:
        """
        system_config.json 로드

        Returns:
            시스템 설정 딕셔너리
        """
        config_file_path = self.config_path / "config" / "system_config.json"
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.debug(f"✅ System Config 로드: {config_file_path}")
                return config
        except FileNotFoundError:
            logger.warning(
                f"⚠️ system_config.json을 찾을 수 없습니다: {config_file_path}. "
                f"기본 설정을 사용합니다."
            )
            return {}
        except Exception as e:
            logger.error(f"❌ System Config 로드 실패: {e}")
            return {}

    def _load_worker_configs(self) -> None:
        """Worker 설정 로드"""
        configs = self.config_loader.load_agent_configs()

        for config in configs:
            self.worker_configs[config.name] = config
            logger.debug(f"✅ Worker 설정 로드: {config.name}")

        logger.info(f"✅ {len(self.worker_configs)}개 Worker 설정 로드 완료")

    def _initialize_circuit_breakers(self) -> None:
        """Worker별 Circuit Breaker 생성"""
        cb_config = self.system_config.get("resilience", {}).get("circuit_breaker", {})

        if not cb_config.get("enable_per_worker", True):
            logger.info("Circuit Breaker가 비활성화되어 있습니다.")
            return

        for worker_name in self.worker_configs.keys():
            self._circuit_breakers[worker_name] = CircuitBreaker(
                name=worker_name,
                failure_threshold=cb_config.get("failure_threshold", 5),
                success_threshold=cb_config.get("success_threshold", 2),
                timeout_seconds=cb_config.get("timeout_seconds", 60),
            )
            logger.debug(f"✅ Circuit Breaker 생성: {worker_name}")

        logger.info(f"✅ {len(self._circuit_breakers)}개 Circuit Breaker 초기화 완료")

    def _create_retry_policy(self) -> IRetryPolicy:
        """
        Retry Policy 생성

        Returns:
            IRetryPolicy 인스턴스
        """
        perf_config = self.system_config.get("performance", {})

        if not perf_config.get("worker_retry_enabled", True):
            # Retry 비활성화 시 None 반환 (사용하지 않음)
            return None

        return ExponentialBackoffRetryPolicy(
            max_attempts=perf_config.get("worker_retry_max_attempts", 3),
            base_delay=perf_config.get("worker_retry_base_delay", 1.0),
            max_delay=perf_config.get("worker_retry_max_delay", 30.0),
            jitter=perf_config.get("worker_retry_jitter", 0.1),
        )

    def _get_worker_timeout(self, worker_name: str) -> Optional[float]:
        """
        Worker별 timeout 조회

        Args:
            worker_name: Worker 이름

        Returns:
            Timeout 시간 (초), None이면 기본값 사용
        """
        # Worker 설정에서 timeout 조회 (향후 확장 가능)
        worker_config = self.worker_configs.get(worker_name)
        if worker_config and hasattr(worker_config, "timeout"):
            return worker_config.timeout

        # System config에서 기본값 조회
        timeouts_config = self.system_config.get("timeouts", {})
        return timeouts_config.get("default_worker_timeout", 300)

    def _get_worker_client(self, worker_name: str) -> IAgentClient:
        """
        Worker Client 가져오기 (캐싱)

        Args:
            worker_name: Worker 이름 (예: "planner", "coder")

        Returns:
            IAgentClient 인스턴스

        Raises:
            WorkerNotFoundError: Worker 설정을 찾을 수 없음
        """
        # 캐시 확인
        if worker_name in self._worker_clients:
            return self._worker_clients[worker_name]

        # 설정 확인
        if worker_name not in self.worker_configs:
            raise WorkerNotFoundError(worker_name=worker_name)

        # 주입받은 Factory로 Worker Client 생성
        config = self.worker_configs[worker_name]
        client = self.worker_client_factory(config)

        # 캐시에 저장
        self._worker_clients[worker_name] = client
        logger.debug(f"✅ Worker Client 생성: {worker_name}")

        return client

    def create_planner_use_case(
        self,
        min_description_length: int = 10
    ) -> ExecutePlannerUseCase:
        """
        Planner Use Case 생성 (Circuit Breaker, Retry Policy 주입)

        Args:
            min_description_length: 최소 작업 설명 길이

        Returns:
            ExecutePlannerUseCase 인스턴스
        """
        cache_key = f"planner_{min_description_length}"

        if cache_key not in self._use_cases:
            client = self._get_worker_client("planner")
            circuit_breaker = self._circuit_breakers.get("planner")
            retry_policy = self._create_retry_policy()
            timeout = self._get_worker_timeout("planner")

            use_case = ExecutePlannerUseCase(
                planner_client=client,
                min_description_length=min_description_length
            )
            # BaseWorkerUseCase 속성 주입
            use_case.circuit_breaker = circuit_breaker
            use_case.retry_policy = retry_policy
            use_case.timeout = timeout

            self._use_cases[cache_key] = use_case
            logger.debug(
                f"✅ Planner Use Case 생성 "
                f"(CB: {circuit_breaker is not None}, "
                f"Retry: {retry_policy is not None}, "
                f"Timeout: {timeout}s)"
            )

        return self._use_cases[cache_key]

    def create_coder_use_case(
        self,
        require_plan: bool = False
    ) -> ExecuteCoderUseCase:
        """
        Coder Use Case 생성 (Circuit Breaker, Retry Policy 주입)

        Args:
            require_plan: 계획 포함 여부 강제

        Returns:
            ExecuteCoderUseCase 인스턴스
        """
        cache_key = f"coder_{require_plan}"

        if cache_key not in self._use_cases:
            client = self._get_worker_client("coder")
            circuit_breaker = self._circuit_breakers.get("coder")
            retry_policy = self._create_retry_policy()
            timeout = self._get_worker_timeout("coder")

            use_case = ExecuteCoderUseCase(
                coder_client=client,
                require_plan=require_plan
            )
            # BaseWorkerUseCase 속성 주입
            use_case.circuit_breaker = circuit_breaker
            use_case.retry_policy = retry_policy
            use_case.timeout = timeout

            self._use_cases[cache_key] = use_case
            logger.debug(
                f"✅ Coder Use Case 생성 "
                f"(CB: {circuit_breaker is not None}, "
                f"Retry: {retry_policy is not None}, "
                f"Timeout: {timeout}s)"
            )

        return self._use_cases[cache_key]

    def create_reviewer_use_case(
        self,
        require_code_reference: bool = False
    ) -> ExecuteReviewerUseCase:
        """
        Reviewer Use Case 생성 (Circuit Breaker, Retry Policy 주입)

        Args:
            require_code_reference: 코드 참조 필수 여부

        Returns:
            ExecuteReviewerUseCase 인스턴스
        """
        cache_key = f"reviewer_{require_code_reference}"

        if cache_key not in self._use_cases:
            client = self._get_worker_client("reviewer")
            circuit_breaker = self._circuit_breakers.get("reviewer")
            retry_policy = self._create_retry_policy()
            timeout = self._get_worker_timeout("reviewer")

            use_case = ExecuteReviewerUseCase(
                reviewer_client=client,
                require_code_reference=require_code_reference
            )
            # BaseWorkerUseCase 속성 주입
            use_case.circuit_breaker = circuit_breaker
            use_case.retry_policy = retry_policy
            use_case.timeout = timeout

            self._use_cases[cache_key] = use_case
            logger.debug(
                f"✅ Reviewer Use Case 생성 "
                f"(CB: {circuit_breaker is not None}, "
                f"Retry: {retry_policy is not None}, "
                f"Timeout: {timeout}s)"
            )

        return self._use_cases[cache_key]

    def create_tester_use_case(
        self,
        require_test_target: bool = False
    ) -> ExecuteTesterUseCase:
        """
        Tester Use Case 생성 (Circuit Breaker, Retry Policy 주입)

        Args:
            require_test_target: 테스트 대상 필수 여부

        Returns:
            ExecuteTesterUseCase 인스턴스
        """
        cache_key = f"tester_{require_test_target}"

        if cache_key not in self._use_cases:
            client = self._get_worker_client("tester")
            circuit_breaker = self._circuit_breakers.get("tester")
            retry_policy = self._create_retry_policy()
            timeout = self._get_worker_timeout("tester")

            use_case = ExecuteTesterUseCase(
                tester_client=client,
                require_test_target=require_test_target
            )
            # BaseWorkerUseCase 속성 주입
            use_case.circuit_breaker = circuit_breaker
            use_case.retry_policy = retry_policy
            use_case.timeout = timeout

            self._use_cases[cache_key] = use_case
            logger.debug(
                f"✅ Tester Use Case 생성 "
                f"(CB: {circuit_breaker is not None}, "
                f"Retry: {retry_policy is not None}, "
                f"Timeout: {timeout}s)"
            )

        return self._use_cases[cache_key]

    def get_use_case_by_worker_name(
        self,
        worker_name: str
    ) -> IExecuteWorkerUseCase:
        """
        Worker 이름으로 Use Case 가져오기

        Args:
            worker_name: Worker 이름 (예: "planner", "coder")

        Returns:
            해당 Worker의 Use Case

        Raises:
            ValueError: 지원하지 않는 Worker 이름
        """
        if worker_name == "planner":
            return self.create_planner_use_case()
        elif worker_name == "coder":
            return self.create_coder_use_case()
        elif worker_name == "reviewer":
            return self.create_reviewer_use_case()
        elif worker_name == "tester":
            return self.create_tester_use_case()
        else:
            raise ValueError(f"지원하지 않는 Worker: {worker_name}")

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._worker_clients.clear()
        self._use_cases.clear()
        logger.info("✅ Use Case Factory 캐시 초기화")
