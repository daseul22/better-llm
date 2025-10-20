"""WorkflowUIManager 단위 테스트."""

import pytest
from datetime import datetime, timedelta

from src.presentation.tui.managers.workflow_ui_manager import (
    WorkflowUIManager,
    WorkflowStep,
    WorkflowState,
    StepStatus,
)


class TestWorkflowStep:
    """WorkflowStep 테스트."""

    def test_create_workflow_step(self):
        """워크플로우 단계 생성 테스트."""
        step = WorkflowStep(
            step_id="step-1",
            name="Plan",
            status=StepStatus.PENDING
        )

        assert step.step_id == "step-1"
        assert step.name == "Plan"
        assert step.status == StepStatus.PENDING
        assert step.start_time is None
        assert step.end_time is None
        assert step.error_message is None

    def test_workflow_step_with_times(self):
        """시간 정보가 있는 워크플로우 단계 테스트."""
        start = datetime.now()
        end = start + timedelta(seconds=10)

        step = WorkflowStep(
            step_id="step-2",
            name="Code",
            status=StepStatus.COMPLETED,
            start_time=start,
            end_time=end
        )

        assert step.start_time == start
        assert step.end_time == end

    def test_workflow_step_with_error(self):
        """에러가 있는 워크플로우 단계 테스트."""
        step = WorkflowStep(
            step_id="step-3",
            name="Test",
            status=StepStatus.FAILED,
            error_message="Tests failed"
        )

        assert step.status == StepStatus.FAILED
        assert step.error_message == "Tests failed"

    def test_workflow_step_str(self):
        """워크플로우 단계 문자열 변환 테스트."""
        step = WorkflowStep(
            step_id="step-1",
            name="Plan",
            status=StepStatus.RUNNING
        )

        result = str(step)
        assert "step-1" in result
        assert "Plan" in result
        assert "running" in result


class TestWorkflowState:
    """WorkflowState 테스트."""

    def test_create_workflow_state(self):
        """워크플로우 상태 생성 테스트."""
        steps = [
            WorkflowStep("1", "Plan", StepStatus.PENDING),
            WorkflowStep("2", "Code", StepStatus.PENDING),
        ]

        workflow = WorkflowState(
            workflow_id="wf-001",
            name="Development",
            steps=steps
        )

        assert workflow.workflow_id == "wf-001"
        assert workflow.name == "Development"
        assert len(workflow.steps) == 2
        assert workflow.current_step_index == 0

    def test_workflow_state_with_current_step(self):
        """현재 단계가 지정된 워크플로우 상태 테스트."""
        steps = [
            WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            WorkflowStep("2", "Code", StepStatus.RUNNING),
        ]

        workflow = WorkflowState(
            workflow_id="wf-002",
            name="Dev",
            steps=steps,
            current_step_index=1
        )

        assert workflow.current_step_index == 1

    def test_workflow_state_str(self):
        """워크플로우 상태 문자열 변환 테스트."""
        steps = [WorkflowStep("1", "Plan", StepStatus.PENDING)]
        workflow = WorkflowState("wf-001", "Test", steps)

        result = str(workflow)
        assert "wf-001" in result
        assert "Test" in result
        assert "1 steps" in result


