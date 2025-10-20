"""
WorkflowCallbackHandler 테스트
"""

import pytest
import asyncio
from src.infrastructure.mcp.workflow_callback_handler import (
    WorkflowCallbackHandler,
    WorkflowEventType,
    CallbackLog,
    WorkflowEvent
)


class TestWorkflowCallbackHandlerInitialization:
    """WorkflowCallbackHandler 초기화 테스트"""

    def test_initialization_default(self):
        """기본 설정으로 초기화 테스트"""
        handler = WorkflowCallbackHandler()

        assert handler.callbacks == {}
        assert handler.async_callbacks == {}
        assert handler.callback_history == []
        assert handler.enable_history is True
        assert handler.max_history_size == 1000

    def test_initialization_custom(self):
        """커스텀 설정으로 초기화 테스트"""
        handler = WorkflowCallbackHandler(
            enable_history=False,
            max_history_size=100
        )

        assert handler.enable_history is False
        assert handler.max_history_size == 100


class TestCallbackRegistration:
    """콜백 등록 테스트"""

    def test_register_callback(self):
        """동기 콜백 등록 테스트"""
        handler = WorkflowCallbackHandler()

        def test_callback(context):
            pass

        handler.register_callback(
            WorkflowEventType.WORKER_COMPLETED,
            test_callback
        )

        event_key = WorkflowEventType.WORKER_COMPLETED.value
        assert event_key in handler.callbacks
        assert test_callback in handler.callbacks[event_key]

    def test_register_async_callback(self):
        """비동기 콜백 등록 테스트"""
        handler = WorkflowCallbackHandler()

        async def test_async_callback(context):
            pass

        handler.register_callback(
            WorkflowEventType.WORKER_COMPLETED,
            test_async_callback,
            async_handler=True
        )

        event_key = WorkflowEventType.WORKER_COMPLETED.value
        assert event_key in handler.async_callbacks
        assert test_async_callback in handler.async_callbacks[event_key]

    def test_register_multiple_callbacks_same_event(self):
        """동일 이벤트에 여러 콜백 등록 테스트"""
        handler = WorkflowCallbackHandler()

        def callback1(context):
            pass

        def callback2(context):
            pass

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, callback1)
        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, callback2)

        event_key = WorkflowEventType.WORKER_COMPLETED.value
        assert len(handler.callbacks[event_key]) == 2

    def test_unregister_callback(self):
        """콜백 등록 해제 테스트"""
        handler = WorkflowCallbackHandler()

        def test_callback(context):
            pass

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, test_callback)
        success = handler.unregister_callback(
            WorkflowEventType.WORKER_COMPLETED,
            test_callback
        )

        assert success is True
        event_key = WorkflowEventType.WORKER_COMPLETED.value
        assert test_callback not in handler.callbacks[event_key]

    def test_unregister_nonexistent_callback(self):
        """존재하지 않는 콜백 등록 해제 테스트"""
        handler = WorkflowCallbackHandler()

        def test_callback(context):
            pass

        success = handler.unregister_callback(
            WorkflowEventType.WORKER_COMPLETED,
            test_callback
        )

        assert success is False


class TestSyncCallbackTrigger:
    """동기 콜백 트리거 테스트"""

    def test_trigger_callback_no_handlers(self):
        """등록된 핸들러가 없는 경우 테스트"""
        handler = WorkflowCallbackHandler()

        # 에러 없이 정상 실행되어야 함
        handler.trigger_callback(
            WorkflowEventType.WORKER_COMPLETED,
            {"worker_name": "test"}
        )

    def test_trigger_callback_execution(self):
        """콜백 실행 테스트"""
        handler = WorkflowCallbackHandler()
        result = []

        def test_callback(context):
            result.append(context["worker_name"])

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, test_callback)
        handler.trigger_callback(
            WorkflowEventType.WORKER_COMPLETED,
            {"worker_name": "coder"}
        )

        assert "coder" in result

    def test_trigger_multiple_callbacks(self):
        """여러 콜백 동시 실행 테스트"""
        handler = WorkflowCallbackHandler()
        results = []

        def callback1(context):
            results.append("callback1")

        def callback2(context):
            results.append("callback2")

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, callback1)
        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, callback2)

        handler.trigger_callback(
            WorkflowEventType.WORKER_COMPLETED,
            {"worker_name": "test"}
        )

        assert "callback1" in results
        assert "callback2" in results

    def test_trigger_callback_with_error(self):
        """콜백 실행 중 에러 발생 테스트"""
        handler = WorkflowCallbackHandler()

        def failing_callback(context):
            raise ValueError("Test error")

        handler.register_callback(WorkflowEventType.WORKER_FAILED, failing_callback)

        # 에러가 발생해도 프로그램이 중단되지 않아야 함
        handler.trigger_callback(
            WorkflowEventType.WORKER_FAILED,
            {"worker_name": "test"}
        )

        # 히스토리에 에러가 기록되어야 함
        assert len(handler.callback_history) == 1
        assert handler.callback_history[0].success is False


