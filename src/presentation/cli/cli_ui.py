"""
CLI UI Components - Rich 라이브러리를 활용한 CLI 출력 개선.

Progress, Tree, Table, Traceback 등의 위젯을 활용하여
사용자에게 친화적인 CLI 인터페이스를 제공합니다.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box


class CLIRenderer:
    """
    CLI 출력 렌더러 - Rich Console 통합.

    GitHub Dark 스타일의 색상 테마를 적용하고, 기존 print()를 대체합니다.

    Attributes:
        console: Rich Console 인스턴스
    """

    # GitHub Dark 스타일 색상 테마
    COLORS = {
        "primary": "#58a6ff",      # 밝은 파랑 (링크, 제목)
        "success": "#3fb950",      # 초록 (성공)
        "warning": "#d29922",      # 노란색 (경고)
        "error": "#f85149",        # 빨강 (에러)
        "info": "#79c0ff",         # 하늘색 (정보)
        "muted": "#8b949e",        # 회색 (비활성)
        "text": "#c9d1d9",         # 기본 텍스트
        "bg": "#0d1117",           # 배경
        "manager": "#d2a8ff",      # 보라 (Manager)
        "planner": "#ffa657",      # 주황 (Planner)
        "coder": "#79c0ff",        # 하늘색 (Coder)
        "reviewer": "#56d364",     # 초록 (Reviewer)
        "tester": "#d2a8ff",       # 보라 (Tester)
    }

    def __init__(self):
        """CLIRenderer 초기화."""
        self.console = Console(highlight=False)

    def print_header(self, title: str, subtitle: Optional[str] = None) -> None:
        """
        헤더 출력 (Rich Panel 사용).

        Args:
            title: 헤더 타이틀
            subtitle: 서브타이틀 (선택)
        """
        content = f"[bold {self.COLORS['primary']}]{title}[/]"
        if subtitle:
            content += f"\n[{self.COLORS['muted']}]{subtitle}[/]"

        panel = Panel(
            content,
            border_style=self.COLORS["primary"],
            box=box.DOUBLE
        )
        self.console.print()
        self.console.print(panel)
        self.console.print()

    def print_task_info(self, task: str, session_id: str, manager: str, tools: List[str]) -> None:
        """
        작업 정보 출력.

        Args:
            task: 작업 설명
            session_id: 세션 ID
            manager: 매니저 이름
            tools: Worker Tool 목록
        """
        self.console.print(f"[{self.COLORS['info']}]📝 작업:[/] {task}")
        self.console.print(f"[{self.COLORS['info']}]🆔 세션:[/] {session_id}")
        self.console.print(f"[{self.COLORS['info']}]👔 매니저:[/] {manager}")
        self.console.print(f"[{self.COLORS['info']}]🛠️  도구:[/] {', '.join(tools)}")
        self.console.print()

    def print_turn_header(self, turn: int, agent_name: str) -> None:
        """
        턴 헤더 출력.

        Args:
            turn: 턴 번호
            agent_name: 에이전트 이름
        """
        emoji = self._get_agent_emoji(agent_name)
        color = self._get_agent_color(agent_name)

        self.console.print()
        self.console.print(
            f"[bold {color}][Turn {turn}] {emoji} {agent_name}[/]",
            style=f"on {self.COLORS['bg']}"
        )
        self.console.print("─" * 60, style=color)

    def print_footer(
        self,
        session_id: str,
        total_turns: int,
        duration: float,
        files_modified: int,
        filepath: Optional[Path] = None
    ) -> None:
        """
        푸터 (작업 완료 요약) 출력.

        Args:
            session_id: 세션 ID
            total_turns: 총 턴 수
            duration: 소요 시간 (초)
            files_modified: 수정된 파일 수
            filepath: 저장된 히스토리 파일 경로
        """
        info = f"""
