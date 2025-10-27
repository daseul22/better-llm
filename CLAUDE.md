# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

**그룹 챗 오케스트레이션 시스템 v4.0 (Clean Architecture)** - Manager Agent가 전문화된 Worker Agent들을 조율하여 복잡한 소프트웨어 개발 작업을 자동화하는 시스템입니다.

### 핵심 개념

#### 1. Worker Tools Pattern
```
사용자 요청
  ↓
Manager Agent (ClaudeSDKClient)
  ↓
Worker Tools (MCP Server) ← Manager가 Tool로 호출
  ↓
Worker Agent (각 전문 분야) ← Tool 내부에서 실행
  ↓
결과를 Manager에게 반환
```

**중요**: Worker Agent는 직접 호출 불가. 반드시 Manager Agent → Worker Tools → Worker Agent 흐름.

#### 2. Artifact Storage (컨텍스트 최적화)
- Worker 전체 출력: `~/.better-llm/{project}/artifacts/{worker}_{timestamp}.txt`
- Manager에게는 **요약만** 전달 → 컨텍스트 90% 절감
- 상세 정보 필요 시: Worker가 read 도구로 artifact 파일 읽기

#### 3. Context Compression (자동 압축)
- **자동 트리거**: 컨텍스트 윈도우 85% 초과 시 자동 압축 수행
- **압축 전략**:
  1. 오래된 메시지를 파일로 저장 (`~/.better-llm/{project}/compressed/`)
  2. 메시지를 메타데이터(파일 참조)로 대체 (약 200자)
  3. 첫 번째 사용자 메시지는 항상 보존 (컨텍스트 유지)
- **효과**: 약 30% 컨텍스트 절감 (설정 가능)
- **필요 시 복원**: Worker가 read 도구로 압축된 파일 읽기

#### 4. Clean Architecture (4계층)
```
Presentation (CLI, TUI)
    ↓
Application (Use Cases, Ports)
    ↓
Domain (Models, Services) ← 의존성 역전
    ↑
Infrastructure (Claude SDK, MCP, Storage, Config)
```

**의존성 규칙**: 외부 계층 → 내부 계층만 의존. 내부 계층은 외부 계층을 모름.

---

## 빠른 시작

### 설치

```bash
# 자동 설치 (권장)
./setup.sh

# 수동 설치
pipx install -e .  # 개발 모드 (소스 변경 시 바로 반영)
pipx install .     # 일반 모드
```

### 환경변수 설정

```bash
# 필수
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'

# 선택 (기본값 있음)
export PERMISSION_MODE=acceptEdits           # bypassPermissions (테스트), default (수동 승인)
export ENABLE_LLM_SUMMARIZATION=true         # LLM 기반 요약 (false: 패턴 매칭)
export ENABLE_INTERACTIVE=false              # Human-in-the-Loop 활성화
export LOG_LEVEL=INFO                        # DEBUG, INFO, WARNING, ERROR
export LOG_FORMAT=console                    # json, console
export LOG_DIR=/custom/path                  # 기본값: ~/.better-llm/{project}/logs
```

### 실행

```bash
# TUI (권장)
better-llm

# Web UI - NEW! (드래그 앤 드롭 워크플로우 에디터)
better-llm-web
# 접속: http://localhost:5173

# CLI
better-llm-cli "작업 설명"

# 개발 중인 경우 (가상환경)
python -m src.presentation.tui.tui_app
python -m src.presentation.cli.orchestrator "작업"
python -m src.presentation.web.app  # 웹 서버
```

---

## 주요 명령어

### 개발 명령어

```bash
# 개발 의존성 설치 (처음 한 번만)
pipx inject better-llm pytest pytest-asyncio black ruff

# 구문 검사 (코드 변경 후 필수)
find src -name "*.py" -type f | xargs python3 -m py_compile

# 특정 파일만 검사
python3 -m py_compile src/infrastructure/claude/manager_client.py

# 린트
ruff check src/

# 포맷
black src/
```

### 테스트

