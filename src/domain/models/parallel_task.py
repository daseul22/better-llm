"""
병렬 실행 가능한 Task 도메인 모델

ParallelTask: 의존성 정보를 포함한 Task
TaskExecutionPlan: Planner가 생성하는 실행 계획
TaskExecutionResult: 병렬 실행 결과
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from .task import TaskStatus  # 기존 TaskStatus 재사용


@dataclass
class ParallelTask:
    """
    병렬 실행 가능한 Task

    Attributes:
        id: Task 고유 식별자 (예: "task_1", "task_2")
        description: 작업 설명
        target_files: 생성/수정할 파일 경로 리스트
        dependencies: 의존하는 task_id 리스트 (이 Task들이 완료되어야 실행 가능)
        status: 작업 상태
        result: 실행 결과 (Coder Agent 출력)
        error: 에러 메시지 (실패 시)
        start_time: 시작 시각
        end_time: 종료 시각
        estimated_time: 예상 실행 시간 (초)
        priority: 우선순위 (낮을수록 먼저 실행)
    """
    id: str
    description: str
    target_files: List[str]
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    estimated_time: int = 300  # 기본 5분
    priority: int = 1

    def duration_seconds(self) -> Optional[float]:
        """
        실행 시간 계산 (초)

        Returns:
            실행 시간 (초), start_time 또는 end_time이 없으면 None
        """
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def is_ready(self, completed_task_ids: set[str]) -> bool:
        """
        실행 가능 여부 확인 (모든 의존성이 완료되었는지)

        Args:
            completed_task_ids: 완료된 Task ID 집합

        Returns:
            실행 가능 여부. 모든 의존성이 완료되었으면 True
        """
        return all(dep_id in completed_task_ids for dep_id in self.dependencies)


@dataclass
class TaskExecutionPlan:
    """
    Task 실행 계획 (Planner Agent가 생성)

    Attributes:
        tasks: ParallelTask 리스트
        integration_notes: 통합 시 주의사항 (Reviewer에게 전달)
        metadata: 추가 메타데이터 (예: 예상 총 시간, 생성 시각 등)
    """
    tasks: List[ParallelTask]
    integration_notes: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_task(self, task_id: str) -> Optional[ParallelTask]:
        """
        Task ID로 Task 조회

        Args:
            task_id: 조회할 Task ID

        Returns:
            해당 Task 객체, 없으면 None
        """
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def build_dependency_graph(self) -> Dict[str, List[str]]:
        """
        의존성 그래프 구축

        Returns:
            {task_id: [dependent_task_ids]}
            예: {"task_1": ["task_2", "task_3"]}  # task_1 완료 후 task_2, task_3 실행 가능

        Raises:
            ValueError: 존재하지 않는 Task ID를 의존성으로 지정한 경우
        """
        graph: Dict[str, List[str]] = {task.id: [] for task in self.tasks}
        task_ids = set(graph.keys())

        for task in self.tasks:
            for dep_id in task.dependencies:
                # 존재하지 않는 의존성 검증
                if dep_id not in task_ids:
                    raise ValueError(
                        f"Task '{task.id}'의 의존성 '{dep_id}'가 "
                        f"존재하지 않습니다."
                    )
                graph[dep_id].append(task.id)

        return graph

    def estimate_total_time(self) -> int:
        """
        순차 실행 시 예상 총 시간 (초)

        Returns:
            모든 Task의 estimated_time 합
        """
        return sum(task.estimated_time for task in self.tasks)


@dataclass
class TaskExecutionResult:
    """
    병렬 실행 결과

    Attributes:
        plan: 원본 실행 계획
        completed_tasks: 완료된 Task 리스트
        failed_tasks: 실패한 Task 리스트
        total_duration: 총 실행 시간 (초)
        speedup_factor: 속도 향상 배율 (순차 실행 대비)
    """
    plan: TaskExecutionPlan
    completed_tasks: List[ParallelTask]
    failed_tasks: List[ParallelTask]
    total_duration: float
    speedup_factor: float

    @property
    def success_rate(self) -> float:
        """
        성공률 계산 (0.0 ~ 1.0)

        Returns:
            성공한 Task 비율
        """
        total = len(self.completed_tasks) + len(self.failed_tasks)
        if total == 0:
            return 0.0
        return len(self.completed_tasks) / total

    @property
    def all_succeeded(self) -> bool:
        """
        모든 Task가 성공했는지 확인

        Returns:
            실패한 Task가 없으면 True
        """
        return len(self.failed_tasks) == 0
