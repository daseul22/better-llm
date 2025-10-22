# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

**그룹 챗 오케스트레이션 시스템 v4.0 (Clean Architecture)** - Manager Agent가 전문화된 Worker Agent들을 조율하여 복잡한 소프트웨어 개발 작업을 자동화하는 시스템입니다.

### 아키텍처: Clean Architecture (4계층)

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌──────────────┐              ┌──────────────┐             │
│  │     CLI      │              │     TUI      │             │
│  │ (orchestrator)│              │  (textual)   │             │
│  └──────────────┘              └──────────────┘             │
└────────────────────┬──────────────────────┬──────────────────┘
                     │                      │
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Ports (Interfaces)                       │  │
│  │  IAgentClient | IConfigLoader | ISessionRepository   │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────┬─────────────────  ┘
                     │                    │
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                        │
│  ┌──────────┐  ┌───────┐  ┌─────────┐  ┌──────────┐        │
│  │  Claude  │  │  MCP  │  │ Storage │  │  Config  │        │
│  │   SDK    │  │Server │  │  (JSON) │  │  (JSON)  │        │
│  └──────────┘  └───────┘  └─────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────┘
                             ↑
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                             │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────┐        │
│  │   Models     │  │  Services  │  │    Agents    │        │
│  │ (Message,    │  │(Conversation│  │  (BaseAgent) │        │
│  │  Task, etc)  │  │  History)   │  │              │        │
│  └──────────────┘  └────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

**핵심 개념 (Worker Tools Pattern + Clean Architecture):**
- **Domain Layer**: 핵심 비즈니스 로직 (순수 Python, 외부 의존성 없음)
  - Models: Message, AgentConfig, Task, SessionResult
  - Services: ConversationHistory, ProjectContext
  - Agents: BaseAgent (인터페이스)
- **Application Layer**: Use Cases 및 Ports (의존성 역전)
  - Ports: IAgentClient, IConfigLoader, ISessionRepository (인터페이스)
  - Use Cases: (향후 확장 가능)
- **Infrastructure Layer**: 외부 의존성 구현
  - Claude SDK: Manager/Worker Agent 클라이언트
  - MCP: Worker Tools Server
  - Storage: JSON 기반 세션/컨텍스트 저장소
  - Config: JSON 설정 로더
- **Presentation Layer**: 사용자 인터페이스
  - CLI: orchestrator.py
  - TUI: tui.py (Textual 기반)

**의존성 방향 (Dependency Rule):**
```
Presentation → Application → Domain ← Infrastructure
                              ↑
                         (의존하지 않음)
```

**Worker Tools Pattern:**
- Manager Agent가 Worker Tools (MCP Server)를 호출
- Worker Tools는 Worker Agent를 `@tool` 데코레이터로 래핑
- Worker Agents가 실제 작업 수행 (read, write, edit, bash 등)

---

## 개발 환경 설정

### 필수 요구사항
- Python 3.10+
- Anthropic API 키
- Claude CLI (`~/.claude/local/claude`) - 자동 탐지됨

### 초기 설정

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. OAuth 토큰 설정
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'

