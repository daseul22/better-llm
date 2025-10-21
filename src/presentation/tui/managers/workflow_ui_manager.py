"""
WorkflowUIManager 모듈

워크플로우 UI 관리 책임:
- 워크플로우 상태 시각화
- 단계 상태 업데이트
- 워크플로우 진행률 계산
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from src.infrastructure.logging import get_logger

logger = get_logger(__name__, component="WorkflowUIManager")


class StepStatus(str, Enum):
    """워크플로우 단계 상태"""
    PENDING = "pending"       # 대기 중
    RUNNING = "running"       # 실행 중
    COMPLETED = "completed"   # 완료
    FAILED = "failed"         # 실패
    SKIPPED = "skipped"       # 스킵


@dataclass
class WorkflowStep:
    """
    워크플로우 단계

    Attributes:
        step_id: 단계 ID
        name: 단계 이름
        status: 단계 상태
        start_time: 시작 시간 (옵셔널)
        end_time: 종료 시간 (옵셔널)
        error_message: 에러 메시지 (옵셔널)
    """
    step_id: str
    name: str
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None

    def __str__(self) -> str:
        return f"WorkflowStep({self.step_id}: {self.name} [{self.status.value}])"


@dataclass
class WorkflowState:
    """
    워크플로우 상태

    Attributes:
        workflow_id: 워크플로우 ID
        name: 워크플로우 이름
        steps: 워크플로우 단계 리스트
        current_step_index: 현재 단계 인덱스
    """
    workflow_id: str
    name: str
    steps: List[WorkflowStep]
    current_step_index: int = 0

    def __str__(self) -> str:
        return f"WorkflowState({self.workflow_id}: {self.name}, {len(self.steps)} steps)"


class WorkflowUIManager:
    """
    워크플로우 UI 관리자

    워크플로우 상태를 시각화하고 진행 상황을 추적합니다.

    Example:
        >>> manager = WorkflowUIManager()
        >>> steps = [
        ...     WorkflowStep("1", "Plan", StepStatus.COMPLETED),
        ...     WorkflowStep("2", "Code", StepStatus.RUNNING),
        ...     WorkflowStep("3", "Test", StepStatus.PENDING)
        ... ]
        >>> workflow = WorkflowState("wf-001", "Development", steps)
        >>> viz = manager.visualize_workflow(workflow)
        >>> progress = manager.get_workflow_progress()
    """

    def __init__(self) -> None:
        """WorkflowUIManager 초기화"""
        self._current_workflow: Optional[WorkflowState] = None
        self._workflow_history: List[WorkflowState] = []
        self._step_styles: Dict[StepStatus, str] = {
            StepStatus.PENDING: "⏳",
            StepStatus.RUNNING: "▶️",
            StepStatus.COMPLETED: "✅",
            StepStatus.FAILED: "❌",
            StepStatus.SKIPPED: "⏭️",
        }
        logger.info("WorkflowUIManager initialized")

    def visualize_workflow(self, workflow: WorkflowState) -> str:
        """
        워크플로우 상태를 시각화합니다.

        Args:
            workflow: 워크플로우 상태

        Returns:
            시각화된 워크플로우 문자열

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [
            ...     WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            ...     WorkflowStep("2", "Code", StepStatus.RUNNING)
            ... ]
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> viz = manager.visualize_workflow(workflow)
            >>> print(len(viz) > 0)
            True
        """
        self._current_workflow = workflow

        lines = [f"=== Workflow: {workflow.name} ===", ""]

        if not workflow.steps:
            lines.append("No steps in workflow")
        else:
            for i, step in enumerate(workflow.steps):
                # 상태 아이콘
                icon = self._step_styles.get(step.status, "⚫")

                # 현재 단계 표시
                is_current = (i == workflow.current_step_index)
                prefix = "→ " if is_current else "  "

                # 단계 정보
                step_line = f"{prefix}{icon} {step.name}"

                # 에러 메시지 추가
                if step.error_message:
                    step_line += f" (Error: {step.error_message})"

                lines.append(step_line)

            # 진행률 표시
            progress = self._calculate_progress(workflow)
            lines.append("")
            lines.append(f"Progress: {progress:.1%}")

        result = "\n".join(lines)

        logger.debug(f"Workflow visualized: {workflow.workflow_id}")

        return result

    def _calculate_progress(self, workflow: WorkflowState) -> float:
        """
        워크플로우 진행률을 계산합니다.

        Args:
            workflow: 워크플로우 상태

        Returns:
            진행률 (0.0 ~ 1.0)
        """
        if not workflow.steps:
            return 0.0

        completed_count = sum(
            1 for step in workflow.steps
            if step.status == StepStatus.COMPLETED
        )

        return completed_count / len(workflow.steps)

    def update_step_status(
        self,
        step_id: str,
        status: StepStatus,
        error_message: Optional[str] = None
    ) -> None:
        """
        단계 상태를 업데이트합니다.

        Args:
            step_id: 단계 ID
            status: 새로운 상태
            error_message: 에러 메시지 (옵셔널)

        Raises:
            ValueError: 현재 워크플로우가 없거나 단계를 찾을 수 없는 경우

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [WorkflowStep("1", "Plan", StepStatus.PENDING)]
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> manager.visualize_workflow(workflow)
            >>> manager.update_step_status("1", StepStatus.RUNNING)
        """
        if not self._current_workflow:
            logger.error("No current workflow")
            raise ValueError("No current workflow set")

        # 단계 찾기
        step = None
        for s in self._current_workflow.steps:
            if s.step_id == step_id:
                step = s
                break

        if not step:
            logger.error(f"Step not found: {step_id}")
            raise ValueError(f"Step '{step_id}' not found in current workflow")

        # 상태 업데이트
        old_status = step.status
        step.status = status

        # 시간 기록
        if status == StepStatus.RUNNING and not step.start_time:
            step.start_time = datetime.now()
        elif status in [StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED]:
            if not step.end_time:
                step.end_time = datetime.now()

        # 에러 메시지 설정
        if error_message:
            step.error_message = error_message

        logger.info(
            f"Step status updated: {step_id} ({old_status.value} -> {status.value})"
        )

    def get_workflow_progress(self) -> float:
        """
        현재 워크플로우의 진행률을 반환합니다.

        Returns:
            진행률 (0.0 ~ 1.0)

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [
            ...     WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            ...     WorkflowStep("2", "Code", StepStatus.RUNNING),
            ...     WorkflowStep("3", "Test", StepStatus.PENDING)
            ... ]
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> manager.visualize_workflow(workflow)
            >>> progress = manager.get_workflow_progress()
            >>> print(0.0 <= progress <= 1.0)
            True
        """
        if not self._current_workflow:
            return 0.0

        return self._calculate_progress(self._current_workflow)

    def get_current_step(self) -> Optional[WorkflowStep]:
        """
        현재 실행 중인 단계를 반환합니다.

        Returns:
            현재 단계 (없으면 None)

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [WorkflowStep("1", "Plan", StepStatus.RUNNING)]
            >>> workflow = WorkflowState("wf-001", "Dev", steps, current_step_index=0)
            >>> manager.visualize_workflow(workflow)
            >>> current = manager.get_current_step()
            >>> print(current.name)
            Plan
        """
        if not self._current_workflow:
            return None

        if 0 <= self._current_workflow.current_step_index < len(self._current_workflow.steps):
            return self._current_workflow.steps[self._current_workflow.current_step_index]

        return None

    def advance_to_next_step(self) -> bool:
        """
        다음 단계로 진행합니다.

        Returns:
            성공 여부 (다음 단계가 없으면 False)

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [
            ...     WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            ...     WorkflowStep("2", "Code", StepStatus.PENDING)
            ... ]
            >>> workflow = WorkflowState("wf-001", "Dev", steps, current_step_index=0)
            >>> manager.visualize_workflow(workflow)
            >>> success = manager.advance_to_next_step()
            >>> print(success)
            True
        """
        if not self._current_workflow:
            logger.warning("No current workflow")
            return False

        next_index = self._current_workflow.current_step_index + 1

        if next_index >= len(self._current_workflow.steps):
            logger.warning("Already at last step")
            return False

        self._current_workflow.current_step_index = next_index
        logger.info(f"Advanced to step {next_index}")

        return True

    def reset_workflow(self) -> None:
        """
        현재 워크플로우를 초기 상태로 리셋합니다.

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [WorkflowStep("1", "Plan", StepStatus.COMPLETED)]
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> manager.visualize_workflow(workflow)
            >>> manager.reset_workflow()
            >>> current = manager.get_current_workflow()
            >>> print(current)
            None
        """
        if self._current_workflow:
            self._workflow_history.append(self._current_workflow)

        self._current_workflow = None
        logger.info("Workflow reset")

    def get_current_workflow(self) -> Optional[WorkflowState]:
        """
        현재 워크플로우를 반환합니다.

        Returns:
            현재 워크플로우 (없으면 None)

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [WorkflowStep("1", "Plan", StepStatus.PENDING)]
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> manager.visualize_workflow(workflow)
            >>> current = manager.get_current_workflow()
            >>> print(current.workflow_id)
            wf-001
        """
        return self._current_workflow

    def get_step_by_id(self, step_id: str) -> Optional[WorkflowStep]:
        """
        단계 ID로 단계를 조회합니다.

        Args:
            step_id: 단계 ID

        Returns:
            워크플로우 단계 (없으면 None)

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [WorkflowStep("1", "Plan", StepStatus.PENDING)]
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> manager.visualize_workflow(workflow)
            >>> step = manager.get_step_by_id("1")
            >>> print(step.name)
            Plan
        """
        if not self._current_workflow:
            return None

        for step in self._current_workflow.steps:
            if step.step_id == step_id:
                return step

        return None

    def get_completed_steps(self) -> List[WorkflowStep]:
        """
        완료된 단계 목록을 반환합니다.

        Returns:
            완료된 단계 리스트

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [
            ...     WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            ...     WorkflowStep("2", "Code", StepStatus.RUNNING)
            ... ]
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> manager.visualize_workflow(workflow)
            >>> completed = manager.get_completed_steps()
            >>> print(len(completed))
            1
        """
        if not self._current_workflow:
            return []

        return [
            step for step in self._current_workflow.steps
            if step.status == StepStatus.COMPLETED
        ]

    def get_failed_steps(self) -> List[WorkflowStep]:
        """
        실패한 단계 목록을 반환합니다.

        Returns:
            실패한 단계 리스트

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [
            ...     WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            ...     WorkflowStep("2", "Code", StepStatus.FAILED)
            ... ]
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> manager.visualize_workflow(workflow)
            >>> failed = manager.get_failed_steps()
            >>> print(len(failed))
            1
        """
        if not self._current_workflow:
            return []

        return [
            step for step in self._current_workflow.steps
            if step.status == StepStatus.FAILED
        ]

    def is_workflow_complete(self) -> bool:
        """
        워크플로우가 완료되었는지 확인합니다.

        Returns:
            완료 여부

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [WorkflowStep("1", "Plan", StepStatus.COMPLETED)]
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> manager.visualize_workflow(workflow)
            >>> print(manager.is_workflow_complete())
            True
        """
        if not self._current_workflow:
            return False

        return all(
            step.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]
            for step in self._current_workflow.steps
        )

    def has_failed_steps(self) -> bool:
        """
        실패한 단계가 있는지 확인합니다.

        Returns:
            실패한 단계 존재 여부

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [WorkflowStep("1", "Plan", StepStatus.FAILED)]
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> manager.visualize_workflow(workflow)
            >>> print(manager.has_failed_steps())
            True
        """
        if not self._current_workflow:
            return False

        return any(
            step.status == StepStatus.FAILED
            for step in self._current_workflow.steps
        )

    def get_workflow_summary(self) -> Dict[str, int]:
        """
        워크플로우의 단계별 개수 요약을 반환합니다.

        Returns:
            단계 상태별 개수 딕셔너리

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [
            ...     WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            ...     WorkflowStep("2", "Code", StepStatus.RUNNING),
            ...     WorkflowStep("3", "Test", StepStatus.PENDING)
            ... ]
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> manager.visualize_workflow(workflow)
            >>> summary = manager.get_workflow_summary()
            >>> print(summary["completed"])
            1
        """
        if not self._current_workflow:
            return {}

        summary = {
            "total": len(self._current_workflow.steps),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
        }

        for step in self._current_workflow.steps:
            status_key = step.status.value
            if status_key in summary:
                summary[status_key] += 1

        return summary

    def set_step_icon(self, status: StepStatus, icon: str) -> None:
        """
        특정 상태의 아이콘을 설정합니다.

        Args:
            status: 단계 상태
            icon: 아이콘 문자열

        Example:
            >>> manager = WorkflowUIManager()
            >>> manager.set_step_icon(StepStatus.COMPLETED, "✔️")
        """
        self._step_styles[status] = icon
        logger.debug(f"Step icon set: {status.value} -> {icon}")

    def get_workflow_duration(self) -> Optional[float]:
        """
        워크플로우의 전체 실행 시간을 초 단위로 반환합니다.

        Returns:
            실행 시간 (초) 또는 None

        Example:
            >>> manager = WorkflowUIManager()
            >>> steps = [WorkflowStep("1", "Plan", StepStatus.COMPLETED)]
            >>> steps[0].start_time = datetime(2025, 1, 1, 12, 0, 0)
            >>> steps[0].end_time = datetime(2025, 1, 1, 12, 0, 10)
            >>> workflow = WorkflowState("wf-001", "Dev", steps)
            >>> manager.visualize_workflow(workflow)
            >>> duration = manager.get_workflow_duration()
            >>> print(duration)
            10.0
        """
        if not self._current_workflow:
            return None

        start_times = [
            step.start_time for step in self._current_workflow.steps
            if step.start_time
        ]
        end_times = [
            step.end_time for step in self._current_workflow.steps
            if step.end_time
        ]

        if not start_times or not end_times:
            return None

        earliest_start = min(start_times)
        latest_end = max(end_times)

        duration = (latest_end - earliest_start).total_seconds()
        return duration

    def get_step_duration(self, step_id: str) -> Optional[float]:
        """
        특정 단계의 실행 시간을 초 단위로 반환합니다.

        Args:
            step_id: 단계 ID

        Returns:
            실행 시간 (초) 또는 None

        Example:
            >>> manager = WorkflowUIManager()
            >>> step = WorkflowStep("1", "Plan", StepStatus.COMPLETED)
            >>> step.start_time = datetime(2025, 1, 1, 12, 0, 0)
            >>> step.end_time = datetime(2025, 1, 1, 12, 0, 5)
            >>> workflow = WorkflowState("wf-001", "Dev", [step])
            >>> manager.visualize_workflow(workflow)
            >>> duration = manager.get_step_duration("1")
            >>> print(duration)
            5.0
        """
        step = self.get_step_by_id(step_id)

        if not step or not step.start_time or not step.end_time:
            return None

        duration = (step.end_time - step.start_time).total_seconds()
        return duration
