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
claude-flow-web
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
pipx inject claude-flow pytest pytest-asyncio black ruff
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
├── planner.txt               # 계획 수립 (read, glob만) - 계획형
├── product_manager.txt       # 제품 기획 (read, glob) - 계획형
├── ideator.txt               # 아이디어 생성 (read, glob) - 계획형
├── coder.txt                 # 코드 작성 (read, write, edit, glob, grep) - 실행형
├── reviewer.txt              # 코드 리뷰 (read, glob, grep만) - 분석형
├── style_reviewer.txt        # 스타일 리뷰 (read, glob, grep) - 분석형
├── security_reviewer.txt     # 보안 리뷰 (read, glob, grep) - 분석형
├── architecture_reviewer.txt # 아키텍처 리뷰 (read, glob, grep) - 분석형
├── tester.txt                # 테스트 실행 (read, bash, glob) - 실행형
├── bug_fixer.txt             # 버그 수정 (read, write, edit, bash, grep) - 실행형
├── committer.txt             # Git 커밋 (bash, read) - 실행형
├── documenter.txt            # 문서화 (read, write, edit, glob, bash) - 실행형
├── log_analyzer.txt          # 로그 분석 (read, bash, glob, grep) - 분석형
├── summarizer.txt            # 텍스트 요약 (read, glob) - 분석형
├── worker_prompt_engineer.txt # 커스텀 워커 프롬프트 생성
└── workflow_designer.txt     # 워크플로우 자동 설계 및 생성
```

### Worker 출력 형식 표준화

**모든 Worker는 표준화된 출력 형식을 사용합니다** (Markdown + JSON):

#### 3가지 출력 형식

| 형식 | Worker 예시 | 특징 |
|------|-------------|------|
| **계획형** (Planning) | Planner, Product Manager, Ideator | 계획/아이디어 제시, 다음 단계 제안 |
| **분석형** (Analysis) | Reviewer, Security Reviewer, Log Analyzer | 분석/평가 결과, 승인 여부, 점수 |
| **실행형** (Execution) | Coder, Tester, Bug Fixer, Committer | 작업 수행 결과, 파일 변경, 상태 |

#### 표준 출력 구조

모든 Worker는 다음 구조를 따릅니다:

```markdown
# [작업] 결과

## 📋 요약
[한 줄 요약]

## 🔍 [작업명] 개요
[상세 정보]

## [작업 내용 섹션들]
...

## ✅ 최종 평가
- **승인 여부** / **상태**: ✅ 성공 / ❌ 실패
- **종합 의견**: [평가]
- **추천 조치**: [다음 단계]

## ➡️ 다음 노드를 위한 데이터
```json
{
  "type": "planning|analysis|execution",
  "status": "success|warning|critical|failure",
  "summary": "한 줄 요약",
  ... (워커별 필드)
}
```
```

**JSON 블록의 역할**:
- 다음 노드가 구조화된 데이터를 쉽게 파싱 가능
- 워크플로우 자동화 및 조건부 분기 지원
- 상태(`status`), 승인 여부(`approved`), 점수(`score`) 등 표준 필드 제공

**예시**:
```json
// 계획형 (Planner)
{
  "type": "planning",
  "status": "success",
  "total_tasks": 5,
  "files_to_modify": ["file1.py", "file2.py"]
}

// 분석형 (Reviewer)
{
  "type": "analysis",
  "status": "critical",
  "approved": false,
  "critical_issues": 2,
  "recommendations": ["SQL 파라미터화", "에러 처리 개선"]
}

// 실행형 (Coder)
{
  "type": "execution",
  "status": "success",
  "operation": "create",
  "files_created": ["src/new.py"],
  "quality_score": 8.5
}
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

### 피드백 루프 (Loop 노드)

**Loop 노드를 통한 제어된 피드백 루프를 지원합니다**:

```
Tester → Condition → Loop (max: 3회) → Bug Fixer → Tester
         ↓ (통과)
    Committer
```

**주요 특징**:
- **제어된 반복**: Loop 노드의 `max_iterations`로 최대 반복 횟수 제한
- **조건부 탈출**: Condition 노드로 루프 탈출 조건 설정
- **무한 루프 방지**: Loop 노드 없는 순환은 검증 단계에서 에러 발생

