# 에러 코드 참조 문서

Better-LLM의 모든 에러 코드와 해결 방법을 설명합니다.

## 에러 코드 체계

에러 코드는 4자리 숫자로 구성되며, 앞 두 자리는 카테고리를 나타냅니다.

| 범위 | 카테고리 | 설명 |
|------|----------|------|
| 1000-1999 | Worker | Worker Agent 실행 관련 에러 |
| 2000-2999 | Config | 설정 파일 및 프롬프트 관련 에러 |
| 3000-3999 | Session | 세션 관리 관련 에러 |
| 4000-4999 | API | Claude API 호출 관련 에러 |
| 5000-5999 | Storage | 파일 시스템 저장소 관련 에러 |
| 6000-6999 | Metrics | 메트릭 수집 관련 에러 |
| 7000-7999 | Logging | 로깅 시스템 관련 에러 |
| 8000-8999 | Cache | 캐시 관련 에러 |
| 9000-9999 | Other | 기타 에러 |

## Worker 에러 (1000-1999)

### 1001: WORKER_TIMEOUT

**설명**: Worker의 실행 시간이 설정된 타임아웃을 초과했습니다.

**원인**:
- 작업이 너무 복잡하여 완료하는 데 시간이 오래 걸림
- 네트워크 지연으로 API 응답이 느림
- 타임아웃 설정이 너무 짧음

**해결 방법**:
1. 환경변수에서 타임아웃 증가:
   ```bash
   export WORKER_TIMEOUT_PLANNER=600  # 10분으로 증가
   ```

2. 작업을 더 작은 단위로 분할

3. 시스템 설정에서 타임아웃 조정:
   ```json
   {
     "worker_timeouts": {
       "planner": 600
     }
   }
   ```

---

### 1002: WORKER_EXECUTION_FAILED

**설명**: Worker 실행 중 예상치 못한 에러가 발생했습니다.

**원인**:
- Worker 내부 로직 오류
- Claude API 응답 파싱 실패
- 필요한 파일이나 리소스 부재

**해결 방법**:
1. 로그 파일 확인 (`logs/better-llm-error.log`)
2. Worker의 입력 파라미터 검증
3. 필요한 파일이 존재하는지 확인
4. API 응답 로그 확인

---

### 1003: WORKER_NOT_FOUND

**설명**: 요청한 Worker가 설정에 정의되어 있지 않습니다.

**원인**:
- `config/agent_config.json`에 Worker 정의 누락
- Worker 이름 오타

**해결 방법**:
1. `config/agent_config.json` 확인:
   ```json
   {
     "agents": [
       {
         "name": "planner",
         "role": "요구사항 분석 및 계획 수립",
         ...
       }
     ]
   }
   ```

2. Worker 이름 확인 (대소문자 구분)

---

### 1006: WORKER_RETRY_EXCEEDED

**설명**: Worker의 재시도 횟수가 최대값을 초과했습니다.

**원인**:
- 반복적인 Worker 실행 실패
- API 연결 문제
- 잘못된 입력 파라미터

**해결 방법**:
1. 에러 로그에서 근본 원인 파악
2. 재시도 설정 조정:
   ```json
   {
     "performance": {
       "worker_retry_max_attempts": 5
     }
   }
   ```

## Config 에러 (2000-2999)

### 2001: CONFIG_LOAD_FAILED

**설명**: 설정 파일을 로드하는 데 실패했습니다.

**원인**:
- 설정 파일이 존재하지 않음
- JSON 형식 오류
- 파일 읽기 권한 없음

**해결 방법**:
1. 설정 파일 존재 여부 확인:
   ```bash
   ls -la config/agent_config.json
   ls -la config/system_config.json
   ```

2. JSON 형식 검증:
   ```bash
   cat config/agent_config.json | jq .
   ```

3. 파일 권한 확인:
   ```bash
   chmod 644 config/agent_config.json
   ```

---

### 2101: PROMPT_FILE_NOT_FOUND

**설명**: 프롬프트 파일을 찾을 수 없습니다.

**원인**:
- `prompts/` 디렉토리에 프롬프트 파일 누락
- 설정에 잘못된 프롬프트 파일 경로 지정

**해결 방법**:
1. 프롬프트 파일 존재 확인:
   ```bash
   ls -la prompts/
   ```

2. `config/agent_config.json`에서 경로 확인:
   ```json
   {
     "system_prompt_file": "prompts/planner.txt"
   }
   ```

## API 에러 (4000-4999)

### 4001: API_KEY_MISSING

**설명**: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.