class TestAsyncCallbackTrigger:
    """비동기 콜백 트리거 테스트"""

    @pytest.mark.asyncio
    async def test_trigger_async_callback_execution(self):
        """비동기 콜백 실행 테스트"""
        handler = WorkflowCallbackHandler()
        result = []

        async def test_async_callback(context):
            await asyncio.sleep(0.01)
            result.append(context["worker_name"])

        handler.register_callback(
            WorkflowEventType.WORKER_COMPLETED,
            test_async_callback,
            async_handler=True
        )

        await handler.trigger_callback_async(
            WorkflowEventType.WORKER_COMPLETED,
            {"worker_name": "coder"}
        )

        assert "coder" in result

    @pytest.mark.asyncio
    async def test_trigger_async_and_sync_callbacks(self):
        """동기/비동기 콜백 동시 실행 테스트"""
        handler = WorkflowCallbackHandler()
        results = []

        def sync_callback(context):
            results.append("sync")

        async def async_callback(context):
            await asyncio.sleep(0.01)
            results.append("async")

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, sync_callback)
        handler.register_callback(
            WorkflowEventType.WORKER_COMPLETED,
            async_callback,
            async_handler=True
        )

        await handler.trigger_callback_async(
            WorkflowEventType.WORKER_COMPLETED,
            {"worker_name": "test"}
        )

        assert "sync" in results
        assert "async" in results

    @pytest.mark.asyncio
    async def test_async_callback_error_handling(self):
        """비동기 콜백 에러 처리 테스트"""
        handler = WorkflowCallbackHandler()

        async def failing_async_callback(context):
            raise ValueError("Async error")

        handler.register_callback(
            WorkflowEventType.WORKER_FAILED,
            failing_async_callback,
            async_handler=True
        )

        # 에러가 발생해도 중단되지 않아야 함
        await handler.trigger_callback_async(
            WorkflowEventType.WORKER_FAILED,
            {"worker_name": "test"}
        )


class TestCallbackHistory:
    """콜백 히스토리 테스트"""

    def test_callback_history_recording(self):
        """히스토리 기록 테스트"""
        handler = WorkflowCallbackHandler()

        def test_callback(context):
            pass

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, test_callback)
        handler.trigger_callback(
            WorkflowEventType.WORKER_COMPLETED,
            {"worker_name": "coder"}
        )

        assert len(handler.callback_history) == 1
        log = handler.callback_history[0]
        assert log.event_type == WorkflowEventType.WORKER_COMPLETED.value
        assert log.success is True

    def test_history_disabled(self):
        """히스토리 비활성화 테스트"""
        handler = WorkflowCallbackHandler(enable_history=False)

        def test_callback(context):
            pass

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, test_callback)
        handler.trigger_callback(
            WorkflowEventType.WORKER_COMPLETED,
            {"worker_name": "coder"}
        )

        # 히스토리 기록 안 됨
        assert len(handler.callback_history) == 0

    def test_get_callback_history(self):
        """히스토리 조회 테스트"""
        handler = WorkflowCallbackHandler()

        def test_callback(context):
            pass

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, test_callback)
        handler.trigger_callback(
            WorkflowEventType.WORKER_COMPLETED,
            {"worker_name": "coder"}
        )

        history = handler.get_callback_history()
        assert len(history) == 1

    def test_get_callback_history_filtered(self):
        """히스토리 필터링 조회 테스트"""
        handler = WorkflowCallbackHandler()

        def test_callback(context):
            pass

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, test_callback)
        handler.register_callback(WorkflowEventType.WORKER_FAILED, test_callback)

        handler.trigger_callback(
            WorkflowEventType.WORKER_COMPLETED,
            {"worker_name": "coder"}
        )
        handler.trigger_callback(
            WorkflowEventType.WORKER_FAILED,
            {"worker_name": "tester"}
        )

        # WORKER_COMPLETED만 필터링
        history = handler.get_callback_history(
            event_type=WorkflowEventType.WORKER_COMPLETED
        )
        assert len(history) == 1

    def test_get_callback_history_with_limit(self):
        """히스토리 개수 제한 조회 테스트"""
        handler = WorkflowCallbackHandler()

        def test_callback(context):
            pass

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, test_callback)

        for i in range(5):
            handler.trigger_callback(
                WorkflowEventType.WORKER_COMPLETED,
                {"worker_name": f"worker{i}"}
            )

        # 최근 2개만 조회
        history = handler.get_callback_history(limit=2)
        assert len(history) == 2

    def test_clear_history(self):
        """히스토리 초기화 테스트"""
        handler = WorkflowCallbackHandler()

        def test_callback(context):
            pass

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, test_callback)
        handler.trigger_callback(
            WorkflowEventType.WORKER_COMPLETED,
            {"worker_name": "coder"}
        )

        handler.clear_history()
        assert len(handler.callback_history) == 0

    def test_history_size_limit(self):
        """히스토리 크기 제한 테스트"""
        handler = WorkflowCallbackHandler(max_history_size=3)

        def test_callback(context):
            pass

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, test_callback)

        for i in range(5):
            handler.trigger_callback(
                WorkflowEventType.WORKER_COMPLETED,
                {"worker_name": f"worker{i}"}
            )

        # 최대 3개만 유지
        assert len(handler.callback_history) == 3