**사용 예시** (테스트 → 버그 수정 → 재테스트):
1. Tester가 테스트 실행
2. Condition 노드가 "테스트 통과" 여부 확인
3. 실패 시: Loop 노드로 → Bug Fixer가 수정 → 다시 Tester로 (최대 3회 반복)
4. 성공 시: Committer로 진행

**검증 규칙**:
- ✅ **허용**: Loop 노드를 포함한 순환 (제어된 피드백 루프)
- ❌ **거부**: Loop 노드 없는 순환 (무한 루프)
- ⚠️ **경고**: `max_iterations` 누락 또는 10 초과

**구현 위치**: `src/presentation/web/services/workflow_validator.py`
- `_check_cycles()`: 순환 참조 검사 (Loop 노드를 통한 피드백 루프 허용)
- `_check_loop_nodes()`: Loop 노드 검증 (max_iterations 확인, 순환 경로 포함 여부)

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
| **Worker Prompt Engineer** | read, glob | 커스텀 워커 프롬프트 생성 |
| **Workflow Designer** | read, glob, grep | 워크플로우 설계 및 생성 |

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
tail -f ~/.claude-flow/{project-name}/logs/claude-flow.log

# 에러만
tail -50 ~/.claude-flow/{project-name}/logs/claude-flow-error.log

# 상세 로깅 활성화
export LOG_LEVEL=DEBUG
export WORKER_DEBUG_INFO=true
```

### 세션 및 워크플로우 검증

```bash
# 세션 확인
ls -la ~/.claude-flow/{project-name}/sessions/
cat ~/.claude-flow/{project-name}/sessions/{session-id}.json

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
1. 로그 확인: `tail -f ~/.claude-flow/{project}/logs/claude-flow.log`
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
tail -f ~/.claude-flow/{project}/logs/claude-flow.log
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

### feat: Workflow Designer 백그라운드 실행 및 세션 복구 (완료)
- **날짜**: 2025-10-29 16:30 (Asia/Seoul)
- **목적**: 워크플로우 설계 중 백그라운드 전환 및 새로고침 시 세션 복구 지원
- **변경사항**:
  - **NodePanel.tsx**:
    - 워크플로우 설계 세션 감지 로직 추가 (36-58줄)
      * localStorage에서 `workflow_design_session` 확인
      * 진행 중인 세션 발견 시 `isWorkflowDesigning` 상태 업데이트
      * 자동으로 모달 열기 (setIsWorkflowDesignerModalOpen(true))
    - 주기적 세션 상태 동기화 (60-74줄)
      * 1초마다 localStorage 체크하여 버튼 상태 업데이트
      * 백그라운드 실행 중에도 "워크플로우 설계 중..." 표시 유지
    - 버튼 클릭 시 동작
      * 진행 중일 때 클릭 → 모달 열어서 진행 상황 확인
      * 미진행 시 클릭 → 새로운 설계 시작
  - **WorkflowDesignerModal.tsx** (기존 구현 확인):
    - localStorage 세션 관리 (STORAGE_KEY: 'workflow_design_session')
    - 모달 열릴 때 세션 자동 복구 (176-240줄)
    - 완료/중단/에러 시 세션 정리 (clearSession)
    - "백그라운드 실행" 버튼: 모달만 닫고 세션 유지
    - "중단" 버튼: 세션 정리 및 초기화
- **사용 시나리오**:
  1. 워크플로우 설계 시작 → "백그라운드 실행" 클릭
  2. 버튼이 "워크플로우 설계 중..."으로 변경됨
  3. 버튼 클릭 → 모달 다시 열림, 진행 중인 출력 확인
  4. 새로고침 → localStorage에서 세션 복구, 모달 자동 열림
  5. 완료 또는 중단 → 세션 자동 정리
- **파일**: `NodePanel.tsx` (40줄 추가), `WorkflowDesignerModal.tsx` (기존 구현 확인)
- **영향범위**: UX 개선, 세션 영속성, 백그라운드 실행
- **패턴**: CustomWorkerCreateModal과 동일한 세션 관리 패턴 적용
- **테스트**: TypeScript 컴파일 및 빌드 통과
- **후속 조치**: 실제 브라우저에서 백그라운드 실행 및 새로고침 테스트

### refactor: Workflow Designer 고급 노드 활용 및 미리보기 개선 (완료)
- **날짜**: 2025-10-29 16:00 (Asia/Seoul)
- **목적**:
  - 워크플로우 설계 시 고급 노드(condition, loop, merge, manager)를 적극 활용하도록 개선
  - 미리보기에서 노드/엣지 연결 관계를 상세히 표시
