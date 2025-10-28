# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

**워크플로우 기반 AI 개발 자동화 시스템 (Clean Architecture)** - 전문화된 Worker Agent들을 노드로 연결하여 복잡한 소프트웨어 개발 작업을 자동화하는 시스템입니다.

### 핵심 개념

#### 워크플로우 노드 시스템 (Web UI)
```
Input 노드 → Planner → Coder → Reviewer → Tester → Committer
```

**특징**:
- 각 Worker는 독립적인 노드로 실행
- 노드 간 연결로 데이터 전달 (이전 노드의 **전체 출력** → 다음 노드 입력)
- 드래그 앤 드롭으로 워크플로우 구성
- Manager 노드로 여러 워커를 병렬 실행 (20-50% 속도 향상)

#### Clean Architecture (4계층)
```
Presentation (Web UI) → Application (Use Cases, Ports)
    → Domain (Models, Services) ← Infrastructure (Claude SDK, MCP, Storage)
```

**의존성 규칙**: 외부 계층 → 내부 계층만 의존. 내부는 외부를 모름.

---

## 빠른 시작

### 설치 및 실행

```bash
# 설치 (개발 모드)
pipx install -e .

# 환경변수 설정 (필수)
export CLAUDE_CODE_OAUTH_TOKEN='your-token-here'

# Web UI 실행
better-llm-web
# → http://localhost:5173
```

---

## 핵심 개발 명령어

### 코드 검증

```bash
# 구문 검사 (코드 변경 후 필수)
find src -name "*.py" -type f | xargs python3 -m py_compile

# 특정 파일만
python3 -m py_compile src/infrastructure/claude/worker_client.py

# 린트 및 포맷
ruff check src/
black src/
```

### 테스트

```bash
# 전체 테스트
pytest

# 특정 디렉토리
pytest tests/unit/ -v
pytest tests/integration/ -v

# 커버리지
pytest --cov=src --cov-report=html
```

### 개발 의존성 설치

```bash
# 처음 한 번만 (pytest, black, ruff 등)
pipx inject better-llm pytest pytest-asyncio black ruff
```

---

## 아키텍처

### Clean Architecture 계층 구조

```
src/
├── domain/                    # 순수 Python, 외부 의존성 없음
│   ├── models/               # Message, AgentConfig, Task, SessionResult
│   ├── services/             # ConversationHistory, ProjectContext
│   └── agents/               # BaseAgent (인터페이스)
│
├── application/               # Use Cases 및 의존성 역전
│   └── ports/                # IAgentClient, IConfigLoader, ISessionRepository
│
├── infrastructure/            # 외부 의존성 구현
│   ├── claude/               # Manager/Worker Agent 클라이언트
│   ├── mcp/                  # Worker Tools MCP Server
│   ├── storage/              # JSON/SQLite 저장소
│   └── config/               # 설정 로더, 환경 검증
│
└── presentation/              # UI
    └── web/                  # Web UI (FastAPI + React)
```

### 주요 설정 파일

```
config/
├── agent_config.json         # Worker Agent 설정 (name, role, tools, model)
└── system_config.json        # 시스템 설정 (max_turns, hooks, permission)

prompts/                       # Worker Agent 시스템 프롬프트
├── planner.txt               # 계획 수립 (read, glob만)
├── coder.txt                 # 코드 작성 (read, write, edit, glob, grep)
├── reviewer.txt              # 코드 리뷰 (read, glob, grep만)
├── tester.txt                # 테스트 실행 (read, bash, glob)
└── committer.txt             # Git 커밋 (bash, read)
```

---

## 워크플로우

### Web UI 워크플로우 (노드 기반 실행)

**실행 과정**:
1. **위상 정렬**: 노드 실행 순서 결정
2. **Input 검증**: Input 노드에서 도달 불가능한 노드는 스킵
3. **순차 실행**: 각 노드를 순서대로 실행
4. **데이터 전달**: 노드 출력을 `node_outputs`에 저장 → 다음 노드 템플릿에 변수 치환

**템플릿 변수**:
- `{{input}}`: 초기 사용자 입력
- `{{parent}}`: 직전 부모 노드의 출력
- `{{node_<id>}}`: 특정 노드의 출력

### Manager 노드 (병렬 실행)

```python
# 백엔드 구현 (workflow_executor.py)
async def _execute_manager_node(self, node, ...):
    # 1. 등록된 워커들 병렬 실행
    worker_tasks = [(name, worker.execute_task(task)) for name in workers]

    # 2. 결과 수집
    worker_results = {}
    for name, stream in worker_tasks:
        chunks = [chunk async for chunk in stream]
        worker_results[name] = "".join(chunks)

    # 3. Markdown 형식으로 통합
    return "\n\n".join(f"## {name.upper()}\n\n{output}"
                       for name, output in worker_results.items())
```

**사용법**:
1. 왼쪽 패널에서 "Manager" 노드 추가
2. 노드 설정에서 워커 체크박스 선택 (최소 1개)
3. 작업 설명 입력 (모든 워커에게 동일하게 전달)

