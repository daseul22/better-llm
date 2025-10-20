# Import 경로 가이드라인

## 개요

Better-LLM 프로젝트에서는 일관성 있는 import 경로 사용을 위해 **절대 경로 import**를 표준으로 사용합니다.

## 규칙

### 1. 절대 경로 사용 (권장)

모든 import는 `src.` 접두사를 사용한 절대 경로로 작성합니다.

```python
# ✅ 올바른 예시
from src.domain.models import AgentConfig, Message
from src.domain.services import ProjectContext
from src.infrastructure.config import get_project_root
from src.application.use_cases import ExecuteCoderUseCase
```

### 2. 상대 경로 사용 금지 (프로덕션 코드)

상대 경로 import는 사용하지 않습니다.

```python
# ❌ 잘못된 예시
from ..config import get_project_root
from ...domain.models import AgentConfig
from .utils import helper_function
```

### 3. __init__.py 예외

`__init__.py` 파일에서는 같은 패키지 내의 모듈을 re-export할 때만 상대 경로를 사용할 수 있습니다.

```python
# src/domain/models/__init__.py
# ✅ 허용됨
from .agent_config import AgentConfig
from .message import Message

__all__ = ["AgentConfig", "Message"]
```

## 계층별 Import 패턴

### Domain 계층

```python
# src/domain/services/conversation.py
from src.domain.models import Message, Role
from src.domain.exceptions import ValidationError
```

### Application 계층

```python
# src/application/use_cases/execute_coder_use_case.py
from src.domain.models import AgentConfig
from src.domain.services import ConversationHistory
from src.domain.exceptions import WorkerExecutionError, ErrorCode
from src.application.ports import WorkerPort
```

### Infrastructure 계층

```python
# src/infrastructure/claude/worker_client.py
from src.domain.models import AgentConfig
from src.domain.services import ProjectContext
from src.infrastructure.config import get_project_root, get_claude_cli_path
from src.infrastructure.logging import get_logger
```

### Presentation 계층

```python
# src/presentation/cli/orchestrator.py
from src.domain.models import Message
from src.application.use_cases import ExecuteCoderUseCase
from src.infrastructure.claude import ManagerAgent
```

## 예외 처리 Import

예외 클래스는 `src.domain.exceptions`에서 통합하여 import합니다.

```python
# ✅ 올바른 예시
from src.domain.exceptions import (
    WorkerError,
    ConfigError,
    ErrorCode,
    handle_error
)

# ❌ 잘못된 예시
from src.domain.errors.error_handler import WorkerError
from src.domain.errors.error_codes import ErrorCode
```

## 마이그레이션 가이드

기존 상대 경로를 절대 경로로 변경할 때:

1. **패턴 확인**
   ```bash
   # 상대 경로 import 찾기
   grep -r "^from \.\." src/
   grep -r "^from \." src/ | grep -v "__init__.py"
   ```

2. **변경 예시**
   ```python
   # Before
   from ..config import get_project_root
   from ...domain.models import AgentConfig

   # After
   from src.infrastructure.config import get_project_root
   from src.domain.models import AgentConfig
   ```

3. **테스트 실행**
   ```bash
   # 변경 후 반드시 테스트 실행
   pytest tests/
   ```

## 자동화 스크립트 (향후 작업)

프로젝트 전체의 import를 자동으로 변환하는 스크립트는 Phase 2에서 개발 예정입니다.

## 체크리스트

새로운 코드를 작성할 때:

- [ ] 모든 import가 `src.`로 시작하는가?
- [ ] 상대 경로 import를 사용하지 않았는가? (\_\_init\_\_.py 제외)
- [ ] 예외 클래스를 `src.domain.exceptions`에서 import했는가?
- [ ] IDE의 자동 import 기능이 절대 경로를 생성하도록 설정했는가?

## FAQ

**Q: 왜 절대 경로를 사용하나요?**

A: 절대 경로는 다음과 같은 장점이 있습니다:
- 파일 이동 시 import 경로 수정 최소화
- 코드 가독성 향상 (전체 경로가 명확)
- IDE 자동완성 및 리팩토링 지원 개선
- 순환 import 문제 감소

**Q: pytest에서 절대 경로가 인식되지 않습니다.**

A: `conftest.py`에서 Python path를 설정합니다:

```python
# tests/conftest.py
import sys
from pathlib import Path

@pytest.fixture(scope="session", autouse=True)
def setup_python_path():
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "src"))
```

**Q: \_\_init\_\_.py에서는 왜 상대 경로가 허용되나요?**

A: `__init__.py`는 패키지를 초기화하고 모듈을 re-export하는 역할만 하므로, 같은 패키지 내에서만 import합니다. 이 경우 상대 경로가 더 명확하고 유지보수가 쉽습니다.
