# Better-LLM 사용 가이드

이 문서는 그룹 챗 오케스트레이션 시스템의 상세한 사용법을 설명합니다. 초보자부터 고급 사용자까지 모두가 활용할 수 있도록 작성되었습니다.

---

## 목차

1. [Quick Start](#1-quick-start)
2. [설치 가이드](#2-설치-가이드)
3. [TUI 사용법](#3-tui-사용법-권장)
4. [CLI 사용법](#4-cli-사용법)
5. [실전 시나리오](#5-실전-시나리오)
6. [고급 기능](#6-고급-기능)
7. [설정 및 커스터마이징](#7-설정-및-커스터마이징)
8. [FAQ 및 문제 해결](#8-faq-및-문제-해결)
9. [Best Practices](#9-best-practices)
10. [참고 자료](#10-참고-자료)

---

## 1. Quick Start

### 30초 만에 시작하기

가장 빠르게 시작하는 방법입니다:

```bash
# 1. 저장소 클론
git clone <repository-url>
cd better-llm

# 2. 의존성 설치
pip install -r requirements.txt

# 3. API 키 설정
export ANTHROPIC_API_KEY='your-api-key-here'

# 4. TUI 실행
python tui.py
```

### 첫 번째 작업 실행

TUI가 실행되면 다음처럼 간단한 작업을 입력해보세요:

```
FastAPI로 /hello 엔드포인트 만들어줘
```

Enter를 누르면 Manager Agent가 자동으로 Planner → Coder → Tester를 호출하여 작업을 완료합니다.

### 시스템 개요

**Better-LLM**은 여러 Claude Agent가 협업하여 소프트웨어 개발 작업을 자동화하는 시스템입니다:

- **Manager Agent**: Worker Tools를 조율하고 작업 흐름을 관리
- **Worker Agents**: 전문화된 역할 수행
  - 🧠 **Planner**: 요구사항 분석 및 계획 수립
  - 💻 **Coder**: 코드 작성 및 수정
  - 🔍 **Reviewer**: 코드 품질 검토
  - 🧪 **Tester**: 테스트 실행 및 검증

**아키텍처**: Clean Architecture (4계층) + Worker Tools Pattern

```
사용자 → Manager Agent → Worker Tools → Worker Agents → 작업 수행
```

---

## 2. 설치 가이드

### 2.1. 시스템 요구사항

- **Python**: 3.10 이상
- **운영체제**: macOS, Linux, Windows (WSL 권장)
- **API 키**: Anthropic API 키 필요
- **Claude CLI**: (선택사항) 자동 탐지됨

### 2.2. 단계별 설치

#### Step 1: 가상 환경 생성

가상 환경을 사용하면 의존성 충돌을 방지할 수 있습니다:

```bash
# 가상 환경 생성
python3 -m venv .venv

# 활성화 (macOS/Linux)
source .venv/bin/activate

# 활성화 (Windows)
.venv\Scripts\activate
```

가상 환경이 활성화되면 터미널 프롬프트에 `(.venv)`가 표시됩니다.

#### Step 2: 의존성 설치

```bash
pip install -r requirements.txt
```

**설치되는 주요 패키지**:
- `claude-agent-sdk`: Claude Agent SDK
- `textual`: TUI 프레임워크
- `rich`: 터미널 출력 포맷팅
- `click`: CLI 프레임워크
- `pytest`: 테스트 프레임워크
- `python-dotenv`: 환경 변수 관리

#### Step 3: API 키 설정

**방법 1: 환경 변수 (임시)**

```bash
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

**방법 2: .env 파일 (권장)**

프로젝트 루트에 `.env` 파일 생성:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." > .env
```

`.env` 파일은 자동으로 로드되며, Git에 커밋되지 않도록 `.gitignore`에 포함되어 있습니다.

**방법 3: 영구 설정 (선택사항)**

`~/.bashrc` 또는 `~/.zshrc`에 추가:

```bash
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

#### Step 4: 설치 확인

설치가 제대로 되었는지 확인:

```bash
# CLI 도움말 확인
python orchestrator.py --help

# 설정 파일 검증
python -c "from pathlib import Path; from src.infrastructure.config.loader import JsonConfigLoader; loader = JsonConfigLoader(); configs = loader.load(Path('config/agent_config.json')); print(f'{len(configs)}개 에이전트 로드됨')"
```

**예상 출력**:
```
4개 에이전트 로드됨
```

### 2.3. 선택적 설정

#### Claude CLI 설정 (선택사항)

Worker Tools가 Claude CLI를 자동으로 탐지합니다. 수동으로 경로를 지정하려면:

```bash
export CLAUDE_CLI_PATH='/path/to/claude'
```

#### 프로젝트 컨텍스트 설정 (선택사항)

프로젝트 루트에 `.context.json` 파일을 생성하면 Worker Agent가 프로젝트 정보를 자동으로 로드합니다:

```json
{
  "project_name": "my-project",
  "language": "python",
  "framework": "fastapi",
  "coding_style": {
    "docstring": "google",
    "type_hints": true,
    "line_length": 100
  }
}
```

### 2.4. 문제 해결

#### "ModuleNotFoundError: No module named 'click'"

가상 환경이 활성화되지 않았을 수 있습니다:

```bash
# 가상 환경 확인
which python  # .venv/bin/python이어야 함

# 가상 환경 활성화
source .venv/bin/activate

# 의존성 재설치
pip install -r requirements.txt
```

#### "ValueError: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다"

API 키가 설정되지 않았습니다:

```bash
# 환경 변수 확인
echo $ANTHROPIC_API_KEY

# .env 파일 확인
cat .env

# API 키 설정
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

#### "FileNotFoundError: 설정 파일을 찾을 수 없습니다"

설정 파일이 없거나 경로가 잘못되었습니다:

```bash
# 설정 파일 확인
ls -la config/

# 필수 파일 목록
# - config/agent_config.json
# - config/system_config.json
```

---

## 3. TUI 사용법 (권장)

### 3.1. TUI 실행

```bash
python tui.py
```

### 3.2. TUI 인터페이스 개요

TUI는 Claude Code 스타일의 터미널 인터페이스를 제공합니다:

```
┌─────────────────────────────────────────────────────────────┐
│ Better-LLM Chat Orchestration                    [Ctrl+Q]   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ [시스템 메시지 영역]                                           │
│ 💬 Manager Agent, Planner, Coder, Reviewer, Tester의         │
│    응답이 실시간으로 스트리밍됩니다.                            │
│                                                               │
│ [Markdown 렌더링, 코드 하이라이팅 지원]                        │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│ > 작업을 입력하세요...                              [Enter]   │
└─────────────────────────────────────────────────────────────┘
```

### 3.3. 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Enter` | 작업 실행 |
| `F1` | 도움말 표시 |
| `F2` | 설정 열기 |
| `F3` | 메트릭 패널 토글 |
| `Ctrl+S` | 로그 저장 |
| `Ctrl+F` | 로그 검색 |
| `Ctrl+N` | 새 세션 시작 |
| `Ctrl+C` | 중단/종료 |
| `Up/Down` | 입력 히스토리 탐색 |

**참고**: 화면 지우기는 `/clear` 슬래시 커맨드를 사용하세요.

### 3.4. 기본 사용법

#### 일반 작업 요청

TUI 하단의 입력 창에 작업을 입력하고 Enter를 누릅니다:

```
FastAPI로 /users CRUD 엔드포인트 구현해줘
```

Manager Agent가 자동으로 작업을 분석하고 적절한 Worker를 호출합니다.

#### 특정 Agent 호출

`@agent_name`을 사용하여 특정 Agent를 직접 호출할 수 있습니다:

```
@planner 이 작업의 구현 계획을 수립해줘
```

```
@coder main.py에 로깅 기능 추가해줘
```

```
@reviewer src/api.py 코드 리뷰해줘
```

```
@tester 테스트 실행하고 결과 보고해줘
```

### 3.5. TUI 고급 기능

#### 설정 (Ctrl+S)

설정 모달에서 다음을 조정할 수 있습니다:

- **테마**: Light/Dark/Auto
- **Markdown 렌더링**: 활성화/비활성화
- **코드 하이라이팅**: 활성화/비활성화
- **자동 스크롤**: 활성화/비활성화
- **입력 히스토리 크기**: 기본 100
- **성능 메트릭 표시**: 활성화/비활성화

설정은 `~/.better-llm/tui_config.json`에 저장됩니다.

#### 검색 (Ctrl+/)

대화 히스토리에서 키워드를 검색할 수 있습니다:

1. `Ctrl+/`를 눌러 검색 모드 진입
2. 검색어 입력
3. `Enter`로 다음 결과 찾기
4. `Shift+Enter`로 이전 결과 찾기
5. `Esc`로 검색 종료

#### 로그 내보내기 (Ctrl+E)

현재 세션의 대화 히스토리를 파일로 내보낼 수 있습니다:

- **Markdown**: `session_<id>.md`
- **JSON**: `session_<id>.json`
- **Plain Text**: `session_<id>.txt`

파일은 `sessions/` 디렉토리에 저장됩니다.

#### 입력 히스토리 (Up/Down)

이전에 입력한 명령을 Up/Down 키로 탐색할 수 있습니다. 히스토리는 세션이 종료되어도 유지됩니다.

### 3.6. 세션 관리

#### 새 세션 시작 (Ctrl+N)

현재 대화를 저장하고 새 세션을 시작합니다.

#### 세션 자동 저장

모든 세션은 `sessions/` 디렉토리에 자동으로 저장됩니다:

```
sessions/
├── abc123_session.json       # 세션 데이터
├── abc123_metrics.txt        # 성능 메트릭
└── abc123_conversation.md    # 대화 히스토리 (Markdown)
```

#### 이전 세션 불러오기

CLI를 사용하여 이전 세션을 확인할 수 있습니다:

```bash
python orchestrator.py session list
python orchestrator.py session show <session_id>
```

### 3.7. 성능 메트릭

설정에서 "성능 메트릭 표시"를 활성화하면 다음 정보가 표시됩니다:

- **Worker별 실행 시간**: 각 Worker가 소요한 시간
- **토큰 사용량**: 입력/출력 토큰 수
- **API 호출 횟수**: Manager/Worker 호출 횟수
- **에러 발생 횟수**: 재시도 횟수 포함

메트릭은 세션 종료 시 `sessions/<session_id>_metrics.txt`에 저장됩니다.

---

## 4. CLI 사용법

### 4.1. 기본 명령어

```bash
python orchestrator.py "작업 설명"
```

### 4.2. 옵션

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--verbose` | 상세 로깅 활성화 | `python orchestrator.py --verbose "작업"` |
| `--config` | 커스텀 설정 파일 | `python orchestrator.py --config custom.json "작업"` |
| `--help` | 도움말 표시 | `python orchestrator.py --help` |

### 4.3. 세션 관리 명령어

```bash
# 세션 목록 조회
python orchestrator.py session list

# 세션 상세 조회
python orchestrator.py session show <session_id>

# 여러 세션 일괄 삭제 (조건: 생성일, 상태)
python orchestrator.py session cleanup --older-than 7 --status failed

# 세션 내보내기
python orchestrator.py session export <session_id> --format markdown
```

### 4.4. 템플릿 관리 명령어

```bash
# 템플릿 목록 조회
python orchestrator.py template list

# 템플릿 사용
python orchestrator.py template use <template_name> --vars key=value

# 내장 템플릿 초기화
python orchestrator.py template init
```

**참고**: 템플릿 생성/삭제는 직접 `templates/` 디렉토리에서 JSON 파일을 편집하세요.

---

## 5. 실전 시나리오

이 섹션에서는 실제 개발 상황에서 Better-LLM을 어떻게 사용하는지 5가지 시나리오로 설명합니다.

### 5.1. 시나리오 1: 신규 기능 개발

**상황**: FastAPI 프로젝트에 사용자 인증 기능을 추가해야 합니다.

**단계별 진행**:

#### Step 1: TUI 실행 및 작업 요청

```bash
python tui.py
```

TUI 입력 창에 다음을 입력:

```
FastAPI에 JWT 기반 사용자 인증 시스템 구현해줘. /login, /register, /me 엔드포인트 필요해.
```

#### Step 2: Manager가 Planner 호출

Manager Agent가 자동으로 작업을 분석하고 Planner를 호출합니다:

```
[Manager] 사용자 인증 시스템 구현 작업을 시작합니다.
[Manager] Planner에게 계획 수립을 요청합니다...

[Planner] 요구사항 분석 중...

## 요구사항 요약
- JWT 기반 사용자 인증
- 엔드포인트: /login, /register, /me
- FastAPI 프레임워크 사용

## 구현 단계
1. 의존성 추가 (python-jose, passlib)
2. User 모델 및 JWT 유틸리티 작성
3. /register 엔드포인트 구현
4. /login 엔드포인트 구현
5. /me 엔드포인트 구현 (인증 필요)
6. 테스트 작성

## 필요한 파일
- requirements.txt (수정)
- models/user.py (생성)
- utils/auth.py (생성)
- routes/auth.py (생성)
- tests/test_auth.py (생성)

@coder please implement this plan
```

#### Step 3: Coder가 코드 작성

Coder가 계획에 따라 파일을 생성/수정합니다:

```
[Coder] 계획에 따라 구현을 시작합니다.

1. requirements.txt에 의존성 추가...
   - python-jose[cryptography]
   - passlib[bcrypt]
   - python-multipart

2. models/user.py 생성...
   [코드 작성 중...]

3. utils/auth.py 생성...
   [코드 작성 중...]

4. routes/auth.py 생성...
   [코드 작성 중...]

@tester please verify this implementation
```

#### Step 4: Tester가 검증

Tester가 코드를 검증하고 테스트를 실행합니다:

```
[Tester] 구현된 코드를 검증합니다.

1. 의존성 설치 확인...
   ✅ python-jose 설치됨
   ✅ passlib 설치됨

2. 코드 검증...
   ✅ User 모델 정의 확인
   ✅ JWT 토큰 생성/검증 로직 확인
   ✅ 엔드포인트 구현 확인

3. 테스트 작성 및 실행...
   [테스트 작성 중...]
   [테스트 실행 중...]

   ✅ test_register_user PASSED
   ✅ test_login_user PASSED
   ✅ test_get_current_user PASSED
   ✅ test_invalid_token PASSED

TERMINATE - 모든 테스트 통과, 작업 완료
```

#### Step 5: 결과 확인

작업이 완료되면 세션 요약이 표시됩니다:

```
[Manager] 작업이 성공적으로 완료되었습니다.

📊 세션 요약
- 세션 ID: abc123
- 소요 시간: 2분 34초
- 호출된 Worker: Planner, Coder, Tester
- 생성된 파일: 4개
- 수정된 파일: 1개
- 테스트 통과: 4/4
- 세션 저장 위치: sessions/abc123_session.json
```

**실제 예시 코드 (생성된 파일)**:

`models/user.py`:
```python
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """사용자 모델."""

    username: str
    email: EmailStr
    hashed_password: str
    is_active: bool = True


class UserCreate(BaseModel):
    """사용자 생성 요청 모델."""

    username: str
    email: EmailStr
    password: str
```

`utils/auth.py`:
```python
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext


SECRET_KEY = "your-secret-key-here"  # 환경 변수로 관리
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해싱."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 액세스 토큰 생성."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

### 5.2. 시나리오 2: 버그 수정

**상황**: 로그인 API에서 500 에러가 발생합니다.

**작업 요청**:

```
로그인 API에서 500 에러 발생. routes/auth.py의 login 함수에서 NoneType 에러. 원인 찾고 수정해줘.
```

**진행 과정**:

1. **Planner**: 에러 원인 분석 계획 수립
   - `routes/auth.py` 파일 읽기
   - 에러 로그 확인
   - 잠재적 원인 식별

2. **Coder**: 파일 읽고 버그 찾기
   ```
   [Coder] routes/auth.py를 분석합니다...

   🔍 발견된 문제:
   Line 45: user = get_user(username)
   Line 46: if verify_password(password, user.hashed_password):

   문제: get_user()가 None을 반환할 때 user.hashed_password 접근 시 AttributeError 발생

   수정 방법:
   - user가 None인지 먼저 확인
   - 사용자 없을 때 적절한 에러 반환
   ```

3. **Coder**: 버그 수정
   ```python
   # Before
   user = get_user(username)
   if verify_password(password, user.hashed_password):
       return create_token(user)

   # After
   user = get_user(username)
   if user is None:
       raise HTTPException(status_code=401, detail="Invalid credentials")
   if verify_password(password, user.hashed_password):
       return create_token(user)
   ```

4. **Reviewer**: 코드 리뷰
   ```
   [Reviewer] 수정 사항 검토...

   ✅ None 체크 추가됨
   ✅ 적절한 HTTP 상태 코드 사용 (401)
   ✅ 에러 메시지 명확함

   🔵 Info: 보안 강화를 위해 에러 메시지를 더 generic하게 변경 권장
   (예: "Invalid credentials" 대신 "Authentication failed")
   ```

5. **Tester**: 테스트 실행
   ```
   [Tester] 테스트 실행 중...

   ✅ test_login_valid_user PASSED
   ✅ test_login_invalid_username PASSED (새로 추가)
   ✅ test_login_invalid_password PASSED

   TERMINATE - 버그 수정 완료, 모든 테스트 통과
   ```

### 5.3. 시나리오 3: 리팩토링

**상황**: `payment.py` 모듈이 너무 길고 복잡해서 유지보수가 어렵습니다.

**작업 요청**:

```
payment.py 모듈을 클래스 기반으로 리팩토링해줘. 단일 책임 원칙 적용하고, 테스트도 같이 리팩토링해야 해.
```

**진행 과정**:

1. **Planner**: 리팩토링 계획 수립
   ```
   [Planner] payment.py 분석 및 리팩토링 계획 수립...

   ## 현재 구조 분석
   - payment.py: 450줄, 15개 함수
   - 책임: 결제 처리, 환불, 검증, 로깅

   ## 리팩토링 계획
   1. PaymentProcessor 클래스 생성
      - process_payment()
      - refund_payment()

   2. PaymentValidator 클래스 생성
      - validate_card()
      - validate_amount()

   3. PaymentLogger 클래스 생성
      - log_transaction()
      - log_error()

   4. 테스트 리팩토링
      - 클래스별로 테스트 분리
      - Mock 객체 사용

   @coder please implement this plan
   ```

2. **Coder**: 리팩토링 실행
   ```
   [Coder] 리팩토링 시작...

   1. payment/processor.py 생성 (PaymentProcessor 클래스)
   2. payment/validator.py 생성 (PaymentValidator 클래스)
   3. payment/logger.py 생성 (PaymentLogger 클래스)
   4. payment/__init__.py 업데이트
   5. tests/test_payment.py 리팩토링

   @reviewer please review this refactoring
   ```

3. **Reviewer**: 코드 리뷰
   ```
   [Reviewer] 리팩토링 검토...

   ✅ 단일 책임 원칙 잘 적용됨
   ✅ 클래스별로 명확히 분리됨
   ✅ 의존성 주입 사용

   🟡 Warning: PaymentProcessor의 __init__에서 logger를 직접 생성
   → 의존성 주입으로 변경 권장

   🔵 Info: Docstring 추가 권장
   ```

4. **Coder**: Reviewer 피드백 반영
   ```
   [Coder] Reviewer 피드백 반영...

   - PaymentProcessor.__init__에 logger 파라미터 추가
   - 모든 클래스에 Google 스타일 docstring 추가

   @tester please verify this implementation
   ```

5. **Tester**: 테스트 실행
   ```
   [Tester] 리팩토링 후 테스트 실행...

   ✅ test_payment_processor PASSED (10 tests)
   ✅ test_payment_validator PASSED (8 tests)
   ✅ test_payment_logger PASSED (5 tests)
   ✅ test_integration PASSED (3 tests)

   Coverage: 95% → 98% (개선됨)

   TERMINATE - 리팩토링 완료, 모든 테스트 통과
   ```

### 5.4. 시나리오 4: 테스트 작성

**상황**: 기존 코드에 테스트가 없어서 추가해야 합니다.

**작업 요청**:

```
src/utils/string_utils.py에 대한 유닛 테스트 작성해줘. pytest 사용하고 coverage 90% 이상 달성해야 해.
```

**진행 과정**:

1. **Planner**: 테스트 계획
   ```
   [Planner] 테스트 계획 수립...

   ## 파일 분석
   - string_utils.py: 5개 함수
     1. capitalize_first(text)
     2. snake_to_camel(text)
     3. camel_to_snake(text)
     4. truncate(text, length)
     5. remove_whitespace(text)

   ## 테스트 케이스
   1. 정상 케이스 (각 함수별)
   2. 엣지 케이스 (빈 문자열, None, 특수문자)
   3. 경계값 테스트 (truncate 길이)
   4. 예외 처리 테스트

   @coder please implement this plan
   ```

2. **Coder**: 테스트 작성
   ```
   [Coder] tests/test_string_utils.py 작성...

   - TestCapitalizeFirst 클래스 (4 tests)
   - TestSnakeToCamel 클래스 (5 tests)
   - TestCamelToSnake 클래스 (5 tests)
   - TestTruncate 클래스 (6 tests)
   - TestRemoveWhitespace 클래스 (4 tests)

   총 24개 테스트 작성

   @tester please verify this implementation
   ```

3. **Tester**: 테스트 실행 및 커버리지 확인
   ```
   [Tester] 테스트 실행 중...

   pytest tests/test_string_utils.py -v --cov=src/utils/string_utils

   ======================== test session starts =========================
   tests/test_string_utils.py::TestCapitalizeFirst::test_normal PASSED
   tests/test_string_utils.py::TestCapitalizeFirst::test_empty PASSED
   ...
   ======================== 24 passed in 0.12s ==========================

   ---------- coverage: platform darwin, python 3.10.0 -----------
   Name                          Stmts   Miss  Cover
   -------------------------------------------------
   src/utils/string_utils.py        25      1    96%

   ✅ Coverage 목표 달성: 96% (목표: 90%)

   TERMINATE - 테스트 작성 완료
   ```

### 5.5. 시나리오 5: 코드 리뷰

**상황**: Pull Request 전에 코드 리뷰가 필요합니다.

**작업 요청**:

```
@reviewer src/api/orders.py 코드 리뷰해줘. 보안, 성능, 코드 품질 모두 체크해야 해.
```

**진행 과정**:

1. **Reviewer**: 코드 리뷰 실행
   ```
   [Reviewer] src/api/orders.py 코드 리뷰 시작...

   ## 🔴 Critical Issues (2)

   1. SQL Injection 취약점 (Line 45)
      ```python
      query = f"SELECT * FROM orders WHERE user_id = {user_id}"
      ```
      → 파라미터화된 쿼리 사용 필요

   2. 하드코딩된 시크릿 (Line 12)
      ```python
      API_KEY = "sk-1234567890abcdef"
      ```
      → 환경 변수로 관리 필요

   ## 🟡 Warnings (3)

   1. 에러 처리 부재 (Line 78)
      - try-except 블록 추가 권장

   2. 긴 함수 (process_order: 150줄)
      - 여러 함수로 분리 권장

   3. Type Hints 누락
      - 모든 함수에 타입 힌트 추가 권장

   ## 🔵 Info (5)

   1. Docstring 형식 통일 (Google 스타일 사용 권장)
   2. 로깅 레벨 조정 (DEBUG → INFO)
   3. 변수명 개선 (d → order_data)
   4. 주석 추가 (복잡한 비즈니스 로직)
   5. 테스트 커버리지 향상 (현재 70% → 목표 90%)

   @coder please fix critical issues
   ```

2. **Coder**: Critical 이슈 수정
   ```
   [Coder] Critical 이슈 수정...

   1. SQL Injection 수정
      ```python
      # Before
      query = f"SELECT * FROM orders WHERE user_id = {user_id}"

      # After
      query = "SELECT * FROM orders WHERE user_id = ?"
      cursor.execute(query, (user_id,))
      ```

   2. 시크릿 환경 변수화
      ```python
      # Before
      API_KEY = "sk-1234567890abcdef"

      # After
      import os
      API_KEY = os.getenv("API_KEY")
      if not API_KEY:
          raise ValueError("API_KEY environment variable not set")
      ```

   @reviewer please re-review
   ```

3. **Reviewer**: 재검토
   ```
   [Reviewer] Critical 이슈 재검토...

   ✅ SQL Injection 수정 확인
   ✅ 시크릿 환경 변수화 확인

   🟡 Warning: API_KEY가 None일 때 에러 처리 추가됨 (Good!)

   남은 Warning/Info 이슈는 우선순위가 낮으므로 별도 PR로 처리 가능

   TERMINATE - Critical 이슈 모두 수정됨
   ```

---

## 6. 고급 기능

### 6.1. 템플릿 시스템

템플릿을 사용하면 반복적인 작업을 자동화할 수 있습니다.

#### 내장 템플릿 사용

```bash
# 템플릿 목록 확인
python orchestrator.py template list

# 내장 템플릿 예시:
# - api_endpoint: REST API 엔드포인트 생성
# - crud_model: CRUD 모델 생성
# - test_suite: 테스트 스위트 생성
# - bug_fix: 버그 수정
# - refactor: 리팩토링

# 템플릿 사용
python orchestrator.py template use api_endpoint --vars \
  model=User \
  endpoint=/users \
  methods=GET,POST,PUT,DELETE
```

#### 커스텀 템플릿 생성

**Step 1**: 템플릿 파일 작성 (`templates/my_template.txt`)

```jinja2
{{ model }} 모델에 대한 {{ framework }} {{ endpoint_type }} 엔드포인트를 구현해줘.

요구사항:
- 엔드포인트: {{ endpoint }}
- 메서드: {% for method in methods %}{{ method }}{% if not loop.last %}, {% endif %}{% endfor %}
- 인증: {{ auth_required|default("불필요") }}
- 검증: {{ validation|default("기본 검증") }}

{% if include_tests %}
테스트 코드도 함께 작성해줘.
{% endif %}
```

**Step 2**: 템플릿 등록

```bash
python orchestrator.py template create my_api_template --file templates/my_template.txt
```

**Step 3**: 템플릿 사용

```bash
python orchestrator.py template use my_api_template --vars \
  model=Product \
  framework=FastAPI \
  endpoint_type=REST API \
  endpoint=/products \
  methods=GET,POST \
  auth_required=JWT \
  include_tests=true
```

### 6.2. 승인 워크플로우

중요한 작업(코드 작성, 배포 등)을 실행하기 전에 사용자 승인을 받을 수 있습니다.

#### 승인 워크플로우 활성화

`config/system_config.json` 수정:

```json
{
  "approval": {
    "enabled": true,
    "timeout_seconds": 300,
    "approval_points": {
      "before_code_write": true,
      "after_code_write": true,
      "before_test_run": false,
      "before_deployment": true
    },
    "auto_approve_on_timeout": false
  }
}
```

#### 승인 프로세스

```
[Coder] 다음 파일을 수정하려고 합니다:
  - src/api/users.py (50줄 추가)
  - src/models/user.py (신규)

승인하시겠습니까? (y/n/feedback)
> y

[Coder] 승인되었습니다. 코드 작성 시작...
```

**피드백 제공**:

```
승인하시겠습니까? (y/n/feedback)
> feedback

피드백을 입력하세요 (완료: Ctrl+D):
> User 모델에 email validation 추가해주세요.
> 그리고 테스트도 함께 작성해주세요.
> ^D

[Coder] 피드백을 반영하여 다시 계획을 수립합니다...
```

#### 승인 이력 조회

```bash
python orchestrator.py approval list
python orchestrator.py approval history --session <session_id>
```

### 6.3. Circuit Breaker 패턴

Worker Agent가 반복적으로 실패할 때 자동으로 차단하여 리소스 낭비를 방지합니다.

#### Circuit Breaker 설정

`config/system_config.json`:

```json
{
  "resilience": {
    "circuit_breaker": {
      "failure_threshold": 5,
      "success_threshold": 2,
      "timeout_seconds": 60,
      "enable_per_worker": true
    }
  }
}
```

**설정 설명**:
- `failure_threshold`: 연속 실패 N회 시 Circuit Open
- `success_threshold`: 연속 성공 N회 시 Circuit Close
- `timeout_seconds`: Circuit Open 후 재시도 대기 시간
- `enable_per_worker`: Worker별로 Circuit Breaker 분리

#### Circuit Breaker 상태

```
[Manager] Coder Worker가 5회 연속 실패하여 Circuit이 OPEN되었습니다.
[Manager] 60초 후 재시도합니다...

[60초 후]
[Manager] Circuit이 HALF_OPEN 상태로 전환되었습니다. 재시도 중...

[성공 시]
[Manager] Coder Worker가 정상 작동합니다. Circuit이 CLOSED되었습니다.
```

### 6.4. 재시도 정책

Worker Tool 실행 실패 시 자동으로 재시도합니다.

#### 재시도 설정

`config/system_config.json`:

```json
{
  "performance": {
    "worker_retry_enabled": true,
    "worker_retry_max_attempts": 3,
    "worker_retry_base_delay": 1.0,
    "worker_retry_max_delay": 30.0,
    "worker_retry_jitter": 0.1,
    "worker_retry_exponential": true
  }
}
```

**재시도 동작**:
- 1회 실패: 1초 후 재시도
- 2회 실패: 2초 후 재시도 (지수 백오프)
- 3회 실패: 4초 후 재시도
- 최종 실패: Circuit Breaker 동작

### 6.5. 프롬프트 캐싱

동일한 시스템 프롬프트를 재사용하여 비용과 지연 시간을 절감합니다.

#### 캐싱 활성화

`config/system_config.json`:

```json
{
  "performance": {
    "enable_caching": true
  }
}
```

**캐싱 효과**:
- API 호출 속도: 2-3배 향상
- 토큰 비용: 최대 90% 절감 (캐시 히트 시)

### 6.6. 세션 저장소 (SQLite)

기본 JSON 파일 대신 SQLite 데이터베이스를 사용할 수 있습니다.

#### SQLite 활성화

`config/system_config.json`:

```json
{
  "storage": {
    "backend": "sqlite",
    "sqlite_db_path": "data/sessions.db",
    "retention_days": 90
  }
}
```

#### 마이그레이션

```bash
# JSON → SQLite 마이그레이션
python orchestrator.py session migrate --from json --to sqlite
```

#### SQLite 장점

- **빠른 검색**: 세션 ID, 날짜, Worker 이름으로 검색
- **집계 쿼리**: 통계 및 분석
- **데이터 무결성**: ACID 보장
- **압축**: JSON 대비 50% 저장 공간 절감

---

## 7. 설정 및 커스터마이징

### 7.1. Agent 설정 (agent_config.json)

`config/agent_config.json`:

```json
{
  "agents": [
    {
      "name": "planner",
      "role": "계획 수립",
      "system_prompt_file": "prompts/planner.txt",
      "tools": ["read", "glob"],
      "model": "claude-sonnet-4-5-20250929"
    },
    {
      "name": "coder",
      "role": "코드 작성",
      "system_prompt_file": "prompts/coder.txt",
      "tools": ["read", "write", "edit", "glob", "grep", "bash"],
      "model": "claude-sonnet-4-5-20250929"
    }
  ]
}
```

**설정 항목**:
- `name`: Worker 이름 (고유해야 함)
- `role`: Worker 역할 (설명)
- `system_prompt_file`: 시스템 프롬프트 파일 경로
- `tools`: 사용 가능한 도구 목록
- `model`: Claude 모델 ID

**사용 가능한 도구**:
- `read`: 파일 읽기
- `write`: 파일 쓰기
- `edit`: 파일 수정
- `glob`: 파일 검색 (패턴)
- `grep`: 코드 검색 (정규식)
- `bash`: 셸 명령 실행

### 7.2. 시스템 설정 (system_config.json)

`config/system_config.json`:

```json
{
  "manager": {
    "model": "claude-sonnet-4-5-20250929",
    "max_history_messages": 20,
    "max_turns": 10
  },
  "resilience": {
    "circuit_breaker": {
      "failure_threshold": 5,
      "success_threshold": 2,
      "timeout_seconds": 60,
      "enable_per_worker": true
    }
  },
  "timeouts": {
    "default_worker_timeout": 300,
    "max_worker_timeout": 1800
  },
  "performance": {
    "enable_caching": true,
    "worker_retry_enabled": true,
    "worker_retry_max_attempts": 3
  },
  "security": {
    "max_input_length": 5000,
    "enable_input_validation": true
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

### 7.3. 시스템 프롬프트 커스터마이징

Worker Agent의 행동을 변경하려면 `prompts/*.txt` 파일을 수정하세요.

**예시**: Coder를 더 설명적으로 만들기

`prompts/coder.txt`:

```
당신은 Staff Software Engineer입니다.
계획에 따라 코드를 작성하거나 수정하세요.

## 추가 규칙
- 모든 변경 사항에 대해 **상세한 설명**을 제공하세요
- 코드 예시를 **항상** 포함하세요
- 복잡한 로직은 **단계별로** 설명하세요

...
```

### 7.4. 새 Worker Agent 추가

#### Step 1: 프롬프트 작성

`prompts/deployer.txt`:

```
당신은 DevOps Engineer입니다.
애플리케이션을 배포하고 인프라를 관리하세요.

## 역할
- Docker 이미지 빌드
- Kubernetes 배포
- CI/CD 파이프라인 관리

...
```

#### Step 2: Agent 설정 추가

`config/agent_config.json`:

```json
{
  "agents": [
    ...
    {
      "name": "deployer",
      "role": "배포 및 인프라",
      "system_prompt_file": "prompts/deployer.txt",
      "tools": ["read", "bash"],
      "model": "claude-sonnet-4-5-20250929"
    }
  ]
}
```

#### Step 3: Worker Tool 추가

`src/infrastructure/mcp/worker_tools.py`:

```python
@tool(
    "execute_deployer_task",
    "배포 및 인프라 관리 작업 수행",
    {"task_description": str}
)
async def execute_deployer_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """Deployer Worker Tool."""
    deployer_use_case = get_deployer_use_case()
    result = await deployer_use_case.execute(args["task_description"])
    return {"content": [{"type": "text", "text": result}]}
```

#### Step 4: Use Case 추가

`src/application/use_cases/execute_deployer_use_case.py`:

```python
from src.application.use_cases.base_worker_use_case import BaseWorkerUseCase


class ExecuteDeployerUseCase(BaseWorkerUseCase):
    """Deployer Use Case."""

    def __init__(self, worker_adapter, context_repo, metrics_collector):
        super().__init__("deployer", worker_adapter, context_repo, metrics_collector)
```

#### Step 5: 사용

```
@deployer Docker 이미지 빌드하고 production 환경에 배포해줘
```

### 7.5. 프로젝트 컨텍스트 설정

`.context.json` 파일을 생성하면 Worker Agent가 프로젝트 정보를 자동으로 로드합니다:

```json
{
  "project_name": "my-awesome-project",
  "description": "FastAPI 기반 REST API",
  "language": "python",
  "framework": "fastapi",
  "architecture": "Clean Architecture",
  "coding_style": {
    "docstring": "google",
    "type_hints": true,
    "line_length": 100,
    "quote_style": "double"
  },
  "testing": {
    "framework": "pytest",
    "coverage_threshold": 90,
    "test_runner": "pytest -v --cov"
  },
  "dependencies": {
    "core": ["fastapi", "pydantic", "sqlalchemy"],
    "dev": ["pytest", "black", "mypy"]
  }
}
```

Worker Agent는 이 정보를 참고하여 일관성 있는 코드를 생성합니다.

---

## 8. FAQ 및 문제 해결

### 8.1. 자주 묻는 질문 (FAQ)

#### Q1: Manager와 Worker의 차이는 무엇인가요?

**A**:
- **Manager Agent**: 전체 작업을 조율하는 에이전트입니다. 사용자 요청을 분석하고 적절한 Worker Tool을 호출합니다.
- **Worker Agents**: 특정 작업을 수행하는 전문화된 에이전트입니다 (Planner, Coder, Reviewer, Tester).

#### Q2: TUI와 CLI 중 어떤 것을 사용해야 하나요?

**A**:
- **TUI 권장**: 인터랙티브한 작업, 실시간 피드백, 세션 관리가 필요한 경우
- **CLI 권장**: 자동화 스크립트, CI/CD 파이프라인, 간단한 일회성 작업

#### Q3: Worker Tool 호출 순서를 지정할 수 있나요?

**A**:
아니요. Manager Agent가 작업 내용을 분석하여 자동으로 Worker 호출 순서를 결정합니다. 다만 `@agent_name`을 사용하여 특정 Worker를 직접 호출할 수는 있습니다.

#### Q4: 여러 프로젝트에서 동시에 사용할 수 있나요?

**A**:
네. 각 프로젝트 디렉토리에서 Better-LLM을 실행하면 해당 프로젝트의 `.context.json`을 자동으로 로드합니다. 세션도 프로젝트별로 분리됩니다.

#### Q5: API 비용은 얼마나 드나요?

**A**:
작업 복잡도에 따라 다르지만, 일반적인 작업(CRUD API 생성)은 약 $0.10-0.50 정도입니다. 프롬프트 캐싱을 활성화하면 비용을 최대 90% 절감할 수 있습니다.

#### Q6: 오프라인 환경에서 사용할 수 있나요?

**A**:
아니요. Better-LLM은 Anthropic API를 사용하므로 인터넷 연결이 필요합니다.

#### Q7: Worker Agent를 병렬로 실행할 수 있나요?

**A**:
현재 버전(v4.0)에서는 순차 실행만 지원합니다. 병렬 실행은 향후 버전에서 지원 예정입니다.

#### Q8: 세션 데이터는 어디에 저장되나요?

**A**:
- JSON 모드: `sessions/` 디렉토리
- SQLite 모드: `data/sessions.db` 파일

#### Q9: 특정 파일만 수정하도록 제한할 수 있나요?

**A**:
현재는 지원하지 않지만, 승인 워크플로우를 활성화하면 코드 작성 전에 확인할 수 있습니다.

#### Q10: Claude Code와의 차이는 무엇인가요?

**A**:
- **Claude Code**: 단일 Agent 기반, IDE 통합
- **Better-LLM**: 다중 Agent 협업, 워크플로우 자동화, Clean Architecture

### 8.2. 일반적인 문제 해결

#### 문제 1: "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다"

**원인**: API 키가 설정되지 않았습니다.

**해결**:
```bash
# 환경 변수 확인
echo $ANTHROPIC_API_KEY

# 없으면 설정
export ANTHROPIC_API_KEY='sk-ant-api03-...'

# 또는 .env 파일 생성
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." > .env
```

#### 문제 2: "ModuleNotFoundError: No module named 'textual'"

**원인**: 의존성이 설치되지 않았습니다.

**해결**:
```bash
# 가상 환경 확인
which python  # .venv/bin/python이어야 함

# 가상 환경 활성화
source .venv/bin/activate

# 의존성 재설치
pip install -r requirements.txt
```

#### 문제 3: "Worker Tool 호출 실패"

**원인**: Worker Agent 설정 오류 또는 프롬프트 파일 누락

**해결**:
```bash
# 설정 파일 확인
cat config/agent_config.json

# 프롬프트 파일 확인
ls -la prompts/

# Worker Tools 단독 테스트
python test_worker_tools.py
```

#### 문제 4: "Circuit Breaker OPEN"

**원인**: Worker Agent가 반복적으로 실패했습니다.

**해결**:
```bash
# 로그 확인
tail -f logs/better-llm.log

# Circuit Breaker 타임아웃 대기 (기본 60초)
# 또는 설정 변경 (config/system_config.json)
```

#### 문제 5: "TUI 화면이 깨짐"

**원인**: 터미널 크기가 너무 작거나 색상 지원 부족

**해결**:
```bash
# 터미널 크기 확인 (최소 80x24 권장)
tput cols  # 80 이상
tput lines # 24 이상

# 색상 지원 확인
echo $TERM  # xterm-256color 권장

# TERM 변수 설정
export TERM=xterm-256color
```

#### 문제 6: "세션 로드 실패"

**원인**: 세션 파일이 손상되었거나 형식이 잘못되었습니다.

**해결**:
```bash
# 세션 파일 확인
cat sessions/<session_id>_session.json | jq .

# 손상된 파일 삭제
rm sessions/<session_id>*

# SQLite 복구 (SQLite 모드인 경우)
sqlite3 data/sessions.db "PRAGMA integrity_check;"
```

#### 문제 7: "API Rate Limit 초과"

**원인**: Anthropic API 요청 한도를 초과했습니다.

**해결**:
```bash
# 재시도 설정 조정 (config/system_config.json)
{
  "performance": {
    "worker_retry_base_delay": 5.0,  # 지연 시간 증가
    "worker_retry_max_delay": 60.0
  }
}

# 또는 잠시 대기 후 재시도
```

#### 문제 8: "프롬프트 파일 로드 실패"

**원인**: 프롬프트 파일이 없거나 권한 문제

**해결**:
```bash
# 파일 존재 확인
ls -la prompts/

# 권한 확인
chmod 644 prompts/*.txt

# 샘플 프롬프트로 테스트
cat prompts/planner.txt
```

### 8.3. 디버깅 팁

#### Verbose 로깅 활성화

```bash
# CLI
python orchestrator.py --verbose "작업"

# 로그 레벨 변경 (config/system_config.json)
{
  "logging": {
    "level": "DEBUG"
  }
}
```

#### Worker Tools 단독 테스트

```bash
python test_worker_tools.py
```

#### 구문 검사

```bash
python3 -m py_compile src/**/*.py *.py
```

#### 통합 테스트

```bash
python test_integration.py
```

---

## 9. Best Practices

### 9.1. 효과적인 작업 요청 작성

#### 좋은 예시

```
FastAPI로 사용자 관리 API를 구현해줘.

요구사항:
- /users GET (목록 조회, 페이지네이션)
- /users POST (사용자 생성, 이메일 검증)
- /users/{id} GET (상세 조회)
- /users/{id} PUT (수정)
- /users/{id} DELETE (삭제)
- SQLAlchemy ORM 사용
- pytest 테스트 포함
```

**이유**:
- ✅ 구체적인 엔드포인트 명시
- ✅ 요구사항 명확함
- ✅ 기술 스택 지정
- ✅ 테스트 포함 요청

#### 나쁜 예시

```
API 만들어줘
```

**이유**:
- ❌ 너무 모호함
- ❌ 엔드포인트 불명확
- ❌ 기술 스택 미지정
- ❌ 요구사항 부족

### 9.2. Agent 선택 가이드

| 작업 유형 | 추천 Agent | 예시 |
|----------|-----------|------|
| 계획 수립 | `@planner` | "이 기능의 구현 계획 수립해줘" |
| 코드 작성 | `@coder` | "User 모델 생성해줘" |
| 코드 리뷰 | `@reviewer` | "이 PR 코드 리뷰해줘" |
| 테스트 실행 | `@tester` | "테스트 실행하고 결과 보고해줘" |
| 자동 판단 | 멘션 없음 | "FastAPI API 만들어줘" |

### 9.3. 세션 관리

#### 세션 분리

각 작업을 별도 세션으로 분리하세요:

```
# 기능 A 작업
[Ctrl+N] 새 세션 시작

# 기능 B 작업
[Ctrl+N] 새 세션 시작
```

**이유**:
- ✅ 컨텍스트 혼란 방지
- ✅ 세션별 메트릭 추적
- ✅ 롤백 용이

#### 세션 저장 확인

중요한 작업 후 세션 저장 확인:

```bash
ls -la sessions/ | grep <session_id>
```

### 9.4. 비용 절감 팁

#### 프롬프트 캐싱 활성화

```json
{
  "performance": {
    "enable_caching": true
  }
}
```

**절감 효과**: 최대 90%

#### 불필요한 Worker 호출 방지

특정 Worker만 필요한 경우 직접 호출:

```
@coder src/utils.py에 함수 추가해줘
```

Manager를 거치지 않아 1회 API 호출 절약

#### 히스토리 크기 조정

```json
{
  "manager": {
    "max_history_messages": 10
  }
}
```

**절감 효과**: 토큰 사용량 감소

### 9.5. 보안 Best Practices

#### 시크릿 관리

```python
# ❌ 나쁜 예시
API_KEY = "sk-1234567890abcdef"

# ✅ 좋은 예시
import os
API_KEY = os.getenv("API_KEY")
```

#### 입력 검증

```json
{
  "security": {
    "max_input_length": 5000,
    "enable_input_validation": true
  }
}
```

#### 파일 접근 제한

`.context.json`에 화이트리스트 추가 (향후 지원 예정):

```json
{
  "security": {
    "allowed_paths": [
      "src/",
      "tests/",
      "config/"
    ]
  }
}
```

### 9.6. 코드 품질 유지

#### Reviewer 자동 호출

중요한 코드 변경 후 항상 Reviewer 호출:

```
@coder 결제 모듈 구현해줘

[Coder 완료 후]
@reviewer 방금 작성한 코드 리뷰해줘
```

#### 테스트 커버리지 목표 설정

`.context.json`:

```json
{
  "testing": {
    "coverage_threshold": 90
  }
}
```

Worker Agent가 자동으로 커버리지를 체크합니다.

---

## 10. 참고 자료

### 10.1. 공식 문서

- [README.md](README.md): 프로젝트 개요
- [INSTALL.md](INSTALL.md): 설치 가이드
- [CLAUDE.md](CLAUDE.md): 아키텍처 및 개발 가이드
- [CHANGELOG.md](CHANGELOG.md): 버전 변경 이력 (있는 경우)

### 10.2. 외부 링크

- [Anthropic API 문서](https://docs.anthropic.com/)
- [Claude Agent SDK](https://docs.anthropic.com/en/docs/agent-sdk/python)
- [Textual 문서](https://textual.textualize.io/)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Pytest 문서](https://docs.pytest.org/)

### 10.3. 추가 예시

#### 예시 1: 마이크로서비스 생성

```
@planner 다음 마이크로서비스를 설계해줘:
- 서비스명: user-service
- 기능: 사용자 관리 (CRUD)
- DB: PostgreSQL
- API: gRPC
- 인증: JWT
- 배포: Docker + Kubernetes

@coder 위 계획대로 구현해줘

@tester 통합 테스트 실행해줘
```

#### 예시 2: 레거시 코드 리팩토링

```
@reviewer legacy/payment.py 분석하고 리팩토링 계획 제안해줘

[Reviewer 완료 후]
@coder Reviewer 제안대로 리팩토링해줘

@tester 리팩토링 전후 테스트 결과 비교해줘
```

#### 예시 3: 성능 최적화

```
성능 문제가 있는 API 엔드포인트 (/products) 최적화해줘.
현재 응답 시간: 3초
목표: 500ms 이하

고려사항:
- DB 쿼리 최적화
- 캐싱 추가
- N+1 문제 해결
```

### 10.4. 커뮤니티

- **GitHub Issues**: 버그 리포트 및 기능 요청
- **Discussions**: 질문 및 아이디어 공유
- **Contributing**: 기여 가이드 (CONTRIBUTING.md 참조)

---

## 마치며

이 가이드는 Better-LLM의 모든 기능을 다루고 있습니다. 추가 질문이 있거나 문제가 발생하면 GitHub Issues를 이용해주세요.

**Happy Coding with Better-LLM!** 🚀

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2025-10-19
**작성자**: Better-LLM Team