**해결 방법**:
1. API 키 설정:
   ```bash
   export ANTHROPIC_API_KEY='your-api-key-here'
   ```

2. 또는 `.env` 파일 생성:
   ```bash
   echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
   ```

---

### 4003: API_RATE_LIMIT_EXCEEDED

**설명**: Claude API 호출 한도를 초과했습니다.

**해결 방법**:
1. 에러 메시지에 표시된 시간만큼 대기
2. API 플랜 업그레이드 고려
3. 프롬프트 캐싱 활성화:
   ```json
   {
     "performance": {
       "enable_caching": true
     }
   }
   ```

---

### 4006: API_TIMEOUT

**설명**: API 응답 시간이 타임아웃을 초과했습니다.

**해결 방법**:
1. 네트워크 연결 확인
2. API 타임아웃 증가:
   ```json
   {
     "api_timeout": 120
   }
   ```

## Session 에러 (3000-3999)

### 3002: SESSION_SAVE_FAILED

**설명**: 세션을 저장하는 데 실패했습니다.

**원인**:
- 디스크 공간 부족
- 저장소 디렉토리 권한 없음
- 파일 시스템 에러

**해결 방법**:
1. 디스크 공간 확인:
   ```bash
   df -h
   ```

2. 저장소 디렉토리 권한 확인:
   ```bash
   ls -la sessions/
   chmod 755 sessions/
   ```

## Storage 에러 (5000-5999)

### 5005: STORAGE_DISK_FULL

**설명**: 디스크 공간이 부족합니다.

**해결 방법**:
1. 디스크 공간 확보:
   ```bash
   # 오래된 세션 파일 삭제
   find sessions/ -mtime +30 -delete

   # 오래된 로그 파일 삭제
   find logs/ -mtime +7 -delete
   ```

2. 압축 활성화:
   ```json
   {
     "performance": {
       "enable_session_compression": true
     }
   }
   ```

## Metrics 에러 (6000-6999)

### 6002: METRICS_QUEUE_FULL

**설명**: 메트릭 큐가 가득 찼습니다.

**원인**:
- 메트릭 생성 속도가 처리 속도보다 빠름
- 메트릭 플러시 실패

**해결 방법**:
1. 큐 크기 증가:
   ```json
   {
     "performance": {
       "metrics_buffer_size": 2000
     }
   }
   ```

2. 플러시 주기 단축:
   ```json
   {
     "performance": {
       "metrics_flush_interval": 3.0
     }
   }
   ```

## 에러 처리 예시

### Python 코드에서 에러 처리

```python
from src.domain.errors import ErrorCode, handle_error, BetterLLMError

try:
    worker.run(task)
except TimeoutError as e:
    raise handle_error(
        ErrorCode.WORKER_TIMEOUT,
        original_error=e,
        worker_name="planner",
        timeout=300
    )
except Exception as e:
    raise handle_error(
        ErrorCode.WORKER_EXECUTION_FAILED,
        original_error=e,
        worker_name="planner"
    )
```

### 에러 정보 로깅

```python
from src.domain.errors import BetterLLMError
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

try:
    worker.run(task)
except BetterLLMError as e:
    # 구조화된 로그 출력
    logger.error(
        "Worker execution failed",
        error_code=e.error_code.name,
        error_number=e.error_code.value,
        **e.context
    )

    # 딕셔너리로 변환 (API 응답용)
    error_dict = e.to_dict()
    return {"error": error_dict}
```

### 특정 카테고리 에러만 처리

```python
from src.domain.errors import WorkerError, APIError

try:
    worker.run(task)
except WorkerError as e:
    # Worker 에러만 처리
    logger.warning(f"Worker error: {e}")
except APIError as e:
    # API 에러는 재시도
    retry_with_backoff()
```

## 로그 파일에서 에러 검색

### 특정 에러 코드 검색

```bash
# JSON 로그에서 WORKER_TIMEOUT 에러 검색
cat logs/better-llm.log | jq 'select(.error_code == "WORKER_TIMEOUT")'

# 최근 10개 에러 확인
cat logs/better-llm-error.log | tail -n 10 | jq .
```

### 에러 통계 확인

```bash
# 에러 코드별 발생 횟수
cat logs/better-llm-error.log | jq -r '.error_code' | sort | uniq -c | sort -rn
```

## 문의

에러 관련 문의는 GitHub Issues에 다음 정보와 함께 등록해주세요:

1. 에러 코드 및 메시지
2. 로그 파일 스니펫 (`logs/better-llm-error.log`)
3. 재현 방법
4. 환경 정보 (OS, Python 버전)
