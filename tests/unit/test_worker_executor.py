"""
Unit Tests for WorkerExecutor

WorkerExecutor 클래스의 모든 기능을 테스트합니다:
- WorkerExecutionContext 직렬화
- Worker 실행 흐름 (pre → execute → post)
- Review cycle 추적 및 최대치 초과 처리
- Commit safety 검증
- 에러 핸들링 (타임아웃, 일반 예외)
- 콜백 트리거 (on_start, on_complete, on_error)
- 메트릭 수집
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, AsyncGenerator

from src.infrastructure.mcp.worker_executor import (
    WorkerExecutor,
    WorkerExecutionContext
)
from src.infrastructure.mcp.review_cycle_manager import ReviewCycleManager
from src.infrastructure.mcp.commit_validator import (
    CommitSafetyValidator,
    ValidationResult
)
from src.infrastructure.mcp.workflow_callback_handler import (
    WorkflowCallbackHandler,
    WorkflowEventType
)
from src.infrastructure.mcp.error_statistics_manager import ErrorStatisticsManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_worker_agent():
    """Mock Worker Agent"""
    agent = Mock()

    async def mock_execute_task(task_description: str) -> AsyncGenerator[str, None]:
        yield "Test output from worker"

    agent.execute_task = mock_execute_task
    return agent


@pytest.fixture
def mock_review_manager():
    """Mock ReviewCycleManager"""
    manager = Mock(spec=ReviewCycleManager)
    manager.reset = Mock()
    manager.mark_reviewer_called = Mock()
    manager.mark_coder_called = Mock()
    manager.should_continue_review = Mock(return_value=(True, None))
    manager.record_review_result = Mock()
    manager.coder_called_after_reviewer = False
    return manager


@pytest.fixture
def mock_commit_validator():
    """Mock CommitSafetyValidator"""
    validator = Mock(spec=CommitSafetyValidator)
    validator.validate_all = AsyncMock(return_value=ValidationResult(is_safe=True))
    return validator


@pytest.fixture
def mock_callback_handler():
    """Mock WorkflowCallbackHandler"""
    handler = Mock(spec=WorkflowCallbackHandler)
    handler.trigger_worker_event = Mock()
    return handler


@pytest.fixture
def mock_error_manager():
    """Mock ErrorStatisticsManager"""
    manager = Mock(spec=ErrorStatisticsManager)
    manager.record_attempt = Mock()
    manager.record_error = Mock()
    return manager


@pytest.fixture
def worker_executor(
    mock_review_manager,
    mock_commit_validator,
    mock_callback_handler,
    mock_error_manager
):
    """WorkerExecutor 인스턴스"""
    return WorkerExecutor(
        review_manager=mock_review_manager,
        commit_validator=mock_commit_validator,
        callback_handler=mock_callback_handler,
        error_manager=mock_error_manager
    )


@pytest.fixture
def basic_context(mock_worker_agent):
    """기본 WorkerExecutionContext"""
    return WorkerExecutionContext(
        worker_name="coder",
        task_description="Implement feature X",
        worker_agent=mock_worker_agent,
        timeout=10
    )


# ============================================================================
# Test: WorkerExecutionContext
# ============================================================================

def test_context_creation():
    """Context 생성 테스트"""
    context = WorkerExecutionContext(
        worker_name="planner",
        task_description="Plan feature Y"
    )

    assert context.worker_name == "planner"
    assert context.task_description == "Plan feature Y"
    assert context.use_retry is False
    assert context.timeout == 300  # 기본값


def test_context_to_dict():
    """Context 직렬화 테스트"""
    context = WorkerExecutionContext(
        worker_name="reviewer",
        task_description="Review code" * 100,  # 긴 설명
        timeout=600,
        session_id="test-session-123",
        metadata={"branch": "main"}
    )

    result = context.to_dict()

    assert result["worker_name"] == "reviewer"
    assert len(result["task_description"]) <= 100  # 잘림
    assert result["timeout"] == 600
    assert result["session_id"] == "test-session-123"
    assert result["metadata"]["branch"] == "main"


def test_context_with_all_fields():
    """Context 모든 필드 설정 테스트"""
    agent = Mock()
    callback = Mock()
    collector = Mock()

    context = WorkerExecutionContext(
        worker_name="tester",
        task_description="Run tests",
        use_retry=True,
        timeout=900,
        session_id="session-456",
        metrics_collector=collector,
        worker_agent=agent,
        worker_output_callback=callback,
        metadata={"env": "staging"}
    )

    assert context.use_retry is True
    assert context.worker_agent is agent
    assert context.worker_output_callback is callback
    assert context.metrics_collector is collector


# ============================================================================
# Test: WorkerExecutor 초기화
# ============================================================================

def test_executor_initialization():
    """Executor 초기화 테스트"""
    executor = WorkerExecutor()

    assert executor.review_manager is not None
    assert executor.commit_validator is not None
    assert executor.callback_handler is not None
    assert executor.error_manager is not None


def test_executor_with_custom_managers():
    """커스텀 매니저로 Executor 초기화 테스트"""
    review_mgr = ReviewCycleManager(max_cycles=5)
    commit_val = CommitSafetyValidator()
    callback_hdl = WorkflowCallbackHandler()
    error_mgr = ErrorStatisticsManager()

    executor = WorkerExecutor(
        review_manager=review_mgr,
        commit_validator=commit_val,
        callback_handler=callback_hdl,
        error_manager=error_mgr
    )

    assert executor.review_manager is review_mgr
    assert executor.commit_validator is commit_val
    assert executor.callback_handler is callback_hdl
    assert executor.error_manager is error_mgr


# ============================================================================
# Test: Worker 실행 - 정상 흐름
# ============================================================================

@pytest.mark.asyncio
async def test_execute_success(worker_executor, basic_context, mock_callback_handler, mock_error_manager):
    """정상 실행 흐름 테스트"""
    result = await worker_executor.execute(basic_context)

    # 결과 검증
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    assert "Test output from worker" in result["content"][0]["text"]

    # 콜백 호출 검증
    assert mock_callback_handler.trigger_worker_event.call_count == 2  # running, completed

    # 에러 통계 기록 검증
    mock_error_manager.record_attempt.assert_called_once_with("coder")


@pytest.mark.asyncio
async def test_execute_without_worker_agent(worker_executor):
    """Worker Agent가 없는 경우 테스트"""
    context = WorkerExecutionContext(
        worker_name="missing_worker",
        task_description="Test task",
        worker_agent=None  # No agent
    )

    result = await worker_executor.execute(context)

    assert "❌" in result["content"][0]["text"]
    assert "찾을 수 없습니다" in result["content"][0]["text"]


@pytest.mark.asyncio
async def test_execute_with_metrics_collector(worker_executor, mock_worker_agent):
    """메트릭 수집기와 함께 실행 테스트"""
    mock_collector = Mock()
    mock_collector.record_worker_execution = Mock()

    context = WorkerExecutionContext(
        worker_name="planner",
        task_description="Plan X",
        worker_agent=mock_worker_agent,
        session_id="session-789",
        metrics_collector=mock_collector,
        timeout=10
    )

    result = await worker_executor.execute(context)

    # 메트릭 기록 호출 검증
    mock_collector.record_worker_execution.assert_called_once()
    call_args = mock_collector.record_worker_execution.call_args[1]
    assert call_args["session_id"] == "session-789"
    assert call_args["worker_name"] == "planner"
    assert call_args["success"] is True


@pytest.mark.asyncio
async def test_execute_with_worker_output_callback(worker_executor, mock_worker_agent):
    """Worker 출력 콜백 테스트"""
    output_chunks = []

    def output_callback(worker_name: str, chunk: str):
        output_chunks.append((worker_name, chunk))

    context = WorkerExecutionContext(
        worker_name="coder",
        task_description="Code X",
        worker_agent=mock_worker_agent,
        worker_output_callback=output_callback,
        timeout=10
    )

    await worker_executor.execute(context)

    # 콜백이 호출되었는지 확인
    assert len(output_chunks) > 0
    assert output_chunks[0][0] == "coder"


# ============================================================================
# Test: Review Cycle 관리
# ============================================================================

@pytest.mark.asyncio
async def test_reviewer_execution_cycle_tracking(worker_executor, mock_worker_agent, mock_review_manager):
    """Reviewer 실행 시 cycle 추적 테스트"""
    context = WorkerExecutionContext(
        worker_name="reviewer",
        task_description="Review code",
        worker_agent=mock_worker_agent,
        timeout=10
    )

    await worker_executor.execute(context)

    # Reviewer 호출 기록 확인
    mock_review_manager.mark_reviewer_called.assert_called_once()
    mock_review_manager.should_continue_review.assert_called_once()


@pytest.mark.asyncio
async def test_reviewer_execution_cycle_exceeded(worker_executor, mock_worker_agent, mock_review_manager):
    """Review cycle 최대치 초과 테스트"""
    # should_continue_review가 False 반환하도록 설정
    mock_review_manager.should_continue_review.return_value = (False, "최대 횟수 초과")

    context = WorkerExecutionContext(
        worker_name="reviewer",
        task_description="Review code",
        worker_agent=mock_worker_agent,
        timeout=10
    )

    result = await worker_executor.execute(context)

    # 에러 응답 확인
    assert "최대 횟수 초과" in result["content"][0]["text"]

    # Review manager reset 호출 확인
    mock_review_manager.reset.assert_called_once()


@pytest.mark.asyncio
async def test_coder_execution_marks_coder_called(worker_executor, mock_worker_agent, mock_review_manager):
    """Coder 실행 시 mark_coder_called 호출 테스트"""
    context = WorkerExecutionContext(
        worker_name="coder",
        task_description="Implement feature",
        worker_agent=mock_worker_agent,
        timeout=10
    )

    await worker_executor.execute(context)

    # Coder 호출 기록 확인
    mock_review_manager.mark_coder_called.assert_called_once()


@pytest.mark.asyncio
async def test_planner_execution_resets_review_cycle(worker_executor, mock_worker_agent, mock_review_manager):
    """Planner 실행 시 Review cycle 초기화 테스트"""
    context = WorkerExecutionContext(
        worker_name="planner",
        task_description="Plan feature",
        worker_agent=mock_worker_agent,
        timeout=10
    )

    await worker_executor.execute(context)

    # Review cycle 초기화 확인
    mock_review_manager.reset.assert_called_once()


@pytest.mark.asyncio
async def test_reviewer_records_review_result(worker_executor, mock_worker_agent, mock_review_manager):
    """Reviewer 실행 후 결과 기록 테스트"""
    context = WorkerExecutionContext(
        worker_name="reviewer",
        task_description="Review code",
        worker_agent=mock_worker_agent,
        timeout=10
    )

    await worker_executor.execute(context)

    # Review 결과 기록 확인
    mock_review_manager.record_review_result.assert_called_once()


# ============================================================================
# Test: Commit Safety 검증
# ============================================================================

@pytest.mark.asyncio
async def test_committer_execution_validates_safety(worker_executor, mock_worker_agent, mock_commit_validator):
    """Committer 실행 시 안전성 검증 테스트"""
    context = WorkerExecutionContext(
        worker_name="committer",
        task_description="Create commit",
        worker_agent=mock_worker_agent,
        timeout=10
    )

    await worker_executor.execute(context)

    # 안전성 검증 호출 확인
    mock_commit_validator.validate_all.assert_called_once()


@pytest.mark.asyncio
async def test_committer_execution_fails_validation(worker_executor, mock_worker_agent, mock_commit_validator):
    """Committer 안전성 검증 실패 테스트"""
    # 검증 실패하도록 설정
    mock_commit_validator.validate_all.return_value = ValidationResult(
        is_safe=False,
        error_message="민감 정보 감지"
    )

    context = WorkerExecutionContext(
        worker_name="committer",
        task_description="Create commit",
        worker_agent=mock_worker_agent,
        timeout=10
    )

    result = await worker_executor.execute(context)

    # 에러 응답 확인
    assert "커밋 거부" in result["content"][0]["text"]
    assert "민감 정보 감지" in result["content"][0]["text"]


# ============================================================================
# Test: 에러 핸들링
# ============================================================================

@pytest.mark.asyncio
async def test_execute_timeout_error(worker_executor, mock_error_manager):
    """타임아웃 에러 처리 테스트"""
    agent = Mock()

    async def slow_execute_task(task_description: str):
        await asyncio.sleep(10)  # 타임아웃보다 긴 시간
        yield "Never reach here"

    agent.execute_task = slow_execute_task

    context = WorkerExecutionContext(
        worker_name="slow_worker",
        task_description="Slow task",
        worker_agent=agent,
        timeout=0.1  # 0.1초 타임아웃
    )

    result = await worker_executor.execute(context)

    # 타임아웃 에러 응답 확인
    assert "타임아웃" in result["content"][0]["text"]

    # 에러 통계 기록 확인
    mock_error_manager.record_error.assert_called_once()


@pytest.mark.asyncio
async def test_execute_general_exception(worker_executor, mock_error_manager):
    """일반 예외 처리 테스트"""
    agent = Mock()

    async def failing_execute_task(task_description: str):
        raise ValueError("Something went wrong")
        yield  # Never reached

    agent.execute_task = failing_execute_task

    context = WorkerExecutionContext(
        worker_name="failing_worker",
        task_description="Failing task",
        worker_agent=agent,
        timeout=10
    )

    result = await worker_executor.execute(context)

    # 에러 응답 확인
    assert "실행 실패" in result["content"][0]["text"]
    assert "Something went wrong" in result["content"][0]["text"]

    # 에러 통계 기록 확인
    mock_error_manager.record_error.assert_called_once()


@pytest.mark.asyncio
async def test_execute_failed_triggers_failed_callback(worker_executor, mock_callback_handler):
    """실행 실패 시 failed 콜백 트리거 테스트"""
    agent = Mock()

    async def failing_execute_task(task_description: str):
        raise RuntimeError("Test error")
        yield

    agent.execute_task = failing_execute_task

    context = WorkerExecutionContext(
        worker_name="test_worker",
        task_description="Test task",
        worker_agent=agent,
        timeout=10
    )

    await worker_executor.execute(context)

    # Failed 콜백 호출 확인
    calls = mock_callback_handler.trigger_worker_event.call_args_list
    # 첫 번째: running, 두 번째: failed
    assert len(calls) == 2
    assert calls[1][1]["status"] == "failed"
    assert calls[1][1]["error"] is not None


# ============================================================================
# Test: 콜백 트리거
# ============================================================================

@pytest.mark.asyncio
async def test_execute_triggers_running_callback(worker_executor, mock_callback_handler, basic_context):
    """실행 시작 시 running 콜백 트리거 테스트"""
    await worker_executor.execute(basic_context)

    # Running 콜백 호출 확인
    calls = mock_callback_handler.trigger_worker_event.call_args_list
    assert len(calls) >= 1
    assert calls[0][1]["worker_name"] == "coder"
    assert calls[0][1]["status"] == "running"


@pytest.mark.asyncio
async def test_execute_triggers_completed_callback(worker_executor, mock_callback_handler, basic_context):
    """실행 완료 시 completed 콜백 트리거 테스트"""
    await worker_executor.execute(basic_context)

    # Completed 콜백 호출 확인
    calls = mock_callback_handler.trigger_worker_event.call_args_list
    assert len(calls) == 2
    assert calls[1][1]["worker_name"] == "coder"
    assert calls[1][1]["status"] == "completed"


# ============================================================================
# Test: 유틸리티 메서드
# ============================================================================

def test_set_review_max_cycles(worker_executor, mock_review_manager):
    """Review max_cycles 설정 테스트"""
    worker_executor.set_review_max_cycles(5)

    assert mock_review_manager.max_cycles == 5


def test_get_error_summary(worker_executor, mock_error_manager):
    """에러 요약 조회 테스트"""
    mock_error_manager.export_to_dict.return_value = {
        "total_attempts": 10,
        "total_failures": 2,
        "error_rate": 20.0
    }

    summary = worker_executor.get_error_summary()

    assert summary["total_attempts"] == 10
    assert summary["total_failures"] == 2
    assert summary["error_rate"] == 20.0


def test_reset_review_cycle(worker_executor, mock_review_manager):
    """Review cycle 초기화 테스트"""
    worker_executor.reset_review_cycle()

    mock_review_manager.reset.assert_called_once()


def test_reset_error_statistics(worker_executor, mock_error_manager):
    """에러 통계 초기화 테스트"""
    worker_executor.reset_error_statistics()

    mock_error_manager.reset_statistics.assert_called_once()


# ============================================================================
# Test: 복잡한 시나리오
# ============================================================================

@pytest.mark.asyncio
async def test_retry_logic_integration(worker_executor):
    """재시도 로직 통합 테스트"""
    agent = Mock()
    call_count = 0

    async def unstable_execute_task(task_description: str):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RuntimeError("Temporary error")
        yield "Success after retry"

    agent.execute_task = unstable_execute_task

    context = WorkerExecutionContext(
        worker_name="unstable_worker",
        task_description="Unstable task",
        worker_agent=agent,
        use_retry=True,
        timeout=10
    )

    # Note: retry_with_backoff는 worker_tools.py에서 import되므로,
    # 여기서는 단순 실행만 테스트
    with patch("src.infrastructure.mcp.worker_executor.retry_with_backoff") as mock_retry:
        async def mock_retry_func():
            return {"content": [{"type": "text", "text": "Retried"}]}

        mock_retry.return_value = mock_retry_func()

        result = await worker_executor.execute(context)

        # 재시도 함수 호출 확인
        mock_retry.assert_called_once()


@pytest.mark.asyncio
async def test_extract_critical_issues():
    """중요 이슈 추출 테스트"""
    executor = WorkerExecutor()

    reviewer_output = """
    코드 리뷰 결과:
    1. CRITICAL: Security vulnerability in authentication
    2. Minor: Typo in comment
    3. ERROR: Null pointer dereference
    4. Warning: Unused variable
    """

    issues = executor._extract_critical_issues(reviewer_output)

    # Critical 키워드가 포함된 라인들 추출 확인
    assert len(issues) >= 2
    assert any("CRITICAL" in issue or "Security" in issue for issue in issues)
    assert any("ERROR" in issue or "Null pointer" in issue for issue in issues)


# ============================================================================
# Test: 엣지 케이스
# ============================================================================

@pytest.mark.asyncio
async def test_execute_with_empty_output(worker_executor):
    """Worker가 빈 출력을 반환하는 경우 테스트"""
    agent = Mock()

    async def empty_execute_task(task_description: str):
        yield ""  # 빈 출력

    agent.execute_task = empty_execute_task

    context = WorkerExecutionContext(
        worker_name="empty_worker",
        task_description="Empty task",
        worker_agent=agent,
        timeout=10
    )

    result = await worker_executor.execute(context)

    # 빈 출력이라도 정상 결과 반환
    assert "content" in result
    assert result["content"][0]["text"] == ""


@pytest.mark.asyncio
async def test_execute_with_very_long_task_description(worker_executor, mock_worker_agent):
    """매우 긴 task_description 처리 테스트"""
    long_description = "A" * 10000

    context = WorkerExecutionContext(
        worker_name="test_worker",
        task_description=long_description,
        worker_agent=mock_worker_agent,
        timeout=10
    )

    result = await worker_executor.execute(context)

    # 정상 실행 확인
    assert "content" in result


@pytest.mark.asyncio
async def test_metrics_collector_exception_handling(worker_executor, mock_worker_agent):
    """메트릭 수집기 예외 처리 테스트"""
    mock_collector = Mock()
    mock_collector.record_worker_execution = Mock(side_effect=RuntimeError("DB error"))

    context = WorkerExecutionContext(
        worker_name="test_worker",
        task_description="Test task",
        worker_agent=mock_worker_agent,
        session_id="session-123",
        metrics_collector=mock_collector,
        timeout=10
    )

    # 메트릭 기록 실패해도 정상 실행되어야 함
    result = await worker_executor.execute(context)

    assert "content" in result
    assert "Test output from worker" in result["content"][0]["text"]


@pytest.mark.asyncio
async def test_worker_output_callback_exception_handling(worker_executor, mock_worker_agent):
    """Worker 출력 콜백 예외 처리 테스트"""
    def failing_callback(worker_name: str, chunk: str):
        raise RuntimeError("Callback error")

    context = WorkerExecutionContext(
        worker_name="test_worker",
        task_description="Test task",
        worker_agent=mock_worker_agent,
        worker_output_callback=failing_callback,
        timeout=10
    )

    # 콜백 실패해도 정상 실행되어야 함
    result = await worker_executor.execute(context)

    assert "content" in result
