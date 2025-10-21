# 그룹 챗 오케스트레이션 시스템 (MVP v0.1)

여러 Claude 에이전트가 하나의 대화 공간에서 협업하여 복잡한 소프트웨어 개발 작업을 자동화하는 오케스트레이션 시스템입니다.

## 특징

- **Worker Tools Architecture**: Manager Agent가 Worker Tools를 자동으로 호출하여 작업 수행
- **특수화된 에이전트**: 계획(Planner), 구현(Coder), 테스트(Tester) 역할 분리
- **Claude Agent SDK**: 모든 Agent가 Claude Agent SDK 기반으로 구현
- **실시간 스트리밍**: Manager와 Worker의 응답을 실시간으로 확인
- **TUI & CLI**: Claude Code 스타일 TUI와 간단한 CLI 제공

## 시스템 요구사항

- Python 3.10 이상
- Anthropic API 키

## 설치

### 방법 1: 자동 설치 (권장) 🚀

**한 번의 스크립트 실행으로 글로벌 설치:**

```bash
git clone https://github.com/simdaseul/better-llm.git
cd better-llm
./install.sh
```

설치 스크립트가 자동으로 다음을 수행합니다:
- Python 버전 체크 (3.10+)
- 설치 방법 선택 (pipx 또는 pip)
- 의존성 설치
- 환경변수 설정 가이드
- 설치 검증

**설치 후 사용:**

```bash
# TUI 모드
better-llm

# CLI 모드
better-llm-cli "작업 설명"
```

### 방법 2: 수동 설치 (개발자용)

**1. 저장소 클론 및 이동**

```bash
git clone https://github.com/simdaseul/better-llm.git
cd better-llm
```

**2. 의존성 설치**

```bash
# pipx 사용 (권장)
pipx install -e .

# 또는 pip 사용
pip install -e .
```

**3. 환경 변수 설정**

```bash
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'
```

또는 `.env` 파일 생성:

```bash
echo "CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here" > .env
```

또는 셸 설정 파일에 영구 추가:

```bash
# bash 사용자
echo "export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'" >> ~/.bashrc
source ~/.bashrc

# zsh 사용자
echo "export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'" >> ~/.zshrc
source ~/.zshrc
```

## 사용법

### 방법 1: TUI (Terminal User Interface) - Claude Code 스타일 💻 (권장)

```bash
# 글로벌 설치 후
better-llm

# 또는 저장소에서 직접 실행
python tui.py
```

터미널에서 Claude Code처럼 사용할 수 있는 인터랙티브 UI가 실행됩니다.

**TUI 기능:**
- 🖥️ Claude Code 스타일 터미널 인터페이스
- 🤖 Manager Agent가 자동으로 Worker Tools 호출
- 📊 실시간 Markdown 렌더링 및 Syntax highlighting
- ⚡ 간단한 사용법: 텍스트 입력 후 Enter
- ⌨️ 키보드 단축키
  - `Enter`: 작업 실행
  - `Ctrl+N`: 새 세션 시작
  - `Ctrl+C`: 종료
- 💾 세션 자동 저장 (sessions/ 디렉토리)

### 방법 2: CLI (Command Line Interface)

```bash
# 글로벌 설치 후
better-llm-cli "작업 설명"

# 또는 저장소에서 직접 실행
python orchestrator.py "작업 설명"
```

### 예시

```bash
# 신규 기능 개발
better-llm-cli "FastAPI로 /users CRUD 엔드포인트 구현해줘"

# 버그 수정
better-llm-cli "로그인 API에서 500 에러 나는 버그 수정해줘"

# 리팩토링
better-llm-cli "payment.py 모듈을 클래스 기반으로 리팩토링해줘"

# 저장소에서 직접 실행
python orchestrator.py "FastAPI로 /users CRUD 엔드포인트 구현해줘"
```

### 옵션

