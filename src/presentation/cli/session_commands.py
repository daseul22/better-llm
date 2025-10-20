"""
세션 관리 CLI 명령어

세션 조회, 검색, 재생, 분석 등의 CLI 명령어를 제공합니다.
"""

import json
import os
import click
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import print as rprint

from application.use_cases import (
    SessionSearchUseCase,
    SessionReplayUseCase,
    SessionAnalyticsUseCase
)
from domain.models import SessionSearchCriteria
from infrastructure.storage.repository_factory import create_session_repository

console = Console()


@click.group(name="session")
def session_commands():
    """세션 관리 명령어"""
    pass


@session_commands.command(name="list")
@click.option("--limit", "-l", default=20, help="최대 표시 개수")
@click.option("--offset", "-o", default=0, help="오프셋")
@click.option("--status", "-s", help="상태 필터 (completed, error, etc.)")
def list_sessions(limit: int, offset: int, status: Optional[str]):
    """
    세션 목록 조회

    저장된 세션들의 목록을 최신순으로 표시합니다.

    Args:
        limit: 최대 표시 개수 (기본값: 20)
        offset: 결과 오프셋 (페이징용)
        status: 상태 필터 (예: completed, error)

    Examples:
        session list
        session list --limit 50
        session list --status completed
    """
    try:
        # 리포지토리 및 Use Case 생성
        repo = create_session_repository()
        use_case = SessionSearchUseCase(repo)

        # 검색 조건 생성
        criteria = SessionSearchCriteria(
            status=status,
            limit=limit,
            offset=offset
        )

        # 세션 조회
        sessions = use_case.execute(criteria)

        if not sessions:
            console.print("[yellow]조회된 세션이 없습니다.[/yellow]")
            return

        # 테이블 생성
        table = Table(title=f"세션 목록 (총 {len(sessions)}건)")
        table.add_column("Session ID", style="cyan", no_wrap=True)
        table.add_column("생성 시각", style="green")
        table.add_column("상태", style="magenta")
        table.add_column("Turns", justify="right")
        table.add_column("사용자 요청", style="white")
        table.add_column("에이전트", style="yellow")

        for session in sessions:
            table.add_row(
                session.session_id[:8],
                session.created_at.strftime("%Y-%m-%d %H:%M"),
                session.status,
                str(session.total_turns),
                session.user_request[:50] + ("..." if len(session.user_request) > 50 else ""),
                ", ".join(session.agents_used[:2]) + ("..." if len(session.agents_used) > 2 else "")
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]세션 조회 실패: {e}[/red]")
        raise click.Abort()


@session_commands.command(name="search")
@click.option("--keyword", "-k", help="검색 키워드")
@click.option("--status", "-s", help="상태 필터")
@click.option("--agent", "-a", help="에이전트 이름 필터")
@click.option("--from", "date_from", help="시작 날짜 (YYYY-MM-DD)")
@click.option("--to", "date_to", help="종료 날짜 (YYYY-MM-DD)")
@click.option("--limit", "-l", default=20, help="최대 표시 개수")
def search_sessions(
    keyword: Optional[str],
    status: Optional[str],
    agent: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    limit: int
):
    """
    세션 검색

    다양한 조건으로 세션을 검색합니다.

    Args:
        keyword: 검색 키워드 (요청 내용, 메시지 내용)
        status: 상태 필터
        agent: 에이전트 이름 필터
        date_from: 시작 날짜 (YYYY-MM-DD)
        date_to: 종료 날짜 (YYYY-MM-DD)
        limit: 최대 결과 수

    Examples:
        session search --keyword "버그"
        session search --status completed --from 2025-01-01
        session search --agent planner
    """
    try:
        # 리포지토리 및 Use Case 생성
        repo = create_session_repository()
        use_case = SessionSearchUseCase(repo)

        # 검색 조건 생성
        criteria = SessionSearchCriteria(
            keyword=keyword,
            status=status,
            agent_name=agent,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )

        # 검색 실행
        sessions = use_case.execute(criteria)

        if not sessions:
            console.print("[yellow]검색 결과가 없습니다.[/yellow]")
            return

        # 테이블 생성
        table = Table(title=f"검색 결과 (총 {len(sessions)}건)")
        table.add_column("Session ID", style="cyan", no_wrap=True)
        table.add_column("생성 시각", style="green")
        table.add_column("상태", style="magenta")
        table.add_column("Turns", justify="right")
        table.add_column("사용자 요청", style="white")
        table.add_column("에이전트", style="yellow")

        for session in sessions:
            table.add_row(
                session.session_id[:8],
                session.created_at.strftime("%Y-%m-%d %H:%M"),
                session.status,
                str(session.total_turns),
                session.user_request[:50] + ("..." if len(session.user_request) > 50 else ""),
                ", ".join(session.agents_used[:2]) + ("..." if len(session.agents_used) > 2 else "")
            )

        console.print(table)

    except ValueError as e:
        console.print(f"[red]입력값 오류: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]검색 실패: {e}[/red]")
        raise click.Abort()


