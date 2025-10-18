# Use Cases 사용 가이드

## 개요

Application Layer의 Use Cases는 비즈니스 로직 오케스트레이션을 담당합니다.
Clean Architecture 원칙에 따라 Infrastructure 계층과 분리되어 있으며, 의존성 주입을 통해 테스트 가능성을 확보했습니다.

## 아키텍처

```
Presentation Layer (CLI/TUI)
        ↓
Application Layer (Use Cases)
        ↓
Domain Layer (Interfaces, Models, Exceptions)
        ↑
Infrastructure Layer (Worker Clients)
```

## 주요 컴포넌트

### 1. Domain Layer

#### 예외 클래스 (`src/domain/exceptions.py`)
- `DomainException`: 기본 예외
- `ValidationError`: 입력 검증 실패
- `WorkerExecutionError`: Worker 실행 실패
- `WorkerNotFoundError`: Worker를 찾을 수 없음
- `WorkerTimeoutError`: Worker 실행 타임아웃
- `PreconditionFailedError`: 사전 조건 실패

#### Use Case 인터페이스 (`src/domain/interfaces/use_cases/`)
- `IExecuteWorkerUseCase`: Worker 실행 Use Case 공통 인터페이스

### 2. Application Layer

#### Base Use Case (`src/application/use_cases/base_worker_use_case.py`)
공통 비즈니스 로직을 구현하는 베이스 클래스:
- Input Validation
- Worker 실행
- 에러 변환 (Infrastructure → Domain)
- 결과 후처리

#### 각 Worker Use Case
- `ExecutePlannerUseCase`: 계획 수립
- `ExecuteCoderUseCase`: 코드 작성
- `ExecuteReviewerUseCase`: 코드 리뷰
- `ExecuteTesterUseCase`: 테스트 작성/실행

#### Use Case Factory (`src/application/use_cases/use_case_factory.py`)
의존성 주입 관리 및 Use Case 인스턴스 생성

### 3. Infrastructure Layer

#### Worker Agent Adapter (`src/infrastructure/claude/worker_agent_adapter.py`)
- WorkerAgent를 IAgentClient 인터페이스로 어댑트
- Adapter 패턴을 통해 Infrastructure와 Application 계층 분리

## 사용 방법

### 1. 기본 사용 예제

**중요**: UseCaseFactory는 의존성 역전 원칙(DIP)을 준수하여 `worker_client_factory`를 주입받아야 합니다.

```python
from src.application.use_cases import UseCaseFactory
from src.domain.models import Task, AgentConfig
from src.application.ports.agent_client_port import IAgentClient
from src.infrastructure.claude import WorkerAgent
from src.infrastructure.claude.worker_agent_adapter import WorkerAgentAdapter

# 1. Worker Client Factory 함수 정의 (Infrastructure 계층)
def create_worker_client(config: AgentConfig) -> IAgentClient:
    """Infrastructure 계층의 Worker Client 팩토리"""
    worker = WorkerAgent(config)
    return WorkerAgentAdapter(worker)

# 2. Factory 생성 (의존성 주입)
factory = UseCaseFactory(worker_client_factory=create_worker_client)

# 3. Use Case 생성
planner_use_case = factory.create_planner_use_case()

# 4. Task 생성
task = Task(
    description="사용자 인증 기능 구현 계획 수립",
    agent_name="planner"
)

# 5. 실행 (스트리밍)
async for chunk in planner_use_case.execute(task):
    print(chunk, end="", flush=True)
```

### 2. 결과 버퍼링 예제

