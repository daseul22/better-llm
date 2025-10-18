# PRD: 그룹 챗 오케스트레이션 시스템 (MVP)

## 문서 정보
- **버전**: 1.0.0
- **작성일**: 2025-01-18
- **상태**: Draft
- **대상 릴리스**: MVP v0.1

---

## 1. 제품 개요

### 1.1 비전
여러 Claude Code 에이전트가 하나의 대화 공간에서 협업하여 복잡한 소프트웨어 개발 작업을 자동화하는 오케스트레이션 시스템

### 1.2 문제 정의
- **현재**: Claude Code를 사용할 때 복잡한 작업(계획 → 구현 → 테스트 → 리뷰)을 단일 에이전트가 처리하거나, 사용자가 수동으로 여러 번 요청해야 함
- **문제점**:
  - 긴 작업 시 컨텍스트 혼란
  - 각 단계마다 사용자 개입 필요
  - 에이전트 간 역할 분리 없음
  - 작업 히스토리 추적 어려움

### 1.3 솔루션
공유 대화 스레드에서 특수화된 에이전트들이 챗 매니저의 조정 하에 협업하며, 사용자는 자연스럽게 개입 가능

### 1.4 MVP 범위
- **포함**: CLI 기반 대화형 인터페이스, 3개 핵심 에이전트, 기본 라우팅 로직, 대화 히스토리 관리
- **제외**: GUI, 고급 라우팅, 에이전트 동적 추가, 분산 실행, 영속성 스토리지

---

## 2. 목표 및 성공 지표

### 2.1 비즈니스 목표
1. 복잡한 개발 작업을 사용자 개입 없이 end-to-end로 완수
2. 에이전트 간 역할 분리로 작업 품질 향상
3. 사용자가 작업 진행 상황을 투명하게 파악

### 2.2 성공 지표 (MVP)
| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| 작업 완료율 | 80% | 시작한 작업 중 TERMINATE까지 도달한 비율 |
| 평균 에이전트 핸드오프 | 2-5회 | 한 작업당 에이전트 간 전환 횟수 |
| 사용자 개입 빈도 | <30% | 전체 작업 중 사용자가 중간 개입한 비율 |
| 무한 루프 발생률 | 0% | 종료 조건 없이 50턴 초과한 비율 |

---

## 3. 타겟 사용자

### 3.1 Primary Persona
- **역할**: 개인 개발자 / 소규모 팀 개발자
- **경험**: Claude Code 사용 경험 있음, CLI 도구 익숙함
- **니즈**:
  - 반복적인 개발 워크플로우 자동화
  - 코드 품질 유지 (구현 후 자동 테스트/리뷰)
  - 컨텍스트 전환 최소화

### 3.2 사용 시나리오
1. **신규 기능 개발**: 계획 → 구현 → 테스트 순차 진행
2. **버그 수정**: 분석 → 패치 → 검증 자동화
3. **리팩토링**: 설계 → 실행 → 테스트 파이프라인

---

## 4. 핵심 기능 명세

### 4.1 기능 개요

| 기능 ID | 기능명 | 우선순위 | MVP 포함 |
|---------|--------|----------|----------|
| F1 | 공유 대화 스레드 관리 | P0 | ✅ |
| F2 | 챗 매니저 (라우팅 로직) | P0 | ✅ |
| F3 | 특수화된 에이전트 (3개) | P0 | ✅ |
| F4 | 사용자 개입 (Human-in-the-loop) | P0 | ✅ |
| F5 | 종료 조건 감지 | P0 | ✅ |
| F6 | CLI 인터페이스 | P0 | ✅ |
| F7 | 대화 히스토리 출력 | P1 | ✅ |
| F8 | 설정 파일 (agent_config.json) | P1 | ✅ |
| F9 | 에러 핸들링 및 재시도 | P2 | ❌ (v0.2) |
| F10 | 대화 히스토리 영속화 | P2 | ❌ (v0.2) |
| F11 | 병렬 에이전트 실행 | P3 | ❌ (Future) |

---

### 4.2 기능 상세