@session_commands.command(name="show")
@click.argument("session_id")
@click.option("--messages/--no-messages", default=True, help="메시지 표시 여부")
def show_session(session_id: str, messages: bool):
    """
    세션 상세 정보 조회

    특정 세션의 상세 정보를 표시합니다.

    Args:
        session_id: 세션 ID
        messages: 메시지 표시 여부 (기본값: True)

    Examples:
        session show abc12345
        session show abc12345 --no-messages
    """
    try:
        # 리포지토리 및 Use Case 생성
        repo = create_session_repository()
        use_case = SessionReplayUseCase(repo)

        # 세션 조회
        detail = use_case.execute(session_id)

        if not detail:
            console.print(f"[red]세션을 찾을 수 없습니다: {session_id}[/red]")
            raise click.Abort()

        # 메타데이터 표시
        metadata = detail.metadata
        info_text = f"""
[cyan]Session ID:[/cyan] {metadata.session_id}
[cyan]사용자 요청:[/cyan] {metadata.user_request}
[cyan]상태:[/cyan] {metadata.status}
[cyan]생성 시각:[/cyan] {metadata.created_at}
[cyan]완료 시각:[/cyan] {metadata.completed_at}
[cyan]총 턴 수:[/cyan] {metadata.total_turns}
[cyan]사용 에이전트:[/cyan] {', '.join(metadata.agents_used)}
"""

        if metadata.files_modified:
            info_text += f"[cyan]수정 파일:[/cyan]\n"
            for file_path in metadata.files_modified:
                info_text += f"  - {file_path}\n"

        if metadata.tests_passed is not None:
            info_text += f"[cyan]테스트 통과:[/cyan] {'✓ Yes' if metadata.tests_passed else '✗ No'}\n"

        if metadata.error_message:
            info_text += f"[cyan]에러 메시지:[/cyan] {metadata.error_message}\n"

        console.print(Panel(info_text.strip(), title="세션 정보", border_style="blue"))

        # 메시지 표시
        if messages and detail.messages:
            console.print("\n[bold]대화 이력[/bold]\n")
            for i, msg in enumerate(detail.messages, 1):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                agent_name = msg.get("agent_name", "")
                timestamp = msg.get("timestamp", "")

                if role == "user":
                    console.print(f"[bold green]👤 사용자[/bold green] ({timestamp})")
                    console.print(Panel(content, border_style="green"))
                elif role == "agent":
                    console.print(f"[bold blue]> {agent_name}[/bold blue] ({timestamp})")
                    console.print(Panel(content, border_style="blue"))
                else:
                    console.print(f"[bold yellow]{role}[/bold yellow] ({timestamp})")
                    console.print(Panel(content, border_style="yellow"))

                console.print()

    except Exception as e:
        console.print(f"[red]세션 조회 실패: {e}[/red]")
        raise click.Abort()