```python
from src.application.use_cases import UseCaseFactory
from src.domain.models import Task, AgentConfig
from src.application.ports.agent_client_port import IAgentClient
from src.infrastructure.claude import WorkerAgent
from src.infrastructure.claude.worker_agent_adapter import WorkerAgentAdapter

# Worker Client Factory 정의
def create_worker_client(config: AgentConfig) -> IAgentClient:
    worker = WorkerAgent(config)
    return WorkerAgentAdapter(worker)

# Factory 및 Use Case 생성
factory = UseCaseFactory(worker_client_factory=create_worker_client)
coder_use_case = factory.create_coder_use_case()

# Task 생성
task = Task(
    description="사용자 인증 API 구현",
    agent_name="coder"
)

# 실행 및 결과 반환
result = await coder_use_case.execute_with_result(task)

print(f"상태: {result.status}")
print(f"출력: {result.output}")
print(f"메타데이터: {result.metadata}")
```

### 3. Worker 이름으로 Use Case 가져오기

```python
from src.application.use_cases import UseCaseFactory
from src.domain.models import Task, AgentConfig
from src.application.ports.agent_client_port import IAgentClient
from src.infrastructure.claude import WorkerAgent
from src.infrastructure.claude.worker_agent_adapter import WorkerAgentAdapter

# Worker Client Factory 정의
def create_worker_client(config: AgentConfig) -> IAgentClient:
    worker = WorkerAgent(config)
    return WorkerAgentAdapter(worker)

factory = UseCaseFactory(worker_client_factory=create_worker_client)

# Worker 이름으로 Use Case 가져오기
worker_name = "reviewer"
use_case = factory.get_use_case_by_worker_name(worker_name)

task = Task(
    description="코드 리뷰 수행",
    agent_name=worker_name
)

result = await use_case.execute_with_result(task)
```

### 4. 사전 조건 설정

```python
from src.application.use_cases import UseCaseFactory
from src.domain.models import AgentConfig
from src.application.ports.agent_client_port import IAgentClient
from src.infrastructure.claude import WorkerAgent
from src.infrastructure.claude.worker_agent_adapter import WorkerAgentAdapter

# Worker Client Factory 정의
def create_worker_client(config: AgentConfig) -> IAgentClient:
    worker = WorkerAgent(config)
    return WorkerAgentAdapter(worker)

factory = UseCaseFactory(worker_client_factory=create_worker_client)

# Coder Use Case - 계획 필수
coder_use_case = factory.create_coder_use_case(require_plan=True)

# Reviewer Use Case - 코드 참조 필수
reviewer_use_case = factory.create_reviewer_use_case(require_code_reference=True)

# Tester Use Case - 테스트 대상 필수
tester_use_case = factory.create_tester_use_case(require_test_target=True)
```

### 5. 에러 처리

```python
from src.application.use_cases import UseCaseFactory
from src.domain.models import Task, AgentConfig
from src.domain.exceptions import (
    ValidationError,
    PreconditionFailedError,
    WorkerExecutionError
)
from src.application.ports.agent_client_port import IAgentClient
from src.infrastructure.claude import WorkerAgent
from src.infrastructure.claude.worker_agent_adapter import WorkerAgentAdapter

# Worker Client Factory 정의
def create_worker_client(config: AgentConfig) -> IAgentClient:
    worker = WorkerAgent(config)
    return WorkerAgentAdapter(worker)

factory = UseCaseFactory(worker_client_factory=create_worker_client)
use_case = factory.create_planner_use_case()

task = Task(description="작업 설명", agent_name="planner")

try:
    result = await use_case.execute_with_result(task)
    print(f"성공: {result.output}")

except ValidationError as e:
    print(f"검증 실패: {e}")

except PreconditionFailedError as e:
    print(f"사전 조건 실패: {e}")

except WorkerExecutionError as e:
    print(f"Worker 실행 실패: {e}")
    print(f"원본 에러: {e.original_error}")
```

## 테스트 전략

### 1. Use Case 단위 테스트

Use Case는 IAgentClient 인터페이스에만 의존하므로 Mock 객체를 주입하여 테스트할 수 있습니다.

