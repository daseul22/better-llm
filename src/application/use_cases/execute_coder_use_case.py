"""
Coder Use Case 구현

코드 작성 및 수정 작업을 실행하는 Use Case입니다.
"""

import logging
from typing import Optional

from .base_worker_use_case import BaseWorkerUseCase
from ...domain.models import Task, TaskResult
from ...domain.exceptions import PreconditionFailedError
from ..ports import IAgentClient


logger = logging.getLogger(__name__)


class ExecuteCoderUseCase(BaseWorkerUseCase):
    """
    Coder Worker 실행 Use Case

    코드 작성, 수정, 리팩토링 작업을 수행합니다.

    특징:
    - 코드 작성을 위한 충분한 정보가 있는지 검증
    - 실행 결과를 구조화하여 반환
    - 작성된 파일 목록 추출 (선택)
    """

    def __init__(
        self,
        coder_client: IAgentClient,
        require_plan: bool = False
    ):
        """
        Args:
            coder_client: Coder Worker 클라이언트
            require_plan: 계획 포함 여부를 강제할지 여부
        """
        super().__init__(
            worker_name="coder",
            worker_client=coder_client
        )
        self.require_plan = require_plan

    def _check_preconditions(self, task: Task) -> None:
        """
        Coder 실행 사전 조건 체크

        Args:
            task: 체크할 작업

        Raises:
            PreconditionFailedError: 사전 조건 실패
        """
        # 1. 계획이 필요한 경우 계획이 포함되어 있는지 확인
        if self.require_plan:
            description_lower = task.description.lower()
            has_plan_keywords = any(
                keyword in description_lower
                for keyword in ["계획", "plan", "단계", "step"]
            )

            if not has_plan_keywords:
                raise PreconditionFailedError(
                    "코드 작성 전 계획이 필요합니다. "
                    "Planner를 먼저 실행하거나 작업 설명에 계획을 포함해주세요."
                )

        logger.debug(f"[{self.worker_name}] ✅ 사전 조건 체크 완료")

    def _process_result(self, task: Task, output: str) -> TaskResult:
        """
        Coder 결과 후처리

        Args:
            task: 원본 작업
            output: Coder 실행 결과

        Returns:
            후처리된 TaskResult
        """
        # 기본 처리 수행
        result = super()._process_result(task, output)

        # 메타데이터 추가
        result.metadata = {
            "worker_type": "coder",
            "output_length": len(output),
            # 간단한 휴리스틱: 파일 작성/수정 여부 체크
            "has_file_operations": any(
                keyword in output.lower()
                for keyword in ["created", "modified", "edited", "작성", "수정"]
            )
        }

        return result
