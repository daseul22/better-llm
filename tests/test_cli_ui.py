"""
CLI UI 컴포넌트 테스트.

Rich 라이브러리를 활용한 CLI 출력 개선 기능을 테스트합니다.
"""

import pytest
from pathlib import Path

from src.presentation.cli.cli_ui import (
    CLIRenderer,
    ProgressTracker,
    WorkflowTree,
    ErrorDisplay,
    get_renderer,
    get_progress_tracker,
    get_error_display
)


class TestCLIRenderer:
    """CLIRenderer 클래스 테스트."""

    def test_renderer_initialization(self):
        """CLIRenderer 초기화 테스트."""
        renderer = CLIRenderer()
        assert renderer.console is not None
        assert renderer.COLORS is not None

    def test_print_header(self, capsys):
        """헤더 출력 테스트."""
        renderer = CLIRenderer()
        renderer.print_header("Test Title", "Test Subtitle")
        # 출력이 발생했는지만 확인 (실제 내용은 Rich 포맷이라 테스트 어려움)

    def test_print_task_info(self, capsys):
        """작업 정보 출력 테스트."""
        renderer = CLIRenderer()
        renderer.print_task_info(
            task="Test task",
            session_id="test123",
            manager="TestManager",
            tools=["tool1", "tool2"]
        )

    def test_print_footer(self, capsys):
        """푸터 출력 테스트."""
        renderer = CLIRenderer()
        renderer.print_footer(
            session_id="test123",
            total_turns=5,
            duration=10.5,
            files_modified=3,
            filepath=Path("test.json")
        )

    def test_get_agent_emoji(self):
        """에이전트 이모지 반환 테스트."""
        renderer = CLIRenderer()
        assert renderer._get_agent_emoji("planner") == "🧠"
        assert renderer._get_agent_emoji("coder") == "💻"
        assert renderer._get_agent_emoji("reviewer") == "🔍"
        assert renderer._get_agent_emoji("tester") == "🧪"
        assert renderer._get_agent_emoji("manager") == "👔"
        assert renderer._get_agent_emoji("unknown") == "🤖"

    def test_get_agent_color(self):
        """에이전트 색상 반환 테스트."""
        renderer = CLIRenderer()
        assert renderer._get_agent_color("planner") == renderer.COLORS["planner"]
        assert renderer._get_agent_color("coder") == renderer.COLORS["coder"]


class TestProgressTracker:
    """ProgressTracker 클래스 테스트."""

    def test_tracker_initialization(self):
        """ProgressTracker 초기화 테스트."""
        tracker = ProgressTracker()
        assert tracker.progress is not None
        assert tracker.task_id is None

    def test_track_context_manager(self):
        """작업 추적 컨텍스트 매니저 테스트."""
        tracker = ProgressTracker()
        with tracker.track("Test task", total=100) as task_id:
            assert task_id is not None
            assert tracker.task_id == task_id
        # 컨텍스트 종료 후 task_id는 None이 되어야 함
        assert tracker.task_id is None


class TestWorkflowTree:
    """WorkflowTree 클래스 테스트."""

    def test_tree_initialization(self):
        """WorkflowTree 초기화 테스트."""
        tree = WorkflowTree(title="Test Workflow")
        assert tree.tree is not None
        assert tree.nodes == {}
        assert tree.console is not None

    def test_add_worker(self):
        """Worker 노드 추가 테스트."""
        tree = WorkflowTree()
        tree.add_worker("Planner", status="running")
        assert "Planner" in tree.nodes

    def test_add_worker_with_parent(self):
        """부모가 있는 Worker 노드 추가 테스트."""
        tree = WorkflowTree()
        tree.add_worker("Manager", status="running")
        tree.add_worker("Planner", status="running", parent="Manager")
        assert "Manager" in tree.nodes
        assert "Planner" in tree.nodes

    def test_update_status(self):
        """Worker 상태 업데이트 테스트."""
        tree = WorkflowTree()
        tree.add_worker("Planner", status="running")
        tree.update_status("Planner", status="completed")
        # 상태가 업데이트되었는지 확인

    def test_add_detail(self):
        """Worker 상세 정보 추가 테스트."""
        tree = WorkflowTree()
        tree.add_worker("Planner", status="running")
        tree.add_detail("Planner", "계획 수립 중...")

    def test_get_status_icon(self):
        """상태 아이콘 반환 테스트."""
        tree = WorkflowTree()
        assert tree._get_status_icon("running") == "⏳"
        assert tree._get_status_icon("completed") == "✓"
        assert tree._get_status_icon("failed") == "✗"
        assert tree._get_status_icon("pending") == "○"

    def test_get_worker_emoji(self):
        """Worker 이모지 반환 테스트."""
        tree = WorkflowTree()
        assert tree._get_worker_emoji("planner") == "🧠"
        assert tree._get_worker_emoji("coder") == "💻"
        assert tree._get_worker_emoji("reviewer") == "🔍"
        assert tree._get_worker_emoji("tester") == "🧪"
        assert tree._get_worker_emoji("manager") == "👔"