```bash
# 상세 로깅 활성화
better-llm-cli --verbose "작업 설명"

# 커스텀 설정 파일 사용
better-llm-cli --config custom_config.json "작업 설명"

# 도움말
better-llm --help
better-llm-cli --help
```

## 사용자 개입

각 에이전트 응답 후 5초 대기하며, 다음 옵션을 선택할 수 있습니다:

- **Enter**: 다음 에이전트로 자동 진행
- **/pause**: 일시정지하고 메시지 입력
- **/stop**: 즉시 종료

## 작업 흐름

일반적인 작업은 다음과 같이 진행됩니다:

```
사용자 요청
    ↓
[1] 🧠 Planner: 요구사항 분석 및 계획 수립
    ↓
[2] 💻 Coder: 코드 작성/수정
    ↓
[3] 🧪 Tester: 테스트 실행 및 검증
    ↓
작업 완료 (TERMINATE)
```

### 에이전트 명시 요청

메시지에 `@agent_name`을 포함하여 특정 에이전트를 직접 호출할 수 있습니다:

```
@coder 결제 모듈에 refund 함수 추가해줘
@tester 통합 테스트도 실행해줘
```

## 프로젝트 구조

```
better-llm/
├── orchestrator.py          # 메인 실행 파일
├── requirements.txt         # 의존성
├── README.md                # 이 파일
├── config/
│   └── agent_config.json    # 에이전트 설정
├── prompts/
│   ├── planner.txt          # Planner 시스템 프롬프트
│   ├── coder.txt            # Coder 시스템 프롬프트
│   └── tester.txt           # Tester 시스템 프롬프트
├── src/
│   ├── __init__.py
│   ├── models.py            # 데이터 모델
│   ├── agents.py            # Agent 클래스
│   ├── chat_manager.py      # 라우팅 로직
│   ├── conversation.py      # 대화 히스토리
│   └── utils.py             # 유틸리티
├── tests/                   # 테스트 (TODO)
└── sessions/                # 세션 히스토리 저장
```

## 설정

### 에이전트 설정 (config/agent_config.json)

```json
{
  "agents": [
    {
      "name": "planner",
      "role": "계획 수립",
      "system_prompt_file": "prompts/planner.txt",
      "tools": ["read", "glob"],
      "model": "claude-sonnet-4"
    }
  ]
}
```

### 시스템 프롬프트 커스터마이징

`prompts/` 디렉토리의 `.txt` 파일을 수정하여 각 에이전트의 행동을 변경할 수 있습니다.

### 워크플로우 안정성 설정

#### 타임아웃 설정

각 Worker의 실행 타임아웃을 환경변수로 설정할 수 있습니다:

```bash
# .env 파일에 추가
WORKER_TIMEOUT_PLANNER=300    # Planner: 5분 (기본값)
WORKER_TIMEOUT_CODER=600      # Coder: 10분 (기본값)
WORKER_TIMEOUT_REVIEWER=300   # Reviewer: 5분 (기본값)
WORKER_TIMEOUT_TESTER=600     # Tester: 10분 (기본값)
WORKER_TIMEOUT_COMMITTER=180  # Committer: 3분 (기본값)
```

타임아웃 초과 시 작업이 중단되고 사용자에게 알림이 표시됩니다.

#### 무한 루프 방지

Manager Agent는 다음 규칙으로 무한 루프를 방지합니다:

- **Review → Coder → Review 사이클**: 최대 3회 반복
- 3회 초과 시 자동 중단 및 사용자 개입 요청
- 반복 횟수를 실시간으로 표시 (예: "Review 사이클 1/3")

설정 조정 (`config/system_config.json`):

```json
{
  "workflow_limits": {
    "max_retry_cycles": 3,
    "max_review_iterations": 3,
    "max_coder_retries": 2
  }
}
```

#### 리소스 관리

- **자동 세션 종료**: try-finally 블록으로 모든 리소스 정리 보장
- **메모리 누수 방지**: Worker Agent 실행 후 자동 cleanup
- **에러 로깅**: 모든 예외에 대한 스택 트레이스 자동 기록