```bash
# 전체 테스트 실행
pytest

# 특정 디렉토리 테스트
pytest tests/unit/ -v               # 단위 테스트
pytest tests/integration/ -v        # 통합 테스트
pytest tests/e2e/ -v                # E2E 테스트

# 특정 파일/테스트 실행
pytest tests/unit/test_session_models.py -v
pytest tests/unit/test_session_models.py::TestSessionModel -v

# 커버리지와 함께 실행
pytest --cov=src --cov-report=html

# 빠른 검증 (루트 디렉토리의 테스트 스크립트)
python test_context_compression.py   # 컨텍스트 압축 테스트
python test_manager_recovery.py      # Manager 복구 테스트
```

### Git (Conventional Commits)

```bash
git add <files>
git commit -m "feat: 새 기능 추가

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 타입: feat, fix, refactor, docs, test, chore
```

---

## 디렉토리 구조 (Clean Architecture)

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
│   ├── storage/              # JSON/SQLite 저장소, Artifact Storage
│   └── config/               # JSON 설정 로더, 환경 검증
│
└── presentation/              # 사용자 인터페이스
    ├── cli/                  # orchestrator.py
    └── tui/                  # tui.py (Textual)

config/                        # 설정 파일
├── agent_config.json         # Worker Agent 설정 (name, role, tools, model)
└── system_config.json        # 시스템 설정 (max_turns, hooks, permission 등)

prompts/                       # Worker Agent 시스템 프롬프트
├── planner.txt               # 계획 수립 전문가
├── coder.txt                 # 코드 작성 전문가 (Reflective Agent)
├── reviewer.txt              # 코드 리뷰 전문가 (🔴 Critical, 🟡 Warning, 🔵 Info)
├── tester.txt                # 테스트 및 검증 전문가
├── committer.txt             # Git 커밋 전문가
├── ideator.txt               # 아이디어 생성 전문가
└── product_manager.txt       # 제품 기획 전문가

~/.better-llm/{project}/       # 실행 데이터 (프로젝트별 독립)
├── sessions/                 # 세션 히스토리 (JSON)
├── logs/                     # 로그 파일
├── data/                     # SQLite DB
└── artifacts/                # Worker 출력 전체 로그
```

---

## 워크플로우

### 일반 작업 흐름

```
사용자 요청
  ↓
[Manager Agent] 작업 분석 및 Worker Tool 호출 결정
  ↓
[Planner Tool] 요구사항 분석 → 계획 수립
  ↓
[Coder Tool] 계획에 따라 코드 작성 (자가 평가 포함)
  ↓
[Reviewer Tool] 코드 품질 검증 (Critical 이슈 있으면 Coder 재호출)
  ↓
[Tester Tool] 테스트 실행 및 검증
  ↓
[Committer Tool] Git 커밋 (선택)
  ↓
