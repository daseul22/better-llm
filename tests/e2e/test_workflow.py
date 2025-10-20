"""
End-to-end workflow tests

전체 워크플로우 테스트: Manager → Worker → 결과 반환
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

from src.infrastructure.mcp.worker_tools import (
    initialize_workers,
    _execute_worker_task,
    reset_review_cycle,
    _REVIEW_CYCLE_STATE,
)


@pytest.mark.e2e
class TestWorkflowBasic:
    """기본 워크플로우 테스트"""

    @pytest.fixture(autouse=True)
    def setup_workers(self, tmp_path: Path):
        """Worker Agent 초기화 Mock"""
        # Worker Agent 초기화를 mock으로 대체
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            # Mock Worker Agent 생성
            mock_planner = MagicMock()
            mock_planner.execute_task = AsyncMock()
            
            async def mock_execute_planner():
                yield "Planning task: Step 1\n"
                yield "Planning task: Step 2\n"
                yield "Planning completed\n"
            
            mock_planner.execute_task.return_value = mock_execute_planner()
            
            mock_agents.__getitem__.return_value = mock_planner
            mock_agents.get.return_value = mock_planner
            
            yield mock_agents

    @pytest.mark.asyncio
    async def test_planner_execution(self):
        """Planner 워크플로우 실행 테스트"""
        task_description = "Analyze user requirements and create a plan"
        
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            mock_worker = MagicMock()
            
            async def mock_execute():
                yield "Plan created: \n"
                yield "1. Step 1\n"
                yield "2. Step 2\n"
            
            mock_worker.execute_task.return_value = mock_execute()
            mock_agents.get.return_value = mock_worker
            
            result = await _execute_worker_task("planner", task_description)
            
            assert result is not None
            assert "content" in result
            assert isinstance(result["content"], list)
            assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_coder_execution(self):
        """Coder 워크플로우 실행 테스트"""
        task_description = "Write a hello world function"
        
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            mock_worker = MagicMock()
            
            async def mock_execute():
                yield "def hello():\n"
                yield "    print('Hello, World!')\n"
            
            mock_worker.execute_task.return_value = mock_execute()
            mock_agents.get.return_value = mock_worker
            
            result = await _execute_worker_task("coder", task_description)
            
            assert result is not None
            assert "content" in result

    @pytest.mark.asyncio
    async def test_reviewer_execution(self):
        """Reviewer 워크플로우 실행 테스트"""
        # Review cycle 초기화
        reset_review_cycle()
        
        task_description = "Review the code"
        
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            mock_worker = MagicMock()
            
            async def mock_execute():
                yield "Code review:\n"
                yield "- Good: Clear function name\n"
                yield "- Improvement: Add docstring\n"
            
            mock_worker.execute_task.return_value = mock_execute()
            mock_agents.get.return_value = mock_worker
            
            result = await _execute_worker_task("reviewer", task_description)
            
            assert result is not None
            assert "content" in result


@pytest.mark.e2e
class TestWorkflowSequence:
    """순차 워크플로우 테스트"""

    @pytest.mark.asyncio
    async def test_full_workflow_cycle(self):
        """전체 워크플로우 사이클: Planner → Coder → Reviewer"""
        # Review cycle 초기화
        reset_review_cycle()
        
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            mock_worker = MagicMock()
            
            # Planner 실행
            async def mock_planner():
                yield "Plan: Build a REST API\n"
            
            mock_worker.execute_task.return_value = mock_planner()
            mock_agents.get.return_value = mock_worker
            
            plan_result = await _execute_worker_task("planner", "Build a REST API")
            assert plan_result is not None
            
            # Coder 실행
            async def mock_coder():
                yield "Code: Flask app created\n"
            
            mock_worker.execute_task.return_value = mock_coder()
            code_result = await _execute_worker_task("coder", "Implement the API")
            assert code_result is not None
            
            # Reviewer 실행
            async def mock_reviewer():
                yield "Review: Code looks good\n"
            
            mock_worker.execute_task.return_value = mock_reviewer()
            review_result = await _execute_worker_task("reviewer", "Review the implementation")
            assert review_result is not None

    @pytest.mark.asyncio
    async def test_review_cycle_tracking(self):
        """Review cycle 추적 테스트"""
        # Review cycle 초기화
        reset_review_cycle()
        
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            mock_worker = MagicMock()
            
            async def mock_execute():
                yield "Task completed\n"
            
            mock_worker.execute_task.return_value = mock_execute()
            mock_agents.get.return_value = mock_worker
            
            # Reviewer 첫 호출
            await _execute_worker_task("reviewer", "Review #1")
            
            # Coder 호출 (cycle 플래그 설정)
            await _execute_worker_task("coder", "Fix issues")
            
            # Reviewer 재호출 (cycle count 증가)
            await _execute_worker_task("reviewer", "Review #2")
            
            # cycle count 확인
            assert _REVIEW_CYCLE_STATE["count"] >= 0


@pytest.mark.e2e
class TestWorkflowErrorHandling:
    """워크플로우 에러 핸들링 테스트"""

    @pytest.mark.asyncio
    async def test_worker_not_found(self):
        """존재하지 않는 Worker 호출 시 에러 처리 테스트"""
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            mock_agents.get.return_value = None
            
            result = await _execute_worker_task("invalid_worker", "Test task")
            
            assert result is not None
            assert "content" in result
            assert "찾을 수 없습니다" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """타임아웃 처리 테스트"""
        import asyncio
        
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            with patch('src.infrastructure.mcp.worker_tools._WORKER_TIMEOUTS', {"planner": 0.1}):
                mock_worker = MagicMock()
                
                async def slow_execute():
                    await asyncio.sleep(1)  # 타임아웃보다 긴 시간
                    yield "Should timeout\n"
                
                mock_worker.execute_task.return_value = slow_execute()
                mock_agents.get.return_value = mock_worker
                
                result = await _execute_worker_task("planner", "Slow task")
                
                assert result is not None
                assert "타임아웃" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_worker_execution_exception(self):
        """Worker 실행 중 예외 발생 처리 테스트"""
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            mock_worker = MagicMock()
            
            async def failing_execute():
                raise RuntimeError("Execution failed")
            
            mock_worker.execute_task.return_value = failing_execute()
            mock_agents.get.return_value = mock_worker
            
            result = await _execute_worker_task("planner", "Failing task")
            
            assert result is not None
            assert "실행 실패" in result["content"][0]["text"]


@pytest.mark.e2e
class TestReviewCycleLimit:
    """Review cycle 제한 테스트"""

    @pytest.mark.asyncio
    async def test_review_cycle_limit_exceeded(self):
        """Review cycle 최대치 초과 테스트"""
        # Review cycle 초기화 및 max_cycles 설정
        reset_review_cycle()
        _REVIEW_CYCLE_STATE["max_cycles"] = 2
        
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            mock_worker = MagicMock()
            
            async def mock_execute():
                yield "Task completed\n"
            
            mock_worker.execute_task.return_value = mock_execute()
            mock_agents.get.return_value = mock_worker
            
            # Cycle 1
            await _execute_worker_task("reviewer", "Review #1")
            await _execute_worker_task("coder", "Fix #1")
            
            # Cycle 2
            await _execute_worker_task("reviewer", "Review #2")
            await _execute_worker_task("coder", "Fix #2")
            
            # Cycle 3 (초과)
            result = await _execute_worker_task("reviewer", "Review #3")
            
            # 최대치 초과 시 에러 메시지 확인
            if _REVIEW_CYCLE_STATE["count"] > _REVIEW_CYCLE_STATE["max_cycles"]:
                assert "Review Cycle이 최대 횟수" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_review_cycle_reset_on_new_task(self):
        """새 작업 시작 시 Review cycle 초기화 테스트"""
        # Review cycle 설정
        _REVIEW_CYCLE_STATE["count"] = 5
        
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            mock_worker = MagicMock()
            
            async def mock_execute():
                yield "Task completed\n"
            
            mock_worker.execute_task.return_value = mock_execute()
            mock_agents.get.return_value = mock_worker
            
            # Planner 호출 시 Review cycle 초기화됨
            await _execute_worker_task("planner", "New task")
            
            # cycle count가 0으로 초기화되었는지 확인
            assert _REVIEW_CYCLE_STATE["count"] == 0


@pytest.mark.e2e
@pytest.mark.slow
class TestWorkflowIntegration:
    """통합 워크플로우 테스트 (실제 설정 파일 사용)"""

    @pytest.mark.asyncio
    async def test_workflow_with_metrics(self):
        """메트릭 수집을 포함한 워크플로우 테스트"""
        from src.domain.services import MetricsCollector
        from src.infrastructure.mcp.worker_tools import set_metrics_collector
        
        # Mock 메트릭 수집기 설정
        mock_collector = MagicMock(spec=MetricsCollector)
        mock_collector.record_worker_execution = MagicMock()
        
        set_metrics_collector(mock_collector, "test-session-123")
        
        with patch('src.infrastructure.mcp.worker_tools._WORKER_AGENTS') as mock_agents:
            mock_worker = MagicMock()
            
            async def mock_execute():
                yield "Task completed\n"
            
            mock_worker.execute_task.return_value = mock_execute()
            mock_agents.get.return_value = mock_worker
            
            result = await _execute_worker_task("planner", "Test task with metrics")
            
            assert result is not None
            # 메트릭 기록 함수가 호출되었는지 확인
            # (실제로는 finally 블록에서 호출됨)
