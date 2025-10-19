# CLI 출력 개선 문서

## 개요

Rich 라이브러리를 활용하여 CLI 출력을 개선했습니다. GitHub Dark 스타일의 색상 테마를 적용하고, Progress, Tree, Table, Panel 등의 위젯을 통해 사용자 친화적인 인터페이스를 제공합니다.

## 주요 기능

### 1. Rich Console 통합

- **CLIRenderer**: 전역 Console 인스턴스 관리
- **색상 테마**: GitHub Dark 스타일 적용
- **기존 print() 대체**: console.print()로 전환

```python
from src.presentation.cli.cli_ui import get_renderer

renderer = get_renderer()
renderer.print_header("Title", "Subtitle")
```

### 2. 작업 실행 상태 표시

**ProgressTracker** 클래스를 통해 작업 진행 상태를 실시간으로 표시합니다.

- **Progress 바**: 작업 진행률 시각화
- **Spinner**: 응답 대기 중 애니메이션
- **완료 체크마크**: 작업 완료 시 ✓ 표시

```python
from src.presentation.cli.cli_ui import get_progress_tracker

tracker = get_progress_tracker()
with tracker.track("작업 수행 중...", total=100) as task_id:
    # 작업 수행
    tracker.update(advance=10)
```

### 3. Worker Tool 호출 내역 시각화

**WorkflowTree** 클래스를 통해 Worker Tool 호출 흐름을 계층 구조로 표시합니다.

- Manager → Planner → Coder → Reviewer → Tester 흐름
- 각 Worker의 상태 (진행 중, 완료, 실패) 표시
- 상세 정보 추가 가능

```python
from src.presentation.cli.cli_ui import WorkflowTree

tree = WorkflowTree(title="Worker Tools Workflow")
tree.add_worker("Planner", status="running")
tree.add_detail("Planner", "계획 수립 중...")
tree.update_status("Planner", status="completed")
tree.render()
```

**출력 예시**:
```
Worker Tools Workflow
├── ⏳ 🧠 Planner (running)
│   └── 계획 수립 중...
├── ✓ 💻 Coder (completed)
├── ✓ 🔍 Reviewer (completed)
└── ✓ 🧪 Tester (completed)
```

### 4. 세션 정보 테이블

**session list** 명령어를 통해 저장된 세션 목록을 Rich Table로 표시합니다.

```bash
# 세션 목록 조회
python orchestrator.py session list

# 최대 50개 표시
python orchestrator.py session list --limit 50

# 상태 필터
python orchestrator.py session list --status completed
```

**출력 예시**:
```
┌──────────────────────── 세션 목록 (총 10건) ─────────────────────────┐
│ Session ID │ 생성 시각         │ 상태      │ Turns │ 사용자 요청        │
├────────────┼──────────────────┼──────────┼───────┼───────────────────┤
│ abc12345   │ 2025-01-18 14:30 │ completed│     5 │ FastAPI CRUD 구현 │
│ def67890   │ 2025-01-18 13:15 │ completed│     3 │ 버그 수정          │
└────────────┴──────────────────┴──────────┴───────┴───────────────────┘
```

### 5. 에러 메시지 개선

**ErrorDisplay** 클래스를 통해 Rich 스타일의 에러 메시지를 표시합니다.

- **Rich Traceback**: 자동 설치 (install_rich_traceback)
- **에러 타입별 색상**: ValueError (노랑), RuntimeError (빨강) 등
- **상세 디버그 정보**: --verbose 옵션으로 전체 traceback 표시

```python
from src.presentation.cli.cli_ui import get_error_display

error_display = get_error_display()
error_display.show_error(
    error_type="ValueError",
    message="Invalid input",
    details="입력값이 유효하지 않습니다",
    traceback="..." # 선택
)
```

## 사용 예시

### 기본 작업 실행

```bash
python orchestrator.py "FastAPI로 /users CRUD 엔드포인트 구현해줘"
```

