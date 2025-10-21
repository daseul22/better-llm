"""
워크플로우 비주얼라이저 위젯

Worker Tool 호출 흐름을 Tree 형태로 실시간 시각화
"""

import time
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, field

from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode
from rich.text import Text


class WorkerStatus(Enum):
    """Worker 실행 상태"""
    PENDING = "pending"  # 대기 중
    RUNNING = "running"  # 진행 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"  # 실패


@dataclass
class WorkflowNode:
    """
    워크플로우 노드 데이터 클래스

    Attributes:
        worker_name: Worker 이름 (planner, coder, reviewer, tester)
        status: 현재 상태
        start_time: 시작 시간 (Unix timestamp)
        end_time: 종료 시간 (Unix timestamp)
        error_message: 에러 메시지 (실패 시)
    """
    worker_name: str
    status: WorkerStatus = WorkerStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None

    def get_duration(self) -> float:
        """
        소요 시간 계산 (초 단위)

        Returns:
            소요 시간 (초). 아직 종료되지 않았으면 현재까지 경과 시간 반환.
        """
        if self.start_time is None:
            return 0.0

        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    def format_duration(self) -> str:
        """
        소요 시간을 읽기 좋은 형식으로 포맷

        Returns:
            포맷된 시간 문자열 (예: "2.5s", "1m 30s")
        """
        duration = self.get_duration()

        if duration < 60:
            return f"{duration:.1f}s"
        else:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            return f"{minutes}m {seconds}s"