[{self.COLORS['info']}]세션 ID:[/] {session_id}
[{self.COLORS['info']}]총 턴:[/] {total_turns}
[{self.COLORS['info']}]소요 시간:[/] {duration:.1f}초
[{self.COLORS['info']}]수정된 파일:[/] {files_modified}개
"""
        if filepath:
            info += f"[{self.COLORS['info']}]히스토리:[/] {filepath.name}\n"

        panel = Panel(
            info.strip(),
            title=f"[bold {self.COLORS['success']}]작업 완료[/]",
            border_style=self.COLORS["success"],
            box=box.ROUNDED
        )
        self.console.print()
        self.console.print(panel)
        self.console.print()

    def print_sessions_table(self, sessions: List[Dict[str, Any]], title: str = "세션 목록") -> None:
        """
        세션 목록 테이블 출력.

        Args:
            sessions: 세션 데이터 리스트
            title: 테이블 타이틀
        """
        table = Table(
            title=f"{title} (총 {len(sessions)}건)",
            box=box.ROUNDED,
            title_style=f"bold {self.COLORS['primary']}"
        )

        table.add_column("Session ID", style=self.COLORS["info"], no_wrap=True)
        table.add_column("생성 시간", style=self.COLORS["success"])
        table.add_column("메시지 수", justify="right", style=self.COLORS["warning"])
        table.add_column("상태", style=self.COLORS["primary"])

        for session in sessions:
            table.add_row(
                session.get("session_id", "")[:8],
                session.get("created_at", ""),
                str(session.get("message_count", 0)),
                session.get("status", "unknown")
            )

        self.console.print()
        self.console.print(table)
        self.console.print()

    def _get_agent_emoji(self, agent_name: str) -> str:
        """
        에이전트 이모지 반환.

        Args:
            agent_name: 에이전트 이름

        Returns:
            이모지 문자열
        """
        emoji_map = {
            "planner": "🧠",
            "coder": "💻",
            "reviewer": "🔍",
            "tester": "🧪",
            "manager": "👔",
            "manageragent": "👔",
        }
        return emoji_map.get(agent_name.lower(), "🤖")

    def _get_agent_color(self, agent_name: str) -> str:
        """
        에이전트 색상 반환.

        Args:
            agent_name: 에이전트 이름

        Returns:
            색상 코드
        """
        agent_lower = agent_name.lower()
        for key in self.COLORS:
            if key in agent_lower:
                return self.COLORS[key]
        return self.COLORS["text"]


class ProgressTracker:
    """
    작업 실행 상태 추적 및 표시.

    Rich Progress를 사용하여 작업 진행 상태, Spinner, 완료 체크마크를 표시합니다.

    Attributes:
        progress: Rich Progress 인스턴스
        task_id: 현재 작업 ID
    """

    def __init__(self):
        """ProgressTracker 초기화."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=Console()
        )
        self.task_id: Optional[int] = None

    @contextmanager
    def track(self, description: str, total: Optional[float] = None):
        """
        작업 추적 컨텍스트 매니저.

        Args:
            description: 작업 설명
            total: 총 작업 수 (None이면 무한 스피너)

        Yields:
            task_id: 작업 ID (업데이트용)
        """
        with self.progress:
            task_id = self.progress.add_task(description, total=total)
            self.task_id = task_id
            try:
                yield task_id
            finally:
                self.progress.update(task_id, completed=True)
                self.task_id = None

    def update(self, advance: float = 1.0, description: Optional[str] = None):
        """
        작업 진행 상태 업데이트.

        Args:
            advance: 진행량
            description: 설명 (업데이트할 경우)
        """
        if self.task_id is not None:
            if description:
                self.progress.update(self.task_id, description=description, advance=advance)
            else:
                self.progress.update(self.task_id, advance=advance)

    def complete(self, description: Optional[str] = None):
        """
        작업 완료 표시.

        Args:
            description: 완료 메시지
        """
        if self.task_id is not None:
            final_desc = description or "완료"
            self.progress.update(
                self.task_id,
                description=f"✓ {final_desc}",
                completed=True
            )