- **변경사항**:
  - **prompts/workflow_designer.txt**:
    - "워크플로우 설계" 섹션에 고급 노드 활용 지침 강화
      * **단순 순차 실행을 피하고 고급 노드를 적극 활용**
      * **독립적인 작업은 반드시 Manager 노드로 병렬 실행** (20-50% 속도 향상)
      * **조건 분기가 필요하면 Condition 노드 추가**
      * **반복 작업은 Loop 노드 사용**
      * **여러 분기를 통합할 때는 Merge 노드 사용**
    - "고급 노드 우선 원칙" 섹션 추가 (3번 항목)
      * 2개 이상의 독립적 작업 → Manager 노드 병렬 실행
      * 조건부 실행 → Condition 노드
      * 반복 실행 → Loop 노드
      * 분기 통합 → Merge 노드
      * 단순 순차 실행은 최소화
    - 예시 3 추가: 고급 노드 활용 (조건 분기 + 반복 + 병합)
      * 테스트 실패 시 자동 버그 수정 반복
      * 테스트 성공 시 Manager 노드로 리뷰 및 문서 작성 병렬 실행
      * Condition, Loop, Manager 노드를 모두 활용한 복잡한 워크플로우 예시
  - **WorkflowDesignerModal.tsx (미리보기 개선)**:
    - 노드 타입별 색상 및 아이콘 추가
      * input: 📥 (파란색), worker: ⚙️ (녹색), manager: 👥 (보라색)
      * condition: 🔀 (노란색), loop: 🔁 (주황색), merge: 🔗 (핑크색)
    - 노드 상세 정보 표시
      * agent_name, task_template/task_description (80자 이내 미리보기)
      * available_workers (Manager 노드), condition_type/value (Condition 노드)
      * max_iterations (Loop 노드), merge_strategy (Merge 노드)
    - 연결 관계 섹션 추가
      * source → target 화살표로 시각적 표시
      * source는 파란색, target은 녹색으로 구분
      * sourceHandle (예: true/false) 표시
- **파일**:
  - `prompts/workflow_designer.txt` (51줄 추가)
  - `src/presentation/web/frontend/src/components/WorkflowDesignerModal.tsx` (80줄 개선)
- **영향범위**: 워크플로우 자동 설계 품질, UI/UX, 사용자 이해도
- **기대효과**:
  - 워커가 단순한 순차 워크플로우가 아닌 고급 노드를 활용한 복잡한 워크플로우를 생성
  - 미리보기에서 노드 구조와 연결 관계를 명확히 파악 가능
  - 조건 분기, 반복, 병렬 실행을 적극 활용하여 실용적인 워크플로우 생성
- **테스트**: TypeScript 컴파일 검사 및 빌드 통과
- **후속 조치**: 실제 워크플로우 설계 시 고급 노드 활용 여부 확인

### feat: Workflow Designer 워커 추가 (완료)
- **날짜**: 2025-10-29 15:00 (Asia/Seoul)
- **목적**: 사용자 요구사항으로부터 워크플로우를 자동으로 설계 및 생성하는 워커 추가
- **변경사항**:
  - **config/agent_config.json**:
    - `workflow_designer` 워커 추가 (read, glob, grep 도구 사용)
    - model: claude-sonnet-4-5-20250929, thinking: true
  - **prompts/workflow_designer.txt**:
    - 워크플로우 설계 전문가 프롬프트 작성
    - 노드 타입 (input, worker, manager, condition, loop, merge) 설명
    - 사용 가능한 기본 워커 목록 (15개)
    - 노드 연결 규칙 및 템플릿 변수 설명
    - JSON 출력 형식 정의:
      * `workflow`: Workflow 객체 (nodes, edges, metadata)
      * `custom_workers`: 필요 시 커스텀 워커 정의 배열
      * `explanation`: 워크플로우 설명
      * `usage_guide`: 사용 방법 가이드
    - 예시 2개 추가 (순차 워크플로우, Manager 병렬 실행)
  - **CLAUDE.md**:
    - prompts 섹션에 workflow_designer.txt 추가
    - agent_config.json 섹션에 Workflow Designer 워커 추가
- **출력 활용**:
  - `workflow` 부분: Web UI 워크플로우 캔버스에 직접 로드 가능
  - `custom_workers` 부분: agent_config.json 및 prompts/ 디렉토리에 추가 가능