#### F1: 공유 대화 스레드 관리

**설명**: 모든 에이전트와 사용자 메시지를 하나의 스레드에 저장하고 관리

**요구사항**:
- 메시지 형식: `{role: 'user' | 'agent', content: string, agent_name?: string, timestamp: string}`
- 전체 히스토리를 각 에이전트에게 컨텍스트로 전달
- 최대 히스토리 길이: 50 메시지 (초과 시 가장 오래된 것부터 제거)

**인터페이스**:
```python
class ConversationHistory:
    def add_message(self, role: str, content: str, agent_name: str = None)
    def get_history(self) -> List[Message]
    def get_context_for_agent(self, agent_name: str) -> List[Message]
    def clear(self)
```

**수락 기준**:
- ✅ 모든 메시지가 시간 순서대로 저장됨
- ✅ 에이전트가 전체 대화 히스토리 접근 가능
- ✅ 50개 제한 정상 작동

---

#### F2: 챗 매니저 (라우팅 로직)

**설명**: 다음 응답할 에이전트를 결정하는 중앙 조정자

**요구사항**:
- **MVP 라우팅 전략**: 규칙 기반 (Rule-based)
  - 키워드 매칭: "plan" → Planner, "code" → Coder, "test" → Tester
  - 에이전트 명시 요청: "@coder please implement" → Coder
  - 순차 진행: Planner → Coder → Tester → TERMINATE
- 무한 루프 방지: 최대 50턴, 동일 에이전트 연속 5회 제한
- 종료 조건:
  - 명시적 "TERMINATE" 반환
  - 모든 에이전트가 "작업 완료" 표시
  - 사용자가 종료 명령

**인터페이스**:
```python
class ChatManager:
    def select_next_agent(self, history: List[Message]) -> str
    # 반환값: agent_name 또는 "TERMINATE" 또는 "USER_INPUT"
```

**라우팅 규칙 (MVP)**:
```python
rules = {
    "keywords": {
        ["plan", "design", "계획"]: "planner",
        ["code", "implement", "구현"]: "coder",
        ["test", "verify", "테스트"]: "tester"
    },
    "sequence": {
        "planner": "coder",
        "coder": "tester",
        "tester": "TERMINATE"
    }
}
```

**수락 기준**:
- ✅ 키워드 기반 라우팅 정확도 80% 이상
- ✅ 무한 루프 0건
- ✅ 작업 완료 시 정상 종료

---

#### F3: 특수화된 에이전트 (3개)

**설명**: 각 역할에 특화된 3개 에이전트

##### 3.1 Planner 에이전트
- **역할**: 작업 분석 및 계획 수립
- **프롬프트 템플릿**:
```
당신은 소프트웨어 개발 계획 전문가입니다.
사용자 요청을 분석하고 구현 계획을 수립하세요.

출력 형식:
1. 요구사항 요약
2. 구현 단계 (3-5단계)
3. 필요한 파일/모듈
4. 예상 위험 요소

계획 완료 후 "@coder please implement this plan" 으로 다음 에이전트를 호출하세요.
```
- **도구 접근**: Read, Glob (코드베이스 분석용)
- **모델**: claude-sonnet-4

##### 3.2 Coder 에이전트
- **역할**: 실제 코드 작성/수정
- **프롬프트 템플릿**:
```
당신은 Staff Software Engineer입니다.
계획에 따라 코드를 작성하거나 수정하세요.

규칙:
- 기존 코드 스타일 준수
- 주석 필수 (함수 docstring)
- 에러 처리 포함

작업 완료 후 "@tester please verify this implementation" 으로 테스트를 요청하세요.
```
- **도구 접근**: Read, Write, Edit, Glob, Grep, Bash (빌드)
- **모델**: claude-sonnet-4

##### 3.3 Tester 에이전트
- **역할**: 테스트 실행 및 검증
- **프롬프트 템플릿**:
```
당신은 QA Engineer입니다.
구현된 코드를 테스트하고 검증하세요.

작업:
1. 기존 테스트 실행
2. 필요 시 새 테스트 작성
3. 결과 분석 및 보고

모든 테스트 통과 시 "TERMINATE - 작업 완료" 를 반환하세요.
실패 시 "@coder please fix: [문제 설명]" 으로 수정 요청하세요.
```
- **도구 접근**: Read, Bash (테스트 실행), Write (테스트 작성)
- **모델**: claude-sonnet-4