class WorkflowTree:
    """
    Worker Tool 호출 내역 시각화 (Tree 위젯).

    Planner → Coder → Reviewer → Tester 흐름을 계층 구조로 표시합니다.

    Attributes:
        tree: Rich Tree 인스턴스
        nodes: 노드 딕셔너리 (에이전트명 → Tree 노드)
    """

    # 색상 매핑
    STATUS_COLORS = {
        "running": "#ffa657",      # 주황 (진행 중)
        "completed": "#3fb950",    # 초록 (완료)
        "failed": "#f85149",       # 빨강 (실패)
        "pending": "#8b949e",      # 회색 (대기)
    }

    def __init__(self, title: str = "Workflow Tree"):
        """
        WorkflowTree 초기화.

        Args:
            title: 트리 타이틀
        """
        self.tree = Tree(
            f"[bold #58a6ff]{title}[/]",
            guide_style="#8b949e"
        )
        self.nodes: Dict[str, Tree] = {}
        self.console = Console()

    def add_worker(
        self,
        worker_name: str,
        status: str = "pending",
        parent: Optional[str] = None
    ) -> None:
        """
        Worker 노드 추가.

        Args:
            worker_name: Worker 이름
            status: 상태 (running, completed, failed, pending)
            parent: 부모 노드 이름 (None이면 루트)
        """
        color = self.STATUS_COLORS.get(status, self.STATUS_COLORS["pending"])
        icon = self._get_status_icon(status)
        emoji = self._get_worker_emoji(worker_name)

        label = f"{icon} [{color}]{emoji} {worker_name}[/]"

        if parent and parent in self.nodes:
            node = self.nodes[parent].add(label)
        else:
            node = self.tree.add(label)

        self.nodes[worker_name] = node

    def update_status(self, worker_name: str, status: str) -> None:
        """
        Worker 상태 업데이트.

        Args:
            worker_name: Worker 이름
            status: 새 상태
        """
        if worker_name in self.nodes:
            color = self.STATUS_COLORS.get(status, self.STATUS_COLORS["pending"])
            icon = self._get_status_icon(status)
            emoji = self._get_worker_emoji(worker_name)

            label = f"{icon} [{color}]{emoji} {worker_name}[/]"
            self.nodes[worker_name].label = label

    def add_detail(self, worker_name: str, detail: str) -> None:
        """
        Worker에 상세 정보 추가.

        Args:
            worker_name: Worker 이름
            detail: 상세 정보
        """
        if worker_name in self.nodes:
            self.nodes[worker_name].add(f"[dim]{detail}[/]")

    def render(self) -> None:
        """트리 렌더링 (콘솔 출력)."""
        self.console.print()
        self.console.print(self.tree)
        self.console.print()

    def _get_status_icon(self, status: str) -> str:
        """
        상태 아이콘 반환.

        Args:
            status: 상태

        Returns:
            아이콘 문자열
        """
        icons = {
            "running": "⏳",
            "completed": "✓",
            "failed": "✗",
            "pending": "○",
        }
        return icons.get(status, "○")

    def _get_worker_emoji(self, worker_name: str) -> str:
        """
        Worker 이모지 반환.

        Args:
            worker_name: Worker 이름

        Returns:
            이모지 문자열
        """
        emoji_map = {
            "planner": "🧠",
            "coder": "💻",
            "reviewer": "🔍",
            "tester": "🧪",
            "manager": "👔",
        }
        for key, emoji in emoji_map.items():
            if key in worker_name.lower():
                return emoji
        return "🛠️"


class ErrorDisplay:
    """
    에러 메시지 표시 (Rich Traceback 스타일).

    에러 타입별 색상 구분, 상세 디버그 정보를 접을 수 있는 형태로 제공합니다.

    Attributes:
        console: Rich Console 인스턴스
    """

    def __init__(self):
        """ErrorDisplay 초기화."""
        self.console = Console()

    def show_error(
        self,
        error_type: str,
        message: str,
        details: Optional[str] = None,
        traceback: Optional[str] = None
    ) -> None:
        """
        에러 메시지 출력.

        Args:
            error_type: 에러 타입 (예: ValueError, RuntimeError)
            message: 에러 메시지
            details: 상세 정보 (선택)
            traceback: 트레이스백 (선택)
        """
        # 에러 타입별 색상
        color = self._get_error_color(error_type)

        content = f"[bold {color}]{error_type}[/]: {message}"

        if details:
            content += f"\n\n[{CLIRenderer.COLORS['muted']}]{details}[/]"

        if traceback:
            content += f"\n\n[dim]Traceback:[/]\n{traceback}"

        panel = Panel(
            content,
            title="[bold red]Error[/]",
            border_style="red",
            box=box.ROUNDED
        )

        self.console.print()
        self.console.print(panel)
        self.console.print()

    def _get_error_color(self, error_type: str) -> str:
        """
        에러 타입별 색상 반환.

        Args:
            error_type: 에러 타입

        Returns:
            색상 코드
        """
        error_colors = {
            "ValueError": "#d29922",      # 노란색
            "RuntimeError": "#f85149",    # 빨강
            "TypeError": "#d2a8ff",       # 보라
            "KeyError": "#ffa657",        # 주황
            "FileNotFoundError": "#f85149", # 빨강
        }
        return error_colors.get(error_type, "#f85149")


# 전역 인스턴스 (싱글톤 패턴)
_renderer: Optional[CLIRenderer] = None
_progress_tracker: Optional[ProgressTracker] = None
_error_display: Optional[ErrorDisplay] = None


def get_renderer() -> CLIRenderer:
    """
    CLIRenderer 싱글톤 인스턴스 반환.

    Returns:
        CLIRenderer 인스턴스
    """
    global _renderer
    if _renderer is None:
        _renderer = CLIRenderer()
    return _renderer


def get_progress_tracker() -> ProgressTracker:
    """
    ProgressTracker 싱글톤 인스턴스 반환.

    Returns:
        ProgressTracker 인스턴스
    """
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker


def get_error_display() -> ErrorDisplay:
    """
    ErrorDisplay 싱글톤 인스턴스 반환.

    Returns:
        ErrorDisplay 인스턴스
    """
    global _error_display
    if _error_display is None:
        _error_display = ErrorDisplay()
    return _error_display