- **영향범위**: 워크플로우 자동 생성, 사용자 생산성 향상
- **사용법**:
  1. Web UI에서 "Workflow Designer" 워커를 노드로 추가
  2. 요구사항 입력 (예: "코드 리뷰 후 테스트 실행하는 워크플로우")
  3. 생성된 JSON의 `workflow` 부분을 복사하여 워크플로우 캔버스에 로드
  4. 필요 시 `custom_workers` 부분을 프로젝트에 추가
- **테스트**: 구문 검사 통과 (agent_config.json)
- **후속 조치**: Web UI에서 실제 워크플로우 생성 테스트

### fix: InputNode 로그 파싱 개선 - ParsedContent 사용 (완료)
- **날짜**: 2025-10-29 14:00 (Asia/Seoul)
- **문제**: InputNode의 실행 로그에서 thinking, tool 블록 등이 파싱되지 않음
  - LogItem 컴포넌트가 `parseLogMessage` (단일 블록) 사용
  - 각 chunk가 개별 로그로 저장되어 JSON이 여러 로그에 걸쳐 분할됨
  - 복잡한 파싱 로직이 LogItem에 중복 구현됨
- **해결**:
  - **InputNodeConfig.tsx 리팩토링**:
    - LogItem에서 `ParsedContent` 컴포넌트 사용
    - 중복된 파싱 로직 (150줄) 완전 제거
    - extractToolUseId, extractToolName, buildToolNameMap 함수 제거
    - 불필요한 import 정리 (Brain, ChevronDown, ChevronRight, useMemo)
  - **일관된 파싱**:
    - 모든 노드 설정 컴포넌트가 동일한 ParsedContent 사용
    - InputNode, Worker, Merge, Loop, Condition 모두 일관성
  - **간결한 코드**:
    - LogItem: 150줄 → 20줄 (87% 감소)
    - 파싱 로직은 ParsedContent에 집중
- **파일**: `src/presentation/web/frontend/src/components/node-config/InputNodeConfig.tsx`
- **영향범위**: Input 노드 실행 로그 표시, 코드 유지보수성
- **테스트**: TypeScript 컴파일 검사 통과
- **후속 조치**: 브라우저에서 실제 로그 확인

### fix: 로그 파싱 혼합 형태 처리 개선 (완료)
- **날짜**: 2025-10-29 13:30 (Asia/Seoul)
- **문제**: Worker 노드 출력에서 텍스트와 JSON이 혼합된 경우 파싱 실패
  - 예: "먼저 프로젝트 구조를 파악하고...{"role": "assistant", "content": [...]}"
  - 기존 파서는 순수 JSON만 처리하여 혼합 형태는 raw 텍스트로 표시됨
- **해결**:
  - **logParser.ts 개선**:
    - `extractJSONBlocks` 함수 추가: 텍스트에서 JSON 블록 추출
      * `{"role":` 패턴으로 JSON 시작 감지
      * 중괄호 카운팅으로 JSON 끝 감지 (문자열 내부 처리 포함)
      * 텍스트와 JSON을 분리하여 배열로 반환
    - `parseLogMessageBlocks` 함수 추가: 여러 블록 파싱 지원
      * 텍스트와 JSON 혼합 형태 처리
      * 각 블록을 개별적으로 파싱하여 배열로 반환
    - `ParsedLogBlocks` 인터페이스 추가: 여러 블록 반환용
  - **ParsedContent.tsx 개선**:
    - `ParsedBlock` 컴포넌트 분리: 단일 블록 렌더링
    - 메인 컴포넌트에서 `parseLogMessageBlocks` 사용
    - 여러 블록을 순서대로 렌더링 (map)
    - 각 블록의 상태(isExpanded) 독립적으로 관리
  - **InputNodeConfig.tsx 타입 에러 수정**:
    - onValidate의 사용하지 않는 파라미터를 `_data`로 변경
- **파일**:
  - `src/presentation/web/frontend/src/lib/logParser.ts`
  - `src/presentation/web/frontend/src/components/ParsedContent.tsx`
  - `src/presentation/web/frontend/src/components/node-config/InputNodeConfig.tsx`
- **영향범위**: Worker 노드 출력 파싱, 로그 가독성
- **테스트**: TypeScript 컴파일 검사 통과
- **후속 조치**: 실제 브라우저에서 혼합 형태 로그 확인