**설정 파일 (agent_config.json)**:
```json
{
  "agents": [
    {
      "name": "planner",
      "role": "계획 수립",
      "system_prompt_file": "prompts/planner.txt",
      "tools": ["read", "glob"],
      "model": "claude-sonnet-4"
    },
    {
      "name": "coder",
      "role": "코드 작성",
      "system_prompt_file": "prompts/coder.txt",
      "tools": ["read", "write", "edit", "glob", "grep", "bash"],
      "model": "claude-sonnet-4"
    },
    {
      "name": "tester",
      "role": "테스트 및 검증",
      "system_prompt_file": "prompts/tester.txt",
      "tools": ["read", "bash", "write"],
      "model": "claude-sonnet-4"
    }
  ]
}
```

**수락 기준**:
- ✅ 각 에이전트가 지정된 역할만 수행
- ✅ 시스템 프롬프트 외부 파일 로드 가능
- ✅ 에이전트 간 명확한 작업 전달

---

#### F4: 사용자 개입 (Human-in-the-loop)

**설명**: 사용자가 언제든 대화에 개입 가능

**요구사항**:
- 각 에이전트 응답 후 사용자 입력 대기 (timeout 5초)
- 사용자 입력 옵션:
  - `Enter`: 다음 에이전트로 진행
  - `/pause`: 일시정지 및 명령 입력 모드
  - `/skip [agent]`: 특정 에이전트 건너뛰기
  - `/stop`: 즉시 종료
  - 일반 메시지: 대화에 추가되고 ChatManager가 다음 에이전트 재결정

**인터페이스**:
```python
class UserInteraction:
    def prompt_user(self, timeout: int = 5) -> Optional[str]
    def parse_command(self, input: str) -> Command
```

**수락 기준**:
- ✅ 5초 내 입력 없으면 자동 진행
- ✅ 사용자 메시지가 히스토리에 추가됨
- ✅ 명령어 정상 작동

---

#### F5: 종료 조건 감지

**설명**: 작업 완료를 자동으로 감지

**종료 트리거**:
1. 에이전트가 "TERMINATE" 문자열 반환
2. 최대 턴 수 도달 (50턴)
3. 사용자가 `/stop` 입력
4. 모든 에이전트가 "완료" 상태 표시

**인터페이스**:
```python
class TerminationDetector:
    def should_terminate(self, history: List[Message], turn: int) -> Tuple[bool, str]
    # 반환: (종료 여부, 종료 이유)
```

**수락 기준**:
- ✅ 정상 종료 시 요약 출력
- ✅ 비정상 종료 시 이유 명시
- ✅ 50턴 제한 정상 작동

---

#### F6: CLI 인터페이스

**설명**: 명령줄 기반 인터랙티브 인터페이스

**명령어**:
```bash
# 기본 실행
$ python orchestrator.py "결제 시스템 구현해줘"

# 설정 파일 지정
$ python orchestrator.py --config custom_agents.json "작업 설명"

# 디버그 모드
$ python orchestrator.py --verbose "작업 설명"

# 히스토리 출력
$ python orchestrator.py --history session_123.json
```