@session_commands.command(name="replay")
@click.argument("session_id")
def replay_session(session_id: str):
    """
    세션 재생

    세션의 전체 대화 내용을 재생합니다.

    Args:
        session_id: 세션 ID

    Examples:
        session replay abc12345
    """
    try:
        # 리포지토리 및 Use Case 생성
        repo = create_session_repository()
        use_case = SessionReplayUseCase(repo)

        # 세션 조회
        detail = use_case.execute(session_id)

        if not detail:
            console.print(f"[red]세션을 찾을 수 없습니다: {session_id}[/red]")
            raise click.Abort()

        # 포맷된 문자열 출력
        formatted = use_case.format_for_display(detail)
        console.print(Panel(formatted, title="세션 재생", border_style="magenta"))

    except Exception as e:
        console.print(f"[red]세션 재생 실패: {e}[/red]")
        raise click.Abort()


@session_commands.command(name="export")
@click.argument("session_id")
@click.option("--output", "-o", help="출력 파일 경로 (기본값: session_<id>.json)")
@click.option("--format", "-f", type=click.Choice(["json", "txt"]), default="json", help="출력 형식")
def export_session(session_id: str, output: Optional[str], format: str):
    """
    세션 내보내기

    세션 데이터를 파일로 내보냅니다.

    Args:
        session_id: 세션 ID
        output: 출력 파일 경로
        format: 출력 형식 (json 또는 txt)

    Examples:
        session export abc12345
        session export abc12345 --format txt
        session export abc12345 --output my_session.json
    """
    try:
        # 리포지토리 및 Use Case 생성
        repo = create_session_repository()
        use_case = SessionReplayUseCase(repo)

        # 세션 조회
        detail = use_case.execute(session_id)

        if not detail:
            console.print(f"[red]세션을 찾을 수 없습니다: {session_id}[/red]")
            raise click.Abort()

        # 출력 파일 경로 결정
        if not output:
            extension = "json" if format == "json" else "txt"
            output = f"session_{session_id[:8]}.{extension}"

        output_path = Path(output)

        # 내보내기
        if format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(detail.to_dict(), f, ensure_ascii=False, indent=2)
        else:  # txt
            formatted = use_case.format_for_display(detail)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted)

        console.print(f"[green]✓ 세션 내보내기 완료: {output_path}[/green]")

    except Exception as e:
        console.print(f"[red]세션 내보내기 실패: {e}[/red]")
        raise click.Abort()


@session_commands.command(name="stats")
@click.option("--days", "-d", default=30, help="조회 기간 (일)")
def show_stats(days: int):
    """
    세션 통계 조회

    지정된 기간 동안의 세션 통계를 표시합니다.

    Args:
        days: 조회 기간 (일 단위, 기본값: 30)

    Examples:
        session stats
        session stats --days 7
        session stats --days 90
    """
    try:
        # 리포지토리 및 Use Case 생성
        repo = create_session_repository()
        use_case = SessionAnalyticsUseCase(repo)

        # 통계 조회
        stats = use_case.get_summary_stats(days=days)

        # 통계 표시
        console.print(Panel(
            f"""
[cyan]조회 기간:[/cyan] 최근 {days}일 ({stats.get('date_from', 'N/A')} ~)

[bold]기본 통계[/bold]
  • 총 세션 수: {stats['total_sessions']}
  • 평균 턴 수: {stats['avg_turns']}
  • 성공률: {stats['success_rate']}%
  • 수정 파일 수: {stats['total_files_modified']}

[bold]상태 분포[/bold]
""".strip(),
            title="세션 통계",
            border_style="cyan"
        ))

        # 상태 분포 테이블
        if stats['status_distribution']:
            status_table = Table()
            status_table.add_column("상태", style="cyan")
            status_table.add_column("건수", justify="right", style="green")

            for status, count in stats['status_distribution'].items():
                status_table.add_row(status, str(count))

            console.print(status_table)

        # 에이전트 사용 빈도
        if stats['agent_usage']:
            console.print("\n[bold]에이전트 사용 빈도 (상위 10)[/bold]")
            agent_table = Table()
            agent_table.add_column("에이전트", style="yellow")
            agent_table.add_column("사용 횟수", justify="right", style="green")

            for agent, count in stats['agent_usage'].items():
                agent_table.add_row(agent, str(count))

            console.print(agent_table)

    except ValueError as e:
        console.print(f"[red]입력값 오류: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]통계 조회 실패: {e}[/red]")
        raise click.Abort()