### 구조화된 로깅 설정 (Priority 2 구현)

Better-LLM은 `structlog` 기반의 구조화된 로깅을 지원합니다.

#### 환경변수로 설정

```bash
# .env 파일에 추가
LOG_LEVEL=INFO          # 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_FORMAT=json         # 출력 형식 (json 또는 console)
LOG_DIR=logs            # 로그 파일 디렉토리
```

또는 셸에서 직접 설정:

```bash
export LOG_LEVEL=INFO
export LOG_FORMAT=json
export LOG_DIR=logs
```

#### 로그 파일

로그는 자동으로 다음과 같이 저장됩니다:

- `logs/better-llm.log`: 전체 로그 (10MB 로테이션, 5개 백업)
- `logs/better-llm-error.log`: 에러 로그만 (5MB 로테이션, 3개 백업)
- `logs/better-llm-debug.log`: DEBUG 레벨일 때만 생성 (20MB 로테이션, 3개 백업)

모든 로그 파일은 UTF-8 인코딩으로 저장되며, 파일명/함수명/줄번호 정보가 자동으로 포함됩니다.

#### JSON 로그 형식 예시

```json
{
  "event": "Worker agent initialized",
  "worker_name": "planner",
  "role": "요구사항 분석 및 계획 수립",
  "model": "claude-sonnet-4-5-20250929",
  "session_id": "abc123",
  "pathname": "src/infrastructure/mcp/worker_tools.py",
  "func_name": "initialize_workers",
  "lineno": 427,
  "timestamp": "2025-01-20T10:30:00.123456Z",
  "level": "info"
}
```

#### 에러 추적

Better-LLM은 내장 에러 추적 시스템을 제공합니다.

**자동 에러 추적:**

모든 에러는 자동으로 추적되며, 다음 정보를 포함합니다:

- 에러 타입 및 메시지
- 발생 시각 (ISO 8601 형식)
- 컨텍스트 정보 (worker_name, task_id 등)
- 스택 트레이스 (exc_info 포함)

**프로그래밍 방식 에러 추적:**

```python
from src.infrastructure.logging import track_error, get_error_stats

# 에러 추적
try:
    ...
except Exception as e:
    track_error(e, "context_name", worker_name="planner")

# 에러 통계 조회
stats = get_error_stats()
print(stats["total_errors"])
print(stats["error_counts"])  # 에러 타입별 횟수
print(stats["recent_errors"][:5])  # 최근 5개 에러
```

**동시성 안전성:**

에러 추적 모듈은 `threading.Lock`을 사용하여 멀티스레드 환경에서도 안전하게 작동합니다.

에러 통계는 TUI에서 실시간으로 확인할 수 있습니다.

## 성능 최적화

Better-LLM은 다음과 같은 성능 최적화 기능을 제공합니다:

### 1. 비동기 메트릭 수집

메트릭 수집이 메인 워크플로우를 블로킹하지 않도록 백그라운드 스레드에서 비동기적으로 처리합니다.

**특징:**
- 큐 기반 버퍼링 (기본 1000개)
- 주기적 플러시 (기본 5초)
- 메모리 효율적인 배치 처리
- 통계 추적 (히트율, 큐 크기 등)

**설정:**

```json
{
  "performance": {
    "enable_async_metrics": true,
    "metrics_buffer_size": 1000,
    "metrics_flush_interval": 5.0
  }
}
```

### 2. 프롬프트 캐싱

중복 프롬프트 호출을 방지하여 API 비용과 응답 시간을 절감합니다.

**특징:**
- LRU (Least Recently Used) 캐시 정책
- TTL (Time-To-Live) 기반 만료
- 스레드 세이프 구현
- 캐시 히트율 모니터링

**설정:**

```json
{
  "performance": {
    "enable_caching": true,
    "cache_ttl_seconds": 3600,
    "cache_max_size": 100
  }
}
```

**사용 예시:**