### docs: README.md 오픈소스 공개 버전으로 업데이트 (완료)
- **날짜**: 2025-10-29 11:00 (Asia/Seoul)
- **목적**: 실제 오픈소스 프로젝트로 공개하기 위해 README 전면 개편
- **변경사항**:
  - **Hero 섹션 개선**: 중앙 정렬, 명확한 설명, 빠른 네비게이션 링크 추가
  - **주요 특징 재구성**:
    - Web UI 워크플로우 에디터를 가장 먼저 배치 (핵심 기능 강조)
    - Manager 노드 병렬 실행 기능 강조 (20-50% 속도 향상)
    - Worker Agent 역할을 표로 정리하여 가독성 향상
    - 커스텀 워커 생성 기능 추가 언급
  - **설치 및 사용법 단순화**:
    - 이모지로 단계 구분 (1️⃣ 2️⃣ 3️⃣)
    - 각 UI별 특징 명확히 표시 (Web UI, TUI, CLI)
    - OAuth 토큰 발급 링크 추가
  - **실용적인 사용 예시 추가**:
    - 예시 1: 신규 기능 개발 (순차 워크플로우)
    - 예시 2: 코드 리뷰 (병렬 실행, 3배 속도)
    - 예시 3: 반복 작업 (Loop + Condition 노드)
    - 각 예시에 워크플로우 다이어그램 및 단계별 설명 포함
  - **문서 구조 개선**:
    - 문서 링크를 사용자 가이드/개발자 가이드로 분리
    - 기여 방법을 상세히 설명 (개발 환경 설정 포함)
    - 버그 리포트 & 기능 요청 섹션 추가
  - **감사의 말 확장**: React Flow 등 사용한 라이브러리 명시
- **파일**: `README.md`
- **영향범위**: 프로젝트 첫인상, 사용자 온보딩, 기여자 유입
- **후속 조치**:
  - 스크린샷/GIF 추가 (워크플로우 캔버스 실행 화면)
  - LICENSE 파일 확인
  - CONTRIBUTING.md 작성

### fix: 노드 패널 설명 텍스트 줄바꿈 버그 수정 (완료)
- **날짜**: 2025-10-29 11:00 (Asia/Seoul)
- **문제**: 커스텀 워커 등의 설명(role)이 길 때 UI 박스를 넘어가는 문제
- **원인**: `line-clamp-1` 클래스가 한 줄로 제한하다 보니 긴 텍스트가 UI를 뚫고 나감
- **해결**:
  - **`line-clamp-2`로 변경** (`NodePanel.tsx`):
    - 범용 워커 섹션 (500줄)
    - 특화 워커 섹션 (549줄)
    - 커스텀 워커 섹션 (642줄)
  - 최대 2줄까지 표시하고 나머지는 말줄임표(...)로 처리
- **파일**: `src/presentation/web/frontend/src/components/NodePanel.tsx`
- **영향범위**: 노드 패널 UI 가독성, 긴 설명 텍스트 표시
- **테스트**: TypeScript 컴파일 검사 (기존 에러와 무관)

### fix: 노드 위치 저장 문제 해결 (완료)
- **날짜**: 2025-10-29 14:00 (Asia/Seoul)
- **문제**: 웹 UI에서 노드 위치를 변경해도 workflow-config.json에 저장되지 않음
- **원인**: React Flow의 `onNodesChange` 이벤트만으로는 드래그 완료 시점을 정확히 감지하기 어려움
- **해결**:
  - **`onNodeDragStop` 핸들러 추가** (`WorkflowCanvas.tsx:287-293`):
    - 노드 드래그 완료 시 확실하게 `updateNodePosition` 호출
    - React Flow의 공식 드래그 완료 이벤트 사용
  - **디버그 로그 추가** (`WorkflowCanvas.tsx:195-199, 289`):
    - position change 이벤트 추적
    - `updateNodePosition` 호출 추적
  - **조건문 개선** (`WorkflowCanvas.tsx:203`):
    - `dragging === false || dragging === undefined` 명시적 검사
    - 이전: `!change.dragging` (암묵적)
  - **타입 에러 수정** (`WorkflowCanvas.tsx:362`):
    - `fitViewOnInit` → `fitView` (React Flow 11.x 호환)
- **파일**: `src/presentation/web/frontend/src/components/WorkflowCanvas.tsx`
- **영향범위**: 노드 위치 영속성, 자동 저장 트리거
- **테스트**: TypeScript 타입 검사 통과
- **후속 조치**: 실제 브라우저에서 노드 드래그 후 workflow-config.json 저장 확인

