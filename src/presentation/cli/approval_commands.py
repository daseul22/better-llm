"""
승인 관리 CLI 커맨드

approval list: 대기 중인 승인 목록 조회
approval history: 승인 이력 조회
approval respond: 승인 응답
"""

import click
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime
from typing import Optional

from ...application.use_cases import (
    GetPendingApprovalsUseCase,
    ApprovalHistoryUseCase,
    ProcessApprovalResponseUseCase
)
from ...domain.models.approval import ApprovalStatus, ApprovalType
from ...infrastructure.storage import create_approval_repository

console = Console()
logger = logging.getLogger(__name__)

# 상수
MAX_TASK_DESC_DISPLAY_LENGTH = 37


def get_approval_type_display(approval_type: ApprovalType) -> str:
    """
    승인 타입을 한글로 변환

    Args:
        approval_type: 승인 타입 Enum

    Returns:
        한글 승인 타입 문자열
    """
    type_map = {
        ApprovalType.BEFORE_CODE_WRITE: "코드 작성 전",
        ApprovalType.AFTER_CODE_WRITE: "코드 작성 후",
        ApprovalType.BEFORE_TEST_RUN: "테스트 실행 전",
        ApprovalType.BEFORE_DEPLOYMENT: "배포 전"
    }
    return type_map.get(approval_type, approval_type.value)


def get_status_color(status: ApprovalStatus) -> str:
    """
    승인 상태에 따른 색상 반환

    Args:
        status: 승인 상태 Enum

    Returns:
        Rich 라이브러리 색상 문자열
    """
    color_map = {
        ApprovalStatus.PENDING: "yellow",
        ApprovalStatus.APPROVED: "green",
        ApprovalStatus.REJECTED: "red",
        ApprovalStatus.MODIFIED: "blue"
    }
    return color_map.get(status, "white")


@click.group(name="approval")
def approval_cli():
    """승인 관리 커맨드"""
    pass


@approval_cli.command(name="list")
@click.option(
    "--session",
    "-s",
    type=str,
    help="세션 ID로 필터링 (선택적)"
)
def list_pending_approvals(session: Optional[str]):
    """
    대기 중인 승인 요청 목록 조회

    Examples:
        better-llm approval list
        better-llm approval list --session session_20250119_123456
    """
    try:
        # 리포지토리 및 Use Case 생성
        approval_repo = create_approval_repository()
        use_case = GetPendingApprovalsUseCase(approval_repo)

        # 대기 중인 승인 목록 조회
        pending_approvals = use_case.execute(session_id=session)

        if not pending_approvals:
            console.print("[yellow]대기 중인 승인 요청이 없습니다.[/yellow]")
            return

        # 테이블 생성
        table = Table(title=f"대기 중인 승인 요청 ({len(pending_approvals)}건)")
        table.add_column("ID", style="cyan", justify="right", width=6)
        table.add_column("세션 ID", style="magenta", width=25)
        table.add_column("타입", style="green", width=20)
        table.add_column("작업 설명", style="white", width=40)
        table.add_column("생성 시각", style="blue", width=20)

        for approval in pending_approvals:
            # 타입 한글 변환 (유틸리티 함수 사용)
            type_text = get_approval_type_display(approval.approval_type)

            # 작업 설명 길이 제한
            task_desc = approval.task_description
            if len(task_desc) > MAX_TASK_DESC_DISPLAY_LENGTH:
                task_desc = task_desc[:MAX_TASK_DESC_DISPLAY_LENGTH] + "..."

            table.add_row(
                str(approval.id),
                approval.session_id,
                type_text,
                task_desc,
                approval.created_at.strftime("%Y-%m-%d %H:%M:%S")
            )

        console.print(table)

        # 응답 방법 안내
        console.print("\n[dim]응답 방법:[/dim]")
        console.print("  better-llm approval respond <ID> --action approve|reject|modify [--feedback \"내용\"]")

    except Exception as e:
        logger.error(f"승인 목록 조회 실패: {e}")
        console.print(f"[red]에러: {e}[/red]")