@session_commands.command(name="agent-stats")
@click.argument("agent_name")
@click.option("--days", "-d", default=30, help="조회 기간 (일)")
def show_agent_stats(agent_name: str, days: int):
    """
    특정 에이전트 성능 분석

    특정 에이전트의 사용 통계 및 성능 지표를 표시합니다.

    Args:
        agent_name: 에이전트 이름
        days: 조회 기간 (일 단위, 기본값: 30)

    Examples:
        session agent-stats planner
        session agent-stats coder --days 7
    """
    try:
        # 리포지토리 및 Use Case 생성
        repo = create_session_repository()
        use_case = SessionAnalyticsUseCase(repo)

        # 에이전트 성능 조회
        performance = use_case.get_agent_performance(agent_name=agent_name, days=days)

        # 성능 표시
        console.print(Panel(
            f"""
[cyan]에이전트:[/cyan] {performance['agent_name']}
[cyan]조회 기간:[/cyan] 최근 {days}일 ({performance.get('date_from', 'N/A')} ~)

[bold]성능 지표[/bold]
  • 총 사용 횟수: {performance['total_uses']}
  • 성공률: {performance['success_rate']}%
  • 평균 턴 수: {performance['avg_turns']}
""".strip(),
            title=f"{agent_name} 성능 분석",
            border_style="yellow"
        ))

        # 상태 분포 테이블
        if performance['status_distribution']:
            console.print("\n[bold]상태 분포[/bold]")
            status_table = Table()
            status_table.add_column("상태", style="cyan")
            status_table.add_column("건수", justify="right", style="green")

            for status, count in performance['status_distribution'].items():
                status_table.add_row(status, str(count))

            console.print(status_table)

    except ValueError as e:
        console.print(f"[red]입력값 오류: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]통계 조회 실패: {e}[/red]")
        raise click.Abort()


@session_commands.command(name="clean")
@click.option("--days", "-d", default=90, help="보존 기간 (일)")
@click.option("--dry-run", "-n", is_flag=True, help="실제 삭제하지 않고 미리보기만")
def clean_metric_files(days: int, dry_run: bool):
    """
    세션 메트릭 파일 정리

    지정된 기간보다 오래된 세션 메트릭 파일 (*_metrics.txt)을 삭제합니다.

    Args:
        days: 보존 기간 (일 단위, 기본값: 90)
        dry_run: True면 삭제하지 않고 미리보기만 표시

    Examples:
        session clean --dry-run
        session clean --days 180
        session clean --days 30
    """
    try:
        sessions_dir = Path("sessions")
        if not sessions_dir.exists():
            console.print("[yellow]sessions 디렉토리가 없습니다.[/yellow]")
            return

        # 메트릭 파일 찾기
        metric_files = list(sessions_dir.glob("*_metrics.txt"))

        if not metric_files:
            console.print("[yellow]삭제할 메트릭 파일이 없습니다.[/yellow]")
            return

        # 오래된 파일 필터링
        cutoff_time = datetime.now() - timedelta(days=days)
        old_files = []

        for file_path in metric_files:
            # 파일 수정 시간 확인
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime < cutoff_time:
                old_files.append((file_path, file_mtime))

        if not old_files:
            console.print(f"[yellow]삭제할 메트릭 파일이 없습니다 ({days}일 이전).[/yellow]")
            return

        # 미리보기
        console.print(f"\n[yellow]삭제 대상: {len(old_files)}개 메트릭 파일 ({days}일 이전)[/yellow]\n")

        table = Table()
        table.add_column("파일명", style="cyan")
        table.add_column("수정 시각", style="green")
        table.add_column("크기 (KB)", style="magenta", justify="right")

        total_size = 0
        for file_path, file_mtime in old_files[:20]:  # 최대 20개만 표시
            file_size = file_path.stat().st_size / 1024  # KB
            total_size += file_size
            table.add_row(
                file_path.name,
                file_mtime.strftime("%Y-%m-%d %H:%M"),
                f"{file_size:.2f}"
            )

        console.print(table)

        if len(old_files) > 20:
            console.print(f"\n... 외 {len(old_files) - 20}건")

        # 총 크기 표시
        console.print(f"\n[cyan]총 크기: {total_size:.2f} KB ({total_size / 1024:.2f} MB)[/cyan]")

        if dry_run:
            console.print("\n[yellow]Dry run 모드: 실제 삭제하지 않았습니다.[/yellow]")
            return

        # 확인
        if not click.confirm(f"\n정말로 {len(old_files)}개 메트릭 파일을 삭제하시겠습니까?"):
            console.print("[yellow]취소되었습니다.[/yellow]")
            return

        # 삭제 실행
        deleted = 0
        deleted_size = 0.0
        for file_path, _ in old_files:
            try:
                file_size = file_path.stat().st_size / 1024  # KB
                file_path.unlink()
                deleted += 1
                deleted_size += file_size
            except Exception as e:
                console.print(f"[red]파일 삭제 실패 ({file_path.name}): {e}[/red]")

        console.print(f"[green]✓ {deleted}개 메트릭 파일 삭제 완료 ({deleted_size:.2f} KB 확보)[/green]")

    except Exception as e:
        console.print(f"[red]메트릭 파일 정리 실패: {e}[/red]")
        raise click.Abort()