**출력 형식**:
```
┌─ Group Chat Orchestration ─────────────────────────┐
│ 작업: 결제 시스템 구현해줘                          │
│ 활성 에이전트: planner, coder, tester              │
└────────────────────────────────────────────────────┘

[Turn 1] 🧠 Planner:
계획을 수립하겠습니다...
1. 요구사항: 결제 API 엔드포인트 구현
2. 단계:
   - Payment 모델 설계
   - API 라우터 작성
   - 결제 로직 구현
   - 단위 테스트 작성
3. 파일: src/payment.py, tests/test_payment.py

@coder please implement this plan

⏸ [Enter: 계속 | /pause: 일시정지 | /stop: 종료] (5초 대기)

[Turn 2] 💻 Coder:
계획에 따라 구현하겠습니다...

[파일: src/payment.py 작성 중...]
✅ src/payment.py 작성 완료
✅ src/api/routes.py 수정 완료

@tester please verify this implementation

⏸ [Enter: 계속 | /pause: 일시정지 | /stop: 종료] (5초 대기)

[Turn 3] 🧪 Tester:
테스트를 실행하겠습니다...

$ pytest tests/test_payment.py
✅ 5 passed in 1.23s

TERMINATE - 모든 테스트 통과, 작업 완료

┌─ 작업 완료 ────────────────────────────────────────┐
│ 총 턴: 3                                            │
│ 소요 시간: 45초                                     │
│ 수정된 파일: 2개                                    │
│ 히스토리: session_abc123.json에 저장됨             │
└────────────────────────────────────────────────────┘
```

**수락 기준**:
- ✅ 실시간 에이전트 응답 출력
- ✅ 사용자 입력 프롬프트 표시
- ✅ 진행 상황 시각화

---

#### F7: 대화 히스토리 출력

**설명**: 작업 완료 후 전체 대화를 JSON으로 저장

**출력 형식**:
```json
{
  "session_id": "abc123",
  "created_at": "2025-01-18T10:23:45Z",
  "completed_at": "2025-01-18T10:24:30Z",
  "user_request": "결제 시스템 구현해줘",
  "total_turns": 3,
  "agents_used": ["planner", "coder", "tester"],
  "messages": [
    {
      "turn": 1,
      "role": "agent",
      "agent_name": "planner",
      "content": "계획을 수립하겠습니다...",
      "timestamp": "2025-01-18T10:23:45Z"
    },
    {
      "turn": 2,
      "role": "agent",
      "agent_name": "coder",
      "content": "구현하겠습니다...",
      "timestamp": "2025-01-18T10:24:10Z"
    }
  ],
  "result": {
    "status": "completed",
    "files_modified": ["src/payment.py", "src/api/routes.py"],
    "tests_passed": true
  }
}
```

**수락 기준**:
- ✅ JSON 형식 유효성 검증
- ✅ 모든 메시지 포함
- ✅ 파일명에 session_id 포함

---

#### F8: 설정 파일 (agent_config.json)

**설명**: 에이전트 구성을 외부 JSON으로 관리

**(F3에 예시 포함됨)**

**수락 기준**:
- ✅ 설정 파일 변경 시 재시작 없이 반영
- ✅ 유효성 검증 (필수 필드 체크)
- ✅ 에러 시 명확한 메시지

---

## 5. 기술 스펙

### 5.1 시스템 아키텍처

```
┌─────────────────────────────────────────────┐
│           CLI Interface                     │
│  (orchestrator.py)                          │
└──────────────┬──────────────────────────────┘
               │
    ┌──────────▼──────────┐
    │   ChatManager       │
    │  - select_next()    │
    │  - detect_terminate │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────────────┐
    │  ConversationHistory        │
    │  - messages: List[Message]  │
    │  - add_message()            │
    └──────────┬──────────────────┘
               │
    ┌──────────▼──────────────────┐
    │  AgentPool                  │
    │  ┌────────┬────────┬──────┐ │
    │  │Planner │ Coder  │Tester│ │
    │  └────────┴────────┴──────┘ │
    └─────────────────────────────┘
               │
    ┌──────────▼──────────────────┐
    │  Claude API Client          │
    │  (anthropic SDK)            │
    └─────────────────────────────┘
```

### 5.2 기술 스택

| 구성 요소 | 기술 | 버전 |
|-----------|------|------|
| 언어 | Python | 3.10+ |
| LLM SDK | anthropic | 0.18+ |
| CLI 프레임워크 | Click | 8.0+ |
| 설정 | JSON (stdlib) | - |
| 로깅 | logging (stdlib) | - |

### 5.3 핵심 클래스

