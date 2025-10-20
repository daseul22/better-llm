"""
Planner Use Case 구현

계획 수립 작업을 실행하는 Use Case입니다.
"""

import logging
from typing import Optional

from .base_worker_use_case import BaseWorkerUseCase
from domain.models import Task, TaskResult
from domain.exceptions import PreconditionFailedError
from ..ports import IAgentClient
from ..validation import UseCaseValidator


logger = logging.getLogger(__name__)


class ExecutePlannerUseCase(BaseWorkerUseCase):
    """
    Planner Worker 실행 Use Case

    요구사항 분석 및 계획 수립 작업을 수행합니다.

    특징:
    - 계획 수립을 위한 충분한 정보가 있는지 검증
    - 실행 결과를 구조화하여 반환
    """

    def __init__(
        self,
        planner_client: IAgentClient,
        min_description_length: int = 10
    ):
        """
        Args:
            planner_client: Planner Worker 클라이언트
            min_description_length: 최소 작업 설명 길이
        """
        super().__init__(
            worker_name="planner",
            worker_client=planner_client
        )
        self.min_description_length = min_description_length

    def _check_preconditions(self, task: Task) -> None:
        """
        Planner 실행 사전 조건 체크

        Args:
            task: 체크할 작업

        Raises:
            PreconditionFailedError: 사전 조건 실패
        """
        # 1. 작업 설명이 충분히 구체적인지 확인
        UseCaseValidator.validate_min_length(
            text=task.description,
            min_length=self.min_description_length,
            field_name="작업 설명"
        )

        logger.debug(f"[{self.worker_name}] ✅ 사전 조건 체크 완료")

    def _process_result(self, task: Task, output: str) -> TaskResult:
        """
        Planner 결과 후처리

        Args:
            task: 원본 작업
            output: Planner 실행 결과

        Returns:
            후처리된 TaskResult
        """
        # 기본 처리 수행
        result = super()._process_result(task, output)

        # 메타데이터 추가
        result.metadata = {
            "worker_type": "planner",
            "output_length": len(output),
            "has_plan": "## " in output or "1." in output  # 계획이 포함되어 있는지 휴리스틱 체크
        }

        return result