class TestWorkflowUIManager:
    """WorkflowUIManager 테스트."""

    @pytest.fixture
    def manager(self):
        """WorkflowUIManager 픽스처."""
        return WorkflowUIManager()

    @pytest.fixture
    def sample_workflow(self):
        """샘플 워크플로우 픽스처."""
        steps = [
            WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            WorkflowStep("2", "Code", StepStatus.RUNNING),
            WorkflowStep("3", "Test", StepStatus.PENDING),
        ]
        return WorkflowState("wf-001", "Development", steps, current_step_index=1)

    def test_initialization(self, manager):
        """초기화 테스트."""
        assert manager._current_workflow is None
        assert len(manager._workflow_history) == 0
        assert len(manager._step_styles) > 0

    def test_visualize_workflow(self, manager, sample_workflow):
        """워크플로우 시각화 테스트."""
        result = manager.visualize_workflow(sample_workflow)

        assert "Development" in result
        assert "Plan" in result
        assert "Code" in result
        assert "Test" in result
        assert "Progress:" in result

    def test_visualize_workflow_empty_steps(self, manager):
        """단계가 없는 워크플로우 시각화 테스트."""
        workflow = WorkflowState("wf-empty", "Empty", [])
        result = manager.visualize_workflow(workflow)

        assert "Empty" in result
        assert "No steps" in result

    def test_visualize_workflow_with_error(self, manager):
        """에러가 있는 워크플로우 시각화 테스트."""
        steps = [
            WorkflowStep("1", "Plan", StepStatus.FAILED, error_message="Planning failed")
        ]
        workflow = WorkflowState("wf-002", "Dev", steps)

        result = manager.visualize_workflow(workflow)

        assert "Plan" in result
        assert "Planning failed" in result

    def test_calculate_progress_empty(self, manager):
        """빈 워크플로우 진행률 계산 테스트."""
        workflow = WorkflowState("wf-empty", "Empty", [])
        progress = manager._calculate_progress(workflow)

        assert progress == 0.0

    def test_calculate_progress_partial(self, manager):
        """부분 완료 워크플로우 진행률 계산 테스트."""
        steps = [
            WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            WorkflowStep("2", "Code", StepStatus.COMPLETED),
            WorkflowStep("3", "Test", StepStatus.RUNNING),
            WorkflowStep("4", "Deploy", StepStatus.PENDING),
        ]
        workflow = WorkflowState("wf-001", "Dev", steps)

        progress = manager._calculate_progress(workflow)

        # 4개 중 2개 완료 = 50%
        assert progress == 0.5

    def test_calculate_progress_complete(self, manager):
        """완료된 워크플로우 진행률 계산 테스트."""
        steps = [
            WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            WorkflowStep("2", "Code", StepStatus.COMPLETED),
        ]
        workflow = WorkflowState("wf-001", "Dev", steps)

        progress = manager._calculate_progress(workflow)

        assert progress == 1.0

    def test_update_step_status_no_workflow(self, manager):
        """워크플로우가 없을 때 단계 상태 업데이트 테스트."""
        with pytest.raises(ValueError, match="No current workflow"):
            manager.update_step_status("1", StepStatus.RUNNING)

    def test_update_step_status_step_not_found(self, manager, sample_workflow):
        """존재하지 않는 단계 상태 업데이트 테스트."""
        manager.visualize_workflow(sample_workflow)

        with pytest.raises(ValueError, match="not found"):
            manager.update_step_status("nonexistent", StepStatus.RUNNING)

    def test_update_step_status_to_running(self, manager, sample_workflow):
        """단계를 실행 중으로 업데이트 테스트."""
        manager.visualize_workflow(sample_workflow)

        step = manager.get_step_by_id("3")
        assert step.status == StepStatus.PENDING
        assert step.start_time is None

        manager.update_step_status("3", StepStatus.RUNNING)

        assert step.status == StepStatus.RUNNING
        assert step.start_time is not None

    def test_update_step_status_to_completed(self, manager, sample_workflow):
        """단계를 완료로 업데이트 테스트."""
        manager.visualize_workflow(sample_workflow)

        step = manager.get_step_by_id("2")
        assert step.end_time is None

        manager.update_step_status("2", StepStatus.COMPLETED)

        assert step.status == StepStatus.COMPLETED
        assert step.end_time is not None

    def test_update_step_status_with_error_message(self, manager, sample_workflow):
        """에러 메시지와 함께 단계 상태 업데이트 테스트."""
        manager.visualize_workflow(sample_workflow)

        manager.update_step_status("2", StepStatus.FAILED, error_message="Build failed")

        step = manager.get_step_by_id("2")
        assert step.status == StepStatus.FAILED
        assert step.error_message == "Build failed"
        assert step.end_time is not None

    def test_get_workflow_progress(self, manager, sample_workflow):
        """워크플로우 진행률 조회 테스트."""
        manager.visualize_workflow(sample_workflow)

        progress = manager.get_workflow_progress()

        # 3개 중 1개 완료 = 33.33%
        assert 0.33 <= progress <= 0.34

    def test_get_workflow_progress_no_workflow(self, manager):
        """워크플로우가 없을 때 진행률 조회 테스트."""
        progress = manager.get_workflow_progress()
        assert progress == 0.0

    def test_get_current_step(self, manager, sample_workflow):
        """현재 단계 조회 테스트."""
        manager.visualize_workflow(sample_workflow)

        current = manager.get_current_step()

        assert current is not None
        assert current.step_id == "2"
        assert current.name == "Code"

    def test_get_current_step_no_workflow(self, manager):
        """워크플로우가 없을 때 현재 단계 조회 테스트."""
        current = manager.get_current_step()
        assert current is None

    def test_advance_to_next_step(self, manager, sample_workflow):
        """다음 단계로 진행 테스트."""
        manager.visualize_workflow(sample_workflow)

        assert manager._current_workflow.current_step_index == 1

        success = manager.advance_to_next_step()

        assert success is True
        assert manager._current_workflow.current_step_index == 2

    def test_advance_to_next_step_at_last_step(self, manager):
        """마지막 단계에서 다음 단계로 진행 테스트."""
        steps = [WorkflowStep("1", "Only", StepStatus.COMPLETED)]
        workflow = WorkflowState("wf-001", "Dev", steps, current_step_index=0)
        manager.visualize_workflow(workflow)

        success = manager.advance_to_next_step()

        assert success is False
        assert manager._current_workflow.current_step_index == 0

    def test_advance_to_next_step_no_workflow(self, manager):
        """워크플로우가 없을 때 다음 단계로 진행 테스트."""
        success = manager.advance_to_next_step()
        assert success is False

    def test_reset_workflow(self, manager, sample_workflow):
        """워크플로우 리셋 테스트."""
        manager.visualize_workflow(sample_workflow)
        assert manager._current_workflow is not None

        manager.reset_workflow()

        assert manager._current_workflow is None
        assert len(manager._workflow_history) == 1

    def test_get_current_workflow(self, manager, sample_workflow):
        """현재 워크플로우 조회 테스트."""
        assert manager.get_current_workflow() is None

        manager.visualize_workflow(sample_workflow)

        current = manager.get_current_workflow()
        assert current is not None
        assert current.workflow_id == "wf-001"

    def test_get_step_by_id(self, manager, sample_workflow):
        """ID로 단계 조회 테스트."""
        manager.visualize_workflow(sample_workflow)

        step = manager.get_step_by_id("2")

        assert step is not None
        assert step.name == "Code"
        assert step.status == StepStatus.RUNNING

    def test_get_step_by_id_not_found(self, manager, sample_workflow):
        """존재하지 않는 ID로 단계 조회 테스트."""
        manager.visualize_workflow(sample_workflow)

        step = manager.get_step_by_id("nonexistent")
        assert step is None

    def test_get_step_by_id_no_workflow(self, manager):
        """워크플로우가 없을 때 단계 조회 테스트."""
        step = manager.get_step_by_id("1")
        assert step is None

    def test_get_completed_steps(self, manager, sample_workflow):
        """완료된 단계 목록 조회 테스트."""
        manager.visualize_workflow(sample_workflow)

        completed = manager.get_completed_steps()

        assert len(completed) == 1
        assert completed[0].step_id == "1"
        assert completed[0].name == "Plan"

    def test_get_completed_steps_no_workflow(self, manager):
        """워크플로우가 없을 때 완료된 단계 조회 테스트."""
        completed = manager.get_completed_steps()
        assert len(completed) == 0

    def test_get_failed_steps(self, manager):
        """실패한 단계 목록 조회 테스트."""
        steps = [
            WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            WorkflowStep("2", "Code", StepStatus.FAILED),
            WorkflowStep("3", "Test", StepStatus.FAILED),
        ]
        workflow = WorkflowState("wf-001", "Dev", steps)
        manager.visualize_workflow(workflow)

        failed = manager.get_failed_steps()

        assert len(failed) == 2
        assert failed[0].step_id == "2"
        assert failed[1].step_id == "3"

    def test_get_failed_steps_no_workflow(self, manager):
        """워크플로우가 없을 때 실패한 단계 조회 테스트."""
        failed = manager.get_failed_steps()
        assert len(failed) == 0

    def test_is_workflow_complete_all_completed(self, manager):
        """모든 단계가 완료된 워크플로우 테스트."""
        steps = [
            WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            WorkflowStep("2", "Code", StepStatus.COMPLETED),
        ]
        workflow = WorkflowState("wf-001", "Dev", steps)
        manager.visualize_workflow(workflow)

        assert manager.is_workflow_complete() is True

    def test_is_workflow_complete_with_skipped(self, manager):
        """스킵된 단계가 있는 완료된 워크플로우 테스트."""
        steps = [
            WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            WorkflowStep("2", "Code", StepStatus.SKIPPED),
        ]
        workflow = WorkflowState("wf-001", "Dev", steps)
        manager.visualize_workflow(workflow)

        assert manager.is_workflow_complete() is True

    def test_is_workflow_complete_partial(self, manager, sample_workflow):
        """부분 완료된 워크플로우 테스트."""
        manager.visualize_workflow(sample_workflow)

        assert manager.is_workflow_complete() is False

    def test_is_workflow_complete_no_workflow(self, manager):
        """워크플로우가 없을 때 완료 확인 테스트."""
        assert manager.is_workflow_complete() is False

    def test_has_failed_steps_with_failures(self, manager):
        """실패한 단계가 있는 워크플로우 테스트."""
        steps = [
            WorkflowStep("1", "Plan", StepStatus.COMPLETED),
            WorkflowStep("2", "Code", StepStatus.FAILED),
        ]
        workflow = WorkflowState("wf-001", "Dev", steps)
        manager.visualize_workflow(workflow)

        assert manager.has_failed_steps() is True

    def test_has_failed_steps_no_failures(self, manager, sample_workflow):
        """실패한 단계가 없는 워크플로우 테스트."""
        manager.visualize_workflow(sample_workflow)

        assert manager.has_failed_steps() is False

    def test_has_failed_steps_no_workflow(self, manager):
        """워크플로우가 없을 때 실패 확인 테스트."""
        assert manager.has_failed_steps() is False

    def test_get_workflow_summary(self, manager, sample_workflow):
        """워크플로우 요약 조회 테스트."""
        manager.visualize_workflow(sample_workflow)

        summary = manager.get_workflow_summary()

        assert summary["total"] == 3
        assert summary["completed"] == 1
        assert summary["running"] == 1
        assert summary["pending"] == 1
        assert summary["failed"] == 0

    def test_get_workflow_summary_no_workflow(self, manager):
        """워크플로우가 없을 때 요약 조회 테스트."""
        summary = manager.get_workflow_summary()
        assert summary == {}

    def test_set_step_icon(self, manager):
        """단계 아이콘 설정 테스트."""
        manager.set_step_icon(StepStatus.COMPLETED, "✔️")

        assert manager._step_styles[StepStatus.COMPLETED] == "✔️"

    def test_get_workflow_duration(self, manager):
        """워크플로우 실행 시간 조회 테스트."""
        start = datetime(2025, 1, 1, 12, 0, 0)
        end = datetime(2025, 1, 1, 12, 0, 30)

        steps = [
            WorkflowStep("1", "Plan", StepStatus.COMPLETED, start_time=start, end_time=end)
        ]
        workflow = WorkflowState("wf-001", "Dev", steps)
        manager.visualize_workflow(workflow)

        duration = manager.get_workflow_duration()

        assert duration == 30.0

    def test_get_workflow_duration_multiple_steps(self, manager):
        """여러 단계의 워크플로우 실행 시간 조회 테스트."""
        start1 = datetime(2025, 1, 1, 12, 0, 0)
        end1 = datetime(2025, 1, 1, 12, 0, 10)
        start2 = datetime(2025, 1, 1, 12, 0, 15)
        end2 = datetime(2025, 1, 1, 12, 0, 40)

        steps = [
            WorkflowStep("1", "Plan", StepStatus.COMPLETED, start_time=start1, end_time=end1),
            WorkflowStep("2", "Code", StepStatus.COMPLETED, start_time=start2, end_time=end2),
        ]
        workflow = WorkflowState("wf-001", "Dev", steps)
        manager.visualize_workflow(workflow)

        duration = manager.get_workflow_duration()

        # 가장 빨리 시작한 시간(12:00:00)부터 가장 늦게 끝난 시간(12:00:40)까지 = 40초
        assert duration == 40.0

    def test_get_workflow_duration_no_times(self, manager, sample_workflow):
        """시간 정보가 없는 워크플로우 실행 시간 조회 테스트."""
        manager.visualize_workflow(sample_workflow)

        duration = manager.get_workflow_duration()

        assert duration is None

    def test_get_workflow_duration_no_workflow(self, manager):
        """워크플로우가 없을 때 실행 시간 조회 테스트."""
        duration = manager.get_workflow_duration()
        assert duration is None

    def test_get_step_duration(self, manager):
        """단계 실행 시간 조회 테스트."""
        start = datetime(2025, 1, 1, 12, 0, 0)
        end = datetime(2025, 1, 1, 12, 0, 15)

        step = WorkflowStep("1", "Plan", StepStatus.COMPLETED, start_time=start, end_time=end)
        workflow = WorkflowState("wf-001", "Dev", [step])
        manager.visualize_workflow(workflow)

        duration = manager.get_step_duration("1")

        assert duration == 15.0

    def test_get_step_duration_no_times(self, manager, sample_workflow):
        """시간 정보가 없는 단계 실행 시간 조회 테스트."""
        manager.visualize_workflow(sample_workflow)

        duration = manager.get_step_duration("3")

        assert duration is None

    def test_get_step_duration_nonexistent_step(self, manager, sample_workflow):
        """존재하지 않는 단계의 실행 시간 조회 테스트."""
        manager.visualize_workflow(sample_workflow)

        duration = manager.get_step_duration("nonexistent")

        assert duration is None

    def test_workflow_history_tracking(self, manager, sample_workflow):
        """워크플로우 히스토리 추적 테스트."""
        assert len(manager._workflow_history) == 0

        manager.visualize_workflow(sample_workflow)
        manager.reset_workflow()

        assert len(manager._workflow_history) == 1
        assert manager._workflow_history[0].workflow_id == "wf-001"

    def test_multiple_workflows_sequential(self, manager):
        """순차적인 여러 워크플로우 처리 테스트."""
        workflow1 = WorkflowState("wf-001", "First", [WorkflowStep("1", "Plan", StepStatus.COMPLETED)])
        workflow2 = WorkflowState("wf-002", "Second", [WorkflowStep("1", "Plan", StepStatus.PENDING)])

        manager.visualize_workflow(workflow1)
        assert manager.get_current_workflow().workflow_id == "wf-001"

        manager.reset_workflow()
        manager.visualize_workflow(workflow2)
        assert manager.get_current_workflow().workflow_id == "wf-002"

        assert len(manager._workflow_history) == 1
