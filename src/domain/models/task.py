"""
작업 도메인 모델

Task: 작업 요청
TaskResult: 작업 실행 결과
TaskStatus: 작업 상태 (Enum)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class TaskStatus(str, Enum):
    """작업 상태"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """
    작업 요청 도메인 모델

    Attributes:
        description: 작업 설명
        agent_name: 담당 에이전트 이름
        created_at: 생성 시각
        status: 작업 상태
    """
    description: str
    agent_name: str
    created_at: datetime = None
    status: TaskStatus = TaskStatus.PENDING

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class TaskResult:
    """
    작업 실행 결과 도메인 모델

    Attributes:
        task: 원본 작업
        status: 최종 상태
        output: 실행 출력
        error: 에러 메시지 (있을 경우)
        metadata: 추가 메타데이터
    """
    task: Task
    status: TaskStatus
    output: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
