# 빠른 시작

Better-LLM을 5분 안에 시작해보세요!

## 전제 조건

- Python 3.10 이상 설치
- Anthropic API 키 발급
- Better-LLM 설치 완료

아직 설치하지 않았다면 [설치 가이드](installation.md)를 먼저 참조하세요.

## 1. 환경 변수 설정

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

## 2. TUI 실행

Terminal User Interface로 Claude Code 스타일 UI를 사용할 수 있습니다.

```bash
better-llm
```

TUI를 실행하면 Claude Code 스타일의 터미널 인터페이스가 표시됩니다:
- **상단**: 현재 세션 정보 및 Worker 상태
- **중단**: 대화 내역 및 작업 진행 상황
- **하단**: 작업 입력창

Worker들의 상태를 실시간으로 모니터링할 수 있습니다.

### TUI 사용법

1. 텍스트 입력창에 작업 설명 입력
2. `Enter` 키로 작업 실행
3. Manager Agent가 자동으로 적절한 Worker 호출
4. 실시간으로 진행 상황 확인

### 키보드 단축키

| 키 | 동작 |
|----|------|
| `Enter` | 작업 실행 |
| `Ctrl+N` | 새 세션 시작 |
| `Ctrl+C` | 종료 |
| `↑` / `↓` | 스크롤 |

## 3. CLI 실행

간단한 명령어로 작업을 실행할 수 있습니다.

```bash
better-llm-cli "작업 설명"
```

### 예시

#### 새 기능 개발

```bash
better-llm-cli "FastAPI로 /users CRUD 엔드포인트 구현해줘"
```

**워크플로우**:
1. **Planner**: FastAPI 프로젝트 구조 분석 및 계획 수립
2. **Coder**: `/users` 라우터, 모델, CRUD 함수 작성
3. **Tester**: 단위 테스트 및 API 테스트 실행
4. **완료**: 구현 완료 및 요약 제공

#### 버그 수정

```bash
better-llm-cli "로그인 API에서 500 에러 나는 버그 수정해줘"
```

**워크플로우**:
1. **Planner**: 로그인 API 코드 분석 및 버그 원인 파악
2. **Coder**: 버그 수정
3. **Tester**: 수정 후 테스트 실행
4. **Reviewer**: 수정 사항 검토
5. **완료**: 버그 수정 완료

#### 리팩토링

```bash
better-llm-cli "payment.py 모듈을 클래스 기반으로 리팩토링해줘"
```

**워크플로우**:
1. **Planner**: 기존 코드 분석 및 리팩토링 계획
2. **Coder**: 클래스 기반으로 재작성
3. **Tester**: 리팩토링 후 테스트 실행 (기존 동작 보존)
4. **Reviewer**: 코드 품질 검토
5. **완료**: 리팩토링 완료

## 4. 특정 Worker 호출

메시지에 `@agent_name`을 포함하여 특정 Worker를 직접 호출할 수 있습니다.

```bash
# Coder만 호출
better-llm-cli "@coder 결제 모듈에 refund 함수 추가해줘"

# Tester만 호출
better-llm-cli "@tester 통합 테스트 실행해줘"

# Reviewer만 호출
better-llm-cli "@reviewer 최근 커밋 코드 리뷰해줘"
```

## 5. 옵션 사용

### 상세 로깅

```bash
better-llm-cli --verbose "작업 설명"
```

모든 Worker의 상세 로그를 출력합니다.

### 커스텀 설정 파일

```bash
better-llm-cli --config my_config.json "작업 설명"
```

기본 설정 대신 커스텀 설정 파일을 사용합니다.

### 도움말

```bash
better-llm --help
better-llm-cli --help
```

## 6. 세션 히스토리 확인

모든 작업은 자동으로 `sessions/` 디렉토리에 저장됩니다.

```bash
# 세션 목록 확인
ls -lh sessions/

# 특정 세션 내용 확인 (JSON 형식)
cat sessions/20250120_103045_abc123.json | jq .

# 압축된 세션 확인 (.json.gz)
zcat sessions/20250120_103045_abc123.json.gz | jq .
```

### 세션 파일 구조

```json
{
  "session_id": "abc123",
  "created_at": "2025-01-20T10:30:45Z",
  "completed_at": "2025-01-20T10:35:12Z",
  "user_request": "FastAPI로 /users CRUD 엔드포인트 구현해줘",
  "total_turns": 5,
  "agents_used": ["planner", "coder", "tester"],
  "messages": [...],
  "result": {
    "status": "completed",
    "tests_passed": true,
    "files_modified": [
      "app/routers/users.py",
      "app/models/user.py",
      "tests/test_users.py"
    ]
  }
}
```

## 7. 로그 확인

로그 파일은 `logs/` 디렉토리에 자동으로 생성됩니다.

```bash
# 전체 로그
tail -f logs/better-llm.log

# 에러만
tail -f logs/better-llm-error.log

# JSON 형식으로 파싱
cat logs/better-llm.log | jq 'select(.level == "error")'
```

## 8. 설정 커스터마이징

### 에이전트 설정

`config/agent_config.json`:

```json
{
  "agents": [
    {
      "name": "planner",
      "role": "요구사항 분석 및 계획 수립",
      "system_prompt_file": "prompts/planner.txt",
      "tools": ["read", "glob", "grep"],
      "model": "claude-sonnet-4"
    }
  ]
}
```

### 시스템 설정

`config/system_config.json`:

```json
{
  "workflow_limits": {
    "max_retry_cycles": 3,
    "max_review_iterations": 3
  },
  "performance": {
    "enable_caching": true,
    "enable_async_metrics": true,
    "cache_ttl_seconds": 3600
  }
}
```

### 환경 변수

`.env` 파일 생성:

```bash
# API 키
ANTHROPIC_API_KEY=your-api-key-here

# 로깅
LOG_LEVEL=INFO
LOG_FORMAT=json

# 타임아웃 (초)
WORKER_TIMEOUT_PLANNER=300
WORKER_TIMEOUT_CODER=600
WORKER_TIMEOUT_TESTER=600
```

## 다음 단계

기본 사용법을 익혔다면:

1. [사용법](usage.md) - 고급 기능 및 팁
2. [아키텍처](../architecture.md) - 시스템 구조 이해
3. [ADR](../adr/0001-clean-architecture.md) - 설계 결정 배경
4. [에러 참조](../errors.md) - 에러 해결 방법

## 문제 해결

### API 키 에러

```
ValueError: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.
```

→ 환경 변수를 확인하세요:

```bash
echo $ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY='your-api-key-here'
```

### Worker 타임아웃

```
WorkerError: Worker 'coder'의 실행 시간이 600초를 초과했습니다.
```

→ 타임아웃을 늘리세요:

```bash
export WORKER_TIMEOUT_CODER=1200  # 20분
```

### 설정 파일 에러

```
ConfigError: 설정 파일 'config/agent_config.json'을 찾을 수 없습니다.
```

→ 설정 파일이 존재하는지 확인하세요:

```bash
ls -la config/
```

더 많은 문제 해결 방법은 [에러 참조](../errors.md)를 확인하세요.