```python
from src.infrastructure.cache import PromptCache

cache = PromptCache(max_size=100, default_ttl=3600.0)

# 캐시에 저장
cache.set("What is Python?", "Python is a programming language")

# 캐시에서 조회
response = cache.get("What is Python?")

# 통계 확인
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
```

### 3. 세션 저장 최적화

세션 데이터 저장 시 압축 및 백그라운드 저장을 지원하여 성능을 향상시킵니다.

**특징:**
- **압축 저장**: gzip으로 파일 크기 30% 이상 절감
- **백그라운드 저장**: 별도 스레드에서 비동기 저장
- **증분 저장**: 변경된 데이터만 추가 저장 (향후 구현)

**설정:**

```json
{
  "performance": {
    "enable_session_compression": true,
    "enable_background_save": true
  }
}
```

**사용 예시:**

```python
from src.infrastructure.storage import OptimizedSessionRepository

# 최적화된 저장소 생성
repo = OptimizedSessionRepository(
    sessions_dir="sessions",
    enable_compression=True,
    enable_background_save=True
)

# 세션 저장 (비동기)
repo.save(session_id, user_request, history, result)

# 종료 시 남은 작업 플러시
repo.stop()
```

### 4. 성능 설정 전체 예시

`config/system_config.json`:

```json
{
  "performance": {
    "enable_caching": true,
    "worker_retry_enabled": true,
    "worker_retry_max_attempts": 3,
    "worker_retry_base_delay": 1.0,
    "worker_retry_max_delay": 30.0,
    "worker_retry_jitter": 0.1,
    "worker_retry_exponential": true,
    "metrics_buffer_size": 1000,
    "metrics_flush_interval": 5.0,
    "cache_ttl_seconds": 3600,
    "cache_max_size": 100,
    "enable_session_compression": true,
    "enable_background_save": true,
    "enable_async_metrics": true
  }
}
```

### 5. 성능 모니터링

**메트릭 수집기 통계:**

```python
from src.infrastructure.metrics import AsyncMetricsCollector

stats = collector.get_stats()
print(f"Total queued: {stats['total_queued']}")
print(f"Total processed: {stats['total_processed']}")
print(f"Queue size: {stats['queue_size']}")
```

**캐시 통계:**

```python
from src.infrastructure.cache import PromptCache

stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
print(f"Cache size: {stats['cache_size']}/{stats['max_size']}")
print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")
```

### 6. 성능 최적화 효과

| 기능 | 개선 효과 |
|------|----------|
| 비동기 메트릭 수집 | 메인 워크플로우 블로킹 제거 |
| 프롬프트 캐싱 | API 호출 30-50% 절감 |
| 압축 저장 | 디스크 공간 30-50% 절감 |
| 백그라운드 저장 | 세션 저장 시간 70% 단축 |

## 세션 히스토리

각 작업 완료 후 `sessions/` 디렉토리에 JSON 파일로 저장됩니다.

**압축 비활성화 시 (`.json`):**

```json
{
  "session_id": "abc123",
  "created_at": "2025-01-18T10:23:45Z",
  "completed_at": "2025-01-18T10:24:30Z",
  "user_request": "작업 설명",
  "total_turns": 3,
  "agents_used": ["planner", "coder", "tester"],
  "messages": [...],
  "result": {
    "status": "completed",
    "tests_passed": true
  }
}
```

**압축 활성화 시 (`.json.gz`):**

파일은 gzip으로 압축되어 저장되며, 로드 시 자동으로 압축 해제됩니다.

## 제약사항

- **순차 실행**: 병렬 에이전트 실행 미지원 (v0.2에서 지원 예정)
- **메모리 내 저장**: 프로세스 종료 시 히스토리 휘발 (JSON 파일 제외)
- **최대 턴 수**: 50턴 제한 (무한 루프 방지)
- **컨텍스트 길이**: 50 메시지 제한

## 문제 해결

### OAuth 토큰 에러

```
ValueError: CLAUDE_CODE_OAUTH_TOKEN 환경변수가 설정되지 않았습니다.
```

