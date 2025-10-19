#!/usr/bin/env python3
"""
CLI UI 데모 스크립트.

Rich 라이브러리를 활용한 CLI 출력 개선 기능을 시연합니다.
"""

import time
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.presentation.cli.cli_ui import (
    get_renderer,
    get_progress_tracker,
    WorkflowTree,
    get_error_display
)


def demo_header_footer():
    """헤더와 푸터 데모."""
    renderer = get_renderer()

    print("\n" + "="*80)
    print("1. 헤더 & 푸터 데모")
    print("="*80 + "\n")

    # 헤더 출력
    renderer.print_header(
        "Group Chat Orchestration v3.0",
        "Worker Tools Architecture - Session demo1234"
    )

    # 작업 정보 출력
    renderer.print_task_info(
        task="FastAPI로 /users CRUD 엔드포인트 구현해줘",
        session_id="demo1234",
        manager="ManagerAgent (Claude Agent SDK)",
        tools=["execute_planner_task", "execute_coder_task", "execute_tester_task", "read"]
    )

    time.sleep(2)

    # 푸터 출력
    renderer.print_footer(
        session_id="demo1234",
        total_turns=5,
        duration=45.2,
        files_modified=3,
        filepath=Path("session_demo1234_20250118_143022.json")
    )


def demo_progress_tracker():
    """Progress Tracker 데모."""
    print("\n" + "="*80)
    print("2. Progress Tracker 데모")
    print("="*80 + "\n")

    tracker = get_progress_tracker()

    # Progress 바 데모
    with tracker.track("작업 진행 중...", total=10) as task_id:
        for i in range(10):
            time.sleep(0.3)
            tracker.update(advance=1, description=f"작업 진행 중... [{i+1}/10]")
        tracker.complete("작업 완료!")


def demo_workflow_tree():
    """Workflow Tree 데모."""
    renderer = get_renderer()

    print("\n" + "="*80)
    print("3. Workflow Tree 데모")
    print("="*80 + "\n")

    tree = WorkflowTree(title="Worker Tools Workflow")

    # Manager 추가
    renderer.console.print("\n[bold cyan]Step 1:[/] Manager 시작")
    tree.add_worker("Manager", status="running")
    tree.render()
    time.sleep(1)

    # Planner 추가
    renderer.console.print("\n[bold cyan]Step 2:[/] Planner 호출")
    tree.add_worker("Planner", status="running", parent="Manager")
    tree.add_detail("Planner", "요구사항 분석 중...")
    tree.render()
    time.sleep(1)

    # Planner 완료
    renderer.console.print("\n[bold cyan]Step 3:[/] Planner 완료")
    tree.update_status("Planner", status="completed")
    tree.add_detail("Planner", "계획 수립 완료")
    tree.render()
    time.sleep(1)

    # Coder 추가
    renderer.console.print("\n[bold cyan]Step 4:[/] Coder 호출")
    tree.add_worker("Coder", status="running", parent="Planner")
    tree.add_detail("Coder", "코드 작성 중...")
    tree.render()
    time.sleep(1)

    # Coder 완료
    renderer.console.print("\n[bold cyan]Step 5:[/] Coder 완료")
    tree.update_status("Coder", status="completed")
    tree.add_detail("Coder", "3개 파일 수정 완료")
    tree.render()
    time.sleep(1)

    # Reviewer 추가
    renderer.console.print("\n[bold cyan]Step 6:[/] Reviewer 호출")
    tree.add_worker("Reviewer", status="running", parent="Coder")
    tree.add_detail("Reviewer", "코드 리뷰 중...")
    tree.render()
    time.sleep(1)

    # Reviewer 완료
    renderer.console.print("\n[bold cyan]Step 7:[/] Reviewer 완료")
    tree.update_status("Reviewer", status="completed")
    tree.add_detail("Reviewer", "리뷰 통과")
    tree.render()
    time.sleep(1)

    # Tester 추가
    renderer.console.print("\n[bold cyan]Step 8:[/] Tester 호출")
    tree.add_worker("Tester", status="running", parent="Reviewer")
    tree.add_detail("Tester", "테스트 실행 중...")
    tree.render()
    time.sleep(1)

    # Tester 완료
    renderer.console.print("\n[bold cyan]Step 9:[/] Tester 완료")
    tree.update_status("Tester", status="completed")
    tree.add_detail("Tester", "모든 테스트 통과")
    tree.render()
    time.sleep(1)

    # Manager 완료
    renderer.console.print("\n[bold cyan]Step 10:[/] 전체 작업 완료")
    tree.update_status("Manager", status="completed")
    tree.render()


def demo_error_display():
    """Error Display 데모."""
    print("\n" + "="*80)
    print("4. Error Display 데모")
    print("="*80 + "\n")

    error_display = get_error_display()

    # ValueError 예시
    error_display.show_error(
        error_type="ValueError",
        message="입력값이 유효하지 않습니다",
        details="사용자 요청이 빈 문자열입니다"
    )

    time.sleep(2)

    # RuntimeError 예시
    error_display.show_error(
        error_type="RuntimeError",
        message="Worker Tool 실행 중 오류가 발생했습니다",
        details="execute_coder_task 실행 실패",
        traceback=(
            "Traceback (most recent call last):\n"
            "  File \"orchestrator.py\", line 145, in run\n"
            "    result = await worker_tool.execute()\n"
            "RuntimeError: Worker Tool execution failed"
        )
    )


def demo_turn_header():
    """턴 헤더 데모."""
    renderer = get_renderer()

    print("\n" + "="*80)
    print("5. 턴 헤더 데모")
    print("="*80 + "\n")

    for turn in range(1, 4):
        renderer.print_turn_header(turn, "ManagerAgent")
        renderer.console.print(
            f"Manager: Worker Tool을 호출하여 작업을 수행합니다... (턴 {turn})"
        )
        renderer.console.print()
        time.sleep(1)


def main():
    """메인 함수."""
    renderer = get_renderer()

    renderer.console.print(
        "\n[bold magenta]CLI UI 개선 기능 데모[/]\n",
        style="on black"
    )
    renderer.console.print(
        "[dim]Rich 라이브러리를 활용한 CLI 출력 개선 기능을 시연합니다.[/]\n"
    )

    try:
        # 1. 헤더 & 푸터
        demo_header_footer()
        time.sleep(1)

        # 2. Progress Tracker
        demo_progress_tracker()
        time.sleep(1)

        # 3. Workflow Tree
        demo_workflow_tree()
        time.sleep(1)

        # 4. Error Display
        demo_error_display()
        time.sleep(1)

        # 5. 턴 헤더
        demo_turn_header()

        # 완료 메시지
        renderer.console.print(
            "\n\n[bold green]✓ 모든 데모 완료![/]\n",
            style="on black"
        )
        renderer.console.print(
            "[dim]자세한 내용은 docs/CLI_OUTPUT_IMPROVEMENTS.md를 참고하세요.[/]\n"
        )

    except KeyboardInterrupt:
        renderer.console.print(
            "\n[yellow]⚠ 데모가 중단되었습니다.[/]\n"
        )
    except Exception as e:
        error_display = get_error_display()
        error_display.show_error(
            error_type=type(e).__name__,
            message=str(e)
        )


if __name__ == "__main__":
    main()