작업 완료
```

### Manager Agent 동작 원리

1. 사용자 입력 검증 (`validate_user_input`)
2. **컨텍스트 압축 체크**: 85% 초과 시 자동 압축 수행 (선택적)
3. **컨텍스트 윈도우 체크**: 70% 초과 시 경고, 95% 초과 시 차단
4. 슬라이딩 윈도우로 프롬프트 히스토리 빌드 (최대 20 메시지)
5. ClaudeSDKClient로 스트리밍 실행
6. Manager가 Worker Tool 호출 결정 (대화 히스토리 기반)
7. Worker Tool 실행 (재시도 로직: 지수 백오프, 최대 3회)
8. **Artifact Storage**: 전체 출력 파일 저장 + 요약만 Manager에게 반환
9. Manager가 다음 단계 결정 또는 최종 응답 생성

### Worker Tools 패턴

```python
# Worker Tools (MCP Server)
@tool("execute_planner_task", "계획 수립", {"task_description": str})
async def execute_planner_task(args: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Worker Agent 가져오기
    worker = _WORKER_AGENTS.get("planner")

    # 2. Worker 실행 (스트리밍)
    result = ""
    async for chunk in worker.execute_task(task):
        result += chunk

    # 3. Artifact 저장 + 요약 추출
    summary = _save_and_summarize_output("planner", result)

    # 4. Manager에게 요약만 반환
    return {"content": [{"type": "text", "text": summary}]}
```

### Web UI 워크플로우 (Manager 노드)

**Manager 노드**는 Web UI에서 사용할 수 있는 오케스트레이터 노드로, 등록된 워커들을 병렬로 실행하여 복잡한 작업을 처리합니다.

#### Manager 노드 vs TUI Manager Agent

| 구분 | TUI Manager Agent | Web UI Manager 노드 |
|------|-------------------|---------------------|
| **실행 방식** | Worker Tools를 순차적으로 호출 | 등록된 워커를 병렬로 실행 |
| **워커 선택** | 대화 히스토리 기반 자동 결정 | 사용자가 미리 등록 (체크박스) |
| **사용 시나리오** | 대화형 작업 (TUI) | 워크플로우 자동화 (Web UI) |
| **독립 사용** | 가능 (직접 사용자 요청 처리) | 불가 (최소 1개 워커 필수) |

#### Manager 노드 사용 방법

1. **노드 추가**: 왼쪽 패널에서 "Manager" 버튼 클릭
2. **워커 등록**: Manager 노드 선택 → 오른쪽 "노드 설정" 탭 → 워커 체크박스 선택
3. **작업 설명**: 작업 설명 입력 (등록된 모든 워커에게 동일하게 전달됨)
4. **실행**: 워크플로우 실행 시 Manager가 등록된 워커들을 병렬로 호출

#### Manager 노드 실행 흐름

```
사용자 입력 (initial_input)
  ↓
[Manager 노드] task_description + available_workers
  ↓
병렬 실행 ━━━┳━━━ [Worker 1: planner] → 결과 1
             ┣━━━ [Worker 2: coder] → 결과 2
             ┗━━━ [Worker 3: reviewer] → 결과 3
  ↓
통합 결과 (Markdown 형식)
  ↓
다음 노드로 전달 또는 최종 출력
```

#### 구현 세부사항

**백엔드 (`workflow_executor.py`)**:
```python
async def _execute_manager_node(self, node, ...):
    # 1. 등록된 워커들 병렬 실행
    worker_tasks = []
    for worker_name in available_workers:
        worker = WorkerAgent(config=worker_config)
        worker_tasks.append((worker_name, worker.execute_task(task_description)))

    # 2. 결과 수집 및 통합
    worker_results = {}
    for worker_name, worker_stream in worker_tasks:
        chunks = []
        async for chunk in worker_stream:
            chunks.append(chunk)
        worker_results[worker_name] = "".join(chunks)

    # 3. Markdown 형식으로 통합
    integrated_output = "\n\n".join(
        f"## {worker_name.upper()} 결과\n\n{output}"
        for worker_name, output in worker_results.items()
    )
```

**프론트엔드 (`ManagerNode.tsx`)**:
- 보라색 테마로 Worker 노드와 시각적 구분
- 등록된 워커 목록 표시 (뱃지 형태)
- 작업 설명 미리보기

**노드 설정 패널 (`NodeConfigPanel.tsx`)**:
- 작업 설명 텍스트 영역
- 워커 체크박스 선택 (최소 1개 필수)
- 선택된 워커 개수 표시

---

## 설정 파일

### agent_config.json - Worker Agent 설정

각 Worker의 역할, 도구, 모델 정의:

- **Planner**: read, glob (읽기 전용)
- **Coder**: read, write, edit, glob, grep (bash 제외 - 빌드는 보고만)
- **Reviewer**: read, glob, grep (읽기 전용)
- **Tester**: read, bash, glob (write 제외 - 테스트 작성은 Coder에게 위임)
- **Committer**: bash, read (Git 전용)
- **Ideator**: read, glob (아이디어 생성용)
- **Product Manager**: read, glob, grep (요구사항 분석용)

**중요**: Worker별 도구 제한으로 역할 경계 명확화

### system_config.json - 시스템 설정

```json
{
  "manager": {
    "max_history_messages": 20,  // 슬라이딩 윈도우 크기
    "max_turns": 10               // 최대 턴 수
  },
  "performance": {
    "enable_caching": true,       // 프롬프트 캐싱
    "worker_retry_max_attempts": 3,
    "worker_retry_delay": 2.0
  },
  "security": {
    "max_input_length": 5000,     // 프롬프트 인젝션 방어
    "enable_input_validation": true
  },
  "hooks": {
    "enable_validation": true,    // PreToolUse Hook (입력 검증)
    "enable_monitoring": true     // PostToolUse Hook (실행 시간 로깅)
  },
  "permission": {
    "mode": "acceptEdits"         // acceptEdits | default | bypassPermissions
  },
  "interaction": {
    "enabled": false,             // Human-in-the-Loop
    "allow_questions": true,
    "timeout_seconds": 300
  },
  "context_metadata": {
    "enabled": true               // Worker 메타데이터 추적
  },
  "context_compression": {
    "enabled": true,              // 자동 압축 활성화
    "auto_compress_threshold": 0.85,  // 압축 시작 임계값 (85%)
    "target_reduction_ratio": 0.3,    // 목표 압축 비율 (30%)
    "compressed_dir": "compressed"    // 압축 파일 저장 디렉토리
  }
}
```

### .context.json - 프로젝트 컨텍스트

프로젝트 메타데이터, 코딩 스타일, 테스팅 방침. Worker Agent 초기화 시 자동 로드.

---

## 디버깅

### 로그 확인

```bash
# 최근 로그 확인
tail -100 ~/.better-llm/{project-name}/logs/better-llm.log

# 에러 로그만 확인
tail -50 ~/.better-llm/{project-name}/logs/better-llm-error.log

# 실시간 로그 모니터링
tail -f ~/.better-llm/{project-name}/logs/better-llm.log
```

### Artifact 파일 확인 (Worker 전체 출력)

```bash
# Artifact 디렉토리 확인
ls -la ~/.better-llm/{project-name}/artifacts/

# 특정 Worker 출력 보기
cat ~/.better-llm/{project-name}/artifacts/planner_20250121_143025.txt
```

### 압축된 메시지 확인 (Context Compression)

```bash
# 압축 디렉토리 확인
ls -la ~/.better-llm/{project-name}/compressed/

# 압축된 메시지 보기 (JSON 형식)
cat ~/.better-llm/{project-name}/compressed/agent_planner_20250127_001.txt
```

### TUI에서 Worker 출력 실시간 모니터링

```
실행 중: Ctrl+O → Worker 출력 화면으로 전환
다시: Ctrl+O → Manager 출력 화면으로 복귀
```

### 상세 로깅 활성화

```bash
export LOG_LEVEL=DEBUG
export WORKER_DEBUG_INFO=true
```

### 통합 테스트 실행

```bash
# Manager 복구 메커니즘 테스트
python test_manager_recovery.py

# 컨텍스트 압축 기능 테스트
python test_context_compression.py

# pytest 기반 통합 테스트
pytest tests/integration/ -v
```

---

## 일반적인 작업 패턴

### 새 Worker Agent 추가

1. **프롬프트 작성**: `prompts/new_agent.txt`
2. **설정 추가**: `config/agent_config.json`에 정의
3. **Worker Tool 추가**: `src/infrastructure/mcp/worker_tools.py`에 `@tool` 함수 추가
4. **MCP Server 등록**: `create_worker_tools_server()`에 tool 등록
5. **테스트**: `test_worker_tools.py`에 테스트 케이스 추가

### 설정 변경

- **모델 변경**: `agent_config.json`의 `model` 필드
- **프롬프트 수정**: `prompts/*.txt` 직접 수정
- **재시도 설정**: `system_config.json`의 `performance.worker_retry_*`
- **입력 검증**: `system_config.json`의 `security.*`

### 프롬프트 수정 시 주의사항

- **Manager 프롬프트**: `src/infrastructure/claude/manager_client.py`의 `SYSTEM_PROMPT` 속성 (중복 작업 방지 규칙 포함)
- **Worker 프롬프트**: `prompts/{worker}.txt` (반드시 요약 섹션 포함)
- **요약 형식**: `## 📋 [{Worker 이름} 요약 - Manager 전달용]`으로 시작
- **프롬프트 변경 후**: 구문 검사 후 실제 실행으로 검증 필요

---

## 중요한 제약사항

### 절대 금지 사항

1. **Worker Agent 직접 호출 금지**: 반드시 Manager → Worker Tools → Worker 흐름
2. **query() 사용 금지**: Worker Tools는 ClaudeSDKClient만 사용
3. **CLI 경로 하드코딩 금지**: `get_claude_cli_path()` 사용
4. **입력 검증 생략 금지**: `validate_user_input()` 필수
5. **시크릿 하드코딩 금지**: 환경변수 사용

### 알려진 제약

- 순차 실행만 지원 (병렬 Worker Tool 실행 미지원)
- 최대 턴 수: 10턴 (system_config.json에서 변경 가능)
- 최대 히스토리: 20 메시지 (슬라이딩 윈도우)
- 최대 입력 길이: 5000자 (프롬프트 인젝션 방어)

---

## 문제 해결

### "CLAUDE_CODE_OAUTH_TOKEN 환경변수가 설정되지 않았습니다"
```bash
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'
```

### "Claude CLI not found"
```bash
export CLAUDE_CLI_PATH='/path/to/claude'
# 또는 ~/.claude/local/claude 에 설치
```

### "Worker Tool 호출 실패"
1. `test_worker_tools.py` 실행하여 단독 테스트
2. Worker Agent 설정 확인 (`config/agent_config.json`)
3. 프롬프트 파일 존재 확인 (`prompts/*.txt`)
4. 로그 확인 (`~/.better-llm/{project}/logs/`)

### "Manager가 Worker를 중복 호출"
- Manager 프롬프트의 "중복 작업 방지 규칙" 확인
- Worker 출력 요약에 "✅ 상태: 작업 완료" 포함 여부 확인
- 로그에서 대화 히스토리 확인

### "Worker 출력이 너무 김"
- Artifact Storage 확인: `~/.better-llm/{project}/artifacts/`
- `ENABLE_LLM_SUMMARIZATION=true` 설정 (LLM 기반 요약)

---

---

## 보안 및 성능

### 보안 체크리스트

- [x] CLI 경로 하드코딩 제거 (환경변수 + 자동 탐지)
- [x] 사용자 입력 검증 (프롬프트 인젝션 방어)
- [x] 시크릿 하드코딩 금지 (환경변수 사용)
- [x] 최대 입력 길이 제한 (5000자)
- [x] Hooks 시스템 (금지 패턴 검사: rm -rf /, sudo rm 등)
- [ ] 파일 접근 화이트리스트 (TODO)

### 성능 최적화

- **프롬프트 캐싱**: `enable_caching: true` (API 호출 30-50% 절감)
- **Artifact Storage**: Worker 출력을 파일로 저장 (Manager 컨텍스트 90% 절감)
- **슬라이딩 윈도우**: 최대 20 메시지 (토큰 비용 절감)
- **Worker Tool 재시도**: 지수 백오프, 최대 3회
- **LLM 기반 요약**: 중요 정보 손실 최소화 (ENABLE_LLM_SUMMARIZATION=true)
- **Performance Metrics**: Worker별 토큰 사용량 자동 추적

---

## 최근 주요 개선사항 (요약)

자세한 내용은 `CHANGELOG.md` 참조.

### v4.2 (2025-10-27)
- **Web UI Manager 노드**: 병렬 워커 실행을 위한 오케스트레이터 노드 추가
  - 등록된 워커들을 병렬로 실행 (TUI는 순차 실행)
  - 체크박스로 사용 가능한 워커 선택 (최소 1개 필수)
  - 결과를 Markdown 형식으로 통합하여 다음 노드에 전달
  - 보라색 테마로 Worker 노드와 시각적 구분

### v4.1 (2025-10-27)
- **Context Compression**: 컨텍스트 윈도우 자동 압축 기능 추가
  - 85% 초과 시 자동 압축 수행 (약 30% 컨텍스트 절감)
  - 오래된 메시지를 파일로 저장하고 메타데이터 참조로 대체
  - 첫 번째 사용자 메시지는 항상 보존 (컨텍스트 유지)
  - 필요 시 Worker가 read 도구로 원본 복원 가능
- **Critical Threshold 상향**: 90% → 95% (압축으로 여유 확보)

### v4.0 (2025-10-23)
- **5차 버그 수정 8개**: Manager/Worker Agent, CLI, SDK 안정성 강화 (메모리 누수 방지, 에러 처리 강화)
- **4차 버그 수정 7개**: 전체 코드베이스 안정성 개선 (LLM 응답 파싱, DB 초기화 등)
- **3차 버그 수정 4개**: Presentation Layer 안정성 개선 (TUI 초기화, 비동기 Task 예외 처리)
- **Hooks 시스템**: PreToolUse/PostToolUse Hook (입력 검증, 실행 시간 로깅)
- **Permission Mode 개선**: 환경변수로 동적 변경 가능 (acceptEdits | default | bypassPermissions)

### v3.0 (2025-10-22)
- **Artifact Storage**: Worker 출력을 파일로 저장, Manager 컨텍스트 90% 절감
- **LLM 기반 Intelligent Summarizer**: Claude Haiku로 지능형 요약
- **Performance Metrics**: Worker별 토큰 사용량 자동 추적
- **Context Metadata**: 작업 흐름 자동 추적
- **Human-in-the-Loop**: ask_user Tool로 대화형 의사결정
- **Reflective Agent**: Coder 자가 평가 및 개선 (평균 점수 < 7.0 시 재작성)
- **Ideator/Product Manager Worker**: 기획 단계 지원 강화

### v2.0 (2025-10-20)
- **세션/로그 저장 위치 변경**: `~/.better-llm/{project-name}/`로 이동 (프로젝트별 독립)
- **Worker 중복 호출 버그 수정**: Manager가 완료된 Worker를 재호출하는 문제 해결
- **Critical/High 버그 5개 수정**: 런타임 크래시 제거 (IndexError, AttributeError 등)

---

## 향후 개선 계획

자세한 내용은 `CHANGELOG.md`의 "Unreleased" 섹션 참조.

### 단기 (우선순위 1)
- 병렬 실행 지원: 독립적인 Worker Tool 병렬 실행
- Worker Tool 동적 로딩: 플러그인 아키텍처
- 파일 접근 화이트리스트: 보안 강화

### 중기 (우선순위 2)
- 캐싱 전략 개선: Worker Agent 파일 캐싱
- 구조화된 로깅: JSON 로그 및 모니터링 도구 연동
- 메트릭 대시보드: Worker별 성능 시각화

### 장기 (우선순위 3)
- 자동 복구: 에러 패턴 분석 후 자동 복구 로직
- 마이크로서비스 아키텍처: Worker Tool 분산 실행

**참고**: 최신 개선사항 및 버그 수정 내역은 `CHANGELOG.md` 참조

---

## Claude Agent SDK Best Practice

본 프로젝트는 Claude Agent SDK v0.1.0+의 최신 Best Practice를 모두 적용하고 있습니다.

### 1. ClaudeAgentOptions 사용 ✅

```python
from claude_agent_sdk.types import ClaudeAgentOptions

options = ClaudeAgentOptions(
    model="claude-sonnet-4-5-20250929",
    allowed_tools=["read", "write", "edit"],
    cli_path="/path/to/claude",
    permission_mode="acceptEdits",  # acceptEdits | default | bypassPermissions
    setting_sources=["user", "project"]  # 명시적 설정 (SDK v0.1.0+)
)
```

**주의**: `ClaudeCodeOptions` → `ClaudeAgentOptions` 변경 (SDK v0.1.0+)

### 2. System Prompt 명시적 설정 ✅

- **Manager Agent**: `self.SYSTEM_PROMPT` 속성으로 관리 (`manager_client.py` - 중복 작업 방지 규칙 포함)
- **Worker Agent**: `prompts/*.txt` 파일에서 로드 (`worker_client.py:68-105` - _load_system_prompt 메서드)
- SDK 호출 시 프롬프트에 포함하여 전달 (현재 방식 유지)

```python
# Worker Agent 예시
full_prompt = f"{self.system_prompt}\n\n{task_description}"
async for response in query(prompt=full_prompt, options=options):
    ...
```

### 3. 에러 처리 패턴 ✅

```python
from claude_agent_sdk import (
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
    ClaudeSDKError
)

try:
    async for response in query(prompt, options):
        ...
except CLINotFoundError:
    # Claude CLI 미설치 → 설치 가이드 제공
except ProcessError as e:
    # CLI 프로세스 실행 실패 → exit_code 확인
except CLIJSONDecodeError:
    # CLI 응답 파싱 실패 → CLI 버전 확인 요청
except ClaudeSDKError:
    # 기타 SDK 에러 → 로그 확인 요청
```

**구현 위치**: `sdk_executor.py` (ManagerSDKExecutor 및 WorkerSDKExecutor의 에러 처리 로직 참조)

### 4. 스트리밍 응답 처리 (Template Method Pattern) ✅

```python
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

# 공통 ResponseHandler 추상 클래스 활용
class SDKResponseHandler(ABC):
    def extract_text_from_response(self, response) -> Optional[str]:
        # AssistantMessage → TextBlock/ThinkingBlock 추출
        # ResultMessage → usage 정보만 (텍스트 없음)
        # Fallback → hasattr()로 동적 추출

# Manager/Worker별 구체적인 구현
class ManagerResponseHandler(SDKResponseHandler):
    async def process_response(self, response):
        # usage 정보 추출 → 콜백 호출
        # 텍스트 추출 → yield
```

**구현 위치**: `sdk_executor.py` (SDKResponseHandler 추상 클래스 및 구현체 참조)

### 5. 프롬프트 캐싱 활용 ✅

- **Planner 결과 캐싱**: Planner Worker 결과 캐싱 (LRU + TTL, 애플리케이션 레벨)
- **설정**: `system_config.json`의 `performance.planner_cache_enabled` (기본: True)
- **효과**: 동일 요청 시 API 호출 절감 (최대 100개 캐싱, 1시간 TTL)

**주의**: 이는 Anthropic의 Prompt Caching Beta API가 아닌 애플리케이션 레벨 캐싱입니다.

**구현 위치**: `cache/prompt_cache.py`, `mcp/worker_tools.py` (execute_planner_task 함수 내 캐싱 로직)

### 6. Permission Mode 설정 ✅

| Mode | 설명 | 사용 시나리오 |
|------|------|--------------|
| **acceptEdits** | 파일 편집 자동 승인 (권장) | 프로덕션, CI/CD |
| **default** | 모든 작업 수동 승인 | 대화형 개발 |
| **bypassPermissions** | 모든 작업 자동 승인 | 테스트, 자동화 |
| **plan** | 계획만 수립 (실행 안 함) | 계획 검토 |

```bash
# 환경변수로 동적 변경 (시스템 설정보다 우선)
export PERMISSION_MODE=acceptEdits
```

**구현 위치**: `sdk_executor.py` (PermissionModeResolver 클래스 참조)

### 7. Context 관리 ✅

```python
options = ClaudeAgentOptions(
    max_turns=10,  # 최대 대화 턴 수 (None이면 무제한)
    continue_conversation=False,  # 세션 재개 여부
    setting_sources=["user", "project"]  # 설정 로드 소스
)
```

**Manager Agent 슬라이딩 윈도우**:
- 최대 20개 메시지 유지 (`max_history_messages=20`)
- 첫 번째 사용자 요청 + 최근 메시지 포함
- 컨텍스트 윈도우 사용량 90% 초과 시 경고

**구현 위치**: `manager_client.py` (ManagerAgent 클래스의 슬라이딩 윈도우 구현 참조)

---

## 참고 자료

- [Claude Agent SDK 마이그레이션 가이드](https://docs.claude.com/en/docs/claude-code/sdk/migration-guide.md) ⭐
- [Claude Agent SDK 공식 문서](https://docs.anthropic.com/en/docs/agent-sdk/python)
- [query() vs ClaudeSDKClient](https://docs.anthropic.com/en/docs/agent-sdk/python/query-vs-client)
- [MCP Server 가이드](https://docs.anthropic.com/en/docs/agent-sdk/python/mcp-servers)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

**개발 히스토리**: 상세한 개발 히스토리는 `CHANGELOG.md` 참조

**최종 업데이트**: 2025-10-25 (Claude Agent SDK Best Practice 문서화)