---

## 설정 파일

### agent_config.json - Worker 도구 제한

Worker별 도구 제한으로 역할 경계 명확화:

| Worker | 도구 | 역할 |
|--------|------|------|
| **Planner** | read, glob | 계획 수립 (읽기만) |
| **Coder** | read, write, edit, glob, grep | 코드 작성 (bash 제외) |
| **Reviewer** | read, glob, grep | 코드 리뷰 (읽기만) |
| **Tester** | read, bash, glob | 테스트 실행 (write 제외) |
| **Committer** | bash, read | Git 커밋만 |

### system_config.json - 주요 설정

```json
{
  "manager": {
    "max_history_messages": 20,      // 슬라이딩 윈도우
    "max_turns": 10
  },
  "performance": {
    "worker_retry_max_attempts": 3
  },
  "permission": {
    "mode": "acceptEdits"             // acceptEdits | default | bypassPermissions
  }
}
```

**Permission Mode 변경**:
```bash
export PERMISSION_MODE=acceptEdits  # 환경변수가 설정 파일보다 우선
```

### .context.json - 프로젝트 컨텍스트

Worker Agent 초기화 시 자동 로드:
- `project_name`, `architecture`
- `key_files`: entry_points, domain, infrastructure
- `coding_style`: docstring, type hints, line length

---

## 디버깅

### 로그 확인

```bash
# 실시간 모니터링
tail -f ~/.better-llm/{project-name}/logs/better-llm.log

# 에러만
tail -50 ~/.better-llm/{project-name}/logs/better-llm-error.log

# 상세 로깅 활성화
export LOG_LEVEL=DEBUG
export WORKER_DEBUG_INFO=true
```

### 세션 및 워크플로우 검증

```bash
# 세션 확인
ls -la ~/.better-llm/{project-name}/sessions/
cat ~/.better-llm/{project-name}/sessions/{session-id}.json

# Web UI에서:
# - 워크플로우 저장 시 자동 검증 (순환 참조, 노드 연결)
# - SSE로 실시간 출력 스트리밍
# - 새로고침 후 세션 자동 복원
```

---

## 중요한 제약사항

### Web 워크플로우

- **Input 노드 필수**: Input에서 도달 불가능한 노드는 실행 안 됨
- **순환 참조 금지**: 사이클 있으면 위상 정렬 실패
- **Manager 노드**: 최소 1개 워커 필수
- **변수 치환**: 존재하지 않는 변수는 빈 문자열로 대체

### 일반

1. **환경변수 필수**: `CLAUDE_CODE_OAUTH_TOKEN` 설정 필수
2. **시크릿 하드코딩 금지**: `.env` 파일 사용
3. **프로젝트 경로**: 워크플로우 실행 시 프로젝트 디렉토리 지정 필요

---

## 일반적인 작업 패턴

### 새 Worker Agent 추가

1. `prompts/new_agent.txt` 작성
2. `config/agent_config.json`에 정의 (name, role, tools, model)
3. `src/infrastructure/mcp/worker_tools.py`에 `@tool` 함수 추가
4. 구문 검사 → Web UI에서 테스트

### 프롬프트 수정

- **위치**: `prompts/{worker}.txt`
- **출력 형식**: 전체 출력이 다음 노드로 전달되므로 요약 불필요
- **검증**: 구문 검사 후 Web UI에서 실제 실행으로 확인

### 설정 변경

- **모델**: `agent_config.json`의 `model` 필드
- **재시도**: `system_config.json`의 `performance.worker_retry_*`
- **입력 검증**: `system_config.json`의 `security.*`

---

## 문제 해결

### "CLAUDE_CODE_OAUTH_TOKEN 환경변수가 설정되지 않았습니다"
```bash
export CLAUDE_CODE_OAUTH_TOKEN='your-token-here'
# 또는 .env 파일에 추가
```

### "워크플로우 실행 실패"
1. 로그 확인: `tail -f ~/.better-llm/{project}/logs/better-llm.log`
2. Worker 설정 확인: `config/agent_config.json`
3. 프롬프트 파일 존재 확인: `prompts/*.txt`
4. 노드 연결 확인: Input 노드에서 도달 가능한지

### "노드 출력이 다음 노드로 전달되지 않음"
- 템플릿 변수 확인: `{{parent}}`, `{{node_<id>}}`
- 이전 노드 완료 확인: node_complete 이벤트
- 워크플로우 엣지(연결) 확인

### "Web UI 접속 불가"
```bash
# 포트 충돌 확인
lsof -i :5173

# 백엔드 로그
tail -f ~/.better-llm/{project}/logs/better-llm.log
```

---

## Claude Agent SDK Best Practice

### 1. ClaudeAgentOptions 사용

```python
from claude_agent_sdk.types import ClaudeAgentOptions

options = ClaudeAgentOptions(
    model="claude-sonnet-4-5-20250929",
    allowed_tools=["read", "write", "edit"],
    permission_mode="acceptEdits",
    setting_sources=["user", "project"]  # SDK v0.1.0+
)
```

