# Domain Errors API

Better-LLM의 에러 코드 및 에러 처리 API입니다.

## ErrorCode

::: src.domain.errors.error_codes.ErrorCode
    options:
      show_source: true
      show_root_heading: true
      heading_level: 3

## Error Messages

::: src.domain.errors.error_messages
    options:
      show_source: true
      members:
        - get_error_message
        - format_error_message

## Error Handler

::: src.domain.errors.error_handler
    options:
      show_source: true
      members:
        - BetterLLMError
        - WorkerError
        - ConfigError
        - SessionError
        - APIError
        - StorageError
        - MetricsError
        - LoggingError
        - CacheError
        - handle_error

## 사용 예시

### 기본 에러 처리

```python
from src.domain.errors import ErrorCode, handle_error

try:
    worker.run(task)
except TimeoutError as e:
    raise handle_error(
        ErrorCode.WORKER_TIMEOUT,
        original_error=e,
        worker_name="planner",
        timeout=300
    )
```

### 특정 카테고리 에러만 처리

```python
from src.domain.errors import WorkerError, APIError

try:
    worker.run(task)
except WorkerError as e:
    # Worker 에러만 처리
    logger.warning(f"Worker error: {e}")
    retry()
except APIError as e:
    # API 에러는 재시도
    retry_with_backoff()
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

## 에러 코드 목록

전체 에러 코드 목록은 [에러 참조 문서](../../errors.md)를 참조하세요.
