# 기여 가이드

Better-LLM에 기여해주셔서 감사합니다! 이 문서는 프로젝트에 기여하는 방법을 안내합니다.

## 행동 강령

모든 기여자는 존중과 배려의 정신으로 프로젝트에 참여해야 합니다.

- 건설적인 피드백을 제공하세요
- 다양한 의견을 존중하세요
- 협업과 학습에 열린 자세를 가지세요

## 기여 방법

### 1. 이슈 보고

버그나 개선 사항을 발견하셨나요?

**버그 리포트**:
1. [Issues](https://github.com/simdaseul/better-llm/issues)에서 중복 확인
2. **New Issue** → **Bug Report** 템플릿 선택
3. 다음 정보 포함:
   - 버그 설명
   - 재현 방법
   - 예상 동작 vs 실제 동작
   - 환경 정보 (OS, Python 버전)
   - 로그 및 스크린샷

**기능 제안**:
1. **New Issue** → **Feature Request** 템플릿 선택
2. 다음 정보 포함:
   - 해결하려는 문제
   - 제안하는 해결 방법
   - 대안 (있다면)
   - 추가 컨텍스트

### 2. 코드 기여

#### 개발 환경 설정

```bash
# 1. Fork & Clone
git clone https://github.com/YOUR_USERNAME/better-llm.git
cd better-llm

# 2. 원본 저장소를 upstream으로 추가
git remote add upstream https://github.com/simdaseul/better-llm.git

# 3. 가상 환경 생성
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\Activate.ps1  # Windows

# 4. 개발 의존성 설치
pip install -r requirements-dev.txt
pip install -e .

# 5. pre-commit 훅 설치
pre-commit install
```

#### 브랜치 전략

```bash
# main 브랜치에서 최신 코드 가져오기
git checkout main
git pull upstream main

# 새 브랜치 생성 (feature, fix, docs 등)
git checkout -b feature/add-new-worker
git checkout -b fix/worker-timeout
git checkout -b docs/update-readme
```

#### 커밋 메시지 규칙

[Conventional Commits](https://www.conventionalcommits.org/) 형식을 따릅니다.

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포맷팅 (동작 변경 없음)
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정 등

**예시**:
```bash
# 좋은 예
git commit -m "feat(worker): add DevOps worker agent"
git commit -m "fix(cache): resolve race condition in prompt cache"
git commit -m "docs(adr): add ADR for event sourcing"

# 나쁜 예
git commit -m "update code"
git commit -m "fix bug"
```

**Body (선택)**:
- 변경 이유
- 변경 내용 상세 설명

**Footer (선택)**:
- `Closes #123`: 이슈 번호
- `BREAKING CHANGE:`: 호환성 깨는 변경

**전체 예시**:
```
feat(worker): add DevOps worker agent

Add a new DevOps worker that handles deployment tasks:
- Docker build and push
- Kubernetes deployment
- CI/CD pipeline configuration

Closes #45
```

#### 코드 스타일

**Python 코드**:
- **포맷터**: Black (line length 100)
- **타입 체커**: mypy
- **린터**: ruff
- **Docstring**: Google 스타일

```python
def execute_worker(worker_name: str, task: str) -> Dict[str, Any]:
    """Worker를 실행하고 결과를 반환합니다.

    Args:
        worker_name: Worker 이름 (예: "planner", "coder")
        task: 실행할 작업 설명

    Returns:
        Worker 실행 결과를 담은 딕셔너리:
            - status: 실행 상태 ("success" | "failed")
            - output: Worker 출력
            - duration: 실행 시간 (초)

    Raises:
        WorkerError: Worker 실행 실패 시
        TimeoutError: 타임아웃 초과 시

    Examples:
        >>> result = execute_worker("planner", "Analyze requirements")
        >>> result["status"]
        'success'
    """
    ...
```

**자동 포맷팅**:
```bash
# 코드 포맷팅
black src/ tests/

# Import 정렬
ruff check --select I --fix src/ tests/

# 타입 체크
mypy src/

# 린트
ruff check src/ tests/
```

**pre-commit 훅**:
```bash
# .pre-commit-config.yaml에 정의됨
# 커밋 시 자동 실행
git commit -m "feat: add new feature"

# 수동 실행
pre-commit run --all-files
```

#### 테스트 작성

**테스트 필수**:
- 새로운 기능 추가 시 테스트 필수
- 버그 수정 시 재현 테스트 추가
- 목표 커버리지: 80% 이상

**테스트 구조**:
```
tests/
├── unit/              # 단위 테스트
│   ├── test_config_loader.py
│   └── test_error_handler.py
├── integration/       # 통합 테스트
│   └── test_worker_integration.py
└── e2e/              # End-to-end 테스트
    └── test_workflow.py
```

**테스트 작성 예시**:
```python
import pytest
from src.domain.errors import ErrorCode, handle_error, WorkerError

@pytest.mark.unit
def test_handle_error_creates_worker_error():
    """handle_error가 WorkerError를 생성하는지 테스트"""
    error = handle_error(
        ErrorCode.WORKER_TIMEOUT,
        worker_name="planner",
        timeout=300,
        log=False  # 테스트에서는 로깅 비활성화
    )

    assert isinstance(error, WorkerError)
    assert error.error_code == ErrorCode.WORKER_TIMEOUT
    assert "planner" in str(error)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_execution_integration():
    """Worker 실행 통합 테스트"""
    # Given
    worker_name = "planner"
    task = "Analyze requirements"

    # When
    result = await execute_worker(worker_name, task)

    # Then
    assert result["status"] == "success"
    assert "output" in result
```

**테스트 실행**:
```bash
# 모든 테스트
pytest

# 특정 마커만
pytest -m unit
pytest -m integration
pytest -m e2e

# 커버리지 포함
pytest --cov=src --cov-report=html

# 특정 파일만
pytest tests/unit/test_error_handler.py

# 특정 테스트만
pytest tests/unit/test_error_handler.py::test_handle_error_creates_worker_error
```

#### Pull Request

**PR 생성 전 체크리스트**:
- [ ] 코드 포맷팅 완료 (black, ruff)
- [ ] 타입 체크 통과 (mypy)
- [ ] 테스트 작성 및 통과
- [ ] 문서 업데이트 (필요시)
- [ ] 커밋 메시지 규칙 준수

**PR 생성**:
1. Fork한 저장소에 푸시:
   ```bash
   git push origin feature/add-new-worker
   ```

2. GitHub에서 **New Pull Request** 클릭

3. PR 템플릿 작성:
   - 변경 사항 설명
   - 관련 이슈 번호 (`Closes #123`)
   - 스크린샷 (UI 변경 시)
   - 테스트 결과

4. 리뷰어 요청

**PR 예시**:
```markdown
## 변경 사항
DevOps worker agent를 추가했습니다.

## 구현 내용
- [ ] DevOps worker 프롬프트 작성
- [ ] MCP Worker Tools에 DevOps tool 추가
- [ ] 단위 테스트 작성
- [ ] 문서 업데이트 (README, ADR)

## 테스트
- [x] 단위 테스트 통과 (100% coverage)
- [x] 통합 테스트 통과
- [x] 수동 테스트 완료

## 관련 이슈
Closes #45

## 스크린샷
![DevOps Worker](screenshot.png)
```

**리뷰 대응**:
- 리뷰 코멘트에 정중하게 응답
- 요청된 변경 사항 반영
- 변경 후 리뷰어에게 알림

### 3. 문서 기여

#### 문서 종류

- **README.md**: 프로젝트 소개 및 Quick Start
- **CONTRIBUTING.md**: 기여 가이드 (이 문서)
- **docs/**: mkdocs 기반 문서
  - `docs/guides/`: 사용 가이드
  - `docs/adr/`: 아키텍처 결정 기록
  - `docs/api/`: API 참조

#### 문서 빌드

```bash
# mkdocs 설치
pip install mkdocs mkdocs-material mkdocstrings[python]

# 로컬 서버 실행
mkdocs serve

# 브라우저에서 확인
open http://localhost:8000

# 문서 빌드
mkdocs build
```

#### ADR 작성

새로운 아키텍처 결정 시 ADR 작성:

```bash
# 템플릿 복사
cp docs/adr/0000-template.md docs/adr/0006-new-decision.md

# ADR 작성
# - Status: Accepted | Rejected | Deprecated
# - Context: 문제 상황 및 배경
# - Decision: 선택한 해결 방안
# - Consequences: 긍정적/부정적 결과, 트레이드오프
```

### 4. 리뷰 기여

코드를 작성하지 않아도 리뷰로 기여할 수 있습니다!

- Pull Request 리뷰
- 이슈 트리아지 (라벨링, 중복 확인)
- 문서 오타 수정

## 개발 워크플로우

### 일반적인 흐름

```bash
# 1. 최신 코드 동기화
git checkout main
git pull upstream main

# 2. 새 브랜치 생성
git checkout -b feature/my-feature

# 3. 코드 작성
# ... 코딩 ...

# 4. 테스트 작성 및 실행
pytest

# 5. 포맷팅 및 린트
black src/ tests/
ruff check src/ tests/
mypy src/

# 6. 커밋
git add .
git commit -m "feat(worker): add new feature"

# 7. 푸시
git push origin feature/my-feature

# 8. PR 생성
# GitHub에서 Pull Request 생성

# 9. 리뷰 대응
# 리뷰 코멘트 반영 후 다시 푸시

# 10. 머지
# 리뷰 승인 후 머지
```

### 충돌 해결

```bash
# upstream의 최신 코드 가져오기
git fetch upstream
git rebase upstream/main

# 충돌 해결
# ... 파일 수정 ...
git add .
git rebase --continue

# 푸시 (force push 필요)
git push origin feature/my-feature --force
```

## 릴리스 프로세스

**메인테이너만 해당**

1. 버전 업데이트 (`pyproject.toml`)
2. CHANGELOG.md 업데이트
3. 태그 생성:
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push upstream v0.2.0
   ```
4. GitHub Release 생성
5. PyPI 배포 (자동)

## 질문 및 지원

- **일반 질문**: [Discussions](https://github.com/simdaseul/better-llm/discussions)
- **버그/기능 요청**: [Issues](https://github.com/simdaseul/better-llm/issues)
- **보안 이슈**: security@better-llm.dev

## 라이선스

Better-LLM에 기여하면 [MIT License](LICENSE)에 동의하는 것으로 간주됩니다.

---

다시 한번 기여해주셔서 감사합니다! 🎉