```python
# models.py
@dataclass
class Message:
    role: str  # 'user' or 'agent'
    content: str
    agent_name: Optional[str]
    timestamp: datetime

@dataclass
class AgentConfig:
    name: str
    role: str
    system_prompt: str
    tools: List[str]
    model: str

# agents.py
class Agent:
    def __init__(self, config: AgentConfig, client: Anthropic)
    def respond(self, history: List[Message]) -> str

# chat_manager.py
class ChatManager:
    def __init__(self, agents: List[Agent], rules: dict)
    def select_next_agent(self, history: List[Message]) -> str

# conversation.py
class ConversationHistory:
    def __init__(self, max_length: int = 50)
    def add_message(self, msg: Message)
    def get_history(self) -> List[Message]

# orchestrator.py
class Orchestrator:
    def __init__(self, config_path: str)
    def run(self, user_request: str)
```

### 5.4 디렉토리 구조

```
group-chat-orchestrator/
├── orchestrator.py          # 메인 실행 파일
├── requirements.txt
├── README.md
├── config/
│   └── agent_config.json    # 기본 설정
├── prompts/
│   ├── planner.txt
│   ├── coder.txt
│   └── tester.txt
├── src/
│   ├── __init__.py
│   ├── models.py            # 데이터 모델
│   ├── agents.py            # Agent 클래스
│   ├── chat_manager.py      # ChatManager
│   ├── conversation.py      # ConversationHistory
│   └── utils.py             # 유틸리티
├── tests/
│   ├── test_chat_manager.py
│   ├── test_agents.py
│   └── test_conversation.py
└── sessions/                # 히스토리 저장 디렉토리
    └── .gitkeep
```

---

## 6. 제약사항 및 가정

### 6.1 제약사항
- **컨텍스트 길이**: 50 메시지 제한 (약 20K 토큰 가정)
- **동시성**: 순차 실행만 지원 (병렬 실행 미지원)
- **에이전트 수**: 3개 고정 (동적 추가/제거 불가)
- **영속성**: 메모리 내 저장, 프로세스 종료 시 휘발 (히스토리 JSON 제외)
- **에러 복구**: 수동 재시작 필요 (자동 재시도 없음)

### 6.2 가정
- Claude API 키가 환경변수에 설정되어 있음
- 사용자는 CLI 사용 경험이 있음
- 프로젝트 디렉토리에서 실행됨 (도구 접근 권한)
- 인터넷 연결 안정적

---

## 7. 성공 시나리오 (MVP)

### 시나리오 1: 신규 기능 개발

**사용자 입력**:
```bash
$ python orchestrator.py "FastAPI로 /users CRUD 엔드포인트 구현해줘"
```

**기대 흐름**:
1. **Planner** → 요구사항 분석, 파일 구조 계획
2. **Coder** → 모델/라우터/스키마 구현
3. **Tester** → 단위 테스트 작성 및 실행
4. **종료** → 모든 테스트 통과

**수락 기준**:
- ✅ 3개 파일 생성/수정
- ✅ 테스트 통과
- ✅ 사용자 개입 0회

---

### 시나리오 2: 버그 수정 (사용자 개입 포함)

**사용자 입력**:
```bash
$ python orchestrator.py "로그인 API에서 500 에러 나는 버그 수정해줘"
```

**기대 흐름**:
1. **Planner** → 에러 로그 분석, 원인 파악
2. **Coder** → 버그 수정
3. **[사용자 개입]** → "테스트도 추가해줘" 입력
4. **Coder** → 회귀 테스트 추가
5. **Tester** → 테스트 실행 및 검증
6. **종료**

**수락 기준**:
- ✅ 버그 수정됨
- ✅ 사용자 요청 반영됨 (테스트 추가)
- ✅ 히스토리에 사용자 메시지 포함

---

## 8. 마일스톤

### Phase 1: 기본 프레임워크 (Week 1-2)
- [ ] 프로젝트 셋업 및 의존성 설치
- [ ] `ConversationHistory` 구현 및 테스트
- [ ] `Agent` 기본 클래스 구현
- [ ] Claude API 연동 및 단순 응답 테스트