```python
import pytest
from unittest.mock import AsyncMock
from src.application.use_cases import ExecutePlannerUseCase
from src.domain.models import Task

@pytest.mark.asyncio
async def test_planner_use_case():
    # Mock Client 생성
    mock_client = AsyncMock()
    mock_client.execute.return_value = iter(["Plan output"])

    # Use Case 생성 (Mock 주입)
    use_case = ExecutePlannerUseCase(planner_client=mock_client)

    # Task 실행
    task = Task(description="Test task", agent_name="planner")
    result = await use_case.execute_with_result(task)

    # 검증
    assert result.status == TaskStatus.COMPLETED
    assert "Plan output" in result.output
    mock_client.execute.assert_called_once()
```

### 2. 통합 테스트

실제 WorkerAgent를 사용한 통합 테스트도 가능합니다.

```python
import pytest
from src.application.use_cases import UseCaseFactory
from src.domain.models import Task, AgentConfig
from src.application.ports.agent_client_port import IAgentClient
from src.infrastructure.claude import WorkerAgent
from src.infrastructure.claude.worker_agent_adapter import WorkerAgentAdapter

@pytest.mark.asyncio
async def test_planner_integration():
    # Worker Client Factory 정의
    def create_worker_client(config: AgentConfig) -> IAgentClient:
        worker = WorkerAgent(config)
        return WorkerAgentAdapter(worker)

    # 실제 Factory 사용
    factory = UseCaseFactory(worker_client_factory=create_worker_client)
    use_case = factory.create_planner_use_case()

    # Task 실행
    task = Task(
        description="간단한 계획 수립",
        agent_name="planner"
    )

    result = await use_case.execute_with_result(task)

    # 결과 검증
    assert result.status == TaskStatus.COMPLETED
    assert len(result.output) > 0
```

## 확장 가이드

### 새로운 Use Case 추가

1. **Use Case 클래스 생성**
   ```python
   from .base_worker_use_case import BaseWorkerUseCase

   class ExecuteNewWorkerUseCase(BaseWorkerUseCase):
       def __init__(self, worker_client):
           super().__init__(
               worker_name="new_worker",
               worker_client=worker_client
           )

       def _check_preconditions(self, task):
           # 사전 조건 체크 로직
           pass

       def _process_result(self, task, output):
           # 결과 후처리 로직
           return super()._process_result(task, output)
   ```

2. **Factory에 메서드 추가**
   ```python
   def create_new_worker_use_case(self):
       client = self._get_worker_client("new_worker")
       return ExecuteNewWorkerUseCase(worker_client=client)
   ```

3. **__init__.py 업데이트**
   ```python
   from .execute_new_worker_use_case import ExecuteNewWorkerUseCase

   __all__ = [
       # ... existing exports
       "ExecuteNewWorkerUseCase",
   ]
   ```

## 모범 사례

1. **의존성 주입 사용**: Factory를 통해 Use Case를 생성하여 의존성 관리
2. **에러 변환**: Infrastructure 에러를 Domain 에러로 변환하여 상위 계층에 전파
3. **단일 책임**: 각 Use Case는 하나의 Worker 실행에만 집중
4. **테스트 가능성**: Mock 객체를 주입하여 단위 테스트 작성
5. **로깅**: 각 단계마다 적절한 로그 기록

## 문제 해결

### Q: ValidationError가 발생합니다
A: Task의 description과 agent_name이 올바른지 확인하세요.

### Q: WorkerNotFoundError가 발생합니다
A: `config/agent_config.json`에 해당 Worker가 정의되어 있는지 확인하세요.

### Q: PreconditionFailedError가 발생합니다
A: Use Case의 사전 조건을 확인하세요. 예: Coder Use Case는 계획이 필요할 수 있습니다.

### Q: 커스텀 사전/사후 조건을 추가하고 싶습니다
A: BaseWorkerUseCase를 상속하고 `_check_preconditions()` 또는 `_process_result()`를 오버라이드하세요.

## 참고 자료

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [SOLID 원칙](https://en.wikipedia.org/wiki/SOLID)
- [의존성 주입](https://en.wikipedia.org/wiki/Dependency_injection)
- [Adapter 패턴](https://refactoring.guru/design-patterns/adapter)