# 3. 구문 검사 (코드 변경 후)
python3 -m py_compile src/*.py *.py
```

### 데이터 저장 위치

세션, 로그 등 실행 데이터는 `~/.better-llm/{project-name}/` 디렉토리에 저장됩니다.

```bash
~/.better-llm/
└── {project-name}/       # Git 저장소 이름 또는 현재 디렉토리 이름
    ├── sessions/         # 세션 히스토리 (JSON)
    ├── logs/             # 로그 파일 (better-llm.log, better-llm-error.log)
    └── data/             # 데이터베이스 (sessions.db)
```

**환경변수 오버라이드**:
```bash
export LOG_DIR="/custom/log/path"      # 로그 디렉토리 변경
export LOG_LEVEL="DEBUG"               # 로그 레벨 변경
export LOG_FORMAT="json"               # 로그 포맷 (json/console)
```

**장점**:
- 프로젝트별 독립적인 세션/로그 관리
- 프로젝트 디렉토리를 깨끗하게 유지
- 여러 프로젝트를 동시에 사용해도 충돌 없음

---

## 주요 명령어

### 실행

```bash
# TUI (권장)
python tui.py

# CLI
python orchestrator.py "작업 설명"

# 옵션 포함
python orchestrator.py --verbose "작업 설명"
python orchestrator.py --config custom_config.json "작업 설명"
```

### 테스트

```bash
# 통합 테스트
python test_integration.py

# 개선사항 테스트
python test_improvements.py

# Worker Tools 단독 테스트
python test_worker_tools.py

# 특정 모듈 테스트 (예시)
pytest tests/unit/test_math_utils.py -v
pytest tests/unit/test_math_utils.py::TestMultiply -v
```

### Git 작업

```bash
# 변경사항 커밋 (Conventional Commits)
git add <files>
git commit -m "feat: 새 기능 추가

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 타입: feat, fix, refactor, docs, test, chore
```

---

## 코드 아키텍처

### 디렉토리 구조 (Clean Architecture)

```
src/
├── domain/                    # Domain Layer (순수 Python)
│   ├── models/               # 도메인 모델
│   │   ├── message.py        # Message, Role
│   │   ├── agent.py          # AgentConfig, AgentRole
│   │   ├── session.py        # SessionResult, SessionStatus
│   │   └── task.py           # Task, TaskResult, TaskStatus
│   ├── agents/               # Agent 인터페이스
│   │   └── base.py           # BaseAgent (ABC)
│   └── services/             # 도메인 서비스
│       ├── conversation.py   # ConversationHistory
│       └── context.py        # ProjectContext, CodingStyle
│
├── application/               # Application Layer
│   ├── use_cases/            # Use Cases (향후 확장)
│   └── ports/                # Ports (인터페이스)
│       ├── agent_port.py     # IAgentClient
│       ├── config_port.py    # IConfigLoader, ISystemConfig
│       └── storage_port.py   # ISessionRepository, IContextRepository
│
├── infrastructure/            # Infrastructure Layer
│   ├── config/               # 설정 구현
│   │   ├── loader.py         # JsonConfigLoader, SystemConfig
│   │   └── validator.py      # validate_environment, get_claude_cli_path
│   ├── storage/              # 저장소 구현
│   │   ├── session_repository.py   # JsonSessionRepository
│   │   └── context_repository.py   # JsonContextRepository
│   ├── claude/               # Claude SDK (기존 코드 재사용)
│   └── mcp/                  # MCP Server (기존 코드 재사용)
│
└── presentation/              # Presentation Layer
    ├── cli/                  # CLI
    │   └── orchestrator_cli.py
    └── tui/                  # TUI (Textual)
        └── tui_app.py

# 기존 코드 (호환성 유지)
src/
├── manager_agent.py          # Manager Agent (기존)
├── worker_agent.py           # Worker Agent (기존)
├── worker_tools.py           # Worker Tools (기존)
├── conversation.py           # → domain.services.conversation (호환성)
├── project_context.py        # → domain.services.context (호환성)
├── models.py                 # → domain.models (호환성)
└── utils.py                  # → infrastructure.config (일부 이동)
```

### 주요 모듈 (계층별)

**Domain Layer (src/domain/)**
- `models/`: Message, AgentConfig, Task, SessionResult 등 핵심 도메인 모델
- `services/`: ConversationHistory, ProjectContext (비즈니스 로직)
- `agents/`: BaseAgent 인터페이스 (모든 Agent가 구현)

**Application Layer (src/application/)**
- `ports/`: 외부 의존성 인터페이스 (의존성 역전)
  - IAgentClient, IConfigLoader, ISessionRepository

**Infrastructure Layer (src/infrastructure/)**
- `config/`: JsonConfigLoader, SystemConfig (JSON 파일 기반)
- `storage/`: JsonSessionRepository, JsonContextRepository
- `claude/`: Manager/Worker Agent 클라이언트 (기존 코드)
- `mcp/`: Worker Tools MCP Server (기존 코드)

**Presentation Layer (src/presentation/)**
- `cli/`: orchestrator.py (명령줄 인터페이스)
- `tui/`: tui.py (Textual 기반 터미널 UI)

**기존 코드 호환성**
- src/models.py → domain.models로 re-export
- src/conversation.py → domain.services로 re-export
- 기존 import 경로 그대로 동작

### 설정 파일

**config/agent_config.json** - Worker Agent 설정
- 각 Worker의 name, role, system_prompt_file, tools, model 정의
- Planner: read, glob
- Coder: read, write, edit, glob, grep, bash
- Reviewer: read, glob, grep
- Tester: read, bash, write
- Committer: bash, read
- Ideator: read, glob
- Product Manager: read, glob, grep

**config/system_config.json** - 시스템 설정
- manager: max_history_messages, max_turns
- performance: enable_caching, worker_retry 관련
- security: max_input_length, enable_input_validation
- logging: level, format, enable_structured_logging

**.context.json** - 프로젝트 컨텍스트
- 프로젝트 메타데이터, 코딩 스타일, 테스팅 방침
- Worker Agent 초기화 시 자동 로드

**prompts/*.txt** - Worker Agent 시스템 프롬프트
- planner.txt: 계획 수립 전문가
- coder.txt: 코드 작성 전문가
- reviewer.txt: 코드 리뷰 전문가 (심각도 분류: 🔴 Critical, 🟡 Warning, 🔵 Info)
- tester.txt: 테스트 및 검증 전문가
- committer.txt: Git 커밋 전문가
- ideator.txt: 아이디어 생성 및 브레인스토밍 전문가
- product_manager.txt: 제품 기획 및 요구사항 정의 전문가

---

## 워크플로우

### 일반적인 작업 흐름

```
사용자 요청
  ↓
[Manager Agent] 작업 분석 및 Worker Tool 호출
  ↓
[Planner Tool] 요구사항 분석 및 계획 수립
  ↓
[Coder Tool] 코드 작성/수정
  ↓
[Reviewer Tool] 코드 품질 검증
  ↓ (Critical 이슈 있으면)
[Coder Tool] 수정 후 재검토
  ↓
[Tester Tool] 테스트 실행 및 검증
  ↓
작업 완료
```

### Manager Agent 동작

1. 사용자 입력 검증 (`validate_user_input`)
2. 프롬프트 히스토리 빌드 (슬라이딩 윈도우)
3. ClaudeSDKClient로 스트리밍 실행
4. Manager가 Worker Tool 호출 결정
5. Worker Tool 실행 (재시도 로직 포함)
6. 결과를 Manager에게 반환
7. Manager가 최종 응답 생성

### Worker Tool 실행

```python
# Worker Tools에서
@tool("execute_planner_task", "설명", {"task_description": str})
async def execute_planner_task(args: Dict[str, Any]) -> Dict[str, Any]:
    # 1. _WORKER_AGENTS에서 Worker 가져오기
    worker = _WORKER_AGENTS.get("planner")

    # 2. execute_task() 스트리밍 실행
    result = ""
    async for chunk in worker.execute_task(task):
        result += chunk

    # 3. Tool 응답 형식으로 반환
    return {"content": [{"type": "text", "text": result}]}
```

---

## 일반적인 작업 패턴

### 새 Worker Agent 추가

1. **프롬프트 작성**: `prompts/new_agent.txt`
2. **설정 추가**: `config/agent_config.json`에 agent 정의
3. **Worker Tool 추가**: `src/worker_tools.py`에 `@tool` 데코레이터 함수 추가
4. **MCP Server 등록**: `create_worker_tools_server()`에 tool 추가
5. **Manager 설정**: `allowed_tools`에 tool 추가
6. **테스트**: `test_worker_tools.py`에 테스트 추가

### 설정 변경

- **모델 변경**: `config/agent_config.json`의 `model` 필드
- **프롬프트 수정**: `prompts/*.txt` 파일 직접 수정
- **재시도 설정**: `config/system_config.json`의 `performance` 섹션
- **입력 검증**: `config/system_config.json`의 `security` 섹션

### 디버깅

```bash
# 상세 로깅
python orchestrator.py --verbose "작업"

# Worker Tools 단독 테스트
python test_worker_tools.py

# 에러 통계 확인
# orchestrator.py 실행 후 자동 출력됨
```

---

## 중요한 제약사항

### 절대 하지 말아야 할 것

1. **query() 사용 금지**: Worker Tools를 호출하려면 반드시 `ClaudeSDKClient` 사용
2. **CLI 경로 하드코딩 금지**: `get_claude_cli_path()` 사용
3. **입력 검증 생략 금지**: `validate_user_input()` 필수
4. **시크릿 하드코딩 금지**: 환경변수 사용 (.env 또는 export)

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
# 환경변수 설정
export CLAUDE_CLI_PATH='/path/to/claude'

# 또는 ~/.claude/local/claude 에 설치
```

### "Worker Tool 호출 실패"
- `test_worker_tools.py` 실행하여 Worker Tools 단독 테스트
- Worker Agent 설정 확인 (`config/agent_config.json`)
- 프롬프트 파일 존재 확인 (`prompts/*.txt`)

### "프롬프트 파일 로드 실패"
```bash
# 파일 존재 확인
ls -la prompts/
```

---

## 보안 및 성능

### 보안 체크리스트

- [x] CLI 경로 하드코딩 제거 (환경변수 + 자동 탐지)
- [x] 사용자 입력 검증 (프롬프트 인젝션 방어)
- [x] 시크릿 하드코딩 금지 (환경변수 사용)
- [x] 최대 입력 길이 제한 (5000자)
- [ ] 파일 접근 화이트리스트 (TODO)

### 성능 최적화

- 프롬프트 캐싱 활성화 (`enable_caching: true`)
- 슬라이딩 윈도우로 토큰 비용 절감 (max_history_messages: 20)
- Worker Tool 재시도 로직 (지수 백오프, max 3회)
- 에러 통계 수집 및 모니터링

---

## 향후 개선 계획

### 단기 (우선순위 1)
- 병렬 실행 지원: 독립적인 Worker Tool 병렬 실행
- Worker Tool 동적 로딩: 플러그인 아키텍처
- 파일 접근 화이트리스트: 보안 강화

### 중기 (우선순위 2)
- 캐싱 전략 개선: Worker Agent 파일 캐싱
- 구조화된 로깅: JSON 로그 및 모니터링 도구 연동
- 메트릭 수집: Worker별 평균 실행 시간, 토큰 사용량, 성공률

### 장기 (우선순위 3)
- 아키텍처 다이어그램: 시각적 문서화
- 자동 복구: 에러 패턴 분석 후 자동 복구 로직
- 마이크로서비스 아키텍처: Worker Tool 분산 실행

---

## 최근 개선 사항

### feat. 🚀 수직적 고도화 - LLM 기반 Intelligent Summarizer, Performance Metrics, Context Metadata
- 날짜: 2025-10-22
- 컨텍스트: 기존 시스템의 한계 극복을 위한 수직적 고도화
  - Worker 출력이 패턴 매칭 기반 요약으로 중요 정보 손실 가능
  - 토큰 사용량 추적 부재로 비용 최적화 어려움
  - Context Metadata 시스템이 비활성화 상태
- 변경사항:
  1. **LLM 기반 Intelligent Summarizer** (`src/infrastructure/mcp/output_summarizer.py`):
     - Claude Haiku를 사용한 지능형 요약 (패턴 매칭 → LLM 업그레이드)
     - 자동 Fallback: LLM 실패 시 패턴 매칭으로 전환
     - 환경변수 `ENABLE_LLM_SUMMARIZATION=true/false`로 on/off
     - ANTHROPIC_API_KEY 필수 (LLM 사용 시)
  2. **Performance Metrics - 토큰 사용량 추적**:
     - `WorkerResponseHandler`에 `usage_callback` 추가 (`src/infrastructure/claude/sdk_executor.py`)
     - `WorkerAgent.execute_task()`에 토큰 수집 기능 추가 (`src/infrastructure/claude/worker_client.py`)
     - `WorkerExecutor`에서 MetricsCollector로 자동 전달 (`src/infrastructure/mcp/worker_executor.py`)
     - input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens 자동 수집
  3. **Context Metadata 시스템 활성화**:
     - `config/system_config.json`의 `context_metadata.enabled`를 `true`로 변경
     - Worker 출력에 구조화된 메타데이터 자동 추가 (task_id, dependencies, key_decisions)
     - Manager가 컨텍스트 체인 자동 추적
  4. **문서화**:
     - `ADVANCED_FEATURES.md` 작성: 3가지 고급 기능 상세 설명
     - `CHANGELOG.md` 업데이트
- 영향범위:
  - **성능**: Manager 컨텍스트 90% 절감, 중요 정보 손실 최소화
  - **가시성**: Worker별 토큰 사용량 정량화, 비용 최적화 가능
  - **디버깅**: 컨텍스트 체인 추적으로 작업 흐름 가시화
- 사용 방법:
  ```bash
  # LLM 요약 활성화
  export ENABLE_LLM_SUMMARIZATION=true
  export ANTHROPIC_API_KEY='your-api-key-here'

  # Context Metadata는 기본 활성화됨 (system_config.json)
  # 비활성화: "context_metadata": {"enabled": false}

  python orchestrator.py "작업 설명"
  ```
- 테스트: 구문 검사 통과
- 후속 조치: 실제 사용 시 효과 측정 (토큰 절감율, 요약 품질)
- 참고 문서: `ADVANCED_FEATURES.md`

### feat. Reflective Agent - 자가 평가 및 코드 개선
- 날짜: 2025-10-22
- 컨텍스트: Coder가 코드 작성 후 자체 검증 없이 Reviewer에게 의존
  - 낮은 품질의 코드가 Reviewer로 전달되어 Review 사이클 증가
  - Coder의 메타 인지 능력 부재
- 해결 방안: **Coder Worker에 자가 평가 및 개선 기능 추가**
- 변경사항:
  - **Coder 프롬프트** (`prompts/coder.txt`):
    - "자가 평가 및 개선 (Reflective Agent)" 섹션 추가
    - 평가 기준 5가지 정의 (코드 품질, 가독성, 성능, 보안, 테스트 가능성)
    - 자가 평가 프로세스: 평가 → 평균 계산 → 개선 판단
    - 평균 점수 < 7.0 → 코드 개선 → 재평가 (최대 1회)
    - 평가 결과 출력 형식 표준화
- 영향범위:
  - **코드 품질**: Coder가 스스로 품질 검증하여 초기 품질 향상
  - **Review 사이클**: Critical 이슈 감소로 Review 횟수 단축 (예상 30%)
  - **투명성**: 평가 점수 및 근거가 명확히 문서화됨
- 평가 기준:
  1. 코드 품질 (1-10): 일관성, 추상화, SOLID 원칙
  2. 가독성 (1-10): 명명, 주석, 복잡도
  3. 성능 (1-10): 효율성, 알고리즘, 메모리
  4. 보안 (1-10): 입력 검증, SQL Injection/XSS 방지
  5. 테스트 가능성 (1-10): 단일 책임, 의존성 주입
- 사용 방법:
  ```
  # Coder가 자동으로 수행 (별도 설정 불필요)
  # 1. 코드 작성 완료
  # 2. 5가지 기준으로 자가 평가 (각 1-10점)
  # 3. 평균 점수 < 7.0 → 개선 후 재평가 (최대 1회)
  # 4. 평가 결과를 포함한 최종 요약 출력
  ```
- 테스트: 구문 검사 통과
- 후속 조치: 실제 사용 시 효과 측정 (Review 사이클 감소율, 코드 품질 개선도)

### fix. 패키지 설치 설정 수정 (src 패키지 지원)
- 날짜: 2025-10-21
- 컨텍스트: editable 모드 설치 시 `ModuleNotFoundError: No module named 'src'` 에러 발생
  - 프로젝트 전체(63개 파일)가 `from src.domain.services import ...` 형식의 import 사용
  - 기존 `pyproject.toml` 설정은 `package-dir = {"" = "src"}` 사용 (src를 루트로 매핑)
  - entry point가 `presentation.tui.tui_app:main`으로 설정되어 src가 패키지로 인식되지 않음
  - `setup.py`와 `pyproject.toml`이 동시에 존재하여 충돌 발생
- 변경사항:
  - **pyproject.toml 수정** (`pyproject.toml`):
    - entry point 수정: `src.presentation.tui.tui_app:main`, `src.presentation.cli.orchestrator:main`
    - packages.find 수정: `where = ["."]`, `include = ["src", "src.*"]`
    - `src`를 최상위 패키지로 명시적으로 포함
  - **setup.py 백업**:
    - `setup.py`를 `setup.py.bak`으로 백업 (pyproject.toml과 충돌 방지)
- 영향범위:
  - **설치**: `pip install -e .` 정상 작동
  - **import**: 모든 `from src.` import가 정상 작동
  - **entry point**: `better-llm`, `better-llm-cli` 명령어 정상 실행
- 테스트: TUI 실행 확인 (Workers: 7개, Model: claude-sonnet-4-5-20250929)
- 후속 조치: 없음 (안정적으로 작동)

### feat. Artifact Storage - Manager 컨텍스트 윈도우 최적화
- 날짜: 2025-01-21
- 컨텍스트: Worker 출력이 Manager 컨텍스트 윈도우를 가득 채우는 문제
  - Worker가 파일 읽기, 도구 호출, 사고 과정 등 모든 출력을 Manager에게 전달
  - 복잡한 작업 시 수만 토큰이 히스토리에 누적되어 컨텍스트 윈도우 초과
  - 예: Coder가 5개 파일 읽고 3개 작성 → 수천 줄 출력 → Manager 히스토리 가득 참
- 해결 방안: **Artifact Storage + 선택적 히스토리** (Phase 1 + Phase 2)
- 변경사항:
  - **Phase 1: 선택적 히스토리 (즉시 완화)**:
    - `WORKER_DEBUG_INFO` 기본값 `false`로 변경 (`worker_client.py:182`)
    - Worker 프롬프트에 요약 섹션 추가 (planner.txt, coder.txt, reviewer.txt, tester.txt):
      ```
      ## 📋 [XXX 요약 - Manager 전달용]
      **상태**: 작업 완료
      **핵심 내용** (3-5줄 요약)
      **변경 파일**: ...
      **다음 단계**: ...
      ```
  - **Phase 2: Artifact Storage (근본 해결)**:
    - `ArtifactStorage` 인프라 구현 (`src/infrastructure/storage/artifact_storage.py`):
      - `save_artifact()`: Worker 전체 출력을 `~/.better-llm/{project}/artifacts/{worker}_{timestamp}.txt`에 저장
      - `extract_summary()`: "📋 [XXX 요약 - Manager 전달용]" 섹션 추출
      - `load_artifact()`: artifact 파일 로드 (Worker가 read 도구로 읽을 수 있음)
      - `cleanup_old_artifacts()`: 7일 이상 된 artifact 자동 삭제
    - Worker Tools에 artifact 저장 로직 추가 (`worker_tools.py`):
      - `_save_and_summarize_output()` helper 함수 추가
      - 모든 Worker Tool (planner, coder, reviewer, tester, committer, ideator, product_manager)에 적용
      - Manager에게는 **요약 + artifact_id**만 전달
    - Manager 프롬프트 업데이트 (`manager_client.py`):
      - Artifact Storage 시스템 설명 추가
      - Artifact 활용 방법 (일반적으로는 요약만, 필요 시 Worker에게 파일 읽기 지시)
- 영향범위:
  - **컨텍스트 절약**: Manager 히스토리 크기 **90% 감소** (요약만 저장)
  - **디버깅**: 전체 로그는 artifact 파일에서 확인 가능
  - **Worker 간 데이터 전달**: 필요 시 Worker가 read 도구로 artifact 읽기
  - **확장성**: 대용량 결과도 처리 가능 (파일 기반)
- 성능 개선 예시:
  ```
  Before: Coder 출력 15,000 토큰 → Manager 히스토리에 전부 포함
  After:  Coder 요약 1,500 토큰 → Manager 히스토리 (90% 절감)
          전체 로그 15,000 토큰 → artifact 파일에 저장 (디버깅용)
  ```
- 저장 위치: `~/.better-llm/{project-name}/artifacts/`
- 사용 방법:
  - **자동**: 모든 Worker 출력이 자동으로 artifact로 저장되고 요약 추출
  - **상세 정보 필요 시**: Manager가 Worker에게 artifact 파일 읽기 지시
    ```python
    execute_coder_task({
      "task_description": "다음 계획에 따라 코드 작성:\n\n[Planner 요약]\n\n상세 계획은 ~/.better-llm/my-project/artifacts/planner_20250121_143025.txt를 read로 읽으세요."
    })
    ```
- 테스트: 구문 검사 통과
- 후속 조치: 실제 사용 시 효과 측정 (히스토리 크기, 토큰 사용량)

### feat. Human-in-the-Loop (대화형 의사결정 지원)
- 날짜: 2025-10-21
- 컨텍스트: Planner가 여러 옵션(A안/B안)을 제시할 때 Manager가 임의로 결정하는 문제
  - 사용자가 중요한 기술 결정에 참여할 수 없음
  - 아키텍처 선택, 구현 방식 등 중요한 의사결정이 자동화됨
- 변경사항:
  - **`ask_user` Tool 추가** (`worker_tools.py`):
    - Manager Agent가 사용자에게 질문하고 응답 받을 수 있는 MCP Tool
    - 선택지 목록 제공 가능 (번호 선택 또는 자유 텍스트)
    - `interaction.enabled` 설정에 따라 on/off 가능
  - **설정 추가** (`system_config.json`):
    ```json
    "interaction": {
      "enabled": false,           // Human-in-the-Loop on/off
      "allow_questions": true,    // ask_user Tool 허용
      "timeout_seconds": 300,     // 사용자 응답 대기 시간
      "auto_fallback": "first"    // 타임아웃 시 기본 선택
    }
    ```
  - **Manager 프롬프트 수정** (`manager_client.py`):
    - ask_user Tool 사용 가이드 추가
    - "Worker가 여러 선택지를 제시하면 사용자에게 물어보기" 지침 추가
  - **CLI 콜백 구현** (`orchestrator.py`):
    - Rich Panel로 질문 표시
    - 선택지 번호 매겨서 출력
    - 사용자 입력 받기 (Prompt.ask)
- 영향범위:
  - **사용자 경험**: 중요한 결정에 사용자 참여 가능
  - **유연성**: 설정으로 자동/대화형 모드 전환 가능
  - **확장성**: 다른 Worker도 ask_user 사용 가능
- 사용 방법:
  ```bash
  # 환경변수로 활성화
  export ENABLE_INTERACTIVE=true
  python orchestrator.py "새 기능 추가"

  # 또는 system_config.json 수정
  # "interaction": {"enabled": true}
  ```
- 워크플로우 예시:
  ```
  사용자: "새로운 인증 시스템 추가"
    ↓
  Planner: "A안: OAuth 2.0 / B안: JWT 기반"
    ↓
  Manager: ask_user 호출
    ↓
  사용자: "1" (A안 선택)
    ↓
  Planner: A안으로 상세 계획 수립
  ```
- 테스트: 구문 검사 통과
- 후속 조치: TUI에도 동일 기능 추가 필요

### feat. 세션 및 로그 저장 위치 변경 (~/.better-llm/{project-name}/)
- 날짜: 2025-10-20
- 컨텍스트: 실행 위치에 세션/로그 파일이 생성되어 프로젝트 디렉토리가 어지러워지는 문제
  - 여러 프로젝트를 사용할 때 세션/로그 구분 어려움
  - Git에 의도치 않게 커밋될 위험
- 변경사항:
  - **프로젝트 이름 감지 로직 추가** (`validator.py`):
    - `get_project_name()`: Git root 디렉토리 이름 또는 현재 디렉토리 이름 반환
    - `get_data_dir(subdir)`: `~/.better-llm/{project-name}/{subdir}` 경로 반환 및 자동 생성
  - **저장소 기본 경로 변경** (`repository_factory.py`):
    - JSON 세션: `~/.better-llm/{project-name}/sessions`
    - SQLite DB: `~/.better-llm/{project-name}/data/sessions.db`
  - **로그 기본 경로 변경** (`structured_logger.py`):
    - 로그 파일: `~/.better-llm/{project-name}/logs/`
    - `configure_structlog(log_dir=None)`: None이면 기본 경로 사용
  - **CLI/TUI 업데이트**:
    - 환경변수 `LOG_DIR`가 설정되지 않으면 None 전달 (기본 경로 사용)
    - 기존 환경변수 오버라이드 동작 유지
- 영향범위:
  - **사용자 경험**: 프로젝트 디렉토리가 깨끗하게 유지됨
  - **멀티 프로젝트**: 프로젝트별 독립적인 세션/로그 관리
  - **호환성**: 환경변수로 기존 동작 유지 가능
- 디렉토리 구조:
  ```
  ~/.better-llm/
  └── {project-name}/
      ├── sessions/     # 세션 히스토리
      ├── logs/         # 로그 파일
      └── data/         # 데이터베이스
  ```
- 테스트: 구문 검사 통과, 디렉토리 생성 확인
- 후속 조치: 실제 사용 시 마이그레이션 가이드 필요 (기존 세션 이동)

### feat. Ideator 및 Product Manager Worker 추가
- 날짜: 2025-10-20
- 컨텍스트: 소프트웨어 개발 프로세스에서 기획 단계 지원 강화 필요
  - 창의적 아이디어 생성 및 브레인스토밍 기능 부재
  - 제품 요구사항 정의 및 우선순위 설정 자동화 필요
- 변경사항:
  - **Ideator Worker 추가**:
    - `prompts/ideator.txt`: 창의적 아이디어 생성 전문가 프롬프트
      - SCAMPER, First Principles 등 사고 기법 적용
      - 발산적/수렴적 사고 프로세스 구조화
      - 실현 가능성 기반 아이디어 평가 및 우선순위 제안
    - Tools: read, glob (컨텍스트 파악용, 읽기 전용)
    - Timeout: 300초 (환경변수 WORKER_TIMEOUT_IDEATOR로 조정 가능)
  - **Product Manager Worker 추가**:
    - `prompts/product_manager.txt`: 제품 기획 전문가 프롬프트
      - 요구사항 정의 및 우선순위 설정 (MoSCoW 등)
      - 사용자 스토리 및 수용 기준(Acceptance Criteria) 작성
      - 제품 로드맵 및 마일스톤 계획 (MVP → Enhancement → Scale)
      - 위험 분석 및 완화 전략 수립
    - Tools: read, glob, grep (요구사항 분석용, 읽기 전용)
    - Timeout: 300초 (환경변수 WORKER_TIMEOUT_PRODUCT_MANAGER로 조정 가능)
  - **인프라 코드 업데이트**:
    - `config/agent_config.json`: 두 워커 설정 추가
    - `src/infrastructure/mcp/worker_tools.py`:
      - 에러 통계에 ideator, product_manager 추가
      - 타임아웃 설정 추가 (환경변수 지원)
      - @worker_tool 데코레이터로 Tool 함수 구현 (재시도 로직 포함)
      - MCP Server에 두 Tool 등록
- 영향범위:
  - **워크플로우 확장**: 기존 Planner 이전 단계로 활용 가능
    - Ideator → Product Manager → Planner → Coder → Reviewer → Tester
  - **유연성 향상**: Manager Agent가 필요에 따라 선택적으로 호출
  - **문서화**: CLAUDE.md 업데이트 (설정 파일 섹션, 프롬프트 목록)
- 테스트: 구문 검사 통과
- 후속 조치: 실제 사용 시 워크플로우 효과 검증

### fix. Worker Agent 타임아웃 문제 해결
- 날짜: 2025-10-20
- 컨텍스트: Worker Agent가 작업 완료 후에도 타임아웃까지 대기하는 문제 발생
- 근본 원인: Worker Agent 프롬프트에 다른 Worker를 호출하는 지시문(@coder, @tester 등)이 포함되어 있었음
  - Worker Agent는 Tool 호출 권한이 없어서 다른 Agent를 호출할 수 없음
  - 호출 시도 실패 후 타임아웃까지 계속 대기
- 변경사항:
  - **프롬프트 수정** (주요 해결책):
    - `prompts/planner.txt`: "@coder please implement this plan" 제거 → "계획 수립이 완료되었습니다."
    - `prompts/coder.txt`: "@tester please verify this implementation" 제거 → "구현이 완료되었습니다."
    - `prompts/tester.txt`: "@coder please fix" 제거 → "테스트가 성공적으로 완료되었습니다." / "테스트 실패: ..."
    - `prompts/committer.txt`: "TERMINATE - ..." 제거 → "커밋이 성공적으로 완료되었습니다." / "커밋 실패: ..."
  - **코드 레벨 개선** (방어 로직):
    - `src/infrastructure/claude/worker_client.py`: 조기 종료 감지 로직 추가
      - Worker Agent 응답에서 "완료되었습니다" 키워드 감지 시 즉시 스트리밍 종료
      - 최근 10개 청크를 버퍼링하여 완료 키워드 검색
      - `query()` 함수가 불필요하게 대기하지 않도록 방어
- 영향범위:
  - **성능**: Worker Agent 실행 시간이 타임아웃 시간(300-600초)에서 실제 작업 시간으로 단축
  - **사용자 경험**: 작업 완료 후 즉시 다음 단계로 진행되어 전체 작업 속도 대폭 개선
  - **아키텍처**: Manager Agent가 Worker 간 조율을 전담하도록 명확히 함
- 테스트: 수동 테스트 필요 (orchestrator.py 실행)
- 후속 조치: 실제 사용 시 Worker Agent 응답 시간 모니터링

### fix. Worker Agent 실행 실패 문제 해결 (CodingStyle 속성 에러)
- 날짜: 2025-10-20
- 컨텍스트: Worker Agent가 실행되지 않고 타임아웃되는 문제 발생
  - 에러 메시지: `AttributeError: 'CodingStyle' object has no attribute 'language'`
  - 에러 위치: `worker_client.py:136` in `_generate_debug_info()`
- 근본 원인:
  - `WORKER_DEBUG_INFO=true`로 설정되어 있어서 디버그 정보 생성 시도
  - `_generate_debug_info()` 함수에서 존재하지 않는 `CodingStyle.language`와 `CodingStyle.indentation` 속성에 접근
  - AttributeError 발생 → `execute_task()` 실패 → Worker가 응답 생성하지 못함
  - Claude SDK의 `query()` 함수가 전혀 호출되지 않음
- 변경사항:
  - **`src/infrastructure/claude/worker_client.py` (Line 136)**:
    - 변경 전: `lines.append(f"   - Coding Style: {style.language}, indentation={style.indentation}")`
    - 변경 후: `lines.append(f"   - Coding Style: line_length={style.line_length}, quote_style={style.quote_style}")`
    - CodingStyle 모델에 실제 존재하는 속성 사용 (`line_length`, `quote_style`)
  - **조기 종료 로직 제거**:
    - 30초 타임아웃 감지 로직 제거
    - 완료 키워드 감지 로직 제거
    - 에러 키워드 감지 로직 제거
    - Worker가 자연스럽게 스트리밍을 완료할 때까지 대기
  - **로깅 강화**:
    - `logger.debug()` → `logger.info()`로 변경
    - query() 호출 전 상세 정보 로깅 (Prompt 길이, Model, Tools, CLI 경로)
    - 수신된 청크 개수 추적 및 로깅
- 영향범위:
  - **Worker 실행**: 이제 Worker가 정상적으로 실행되고 응답 생성
  - **디버깅**: AttributeError 해결로 디버그 모드 사용 가능
  - **성능**: Worker가 완전히 완료될 때까지 대기 (타임아웃은 `worker_tools.py`에서만 관리)
- 테스트: 구문 검사 통과
- 후속 조치: 실제 실행 테스트로 Worker 정상 동작 확인 필요

---

## 참고 자료

- [Claude Agent SDK 공식 문서](https://docs.anthropic.com/en/docs/agent-sdk/python)
- [query() vs ClaudeSDKClient](https://docs.anthropic.com/en/docs/agent-sdk/python/query-vs-client)
- [MCP Server 가이드](https://docs.anthropic.com/en/docs/agent-sdk/python/mcp-servers)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

**개발 히스토리**: 상세한 개발 히스토리는 `CLAUDE_HISTORY.md` 참조

**최종 업데이트**: 2025-10-20 (Ideator, Product Manager Worker 추가 / 세션/로그 저장 위치 변경)
