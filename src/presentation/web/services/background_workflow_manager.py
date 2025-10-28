"""
백그라운드 워크플로우 실행 관리자

워크플로우를 백그라운드 Task로 실행하고, SSE 연결이 끊어져도 계속 실행되도록 합니다.
새로고침 후 재접속 시 진행 중인 워크플로우의 이벤트를 복구할 수 있습니다.
"""

import asyncio
from typing import Dict, Optional, AsyncIterator, Any
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime

from src.infrastructure.logging import get_logger
from src.presentation.web.schemas.workflow import (
    Workflow,
    WorkflowNodeExecutionEvent,
)
from src.presentation.web.services.workflow_executor import WorkflowExecutor
from src.presentation.web.services.workflow_session_store import (
    get_session_store,
    WorkflowSessionStore,
)

logger = get_logger(__name__)


@dataclass
class BackgroundWorkflowTask:
    """
    백그라운드 워크플로우 Task

    Attributes:
        session_id: 세션 ID
        task: asyncio Task 객체
        event_queue: 이벤트 큐 (무제한, 메모리 관리는 cleanup_completed_tasks로 처리)
        completed: 완료 여부
        error: 에러 메시지 (에러 발생 시)
    """
    session_id: str
    task: asyncio.Task
    event_queue: deque = field(default_factory=deque)
    completed: bool = False
    error: Optional[str] = None
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())


