"""
Workflow Callback Handler - 워크플로우 이벤트 콜백 관리

Worker 실행, 완료, 실패 등의 워크플로우 이벤트에 대한 콜백을
등록하고 관리합니다. TUI/CLI에서 실시간 상태 업데이트에 사용됩니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List
from enum import Enum
import asyncio
import logging

from src.infrastructure.logging import get_logger

logger = get_logger(__name__, component="WorkflowCallbackHandler")


class WorkflowEventType(Enum):
    """워크플로우 이벤트 타입"""
    WORKER_STARTED = "worker_started"
    WORKER_RUNNING = "worker_running"
    WORKER_COMPLETED = "worker_completed"
    WORKER_FAILED = "worker_failed"
    REVIEW_CYCLE_EXCEEDED = "review_cycle_exceeded"
    PARALLEL_TASK_STARTED = "parallel_task_started"
    PARALLEL_TASK_COMPLETED = "parallel_task_completed"
    PARALLEL_TASK_FAILED = "parallel_task_failed"


@dataclass
class CallbackLog:
    """콜백 실행 로그"""
    event_type: str
    context: Dict[str, Any]
    timestamp: datetime
    success: bool
    error: Optional[str] = None


@dataclass
class WorkflowEvent:
    """워크플로우 이벤트"""
    event_type: WorkflowEventType
    worker_name: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class WorkflowCallbackHandler:
    """
    워크플로우 콜백 핸들러

    Worker 실행 중 발생하는 다양한 이벤트에 대한 콜백을 등록하고 관리합니다.
    동기/비동기 콜백을 모두 지원하며, 콜백 실행 히스토리를 기록합니다.

    Attributes:
        callbacks: 이벤트별 콜백 함수 딕셔너리
        callback_history: 콜백 실행 히스토리
        async_callbacks: 비동기 콜백 딕셔너리

    Example:
        >>> handler = WorkflowCallbackHandler()
        >>> handler.register_callback(
        ...     WorkflowEventType.WORKER_COMPLETED,
        ...     lambda ctx: print(f"Worker {ctx['worker_name']} completed")
        ... )
        >>> await handler.trigger_callback(
        ...     WorkflowEventType.WORKER_COMPLETED,
        ...     {"worker_name": "coder"}
        ... )
    """

    def __init__(self, enable_history: bool = True, max_history_size: int = 1000):
        """
        WorkflowCallbackHandler 초기화

        Args:
            enable_history: 히스토리 기록 활성화 여부
            max_history_size: 최대 히스토리 크기
        """
        self.callbacks: Dict[str, List[Callable]] = {}
        self.async_callbacks: Dict[str, List[Callable]] = {}
        self.callback_history: List[CallbackLog] = []
        self.enable_history = enable_history
        self.max_history_size = max_history_size

        logger.info("WorkflowCallbackHandler initialized")

    def register_callback(
        self,
        event: WorkflowEventType,
        handler: Callable,
        async_handler: bool = False
    ) -> None:
        """
        콜백 함수 등록

        Args:
            event: 이벤트 타입
            handler: 콜백 함수
                     시그니처: handler(context: Dict[str, Any]) -> None
            async_handler: 비동기 핸들러 여부

        Example:
            >>> def on_worker_completed(context):
            ...     print(f"Worker {context['worker_name']} done")
            >>> handler.register_callback(
            ...     WorkflowEventType.WORKER_COMPLETED,
            ...     on_worker_completed
            ... )
        """
        event_key = event.value

        if async_handler:
            if event_key not in self.async_callbacks:
                self.async_callbacks[event_key] = []
            self.async_callbacks[event_key].append(handler)
            logger.info(f"Async callback registered for event: {event_key}")
        else:
            if event_key not in self.callbacks:
                self.callbacks[event_key] = []
            self.callbacks[event_key].append(handler)
            logger.info(f"Callback registered for event: {event_key}")

    def unregister_callback(
        self,
        event: WorkflowEventType,
        handler: Callable,
        async_handler: bool = False
    ) -> bool:
        """
        콜백 함수 등록 해제

        Args:
            event: 이벤트 타입
            handler: 등록 해제할 콜백 함수
            async_handler: 비동기 핸들러 여부

        Returns:
            성공 여부
        """
        event_key = event.value
        target_dict = self.async_callbacks if async_handler else self.callbacks

        if event_key in target_dict and handler in target_dict[event_key]:
            target_dict[event_key].remove(handler)
            logger.info(f"Callback unregistered for event: {event_key}")
            return True

        logger.warning(f"Callback not found for event: {event_key}")
        return False

    def trigger_callback(self, event: WorkflowEventType, context: Dict[str, Any]) -> None:
        """
        동기 콜백 트리거 (즉시 실행)

        Args:
            event: 이벤트 타입
            context: 콜백에 전달할 컨텍스트 정보

        Note:
            동기 콜백만 실행됩니다. 비동기 콜백은 trigger_callback_async()를 사용하세요.
        """
        event_key = event.value
        handlers = self.callbacks.get(event_key, [])

        if not handlers:
            logger.debug(f"No callbacks registered for event: {event_key}")
            return

        for handler in handlers:
            try:
                handler(context)
                self._record_callback_log(event_key, context, success=True)

            except Exception as e:
                logger.error(f"Callback execution failed for event {event_key}: {e}")
                self._record_callback_log(event_key, context, success=False, error=str(e))

    async def trigger_callback_async(
        self,
        event: WorkflowEventType,
        context: Dict[str, Any]
    ) -> None:
        """
        비동기 콜백 트리거 (await 필요)

        Args:
            event: 이벤트 타입
            context: 콜백에 전달할 컨텍스트 정보

        Note:
            동기 콜백과 비동기 콜백을 모두 실행합니다.
        """
        event_key = event.value

        # 동기 콜백 실행
        self.trigger_callback(event, context)

        # 비동기 콜백 실행
        async_handlers = self.async_callbacks.get(event_key, [])

        if not async_handlers:
            logger.debug(f"No async callbacks registered for event: {event_key}")
            return

        tasks = []
        for handler in async_handlers:
            task = self._execute_async_callback(handler, event_key, context)
            tasks.append(task)

        # 모든 비동기 콜백 병렬 실행
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_async_callback(
        self,
        handler: Callable,
        event_key: str,
        context: Dict[str, Any]
    ) -> None:
        """비동기 콜백 실행 (에러 핸들링 포함)"""
        try:
            await handler(context)
            self._record_callback_log(event_key, context, success=True)

        except Exception as e:
            logger.error(f"Async callback execution failed for event {event_key}: {e}")
            self._record_callback_log(event_key, context, success=False, error=str(e))

    def _record_callback_log(
        self,
        event_type: str,
        context: Dict[str, Any],
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """콜백 실행 로그 기록"""
        if not self.enable_history:
            return

        log_entry = CallbackLog(
            event_type=event_type,
            context=context.copy(),
            timestamp=datetime.now(),
            success=success,
            error=error
        )

        self.callback_history.append(log_entry)

        # 히스토리 크기 제한
        if len(self.callback_history) > self.max_history_size:
            self.callback_history = self.callback_history[-self.max_history_size:]

    def get_callback_history(
        self,
        event_type: Optional[WorkflowEventType] = None,
        limit: Optional[int] = None
    ) -> List[CallbackLog]:
        """
        콜백 실행 히스토리 조회

        Args:
            event_type: 특정 이벤트 타입만 필터링 (None이면 전체)
            limit: 반환할 최대 개수 (None이면 전체)

        Returns:
            CallbackLog 목록
        """
        history = self.callback_history

        if event_type:
            history = [
                log for log in history
                if log.event_type == event_type.value
            ]

        if limit:
            history = history[-limit:]

        return history

    def clear_history(self) -> None:
        """히스토리 초기화"""
        self.callback_history.clear()
        logger.info("Callback history cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """
        콜백 실행 통계 조회

        Returns:
            이벤트별 콜백 실행 통계
        """
        stats = {}

        for log in self.callback_history:
            event_type = log.event_type
            if event_type not in stats:
                stats[event_type] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0
                }

            stats[event_type]["total"] += 1
            if log.success:
                stats[event_type]["success"] += 1
            else:
                stats[event_type]["failed"] += 1

        return stats

    def trigger_worker_event(
        self,
        worker_name: str,
        status: str,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Worker 이벤트 트리거 (편의 메서드)

        Args:
            worker_name: Worker 이름
            status: Worker 상태 ("running", "completed", "failed")
            error: 에러 메시지 (실패 시)
            metadata: 추가 메타데이터
        """
        event_map = {
            "running": WorkflowEventType.WORKER_RUNNING,
            "completed": WorkflowEventType.WORKER_COMPLETED,
            "failed": WorkflowEventType.WORKER_FAILED,
        }

        event = event_map.get(status)
        if not event:
            logger.warning(f"Unknown worker status: {status}")
            return

        context = {
            "worker_name": worker_name,
            "status": status,
            "error": error,
            "metadata": metadata or {}
        }

        self.trigger_callback(event, context)

    async def trigger_worker_event_async(
        self,
        worker_name: str,
        status: str,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Worker 이벤트 트리거 (비동기, 편의 메서드)

        Args:
            worker_name: Worker 이름
            status: Worker 상태
            error: 에러 메시지
            metadata: 추가 메타데이터
        """
        event_map = {
            "running": WorkflowEventType.WORKER_RUNNING,
            "completed": WorkflowEventType.WORKER_COMPLETED,
            "failed": WorkflowEventType.WORKER_FAILED,
        }

        event = event_map.get(status)
        if not event:
            logger.warning(f"Unknown worker status: {status}")
            return

        context = {
            "worker_name": worker_name,
            "status": status,
            "error": error,
            "metadata": metadata or {}
        }

        await self.trigger_callback_async(event, context)