@session_commands.command(name="cleanup")
@click.option("--days", "-d", default=90, help="보존 기간 (일)")
@click.option("--dry-run", "-n", is_flag=True, help="실제 삭제하지 않고 미리보기만")
def cleanup_sessions(days: int, dry_run: bool):
    """
    오래된 세션 정리

    지정된 기간보다 오래된 세션을 삭제합니다.

    Args:
        days: 보존 기간 (일 단위, 기본값: 90)
        dry_run: True면 삭제하지 않고 미리보기만 표시

    Examples:
        session cleanup --dry-run
        session cleanup --days 180
        session cleanup --days 30
    """
    try:
        # 리포지토리 생성
        repo = create_session_repository()
        use_case = SessionSearchUseCase(repo)

        # 삭제 대상 조회
        date_to = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        criteria = SessionSearchCriteria(
            date_to=date_to,
            limit=1000
        )

        sessions = use_case.execute(criteria)

        if not sessions:
            console.print(f"[yellow]삭제할 세션이 없습니다 ({days}일 이전).[/yellow]")
            return

        # 미리보기
        console.print(f"\n[yellow]삭제 대상: {len(sessions)}개 세션 ({days}일 이전)[/yellow]\n")

        table = Table()
        table.add_column("Session ID", style="cyan", no_wrap=True)
        table.add_column("생성 시각", style="green")
        table.add_column("상태", style="magenta")

        for session in sessions[:10]:  # 최대 10개만 표시
            table.add_row(
                session.session_id[:8],
                session.created_at.strftime("%Y-%m-%d %H:%M"),
                session.status
            )

        console.print(table)

        if len(sessions) > 10:
            console.print(f"\n... 외 {len(sessions) - 10}건")

        if dry_run:
            console.print("\n[yellow]Dry run 모드: 실제 삭제하지 않았습니다.[/yellow]")
            return

        # 확인
        if not click.confirm(f"\n정말로 {len(sessions)}개 세션을 삭제하시겠습니까?"):
            console.print("[yellow]취소되었습니다.[/yellow]")
            return

        # 삭제 실행
        deleted = 0
        for session in sessions:
            if repo.delete_session(session.session_id):
                deleted += 1

        console.print(f"[green]✓ {deleted}개 세션 삭제 완료[/green]")

    except ValueError as e:
        console.print(f"[red]입력값 오류: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]세션 정리 실패: {e}[/red]")
        raise click.Abort()