**출력**:
```
╔══════════════════════════════════════════════════════════════╗
║ Group Chat Orchestration v3.0                              ║
║ Worker Tools Architecture - Session abc12345                ║
╚══════════════════════════════════════════════════════════════╝

📝 작업: FastAPI로 /users CRUD 엔드포인트 구현해줘
🆔 세션: abc12345
👔 매니저: ManagerAgent (Claude Agent SDK)
🛠️  도구: execute_planner_task, execute_coder_task, execute_tester_task, read

[Turn 1] 👔 ManagerAgent
────────────────────────────────────────────────────────────
...

╭───────────────────── 작업 완료 ─────────────────────────╮
│ 세션 ID: abc12345                                        │
│ 총 턴: 5                                                 │
│ 소요 시간: 45.2초                                        │
│ 수정된 파일: 3개                                         │
│ 히스토리: session_abc12345_20250118_143022.json        │
╰─────────────────────────────────────────────────────────╯
```

### 상세 로깅 (에러 디버깅)

```bash
python orchestrator.py --verbose "로그인 API 버그 수정해줘"
```

### 세션 관리

```bash
# 세션 목록
python orchestrator.py session list

# 세션 검색
python orchestrator.py session search --keyword "API"

# 세션 상세 조회
python orchestrator.py session show abc12345

# 세션 통계
python orchestrator.py session stats --days 7
```

## 아키텍처

### 클래스 다이어그램

```
┌─────────────────┐
│  CLIRenderer    │ (Rich Console 통합, 헤더/푸터 출력)
└─────────────────┘
        ▲
        │
┌───────┴────────┐
│  Orchestrator  │ (renderer 인스턴스 사용)
└────────────────┘

┌─────────────────┐
│ ProgressTracker │ (Progress 바, Spinner)
└─────────────────┘

┌─────────────────┐
│  WorkflowTree   │ (Tree 위젯, Worker Tool 추적)
└─────────────────┘

┌─────────────────┐
│  ErrorDisplay   │ (Rich Traceback, 에러 패널)
└─────────────────┘
```

### 파일 구조

```
src/presentation/cli/
├── orchestrator.py         # Orchestrator 클래스 (CLIRenderer 통합)
├── cli_ui.py              # CLI UI 컴포넌트 (새 파일)
│   ├── CLIRenderer        # Rich Console, 헤더/푸터
│   ├── ProgressTracker    # Progress 바
│   ├── WorkflowTree       # Tree 위젯
│   └── ErrorDisplay       # 에러 메시지
├── feedback.py            # 피드백 시스템 (기존)
├── session_commands.py    # 세션 관리 명령어 (Rich Table 사용)
└── utils.py              # 유틸리티 함수 (기존)
```

## 색상 테마 (GitHub Dark)

| 용도           | 색상 코드  | 설명              |
|----------------|-----------|-------------------|
| Primary        | #58a6ff   | 링크, 제목        |
| Success        | #3fb950   | 성공 메시지       |
| Warning        | #d29922   | 경고              |
| Error          | #f85149   | 에러              |
| Info           | #79c0ff   | 정보              |
| Muted          | #8b949e   | 비활성            |
| Text           | #c9d1d9   | 기본 텍스트       |
| Manager        | #d2a8ff   | Manager Agent     |
| Planner        | #ffa657   | Planner Worker    |
| Coder          | #79c0ff   | Coder Worker      |
| Reviewer       | #56d364   | Reviewer Worker   |
| Tester         | #d2a8ff   | Tester Worker     |

## 기존 코드와의 호환성

- **기존 print() 문**: 점진적으로 renderer.console.print()로 전환 가능
- **FeedbackMessage**: 기존 피드백 시스템과 병행 사용 가능
- **하위 호환성**: 기존 코드 변경 없이 동작

## 향후 개선 사항

1. **Live Display**: 실시간 대시보드 (Layout 사용)
2. **Workflow Tree 자동 추적**: Manager의 Worker Tool 호출 시 자동 업데이트
3. **Progress 바 통합**: Manager 응답 스트리밍 시 progress 표시
4. **세션 재생 UI**: 터미널에서 대화 재생 (애니메이션 효과)
5. **메트릭 시각화**: Chart 라이브러리 연동 (Token 사용량, 성능 지표)

## 참고 자료

- [Rich 공식 문서](https://rich.readthedocs.io/)
- [GitHub Dark 색상 팔레트](https://primer.style/design/foundations/color)