class WorkflowVisualizer(ScrollableContainer):
    """
    워크플로우 비주얼라이저 위젯

    Worker Tool 호출 흐름을 Tree 형태로 실시간 시각화합니다.

    Features:
        - Tree 형태로 워크플로우 표시
        - Manager → Planner → Coder → Reviewer → Tester 흐름
        - 각 Worker의 상태 실시간 업데이트
        - 소요 시간 표시
        - 상태별 아이콘 및 색상

    Attributes:
        workflow_tree: Tree 위젯
        nodes: Worker 이름 → WorkflowNode 매핑
        tree_nodes: Worker 이름 → TreeNode 매핑
    """

    # 상태별 아이콘 및 스타일
    STATUS_ICONS = {
        WorkerStatus.PENDING: ("⏸", "dim"),
        WorkerStatus.RUNNING: ("⚙️", "yellow"),
        WorkerStatus.COMPLETED: ("✅", "green"),
        WorkerStatus.FAILED: ("❌", "red"),
    }

    # Worker별 이모지
    WORKER_EMOJIS = {
        "manager": "🤖",
        "planner": "🧠",
        "coder": "💻",
        "reviewer": "🔍",
        "tester": "🧪",
        "committer": "📝",
    }

    def __init__(self, **kwargs):
        """
        WorkflowVisualizer 초기화

        Args:
            **kwargs: 부모 클래스에 전달할 키워드 인자
        """
        super().__init__(**kwargs)
        self.nodes: Dict[str, WorkflowNode] = {}
        self.tree_nodes: Dict[str, TreeNode] = {}
        self.workflow_tree: Optional[Tree] = None
        self.root_node: Optional[TreeNode] = None

    def compose(self) -> ComposeResult:
        """UI 구성"""
        # Tree 위젯 생성
        tree = Tree("🔄 Workflow")
        tree.show_root = True
        tree.show_guides = True
        self.workflow_tree = tree
        self.root_node = tree.root

        yield tree

    def on_mount(self) -> None:
        """마운트 시 초기화"""
        # 기본 노드들 생성 (비활성 상태)
        self._create_initial_tree()

    def _create_initial_tree(self) -> None:
        """
        초기 트리 구조 생성

        Manager 노드를 루트에 추가하고, 나머지 Worker 노드들을 준비합니다.
        """
        if not self.workflow_tree or not self.root_node:
            return

        # 루트 노드 레이블 업데이트
        self.root_node.set_label(Text("🔄 Workflow (대기 중)", style="bold"))

    def add_worker(self, worker_name: str) -> None:
        """
        새로운 Worker 노드 추가

        Args:
            worker_name: Worker 이름 (소문자, 예: "planner", "coder")
        """
        if worker_name in self.nodes:
            # 이미 존재하면 무시
            return

        # WorkflowNode 생성
        node = WorkflowNode(worker_name=worker_name)
        self.nodes[worker_name] = node

        # TreeNode 생성
        if self.root_node:
            label = self._generate_node_label(node)
            tree_node = self.root_node.add(label, expand=True)
            self.tree_nodes[worker_name] = tree_node

    def update_worker_status(
        self,
        worker_name: str,
        status: str,  # 문자열로 받아서 WorkerStatus Enum으로 변환
        error_message: Optional[str] = None
    ) -> None:
        """
        Worker 상태 업데이트

        Args:
            worker_name: Worker 이름
            status: 새로운 상태 (문자열: "running", "completed", "failed")
            error_message: 에러 메시지 (FAILED 상태일 때만)
        """
        # 문자열을 WorkerStatus Enum으로 변환
        try:
            status_enum = WorkerStatus(status.lower())
        except ValueError:
            # 알 수 없는 상태는 PENDING으로 처리
            status_enum = WorkerStatus.PENDING

        # 노드가 없으면 추가
        if worker_name not in self.nodes:
            self.add_worker(worker_name)

        node = self.nodes[worker_name]
        old_status = node.status
        node.status = status_enum

        # 시간 기록
        if status_enum == WorkerStatus.RUNNING and old_status != WorkerStatus.RUNNING:
            node.start_time = time.time()
        elif status_enum in (WorkerStatus.COMPLETED, WorkerStatus.FAILED):
            node.end_time = time.time()

        # 에러 메시지 저장
        if status_enum == WorkerStatus.FAILED and error_message:
            node.error_message = error_message

        # TreeNode 레이블 업데이트
        self._update_tree_node(worker_name)

        # 루트 노드 레이블 업데이트
        self._update_root_label()

    def _generate_node_label(self, node: WorkflowNode) -> Text:
        """
        노드 레이블 생성

        Args:
            node: WorkflowNode 인스턴스

        Returns:
            Rich Text 객체
        """
        # 아이콘 및 스타일
        icon, style = self.STATUS_ICONS[node.status]

        # Worker 이모지
        worker_emoji = self.WORKER_EMOJIS.get(node.worker_name.lower(), "🔧")

        # 레이블 텍스트 생성
        label = Text()
        label.append(f"{icon} ", style=style)
        label.append(f"{worker_emoji} ", style="bold")
        label.append(f"{node.worker_name.upper()}", style=f"bold {style}")

        # 소요 시간 추가 (진행 중 또는 완료/실패 시)
        if node.status in (WorkerStatus.RUNNING, WorkerStatus.COMPLETED, WorkerStatus.FAILED):
            duration_str = node.format_duration()
            label.append(f" ({duration_str})", style="dim")

        # 에러 메시지 추가 (실패 시)
        if node.status == WorkerStatus.FAILED and node.error_message:
            label.append(f"\n  ↳ {node.error_message}", style="red dim")

        return label

    def _update_tree_node(self, worker_name: str) -> None:
        """
        TreeNode 레이블 업데이트

        Args:
            worker_name: Worker 이름
        """
        if worker_name not in self.tree_nodes or worker_name not in self.nodes:
            return

        tree_node = self.tree_nodes[worker_name]
        node = self.nodes[worker_name]

        # 레이블 업데이트
        label = self._generate_node_label(node)
        tree_node.set_label(label)

    def _update_root_label(self) -> None:
        """루트 노드 레이블 업데이트 (전체 진행 상태 반영)"""
        if not self.root_node:
            return

        # 전체 상태 계산
        total_workers = len(self.nodes)
        if total_workers == 0:
            self.root_node.set_label(Text("🔄 Workflow (대기 중)", style="bold"))
            return

        completed = sum(1 for n in self.nodes.values() if n.status == WorkerStatus.COMPLETED)
        failed = sum(1 for n in self.nodes.values() if n.status == WorkerStatus.FAILED)
        running = sum(1 for n in self.nodes.values() if n.status == WorkerStatus.RUNNING)

        # 레이블 생성
        label = Text()

        if failed > 0:
            label.append("❌ Workflow (실패)", style="bold red")
        elif running > 0:
            label.append("⚙️ Workflow (진행 중)", style="bold yellow")
        elif completed == total_workers:
            label.append("✅ Workflow (완료)", style="bold green")
        else:
            label.append("🔄 Workflow (진행 중)", style="bold")

        # 진행률 추가
        label.append(f" [{completed}/{total_workers}]", style="dim")

        self.root_node.set_label(label)

    def update_worker_time(self, worker_name: str) -> None:
        """
        Worker 실행 시간 업데이트 (진행 중인 Worker만)

        Args:
            worker_name: Worker 이름
        """
        if worker_name not in self.nodes:
            return

        node = self.nodes[worker_name]
        if node.status == WorkerStatus.RUNNING:
            self._update_tree_node(worker_name)

    def get_running_workers(self) -> list[tuple[str, float]]:
        """
        현재 실행 중인 워커 목록 반환

        Returns:
            (워커 이름, 실행 시간) 튜플 리스트
        """
        running = []
        for worker_name, node in self.nodes.items():
            if node.status == WorkerStatus.RUNNING:
                running.append((worker_name, node.get_duration()))
        return running

    def has_running_workers(self) -> bool:
        """
        실행 중인 워커가 있는지 확인

        Returns:
            실행 중인 워커가 있으면 True, 없으면 False
        """
        return any(node.status == WorkerStatus.RUNNING for node in self.nodes.values())

    def clear_workflow(self) -> None:
        """워크플로우 초기화"""
        self.nodes.clear()
        self.tree_nodes.clear()

        if self.workflow_tree and self.root_node:
            # 기존 자식 노드 제거
            self.root_node.remove_children()
            # 루트 레이블 리셋
            self.root_node.set_label(Text("🔄 Workflow (대기 중)", style="bold"))