class TestStatistics:
    """통계 기능 테스트"""

    def test_get_statistics(self):
        """통계 조회 테스트"""
        handler = WorkflowCallbackHandler()

        def success_callback(context):
            pass

        def failing_callback(context):
            raise ValueError("Error")

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, success_callback)
        handler.register_callback(WorkflowEventType.WORKER_FAILED, failing_callback)

        handler.trigger_callback(
            WorkflowEventType.WORKER_COMPLETED,
            {"worker_name": "coder"}
        )
        handler.trigger_callback(
            WorkflowEventType.WORKER_FAILED,
            {"worker_name": "tester"}
        )

        stats = handler.get_statistics()

        assert WorkflowEventType.WORKER_COMPLETED.value in stats
        assert stats[WorkflowEventType.WORKER_COMPLETED.value]["success"] == 1
        assert stats[WorkflowEventType.WORKER_FAILED.value]["failed"] == 1


class TestWorkerEventHelpers:
    """Worker 이벤트 헬퍼 메서드 테스트"""

    def test_trigger_worker_event_running(self):
        """Worker running 이벤트 트리거 테스트"""
        handler = WorkflowCallbackHandler()
        result = []

        def test_callback(context):
            result.append(context["status"])

        handler.register_callback(WorkflowEventType.WORKER_RUNNING, test_callback)
        handler.trigger_worker_event("coder", "running")

        assert "running" in result

    def test_trigger_worker_event_completed(self):
        """Worker completed 이벤트 트리거 테스트"""
        handler = WorkflowCallbackHandler()
        result = []

        def test_callback(context):
            result.append(context["worker_name"])

        handler.register_callback(WorkflowEventType.WORKER_COMPLETED, test_callback)
        handler.trigger_worker_event("coder", "completed")

        assert "coder" in result

    def test_trigger_worker_event_failed(self):
        """Worker failed 이벤트 트리거 테스트"""
        handler = WorkflowCallbackHandler()
        result = []

        def test_callback(context):
            result.append(context["error"])

        handler.register_callback(WorkflowEventType.WORKER_FAILED, test_callback)
        handler.trigger_worker_event("coder", "failed", error="Test error")

        assert "Test error" in result

    @pytest.mark.asyncio
    async def test_trigger_worker_event_async(self):
        """Worker 이벤트 비동기 트리거 테스트"""
        handler = WorkflowCallbackHandler()
        result = []

        async def test_async_callback(context):
            await asyncio.sleep(0.01)
            result.append(context["worker_name"])

        handler.register_callback(
            WorkflowEventType.WORKER_COMPLETED,
            test_async_callback,
            async_handler=True
        )

        await handler.trigger_worker_event_async("coder", "completed")

        assert "coder" in result
