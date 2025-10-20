# 사용법 가이드

Better-LLM의 고급 기능 및 사용 팁을 안내합니다.

## TUI (Terminal User Interface)

### 시작하기

```bash
better-llm
```

### 주요 기능

#### 1. 실시간 스트리밍

Manager와 Worker의 응답을 실시간으로 확인할 수 있습니다.

- Markdown 렌더링
- Syntax highlighting (코드 블록)
- 진행 상황 표시

#### 2. 세션 관리

- **새 세션**: `Ctrl+N`
- **세션 자동 저장**: `sessions/` 디렉토리
- **세션 불러오기**: TUI 시작 시 목록 표시

#### 3. Worker 상태 모니터링

우측 패널에서 각 Worker의 상태를 실시간으로 확인:

- ✅ 완료 (Completed)
- ⏳ 진행 중 (In Progress)
- ⏸️ 대기 중 (Pending)
- ❌ 실패 (Failed)

#### 4. 설정 변경

TUI 내에서 설정을 동적으로 변경할 수 있습니다:

- Worker 활성화/비활성화
- 로그 레벨 변경
- 캐싱 설정 토글

## CLI (Command Line Interface)

### 기본 사용법

```bash
better-llm-cli "작업 설명"
```

### 옵션

#### `--verbose` / `-v`

상세 로깅을 활성화합니다.

```bash
better-llm-cli -v "작업 설명"
```

출력:
- Worker 실행 로그
- API 호출 정보
- 메트릭 통계

#### `--config` / `-c`

커스텀 설정 파일을 사용합니다.

```bash
better-llm-cli -c custom_config.json "작업 설명"
```

#### `--session-id` / `-s`

특정 세션 ID를 지정합니다 (디버깅용).

```bash
better-llm-cli -s my-session-id "작업 설명"
```

#### `--no-save`

세션을 저장하지 않습니다 (임시 작업용).

```bash
better-llm-cli --no-save "간단한 질문"
```

## 특정 Worker 호출

### 문법

메시지에 `@worker_name`을 포함:

```bash
better-llm-cli "@planner 프로젝트 구조 분석해줘"
```

### 지원 Worker

| Worker | 역할 | 예시 |
|--------|------|------|
| `@planner` | 계획 수립 | `@planner 리팩토링 계획 세워줘` |
| `@coder` | 코드 작성 | `@coder auth 모듈 구현해줘` |
| `@tester` | 테스트 실행 | `@tester 단위 테스트 실행해줘` |
| `@reviewer` | 코드 리뷰 | `@reviewer 최근 커밋 리뷰해줘` |
| `@committer` | Git 커밋 | `@committer 커밋 및 PR 생성해줘` |

### 여러 Worker 순차 호출

```bash
better-llm-cli "@planner 계획 수립하고 @coder 구현해줘"
```

Manager Agent가 자동으로 순서대로 호출합니다.

## 사용자 개입

각 Worker 응답 후 5초 대기하며, 다음 옵션을 선택할 수 있습니다:

- **Enter**: 다음 Worker로 자동 진행
- **/pause**: 일시정지하고 메시지 입력
- **/stop**: 즉시 종료

### 예시

```
[Planner 응답 완료]

다음 작업을 계속하시겠습니까? (5초)
[Enter] 계속  [/pause] 일시정지  [/stop] 종료

> /pause
메시지를 입력하세요:
> @planner 계획을 좀 더 상세하게 작성해줘
```

## 설정 커스터마이징

### Agent 설정 (`config/agent_config.json`)

```json
{
  "agents": [
    {
      "name": "planner",
      "role": "요구사항 분석 및 계획 수립",
      "system_prompt_file": "prompts/planner.txt",
      "tools": ["read", "glob", "grep"],
      "model": "claude-sonnet-4",
      "timeout": 300
    }
  ]
}
```

**커스터마이징 가능 항목**:
- `name`: Worker 이름 (변경 금지)
- `role`: Worker 역할 설명
- `system_prompt_file`: 프롬프트 파일 경로
- `tools`: 사용 가능한 도구 목록
- `model`: Claude 모델 선택
- `timeout`: 타임아웃 (초)

### 시스템 설정 (`config/system_config.json`)

```json
{
  "workflow_limits": {
    "max_retry_cycles": 3,
    "max_review_iterations": 3,
    "max_coder_retries": 2
  },
  "performance": {
    "enable_caching": true,
    "enable_async_metrics": true,
    "cache_ttl_seconds": 3600,
    "cache_max_size": 100,
    "metrics_buffer_size": 1000,
    "metrics_flush_interval": 5.0,
    "enable_session_compression": true,
    "enable_background_save": true
  }
}
```

### 환경 변수 (`.env`)

```bash
# API 키
ANTHROPIC_API_KEY=your-api-key-here

# 로깅
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json         # json 또는 console
LOG_DIR=logs            # 로그 파일 디렉토리

# Worker 타임아웃 (초)
WORKER_TIMEOUT_PLANNER=300
WORKER_TIMEOUT_CODER=600
WORKER_TIMEOUT_TESTER=600
WORKER_TIMEOUT_REVIEWER=300
WORKER_TIMEOUT_COMMITTER=180
```

## 고급 기능

### 1. 프롬프트 커스터마이징

`prompts/` 디렉토리의 `.txt` 파일을 수정하여 각 Worker의 행동을 변경할 수 있습니다.

