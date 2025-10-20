# 에러 처리 가이드라인

## 개요

Better-LLM 프로젝트에서는 일관된 에러 처리를 위해 커스텀 예외 시스템을 사용합니다.

## 예외 시스템 구조

### 1. Domain 계층 예외

비즈니스 로직과 관련된 예외입니다.

```python
from src.domain.exceptions import (
    DomainException,          # 기본 예외
    ValidationError,          # 입력 검증 실패
    WorkerExecutionError,     # Worker 실행 실패
    WorkerNotFoundError,      # Worker를 찾을 수 없음
    WorkerTimeoutError,       # Worker 타임아웃
    PreconditionFailedError,  # 사전 조건 실패
    CircuitOpenError,         # Circuit Breaker OPEN
    RetryableError,           # 재시도 가능한 에러
)
```

### 2. 시스템 예외 (Better-LLM Error)

인프라 및 시스템 레벨 예외입니다.

```python
from src.domain.exceptions import (
    BetterLLMError,    # 기본 시스템 예외
    WorkerError,       # Worker 관련
    ConfigError,       # 설정 관련
    SessionError,      # 세션 관련
    APIError,          # API 관련
    StorageError,      # 스토리지 관련
    MetricsError,      # 메트릭 관련
    LoggingError,      # 로깅 관련
    CacheError,        # 캐시 관련
)
```

## 에러 코드

에러 코드를 사용하여 구체적인 에러 상황을 표현합니다.

```python
from src.domain.exceptions import ErrorCode

# 예시
ErrorCode.WORKER_TIMEOUT           # 1001
ErrorCode.WORKER_EXECUTION_FAILED  # 1002
ErrorCode.CONFIG_LOAD_FAILED       # 2001
ErrorCode.API_KEY_MISSING          # 4001
```

## 사용 패턴

### 1. 기본 사용법

```python
from src.domain.exceptions import WorkerError, ErrorCode, handle_error
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

def execute_worker(worker_name: str):
    try:
        # 작업 수행
        result = perform_task()
        return result
    except TimeoutError as e:
        # handle_error로 적절한 예외 생성 및 로깅
        raise handle_error(
            ErrorCode.WORKER_TIMEOUT,
            original_error=e,
            worker_name=worker_name,
            timeout=300
        )
    except Exception as e:
        raise handle_error(
            ErrorCode.WORKER_EXECUTION_FAILED,
            original_error=e,
            worker_name=worker_name
        )
```

### 2. 계층별 패턴

#### Infrastructure 계층

인프라 계층에서는 `handle_error`를 사용하여 시스템 예외를 발생시킵니다.

```python
# src/infrastructure/claude/worker_client.py
from src.domain.exceptions import ErrorCode, handle_error
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

class WorkerAgent:
    def _load_system_prompt(self) -> str:
        try:
            # 파일 로드 시도
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError as e:
            raise handle_error(
                ErrorCode.PROMPT_FILE_NOT_FOUND,
                original_error=e,
                file_path=str(prompt_path)
            )
        except Exception as e:
            raise handle_error(
                ErrorCode.PROMPT_LOAD_FAILED,
                original_error=e,
                file_path=str(prompt_path)
            )
```

#### Application 계층

Application 계층에서는 Infrastructure 예외를 Domain 예외로 변환합니다.

```python
# src/application/use_cases/execute_coder_use_case.py
from src.domain.exceptions import (
    WorkerExecutionError,
    WorkerTimeoutError,
    ConfigError,
)
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

class ExecuteCoderUseCase:
    async def execute(self, task: str) -> str:
        try:
            result = await self.worker_port.execute(task)
            return result
        except ConfigError as e:
            # 설정 에러는 그대로 전파
            logger.error(f"설정 에러: {e}")
            raise
        except TimeoutError as e:
            # 인프라 예외를 Domain 예외로 변환
            logger.error(f"Worker 타임아웃: {e}")
            raise WorkerTimeoutError(
                worker_name=self.config.name,
                message=str(e),
                timeout=300
            )
        except Exception as e:
            # 일반 예외를 Domain 예외로 변환
            logger.error(f"Worker 실행 실패: {e}", exc_info=True)
            raise WorkerExecutionError(
                worker_name=self.config.name,
                message=f"작업 실행 중 오류 발생: {e}",
                original_error=e
            )
```

#### Presentation 계층

Presentation 계층에서는 사용자 친화적인 메시지로 변환합니다.