→ 환경 변수를 확인하세요: `echo $CLAUDE_CODE_OAUTH_TOKEN`

### 설정 파일 에러

```
FileNotFoundError: 설정 파일을 찾을 수 없습니다
```

→ `config/agent_config.json` 파일이 존재하는지 확인하세요.

### 프롬프트 파일 로드 실패

```
⚠️  프롬프트 파일 없음: prompts/planner.txt
```

→ `prompts/` 디렉토리에 필요한 `.txt` 파일이 있는지 확인하세요.

### TUI 종료 후 터미널 이상 동작

TUI가 비정상 종료되어 마우스 클릭이나 커서가 이상하게 동작하는 경우:

**방법 1: 자동 복원 스크립트 (권장)**

```bash
./reset_terminal.sh
```

**방법 2: 수동 복원**

```bash
reset
# 또는
stty sane
```

**참고**: TUI는 정상 종료 시 자동으로 터미널 상태를 복원합니다 (Ctrl+C 또는 `q` 키).

## 예제 (Examples)

더 많은 사용 예제는 [docs/examples/](docs/examples/) 디렉토리를 참조하세요.

**제공되는 예제:**
- `cli_ui_demo.py`: CLI/TUI 데모 및 사용법 예시

## 테스트

Better-LLM은 단위 테스트, 통합 테스트, E2E 테스트를 포함합니다.

### 테스트 실행

```bash
# 테스트 의존성 설치
pip install -r requirements-dev.txt

# 모든 테스트 실행
pytest

# 특정 마커만 실행
pytest -m unit          # 단위 테스트
pytest -m integration   # 통합 테스트
pytest -m e2e           # E2E 테스트

# 커버리지 포함 실행
pytest --cov=src --cov-report=html

# 또는 테스트 스크립트 사용
./scripts/run_tests.sh
```

### 테스트 구조

```
tests/
├── unit/              # 단위 테스트
│   ├── test_config_loader.py      # Config 로딩 테스트
│   ├── test_structured_logger.py  # 로깅 테스트
│   └── test_error_tracker.py      # 에러 추적 테스트
├── integration/       # 통합 테스트
│   └── ...
├── e2e/              # End-to-end 테스트
│   └── test_workflow.py           # 워크플로우 테스트
└── mocks/            # Mock 객체
    └── claude_api_mock.py         # Claude API Mock
```

### 커버리지 목표

- **목표**: 80% 이상
- **커버리지 리포트 확인**: `htmlcov/index.html` (HTML 리포트 생성 후)

### 테스트 작성 가이드

#### Unit Test 예시

```python
import pytest
from src.infrastructure.config.loader import load_system_config

@pytest.mark.unit
def test_load_system_config(tmp_path):
    """시스템 설정 로드 테스트"""
    config_file = tmp_path / "config.json"
    config_file.write_text('{"key": "value"}')

    result = load_system_config(str(config_file))
    assert result["key"] == "value"
```

#### E2E Test 예시

```python
import pytest
from src.infrastructure.mcp.worker_tools import _execute_worker_task

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_planner_workflow():
    """Planner 워크플로우 테스트"""
    result = await _execute_worker_task("planner", "Analyze requirements")
    assert result is not None
```

## 향후 계획 (Roadmap)

### v0.2 (Enhanced)
- [ ] 에러 핸들링 및 자동 재시도
- [ ] LLM 기반 동적 라우팅
- [ ] 대화 히스토리 영속화 (SQLite)
- [ ] 추가 에이전트 (Reviewer, DevOps)

### v0.3 (Advanced)
- [ ] 병렬 에이전트 실행
- [ ] 웹 UI (실시간 대시보드)
- [ ] 에이전트 성능 메트릭
- [ ] 커스텀 에이전트 추가 지원

## 라이선스

MIT License

## 문의

이슈나 질문은 GitHub Issues를 사용해주세요.

---

**Made with ❤️ using Claude API**