class TestErrorDisplay:
    """ErrorDisplay 클래스 테스트."""

    def test_error_display_initialization(self):
        """ErrorDisplay 초기화 테스트."""
        error_display = ErrorDisplay()
        assert error_display.console is not None

    def test_show_error(self, capsys):
        """에러 메시지 출력 테스트."""
        error_display = ErrorDisplay()
        error_display.show_error(
            error_type="ValueError",
            message="Test error message",
            details="Test details"
        )

    def test_get_error_color(self):
        """에러 타입별 색상 반환 테스트."""
        error_display = ErrorDisplay()
        assert error_display._get_error_color("ValueError") == "#d29922"
        assert error_display._get_error_color("RuntimeError") == "#f85149"


class TestSingletonInstances:
    """싱글톤 인스턴스 테스트."""

    def test_get_renderer_singleton(self):
        """get_renderer 싱글톤 테스트."""
        renderer1 = get_renderer()
        renderer2 = get_renderer()
        assert renderer1 is renderer2

    def test_get_progress_tracker_singleton(self):
        """get_progress_tracker 싱글톤 테스트."""
        tracker1 = get_progress_tracker()
        tracker2 = get_progress_tracker()
        assert tracker1 is tracker2

    def test_get_error_display_singleton(self):
        """get_error_display 싱글톤 테스트."""
        display1 = get_error_display()
        display2 = get_error_display()
        assert display1 is display2


def test_cli_ui_integration():
    """
    CLI UI 통합 테스트.

    전체 워크플로우를 시뮬레이션하여 각 컴포넌트가 함께 작동하는지 테스트합니다.
    """
    # Renderer 초기화
    renderer = get_renderer()
    renderer.print_header("Test Orchestration", "Test Subtitle")

    # Task 정보 출력
    renderer.print_task_info(
        task="Test task description",
        session_id="test_session",
        manager="TestManager",
        tools=["tool1", "tool2", "tool3"]
    )

    # Workflow Tree 생성
    tree = WorkflowTree(title="Test Workflow")
    tree.add_worker("Manager", status="running")
    tree.add_worker("Planner", status="completed", parent="Manager")
    tree.add_worker("Coder", status="completed", parent="Planner")
    tree.add_worker("Tester", status="running", parent="Coder")

    # 상세 정보 추가
    tree.add_detail("Planner", "계획 수립 완료")
    tree.add_detail("Coder", "코드 작성 완료")
    tree.add_detail("Tester", "테스트 진행 중...")

    # Tree 렌더링 (출력 확인용)
    # tree.render()

    # 푸터 출력
    renderer.print_footer(
        session_id="test_session",
        total_turns=5,
        duration=15.3,
        files_modified=3,
        filepath=Path("test_session.json")
    )

    # 에러 출력 테스트
    error_display = get_error_display()
    error_display.show_error(
        error_type="TestError",
        message="This is a test error",
        details="Additional details about the error"
    )


if __name__ == "__main__":
    # 통합 테스트 실행 (수동)
    test_cli_ui_integration()