### 2. System Prompt 설정

- **Manager**: `self.SYSTEM_PROMPT` 속성 (`manager_client.py`)
- **Worker**: `prompts/*.txt` 파일에서 로드 (`worker_client.py:68-105`)

```python
# Worker 예시
full_prompt = f"{self.system_prompt}\n\n{task_description}"
async for response in query(prompt=full_prompt, options=options):
    ...
```

### 3. 에러 처리

```python
from claude_agent_sdk import CLINotFoundError, ProcessError, ClaudeSDKError

try:
    async for response in query(prompt, options):
        ...
except CLINotFoundError:
    # Claude CLI 미설치
except ProcessError as e:
    # 프로세스 실행 실패
except ClaudeSDKError:
    # 기타 SDK 에러
```

**구현**: `sdk_executor.py` (ManagerSDKExecutor, WorkerSDKExecutor)

### 4. Permission Mode

| Mode | 설명 | 사용 시나리오 |
|------|------|--------------|
| **acceptEdits** | 파일 편집 자동 승인 | 프로덕션, CI/CD |
| **default** | 수동 승인 | 대화형 개발 |
| **bypassPermissions** | 모든 작업 자동 승인 | 테스트 |

```bash
export PERMISSION_MODE=acceptEdits  # 동적 변경
```

**구현**: `sdk_executor.py` (PermissionModeResolver)

### 5. Context 관리

**Manager Agent 슬라이딩 윈도우**:
- 최대 20개 메시지 유지 (`max_history_messages=20`)
- 첫 사용자 요청 + 최근 메시지 포함
- 컨텍스트 90% 초과 시 경고

**구현**: `manager_client.py` (ManagerAgent 슬라이딩 윈도우)

---

## 참고

- [Claude Agent SDK 마이그레이션 가이드](https://docs.claude.com/en/docs/claude-code/sdk/migration-guide.md)
- [MCP Server 가이드](https://docs.anthropic.com/en/docs/agent-sdk/python/mcp-servers)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

**상세 히스토리**: `CHANGELOG.md` 참조

**최종 업데이트**: 2025-10-29

---

## 최근 작업 (2025-10-29)

### 병렬 실행 버그 수정 (완료)
- **문제 1**: 노드 상태가 "진행중"으로 안바뀌는 문제
  - **원인**: 병렬 실행 시 모든 이벤트를 수집한 후 일괄 전송
  - **해결**: `asyncio.Queue`로 실시간 이벤트 스트리밍 구현
  - **파일**: `workflow_executor.py:1218-1254, 1342-1408`

- **문제 2**: Input 노드 로그에 병렬 노드 로그가 안찍히는 문제
  - **원인**: 동일 (이벤트 지연 전송)
  - **해결**: 실시간 스트리밍으로 해결

- **문제 3**: 중단 시 병렬 워커가 멈추지 않는 문제
  - **원인**: 취소 API 부재, CancelledError 처리 미흡
  - **해결**:
    - 취소 API 추가: `POST /api/workflows/sessions/{session_id}/cancel` (`workflows.py:652-700`)
    - `CancelledError` 처리 구현 (`workflow_executor.py:1428-1456`)
    - 모든 병렬 태스크 정리 및 취소 이벤트 생성

### 노드 좌표 영속성 저장 버그 수정
- **문제**: 노드 이동 후 저장/로드 시 위치가 초기화됨
- **원인**: React Flow의 position 변경이 Zustand 스토어에 반영되지 않음
- **해결**:
  - `updateNodePosition` 함수 추가 (`workflowStore.ts:147-154`)
  - position 변경 시 명시적 업데이트 (`WorkflowCanvas.tsx:194-196`)
- **파일**: `workflowStore.ts`, `WorkflowCanvas.tsx`

### {{parent}} 템플릿 변수 버그 수정
- **문제**: 병합 노드 → 다음 노드 연결 시, 다음 노드 입력에 Input 노드 값이 들어감
- **원인**: `_render_task_template`에서 부모 노드를 잘못 찾음 (노드 ID가 템플릿에 포함되어 있는지 확인)
- **해결**: 부모 노드 출력을 올바르게 치환하도록 수정
- **파일**: `workflow_executor.py:332-348`

### 병렬 실행 체크박스 영속성 저장 버그 수정 (이전)
- **문제**: `parallel_execution` 체크박스 상태가 저장/로드 시 유지되지 않음
- **원인**: Pydantic `model_dump()`가 기본값(False) 필드를 생략
- **해결**: `model_dump(mode='json', exclude_none=False)` 사용
- **파일**: `projects.py:235`

### 커스텀 워커 지원 (이전)
- **문제**: 커스텀 워커 노드 실행 시 "Agent를 찾을 수 없습니다" 에러
- **해결**: WorkflowExecutor에서 프로젝트 경로 기반 커스텀 워커 자동 로드
- **파일**: `workflow_executor.py`, `workflows.py`

---