class BackgroundWorkflowManager:
    """
    백그라운드 워크플로우 실행 관리자 (싱글톤)

    워크플로우를 백그라운드 Task로 실행하고, 이벤트를 메모리 큐에 저장합니다.
    SSE 연결이 끊어져도 워크플로우는 계속 실행되며, 재접속 시 이벤트를 복구할 수 있습니다.

    Attributes:
        executor: WorkflowExecutor 인스턴스
        session_store: WorkflowSessionStore 인스턴스
        tasks: 세션 ID → BackgroundWorkflowTask 매핑
    """

    def __init__(
        self,
        executor: WorkflowExecutor,
        session_store: Optional[WorkflowSessionStore] = None,
    ):
        """
        BackgroundWorkflowManager 초기화

        Args:
            executor: WorkflowExecutor 인스턴스
            session_store: WorkflowSessionStore 인스턴스 (기본값: 싱글톤)
        """
        self.executor = executor
        self.session_store = session_store or get_session_store()
        self.tasks: Dict[str, BackgroundWorkflowTask] = {}

        logger.info("백그라운드 워크플로우 관리자 초기화")

    async def start_workflow(
        self,
        session_id: str,
        workflow: Workflow,
        initial_input: str,
        project_path: Optional[str] = None,
    ) -> None:
        """
        워크플로우를 백그라운드 Task로 시작

        Args:
            session_id: 세션 ID
            workflow: 실행할 워크플로우
            initial_input: 초기 입력
            project_path: 프로젝트 디렉토리 경로 (세션별 로그 저장용)

        Raises:
            ValueError: 이미 실행 중인 세션인 경우
        """
        # 이미 실행 중인 세션 확인
        if session_id in self.tasks:
            existing_task = self.tasks[session_id]
            if not existing_task.completed:
                raise ValueError(
                    f"세션 {session_id}는 이미 실행 중입니다"
                )

        logger.info(
            f"[{session_id}] 백그라운드 워크플로우 시작: {workflow.name}"
        )

        # 백그라운드 Task 생성 (project_path 전달)
        task = asyncio.create_task(
            self._run_workflow(session_id, workflow, initial_input, project_path)
        )

        # Task 등록
        self.tasks[session_id] = BackgroundWorkflowTask(
            session_id=session_id,
            task=task,
        )

    async def _run_workflow(
        self,
        session_id: str,
        workflow: Workflow,
        initial_input: str,
        project_path: Optional[str] = None,
    ) -> None:
        """
        워크플로우 실행 (백그라운드 Task 내부)

        Args:
            session_id: 세션 ID
            workflow: 실행할 워크플로우
            initial_input: 초기 입력
            project_path: 프로젝트 디렉토리 경로 (세션별 로그 저장용)
        """
        bg_task = self.tasks[session_id]

        try:
            logger.info(
                f"[{session_id}] 워크플로우 실행 시작 (백그라운드)"
            )

            # WorkflowExecutor 실행 (project_path 전달)
            async for event in self.executor.execute_workflow(
                workflow=workflow,
                initial_input=initial_input,
                session_id=session_id,
                project_path=project_path,
            ):
                # 이벤트를 큐에 저장
                bg_task.event_queue.append(event)

                # 세션 저장소에도 기록
                await self.session_store.append_log(session_id, event)

                logger.debug(
                    f"[{session_id}] 이벤트 큐에 추가: {event.event_type} "
                    f"(큐 크기: {len(bg_task.event_queue)})"
                )

            # 완료 처리
            bg_task.completed = True
            logger.info(
                f"[{session_id}] 워크플로우 실행 완료 (백그라운드)"
            )

        except Exception as e:
            error_msg = str(e)
            bg_task.error = error_msg

            logger.error(
                f"[{session_id}] 워크플로우 실행 실패 (백그라운드): {error_msg}",
                exc_info=True,
            )

            # 에러 이벤트를 큐에 추가 (SSE 클라이언트가 에러를 받을 수 있도록)
            error_event = WorkflowNodeExecutionEvent(
                event_type="workflow_error",
                node_id="",
                data={"error": error_msg},
                timestamp=datetime.now().isoformat(),
            )
            bg_task.event_queue.append(error_event)

            # 완료 처리
            bg_task.completed = True

            # 세션 상태 업데이트
            await self.session_store.update_session(
                session_id,
                status="error",
                error=error_msg,
                end_time=datetime.now().isoformat(),
            )

    async def stream_events(
        self,
        session_id: str,
        start_from_index: int = 0,
    ) -> AsyncIterator[WorkflowNodeExecutionEvent]:
        """
        세션의 이벤트 스트리밍 (세션 저장소 기반 + 실시간 폴링)

        새로고침 후 재접속 시에도 중복 없이 이벤트를 이어받을 수 있습니다.

        Args:
            session_id: 세션 ID
            start_from_index: 시작 이벤트 인덱스 (0부터 시작, 기본값 0)

        Yields:
            WorkflowNodeExecutionEvent: 노드 실행 이벤트

        Raises:
            ValueError: 세션을 찾을 수 없는 경우
        """
        # 세션 저장소에서 세션 가져오기
        session = await self.session_store.get_session(session_id)
        if not session:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")

        # 백그라운드 Task 확인 (실시간 폴링 여부 결정)
        bg_task = self.tasks.get(session_id)
        is_task_running = bg_task is not None and not bg_task.completed

        logger.info(
            f"[{session_id}] 이벤트 스트리밍 시작 "
            f"(start_from_index={start_from_index}, "
            f"저장된 로그={len(session.logs)}, "
            f"실시간 폴링={is_task_running})"
        )

        # 1. 세션 저장소에서 기존 이벤트 전송 (start_from_index 이후)
        existing_logs = session.logs[start_from_index:]
        for log_entry in existing_logs:
            # Dict → WorkflowNodeExecutionEvent 변환
            event = WorkflowNodeExecutionEvent(**log_entry)
            yield event

        sent_count = start_from_index + len(existing_logs)
        logger.info(
            f"[{session_id}] 기존 이벤트 전송 완료: {len(existing_logs)}개 "
            f"(총 누적: {sent_count}개)"
        )

        # 2. 실시간 이벤트 스트리밍 (백그라운드 Task가 실행 중인 경우)
        if is_task_running:
            logger.info(f"[{session_id}] 실시간 폴링 시작")

            while not bg_task.completed:
                # 세션 저장소 다시 로드 (새 이벤트 확인)
                session = await self.session_store.get_session(session_id)
                if not session:
                    logger.warning(f"[{session_id}] 세션이 삭제되었습니다. 스트리밍 중단")
                    break

                current_log_count = len(session.logs)

                # 새 이벤트가 있으면 전송
                if current_log_count > sent_count:
                    new_logs = session.logs[sent_count:]
                    for log_entry in new_logs:
                        event = WorkflowNodeExecutionEvent(**log_entry)
                        yield event
                        sent_count += 1

                # 짧은 대기 (CPU 사용률 최소화)
                await asyncio.sleep(0.1)

            # 3. 완료 후 남은 이벤트 전송 (race condition 방지)
            session = await self.session_store.get_session(session_id)
            if session:
                final_logs = session.logs[sent_count:]
                for log_entry in final_logs:
                    event = WorkflowNodeExecutionEvent(**log_entry)
                    yield event

                logger.info(
                    f"[{session_id}] 실시간 폴링 완료 "
                    f"(총 {len(session.logs)}개 이벤트)"
                )
        else:
            logger.info(
                f"[{session_id}] 백그라운드 Task 없음. 저장된 이벤트만 전송 완료 "
                f"(상태: {session.status})"
            )

    def get_task_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Task 상태 조회

        Args:
            session_id: 세션 ID

        Returns:
            Dict[str, any]: Task 상태 (None이면 세션을 찾을 수 없음)
                - session_id: 세션 ID
                - completed: 완료 여부
                - error: 에러 메시지 (에러 발생 시)
                - event_count: 이벤트 개수
                - start_time: 시작 시각
        """
        if session_id not in self.tasks:
            return None

        bg_task = self.tasks[session_id]
        return {
            "session_id": session_id,
            "completed": bg_task.completed,
            "error": bg_task.error,
            "event_count": len(bg_task.event_queue),
            "start_time": bg_task.start_time,
        }

    async def cancel_workflow(self, session_id: str) -> None:
        """
        워크플로우 취소

        Args:
            session_id: 세션 ID

        Raises:
            ValueError: 세션을 찾을 수 없는 경우
        """
        if session_id not in self.tasks:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")

        bg_task = self.tasks[session_id]

        # Task 취소
        bg_task.task.cancel()

        try:
            await bg_task.task
        except asyncio.CancelledError:
            logger.info(f"[{session_id}] 워크플로우 취소 완료")

        # 완료 처리
        bg_task.completed = True

        # 세션 상태 업데이트
        await self.session_store.update_session(
            session_id,
            status="cancelled",
            end_time=datetime.now().isoformat(),
        )

    async def cleanup_completed_tasks(self, max_age_seconds: int = 3600) -> int:
        """
        완료된 Task 정리 (메모리 절약)

        Args:
            max_age_seconds: 최대 보존 시간 (초)

        Returns:
            int: 정리된 Task 개수
        """
        now = datetime.now()
        removed_count = 0

        session_ids_to_remove = []
        for session_id, bg_task in self.tasks.items():
            if not bg_task.completed:
                continue

            # 시작 시간 파싱
            start_time = datetime.fromisoformat(bg_task.start_time)
            age_seconds = (now - start_time).total_seconds()

            if age_seconds > max_age_seconds:
                session_ids_to_remove.append(session_id)

        # Task 제거
        for session_id in session_ids_to_remove:
            del self.tasks[session_id]
            removed_count += 1
            logger.info(f"[{session_id}] 완료된 Task 정리 (메모리 절약)")

        return removed_count


# 싱글톤 인스턴스
_manager: Optional[BackgroundWorkflowManager] = None


def get_background_workflow_manager(
    executor: Optional[WorkflowExecutor] = None,
) -> BackgroundWorkflowManager:
    """
    BackgroundWorkflowManager 싱글톤 인스턴스 반환

    Args:
        executor: WorkflowExecutor 인스턴스 (첫 호출 시 필수)

    Returns:
        BackgroundWorkflowManager: 싱글톤 인스턴스

    Raises:
        ValueError: 첫 호출 시 executor가 None인 경우
    """
    global _manager
    if _manager is None:
        if executor is None:
            raise ValueError(
                "첫 호출 시 executor를 제공해야 합니다"
            )
        _manager = BackgroundWorkflowManager(executor)
    return _manager