### Phase 2: 라우팅 로직 (Week 2-3)
- [ ] `ChatManager` 규칙 기반 라우팅 구현
- [ ] 키워드 매칭 엔진
- [ ] 종료 조건 감지 로직
- [ ] 무한 루프 방지 테스트

### Phase 3: 에이전트 특수화 (Week 3-4)
- [ ] Planner 시스템 프롬프트 작성 및 튜닝
- [ ] Coder 시스템 프롬프트 및 도구 통합
- [ ] Tester 시스템 프롬프트 및 bash 실행
- [ ] 3 에이전트 통합 테스트

### Phase 4: CLI 인터페이스 (Week 4-5)
- [ ] Click 기반 CLI 구현
- [ ] 실시간 출력 포매팅
- [ ] 사용자 입력 핸들링 (timeout)
- [ ] 명령어 파서 (`/pause`, `/stop`)

### Phase 5: 통합 및 테스트 (Week 5-6)
- [ ] End-to-end 시나리오 테스트 (2개)
- [ ] 설정 파일 로더 및 유효성 검증
- [ ] 히스토리 JSON 저장
- [ ] 문서화 (README, 사용 가이드)

### Phase 6: 알파 릴리스 (Week 6)
- [ ] 버그 수정 및 안정화
- [ ] 성능 테스트 (컨텍스트 길이)
- [ ] 알파 사용자 피드백 수집
- [ ] v0.1.0 릴리스

---

## 9. 비기능 요구사항

### 9.1 성능
- 에이전트 응답 시간: 평균 5초 이하 (Claude API 의존적)
- 50 메시지 히스토리 처리: 1초 이내

### 9.2 신뢰성
- 무한 루프 발생률: 0%
- API 에러 시 명확한 에러 메시지

### 9.3 사용성
- 첫 실행까지 5분 이내 (설치 포함)
- 에러 메시지 한국어 지원
- 사용자 입력 대기 시간 시각적 표시

---

## 10. 위험 및 완화 전략

| 위험 | 확률 | 영향 | 완화 전략 |
|------|------|------|----------|
| 컨텍스트 길이 초과 | 중 | 높음 | 50 메시지 제한, 요약 기능 (v0.2) |
| 라우팅 오류 (잘못된 에이전트 선택) | 중 | 중 | 사용자 개입 허용, 수동 재라우팅 |
| 에이전트 응답 무한 대기 | 낮 | 높음 | API timeout 30초 설정 |
| Claude API 장애 | 낮 | 높음 | 명확한 에러 메시지, 재시도 안내 |

---

## 11. 출시 기준 (Definition of Done)

MVP v0.1 출시를 위한 체크리스트:

- [ ] 모든 P0 기능 구현 완료
- [ ] 2개 성공 시나리오 통과
- [ ] 단위 테스트 커버리지 70% 이상
- [ ] README 및 사용 가이드 작성
- [ ] 알파 사용자 3명 이상 테스트 완료
- [ ] 크리티컬 버그 0건
- [ ] 성공 지표 목표치 달성

---

## 12. 향후 계획 (Post-MVP)

### v0.2 (Enhanced)
- 에러 핸들링 및 자동 재시도
- LLM 기반 동적 라우팅 (규칙 기반 → 컨텍스트 기반)
- 대화 히스토리 영속화 (SQLite)
- 더 많은 에이전트 (Reviewer, DevOps)

### v0.3 (Advanced)
- 병렬 에이전트 실행
- 웹 UI (실시간 대시보드)
- 에이전트 성능 메트릭
- 커스텀 에이전트 추가 지원

---

## 부록

### A. 참고 자료
- Microsoft Azure AI Agent Orchestration Patterns
- AutoGen Group Chat 구현
- LangGraph Multi-Agent Systems

### B. 용어 사전
- **턴 (Turn)**: 에이전트 또는 사용자의 한 번의 메시지
- **핸드오프 (Handoff)**: 에이전트 간 작업 전달
- **TERMINATE**: 작업 완료 신호

### C. 변경 이력
| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 2025-01-18 | 1.0.0 | 초안 작성 | - |