#### 예시: Planner 프롬프트 수정

`prompts/planner.txt`:

```
당신은 Staff Software Engineer입니다.
요구사항을 분석하고 구현 계획을 수립하세요.

## 역할
- 요구사항 분석
- 구현 계획 수립 (단계별)
- 파일 구조 탐색

## 출력 형식
1. 요구사항 요약
2. 구현 계획 (단계별)
3. 예상 파일 목록
4. 고려사항 및 주의점

## 추가 규칙
- 항상 기존 코드베이스를 먼저 탐색하세요
- 보안 및 성능을 고려하세요
- 테스트 가능한 설계를 제안하세요
```

### 2. 메트릭 수집 및 분석

#### 메트릭 확인

```python
from src.infrastructure.metrics import AsyncMetricsCollector

collector = AsyncMetricsCollector()

# 통계 확인
stats = collector.get_stats()
print(f"Total queued: {stats['total_queued']}")
print(f"Total processed: {stats['total_processed']}")
print(f"Queue size: {stats['queue_size']}")
```

#### 메트릭 파일 분석

```bash
# 메트릭 파일 확인
cat metrics.jsonl | jq .

# Worker별 평균 실행 시간
cat metrics.jsonl | jq -r 'select(.metric_name == "worker_duration") | [.worker_name, .value] | @tsv' | awk '{sum[$1] += $2; count[$1]++} END {for (name in sum) print name, sum[name]/count[name]}'
```

### 3. 캐시 관리

#### 캐시 통계 확인

```python
from src.infrastructure.cache import PromptCache

cache = PromptCache()

stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
print(f"Cache size: {stats['cache_size']}/{stats['max_size']}")
```

#### 캐시 초기화

```python
cache.clear()
```

### 4. 세션 관리

#### 세션 로드

```python
from src.infrastructure.storage import SessionRepository

repo = SessionRepository()

# 모든 세션 목록
sessions = repo.list_all()

# 특정 세션 로드
session = repo.load("abc123")
```

#### 세션 검색

```bash
# 특정 날짜 세션
ls sessions/20250120_*.json

# 최근 10개 세션
ls -t sessions/ | head -10

# 특정 키워드 검색
grep -l "FastAPI" sessions/*.json
```

## 베스트 프랙티스

### 1. 작업 분할

큰 작업은 여러 개의 작은 작업으로 나누세요.

❌ **나쁜 예**:
```bash
better-llm-cli "전체 프로젝트를 FastAPI로 마이그레이션해줘"
```

✅ **좋은 예**:
```bash
better-llm-cli "@planner FastAPI 마이그레이션 계획 세워줘"
# 계획 확인 후
better-llm-cli "@coder auth 모듈만 먼저 마이그레이션해줘"
better-llm-cli "@tester auth 모듈 테스트 실행"
# 반복...
```

### 2. 명확한 요청

구체적이고 명확한 요청을 하세요.

❌ **나쁜 예**:
```bash
better-llm-cli "버그 고쳐줘"
```

✅ **좋은 예**:
```bash
better-llm-cli "로그인 API (/api/auth/login)에서 500 에러가 발생합니다. 에러 로그를 확인하고 원인을 파악한 후 수정해주세요."
```

### 3. 컨텍스트 제공

필요한 정보를 함께 제공하세요.

✅ **좋은 예**:
```bash
better-llm-cli "@coder src/auth/login.py 파일의 validate_user 함수에 이메일 중복 체크 로직을 추가해주세요. 기존 validate_email 함수를 참고하세요."
```

### 4. 검증 및 리뷰

중요한 변경사항은 반드시 검토하세요.

```bash
# 코드 작성 후
better-llm-cli "@reviewer 방금 작성한 auth 모듈 리뷰해줘"

# 테스트 실행
better-llm-cli "@tester auth 모듈 단위 테스트 실행"
```

## 트러블슈팅

### Worker 타임아웃

**문제**: Worker 실행 시간이 너무 오래 걸림

**해결**:
1. 타임아웃 증가:
   ```bash
   export WORKER_TIMEOUT_CODER=1200
   ```

2. 작업 분할:
   ```bash
   # 한 번에 하지 말고 단계별로
   better-llm-cli "@planner 계획 수립"
   better-llm-cli "@coder 1단계만 구현"
   ```

### 무한 루프

**문제**: Review → Coder → Review 무한 반복

**해결**:
1. 자동 중단 (3회 반복 후)
2. `/stop` 명령으로 수동 중단
3. 설정 조정:
   ```json
   {
     "workflow_limits": {
       "max_review_iterations": 2
     }
   }
   ```

### 메모리 부족

**문제**: 세션이 너무 길어져서 메모리 부족

**해결**:
1. 세션 압축 활성화:
   ```json
   {
     "performance": {
       "enable_session_compression": true
     }
   }
   ```

2. 새 세션 시작:
   ```bash
   # TUI에서 Ctrl+N
   # 또는 CLI에서 새 세션
   better-llm-cli -s new-session "작업 설명"
   ```

## 다음 단계

- [아키텍처](../architecture.md) - 시스템 구조 이해
- [ADR](../adr/0001-clean-architecture.md) - 설계 결정 배경
- [에러 참조](../errors.md) - 에러 해결 방법
- [API Reference](../api/domain/errors.md) - API 문서