@approval_cli.command(name="history")
@click.option(
    "--session",
    "-s",
    type=str,
    required=True,
    help="세션 ID"
)
def show_approval_history(session: str):
    """
    세션별 승인 이력 조회

    Examples:
        better-llm approval history --session session_20250119_123456
    """
    try:
        # 리포지토리 및 Use Case 생성
        approval_repo = create_approval_repository()
        use_case = ApprovalHistoryUseCase(approval_repo)

        # 승인 이력 조회
        history = use_case.execute(session_id=session)

        if not history:
            console.print(f"[yellow]세션 '{session}'의 승인 이력이 없습니다.[/yellow]")
            return

        # 이력 출력
        console.print(f"\n[bold cyan]세션 승인 이력: {session}[/bold cyan]\n")

        for approval, feedbacks in history:
            # 상태 색상 (유틸리티 함수 사용)
            status_color = get_status_color(approval.status)

            # 타입 한글 변환 (유틸리티 함수 사용)
            type_text = get_approval_type_display(approval.approval_type)

            # 승인 정보 패널
            content = f"""
[bold]ID:[/bold] {approval.id}
[bold]타입:[/bold] {type_text}
[bold]상태:[/bold] [{status_color}]{approval.status.value}[/{status_color}]
[bold]작업 설명:[/bold] {approval.task_description}
[bold]생성 시각:[/bold] {approval.created_at.strftime("%Y-%m-%d %H:%M:%S")}
"""
            if approval.responded_at:
                content += f"[bold]응답 시각:[/bold] {approval.responded_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

            # 피드백이 있으면 표시
            if feedbacks:
                content += "\n[bold]피드백:[/bold]\n"
                for fb in feedbacks:
                    content += f"  - {fb.feedback_content}\n"

            panel = Panel(
                content.strip(),
                title=f"승인 요청 #{approval.id}",
                border_style=status_color
            )
            console.print(panel)
            console.print()

    except ValueError as e:
        console.print(f"[red]에러: {e}[/red]")
    except Exception as e:
        logger.error(f"승인 이력 조회 실패: {e}")
        console.print(f"[red]에러: {e}[/red]")


@approval_cli.command(name="respond")
@click.argument("approval_id", type=int)
@click.option(
    "--action",
    "-a",
    type=click.Choice(["approve", "reject", "modify"], case_sensitive=False),
    required=True,
    help="승인 액션 (approve, reject, modify)"
)
@click.option(
    "--feedback",
    "-f",
    type=str,
    help="피드백 내용 (선택적)"
)
def respond_to_approval(approval_id: int, action: str, feedback: Optional[str]):
    """
    승인 요청에 응답

    Examples:
        better-llm approval respond 1 --action approve
        better-llm approval respond 2 --action reject --feedback "요구사항 불충분"
        better-llm approval respond 3 --action modify --feedback "변수명을 더 명확하게 수정"
    """
    try:
        # 액션을 ApprovalStatus로 변환
        action_map = {
            "approve": ApprovalStatus.APPROVED,
            "reject": ApprovalStatus.REJECTED,
            "modify": ApprovalStatus.MODIFIED
        }
        status = action_map[action.lower()]

        # 리포지토리 및 Use Case 생성
        approval_repo = create_approval_repository()
        use_case = ProcessApprovalResponseUseCase(approval_repo)

        # 승인 응답 처리
        console.print(f"[cyan]승인 요청 #{approval_id} 처리 중...[/cyan]")
        updated_approval, created_feedback = use_case.execute(
            approval_id=approval_id,
            status=status,
            feedback_content=feedback
        )

        # 결과 출력 (유틸리티 함수 사용)
        status_color = get_status_color(status)

        console.print(f"\n[{status_color}]✓ 승인 요청이 처리되었습니다.[/{status_color}]\n")

        # 상세 정보 패널
        content = f"""
[bold]승인 ID:[/bold] {updated_approval.id}
[bold]세션 ID:[/bold] {updated_approval.session_id}
[bold]상태:[/bold] [{status_color}]{updated_approval.status.value}[/{status_color}]
[bold]작업 설명:[/bold] {updated_approval.task_description}
[bold]응답 시각:[/bold] {updated_approval.responded_at.strftime("%Y-%m-%d %H:%M:%S")}
"""

        if created_feedback:
            content += f"\n[bold]피드백:[/bold]\n{created_feedback.feedback_content}"

        panel = Panel(content.strip(), title="처리 결과", border_style=status_color)
        console.print(panel)

    except ValueError as e:
        console.print(f"[red]에러: {e}[/red]")
    except Exception as e:
        logger.error(f"승인 응답 처리 실패: {e}")
        console.print(f"[red]에러: {e}[/red]")


# CLI 엔트리 포인트
if __name__ == "__main__":
    approval_cli()