```python
# src/presentation/cli/orchestrator.py
from src.domain.exceptions import (
    WorkerError,
    ConfigError,
    ValidationError,
)
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

async def run_task(user_input: str):
    try:
        result = await use_case.execute(user_input)
        print(f"✅ 작업 완료: {result}")
    except ValidationError as e:
        logger.warning(f"입력 검증 실패: {e}")
        print(f"⚠️  입력이 올바르지 않습니다: {e}")
    except ConfigError as e:
        logger.error(f"설정 에러: {e}")
        print(f"❌ 설정 오류: {e}")
        print("   config/agent_config.json을 확인하세요.")
    except WorkerError as e:
        logger.error(f"Worker 에러: {e}")
        print(f"❌ 작업 실행 실패: {e}")
    except Exception as e:
        logger.critical(f"예상치 못한 에러: {e}", exc_info=True)
        print(f"❌ 시스템 오류가 발생했습니다: {e}")
```

## 로깅 규칙

### 1. 로깅 레벨

```python
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

# DEBUG: 상세한 디버깅 정보
logger.debug(f"Worker 실행 시작: {worker_name}")

# INFO: 일반 정보
logger.info(f"✅ 작업 완료: {task_id}")

# WARNING: 경고 (복구 가능한 문제)
logger.warning(f"⚠️  캐시 미스: {cache_key}")

# ERROR: 에러 (복구 불가능한 문제)
logger.error(f"❌ Worker 실행 실패: {worker_name}", exc_info=True)

# CRITICAL: 치명적 에러 (시스템 중단)
logger.critical(f"🚨 API 키 누락", exc_info=True)
```

### 2. 구조화된 로깅

```python
# ✅ 올바른 예시 - 구조화된 로그
logger.error(
    "Worker 실행 실패",
    worker_name=worker_name,
    task_id=task_id,
    error_code=error_code.name,
    exc_info=True
)

# ❌ 잘못된 예시 - 문자열만 사용
logger.error(f"Worker {worker_name} 실행 실패: task_id={task_id}")
```

### 3. 예외 정보 포함

예외를 로깅할 때는 `exc_info=True`를 사용하여 스택 트레이스를 포함합니다.

```python
try:
    result = perform_task()
except Exception as e:
    logger.error(
        "작업 실행 실패",
        task=task_description,
        exc_info=True  # 스택 트레이스 포함
    )
    raise
```

## 에러 메시지 표준

### 1. 메시지 형식

에러 메시지는 다음 형식을 따릅니다:

```
[상태 아이콘] [대상] [동작] [결과]: [상세 정보]
```

예시:
```
✅ Worker 'planner' 실행 완료
❌ 설정 파일 'config.json' 로드 실패: 파일이 존재하지 않습니다
⚠️  캐시 'prompt_cache' 만료: 재생성 중
```

### 2. 아이콘 사용

- ✅ 성공
- ❌ 실패
- ⚠️  경고
- 🚨 치명적 에러
- 🔍 디버그
- 📋 정보
- ⏱️  타임아웃
- 🔄 재시도

## 체크리스트

새로운 에러 처리 코드를 작성할 때:

- [ ] `from src.domain.exceptions import ...`로 예외 import
- [ ] Infrastructure에서는 `handle_error()` 사용
- [ ] Application에서는 Infrastructure 예외를 Domain 예외로 변환
- [ ] Presentation에서는 사용자 친화적 메시지 제공
- [ ] 로깅 시 `exc_info=True` 포함 (스택 트레이스 필요시)
- [ ] 구조화된 로깅 사용 (키워드 인자)
- [ ] 적절한 로깅 레벨 사용 (DEBUG/INFO/WARNING/ERROR/CRITICAL)

## 마이그레이션 가이드

기존 코드를 새로운 에러 처리 시스템으로 마이그레이션:

### Before (기존 코드)

```python
try:
    result = worker.execute(task)
except Exception as e:
    logger.error(f"Worker 실행 실패: {e}")
    raise
```

### After (새로운 코드)

```python
from src.domain.exceptions import ErrorCode, handle_error

try:
    result = worker.execute(task)
except TimeoutError as e:
    raise handle_error(
        ErrorCode.WORKER_TIMEOUT,
        original_error=e,
        worker_name=worker.name,
        timeout=300
    )
except Exception as e:
    raise handle_error(
        ErrorCode.WORKER_EXECUTION_FAILED,
        original_error=e,
        worker_name=worker.name
    )
```

## FAQ

**Q: 언제 Domain 예외를, 언제 시스템 예외를 사용하나요?**

A:
- **Domain 예외**: 비즈니스 로직 검증 실패 (예: 입력 검증, 사전 조건 미충족)
- **시스템 예외**: 인프라/시스템 문제 (예: 파일 로드 실패, API 호출 실패)

**Q: `handle_error`는 언제 사용하나요?**

A: Infrastructure 계층에서 시스템 예외를 발생시킬 때 사용합니다. Application 계층 이상에서는 Domain 예외를 직접 생성합니다.

**Q: 모든 예외를 로깅해야 하나요?**

A: 아니요. `handle_error`는 자동으로 로깅하므로, Infrastructure에서는 별도 로깅이 불필요합니다. Application/Presentation에서는 필요시 추가 로깅을 합니다.