---

### 커스텀 워커 세션 복구 버그 수정 (완료)
- **날짜**: 2025-10-29 10:30 (Asia/Seoul)
- **문제**: 커스텀 워커 실행 중 웹 새로고침 시 세션 복구 실패
  - 싱글톤 `BackgroundWorkflowManager`가 첫 초기화 시 프로젝트 경로 없이 생성됨
  - 이후 프로젝트 선택 후 커스텀 워커 실행 시 구버전 `executor` 사용
  - 결과: "Agent를 찾을 수 없습니다" 에러
- **원인**:
  - `get_background_workflow_manager`가 전역 싱글톤 패턴 사용
  - 첫 호출 시 전달된 `executor`로 한 번만 초기화
  - 프로젝트 전환 시 새로운 `executor` (커스텀 워커 포함) 무시
- **해결**:
  - **프로젝트별 인스턴스 캐싱** (`background_workflow_manager.py`):
    - 싱글톤 → 프로젝트 경로별 딕셔너리 캐싱 (`_managers: Dict[str, BackgroundWorkflowManager]`)
    - `get_background_workflow_manager`에 `project_path` 매개변수 추가
    - 프로젝트 경로 변경 시 자동으로 올바른 인스턴스 반환
    - 기존 인스턴스의 `executor` 동적 업데이트 지원
  - **워크플로우 라우터 수정** (`workflows.py:79-93`):
    - `get_background_manager`에서 현재 프로젝트 경로 전달
  - **에러 메시지 개선** (`workflow_executor.py`):
    - 커스텀 워커 로드 실패 시 프로젝트 경로 포함하여 로깅
    - Agent 찾을 수 없을 때 사용 가능한 Agent 목록 표시
    - 커스텀 워커 여부에 따라 힌트 메시지 제공
- **영향범위**: 세션 복구, 프로젝트 전환, 커스텀 워커 실행
- **테스트**: 구문 검사 통과
- **후속 조치**: 실제 시나리오 테스트 필요 (커스텀 워커 실행 중 새로고침)

### 템플릿 변수 설명 및 기본값 수정 (완료)
- **문제**: 노드 설정 패널과 기본 템플릿에서 `{{input}}`이 "이전 노드 출력"이라고 잘못 설명됨
- **원인**:
  - `{{input}}`은 Input 노드의 초기 입력값
  - `{{parent}}`가 직전 부모 노드의 출력
- **해결**:
  - **백엔드 검증 로직 수정** (`workflow_validator.py`):
    - 263-265줄: `{{parent}}` 변수를 유효한 변수로 추가
    - 227줄: docstring에 `{{parent}}` 추가
    - 280줄: 에러 메시지에 변수 설명 추가
  - **프론트엔드 설명 수정** (`WorkerNodeConfig.tsx`):
    - 211-213줄: 툴팁 설명에 모든 템플릿 변수 정보 추가
    - 236-252줄: 사용 가능한 변수 섹션에 `{{parent}}`, `{{input}}`, `{{node_<id>}}` 상세 설명
    - 561-563줄: 정보 탭 사용법에 변수별 용도 명시
  - **기본 템플릿 변경** (`NodePanel.tsx`):
    - 161줄 (handleAddAgent): `{{input}}` → `{{parent}}`
    - 495, 544, 637줄 (드래그 핸들러): 모두 `{{parent}}`로 변경
  - **프론트엔드 빌드 완료**
- **파일**: `workflow_validator.py`, `WorkerNodeConfig.tsx`, `NodePanel.tsx`
- **영향**: 신규 워커 노드 추가 시 `{{parent}}`가 기본값으로 설정되어 대부분의 경우 올바르게 작동

### 병합 노드 경고 로그 추가 (완료)
- **문제**: 병합 노드에서 부모 출력이 없을 때 경고 없이 빈 문자열 사용
- **해결**: 부모 출력 누락 시 경고 로그 추가
  - 부모 노드 ID와 병합 노드 ID를 포함한 상세 경고 메시지
  - 빈 문자열 대체 사실을 명시적으로 로깅
- **파일**: `workflow_executor.py:720-726`
- **참고**: 템플릿 변수 사용법
  - `{{input}}`: 초기 입력값 (Input 노드 값)
  - `{{parent}}`: 직전 부모 노드의 출력
  - `{{node_<id>}}`: 특정 노드의 출력

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
