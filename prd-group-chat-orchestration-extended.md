# PRD: 그룹 챗 오케스트레이션 시스템 (Extended)

## 문서 정보
- **버전**: 2.0.0
- **작성일**: 2025-01-18
- **상태**: Draft
- **대상 릴리스**: v0.2 (Extended)
- **기반**: MVP v0.1 확장

---

## 1. 제품 개요

### 1.1 비전
여러 Claude Code 에이전트가 하나의 대화 공간에서 지능적으로 협업하며, 복잡한 소프트웨어 개발 작업을 자동화하고 지속적으로 개선하는 오케스트레이션 시스템

### 1.2 문제 정의
- **MVP 달성**: 기본 에이전트 협업 가능, 하지만 실제 프로덕션 사용 시 한계 발견
- **추가 문제점**:
  - 에러 발생 시 전체 작업 중단 → 수동 재시작 필요
  - 규칙 기반 라우팅의 한계 → 복잡한 컨텍스트 이해 못함
  - 3개 에이전트로 제한적 → 리뷰, 보안, 문서화 등 추가 역할 필요
  - 세션 종료 시 히스토리 소실 → 작업 연속성 없음
  - 단순 CLI만 제공 → 팀 협업/모니터링 어려움

### 1.3 솔루션 확장
**MVP 기반 + 다음 요소 추가**:
1. **지능형 라우팅**: LLM이 대화 컨텍스트를 분석해 최적 에이전트 선택
2. **에러 복구**: 자동 재시도, 대안 에이전트 호출, 체크포인트 복구
3. **확장된 에이전트**: 총 6개 (Planner, Coder, Tester, Reviewer, Security, Docs)
4. **영속화**: SQLite 기반 대화 히스토리, 작업 재개 가능
5. **웹 UI**: 실시간 대시보드, 히스토리 브라우징, 멀티 세션 관리

### 1.4 Extended 범위
- **포함**:
  - MVP 모든 기능
  - LLM 기반 동적 라우팅
  - 에러 핸들링 및 복구
  - 6개 특수화 에이전트
  - SQLite 영속성
  - 웹 UI (FastAPI + React)
  - 에이전트 성능 메트릭
  - 커스텀 에이전트 추가 지원

- **제외**:
  - 병렬 에이전트 실행 (v0.3)
  - 분산 실행 (v0.3)
  - 엔터프라이즈 인증/권한 (v1.0)

---

## 2. 목표 및 성공 지표

### 2.1 비즈니스 목표
1. **MVP 대비 작업 완료율 20% 향상** (80% → 95%)
2. **에러 복구율 90% 이상** (수동 개입 없이)
3. **팀 협업 지원**: 여러 사용자가 동시 세션 실행
4. **작업 연속성**: 중단된 작업을 재개 가능

### 2.2 성공 지표 (Extended)
| 지표 | MVP 목표 | Extended 목표 | 측정 방법 |
|------|----------|---------------|-----------|
| 작업 완료율 | 80% | **95%** | TERMINATE 도달 비율 |
| 에러 자동 복구율 | 0% | **90%** | 에러 발생 중 재시도 성공 비율 |
| 평균 라우팅 정확도 | 80% | **95%** | 사용자 재라우팅 요청 감소율 |
| 세션 재개 성공률 | 0% | **100%** | 중단된 세션 복구 성공 |
| 웹 UI 응답 시간 | N/A | **<2초** | 페이지 로드 시간 |
| 커스텀 에이전트 추가 시간 | N/A | **<10분** | 설정 파일 작성 → 동작까지 |

---

## 3. 타겟 사용자

### 3.1 Primary Persona (MVP 동일)
- **역할**: 개인 개발자 / 소규모 팀 개발자
- **경험**: Claude Code 사용 경험 있음, CLI/웹 도구 익숙함
- **니즈**:
  - 반복적인 개발 워크플로우 자동화
  - 코드 품질 유지 (구현 후 자동 테스트/리뷰/보안 검사)
  - 컨텍스트 전환 최소화
  - **[추가]** 작업 중단/재개 기능 (긴 작업 시)
  - **[추가]** 팀원과 세션 공유/모니터링

### 3.2 Secondary Persona (신규)
- **역할**: 테크 리드 / 엔지니어링 매니저
- **경험**: 팀 관리, CI/CD 파이프라인 운영
- **니즈**:
  - 팀원들의 작업 진행 상황 모니터링
  - 에이전트 성능 메트릭 분석
  - 커스텀 에이전트로 팀 워크플로우 표준화

### 3.3 사용 시나리오 (확장)
1. **신규 기능 개발**: 계획 → 구현 → 테스트 → **리뷰** → **보안 검사** → **문서화**
2. **버그 수정**: 분석 → 패치 → 검증 → **회귀 테스트**
3. **리팩토링**: 설계 → 실행 → 테스트 → **코드 리뷰** → **영향도 분석**
4. **[신규] 장기 작업**: 오늘 구현 시작 → 저장 → 내일 재개 → 완료
5. **[신규] 팀 협업**: 리드가 웹 UI로 진행 중인 세션 모니터링

---

## 4. 핵심 기능 명세

### 4.1 기능 개요

| 기능 ID | 기능명 | 우선순위 | MVP | Extended |
|---------|--------|----------|-----|----------|
| F1 | 공유 대화 스레드 관리 | P0 | ✅ | ✅ |
| F2 | ~~챗 매니저 (규칙 기반)~~ | P0 | ✅ | ⚠️ (deprecated) |
| **F2-E** | **LLM 기반 동적 라우팅** | **P0** | ❌ | **✅** |
| F3 | 특수화된 에이전트 (3개) | P0 | ✅ | ⚠️ (확장) |
| **F3-E** | **확장 에이전트 (6개)** | **P0** | ❌ | **✅** |
| F4 | 사용자 개입 (HITL) | P0 | ✅ | ✅ |
| F5 | 종료 조건 감지 | P0 | ✅ | ✅ (강화) |
| F6 | CLI 인터페이스 | P0 | ✅ | ✅ |
| **F6-E** | **웹 UI 인터페이스** | **P0** | ❌ | **✅** |
| F7 | 대화 히스토리 출력 | P1 | ✅ | ✅ |
| F8 | 설정 파일 | P1 | ✅ | ✅ (확장) |
| **F9** | **에러 핸들링 및 재시도** | **P0** | ❌ | **✅** |
| **F10** | **대화 히스토리 영속화 (SQLite)** | **P0** | ❌ | **✅** |
| **F11** | **에이전트 성능 메트릭** | **P1** | ❌ | **✅** |
| **F12** | **커스텀 에이전트 추가** | **P1** | ❌ | **✅** |
| **F13** | **체크포인트 & 작업 재개** | **P1** | ❌ | **✅** |
| F14 | 병렬 에이전트 실행 | P2 | ❌ | ❌ (v0.3) |

---

### 4.2 기능 상세

#### F2-E: LLM 기반 동적 라우팅 ⭐ (신규)

**설명**: LLM이 대화 히스토리를 분석하여 다음 에이전트를 지능적으로 선택

**문제점 (MVP 규칙 기반)**:
```python
# MVP의 한계
rules = {
    "keywords": {
        ["plan", "design"]: "planner",  # 단순 키워드 매칭
        ["code", "implement"]: "coder"
    }
}
# → "설계를 개선하고 코드를 수정해줘" → planner만 호출? coder만 호출?
```

**해결책 (LLM 기반)**:
```python
# Extended: LLM이 컨텍스트 분석
prompt = f"""
대화 히스토리를 분석하고 다음 에이전트를 선택하세요.

<history>
{conversation_history}
</history>

<available_agents>
- planner: 작업 분석 및 계획 수립
- coder: 코드 작성/수정
- tester: 테스트 실행 및 검증
- reviewer: 코드 리뷰 및 개선 제안
- security: 보안 취약점 분석
- docs: 문서 작성
</available_agents>

다음 에이전트를 선택하고 이유를 설명하세요.
출력 형식: {{"agent": "coder", "reason": "계획이 완료되어 구현 필요"}}
"""
```

**요구사항**:
- **메타 LLM 모델**: `claude-sonnet-4` (라우팅 전용, 빠른 응답)
- **입력**: 전체 대화 히스토리 (최근 20 메시지)
- **출력**: JSON `{agent: string, reason: string, confidence: 0-1}`
- **Fallback**: confidence < 0.7 이면 사용자에게 선택 요청
- **캐싱**: 동일 컨텍스트는 30초간 캐시 (비용 절감)

**라우팅 전략**:
1. **단순 요청** (키워드 명확) → 규칙 기반 (빠름)
2. **복잡한 요청** (컨텍스트 필요) → LLM 기반
3. **명시적 호출** (`@coder`) → 직접 라우팅

**인터페이스**:
```python
class SmartChatManager:
    def select_next_agent(
        self,
        history: List[Message],
        available_agents: List[str]
    ) -> AgentSelection:
        # AgentSelection(agent="coder", reason="...", confidence=0.95)

    def should_use_llm_routing(self, history: List[Message]) -> bool:
        # 규칙 기반으로 충분한지 판단
```

**수락 기준**:
- ✅ 라우팅 정확도 95% 이상 (사용자 재라우팅 요청 5% 이하)
- ✅ 평균 라우팅 시간 <2초
- ✅ 복잡한 멀티 태스크 요청 정확히 분해 (예: "구현하고 테스트하고 문서 작성" → coder → tester → docs)

---

#### F3-E: 확장 에이전트 (6개) ⭐ (신규)

**설명**: MVP 3개 → Extended 6개 에이전트

##### 4.1 Planner (MVP와 동일)
- **역할**: 작업 분석 및 계획 수립
- **도구**: Read, Glob
- **모델**: claude-sonnet-4

##### 4.2 Coder (MVP와 동일)
- **역할**: 실제 코드 작성/수정
- **도구**: Read, Write, Edit, Glob, Grep, Bash (빌드)
- **모델**: claude-sonnet-4

##### 4.3 Tester (MVP와 동일)
- **역할**: 테스트 실행 및 검증
- **도구**: Read, Bash (테스트 실행), Write (테스트 작성)
- **모델**: claude-sonnet-4

##### 4.4 Reviewer ⭐ (신규)
- **역할**: 코드 리뷰 및 개선 제안
- **프롬프트 템플릿**:
```
당신은 Senior Code Reviewer입니다.
작성된 코드를 리뷰하고 개선 사항을 제안하세요.

검토 항목:
1. 코드 품질 (가독성, 유지보수성)
2. 성능 (비효율적인 알고리즘, N+1 쿼리)
3. 버그 위험 (엣지 케이스, 에러 처리)
4. 베스트 프랙티스 위반
5. 테스트 커버리지 충분성

출력 형식:
- ✅ 잘된 점 (1-2개)
- ⚠️ 개선 필요 (우선순위 순)
- 📝 제안 코드 (필요 시)

승인 조건:
- 크리티컬 이슈 0건
- 테스트 커버리지 70% 이상

승인 시 "APPROVE - 리뷰 완료", 수정 필요 시 "@coder please fix: [이슈]"
```
- **도구**: Read, Grep, Bash (정적 분석 도구)
- **모델**: claude-sonnet-4

##### 4.5 Security ⭐ (신규)
- **역할**: 보안 취약점 분석
- **프롬프트 템플릿**:
```
당신은 Security Engineer입니다.
코드의 보안 취약점을 분석하세요.

검사 항목:
1. SQL Injection, XSS, CSRF
2. 하드코딩된 시크릿/API 키
3. 인증/권한 검증 누락
4. 민감 데이터 로깅
5. 안전하지 않은 의존성

출력 형식:
- 🔴 Critical: 즉시 수정 필요
- 🟡 Warning: 개선 권장
- 🟢 Pass: 문제 없음

Critical 발견 시 "@coder please fix CRITICAL: [취약점]"
모두 Pass 시 "SECURITY_OK - 보안 검사 통과"
```
- **도구**: Read, Grep, Bash (`safety`, `bandit`, `semgrep`)
- **모델**: claude-sonnet-4

##### 4.6 Docs ⭐ (신규)
- **역할**: 문서 작성 (README, API 문서, 주석)
- **프롬프트 템플릿**:
```
당신은 Technical Writer입니다.
코드베이스의 문서를 작성하세요.

작업:
1. README.md 업데이트 (새 기능 추가 시)
2. API 문서 (FastAPI → OpenAPI, Django → drf-spectacular)
3. 함수/클래스 docstring
4. 아키텍처 다이어그램 (필요 시 Mermaid)

원칙:
- 사용자 관점 (How to use)
- 예제 코드 포함
- 최신 상태 유지 (deprecated 표시)

완료 시 "DOCS_COMPLETE - 문서 작성 완료"
```
- **도구**: Read, Write, Glob
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
      "model": "claude-sonnet-4",
      "enabled": true
    },
    {
      "name": "coder",
      "role": "코드 작성",
      "system_prompt_file": "prompts/coder.txt",
      "tools": ["read", "write", "edit", "glob", "grep", "bash"],
      "model": "claude-sonnet-4",
      "enabled": true
    },
    {
      "name": "tester",
      "role": "테스트 및 검증",
      "system_prompt_file": "prompts/tester.txt",
      "tools": ["read", "bash", "write"],
      "model": "claude-sonnet-4",
      "enabled": true
    },
    {
      "name": "reviewer",
      "role": "코드 리뷰",
      "system_prompt_file": "prompts/reviewer.txt",
      "tools": ["read", "grep", "bash"],
      "model": "claude-sonnet-4",
      "enabled": true
    },
    {
      "name": "security",
      "role": "보안 분석",
      "system_prompt_file": "prompts/security.txt",
      "tools": ["read", "grep", "bash"],
      "model": "claude-sonnet-4",
      "enabled": true
    },
    {
      "name": "docs",
      "role": "문서 작성",
      "system_prompt_file": "prompts/docs.txt",
      "tools": ["read", "write", "glob"],
      "model": "claude-sonnet-4",
      "enabled": true
    }
  ]
}
```

**수락 기준**:
- ✅ 6개 에이전트 모두 독립적 작동
- ✅ 에이전트 활성화/비활성화 (`enabled: false`)
- ✅ 에이전트 간 명확한 역할 분리

---

#### F9: 에러 핸들링 및 재시도 ⭐ (신규)

**설명**: 에이전트 실행 중 에러 발생 시 자동 복구

**에러 유형 및 대응**:

| 에러 유형 | 예시 | 대응 전략 |
|----------|------|----------|
| **일시적 에러** | API rate limit, 네트워크 타임아웃 | 지수 백오프 재시도 (3회) |
| **도구 실행 에러** | 파일 없음, 빌드 실패 | 1회 재시도 + 사용자 알림 |
| **에이전트 응답 에러** | JSON 파싱 실패, TERMINATE 없음 | 프롬프트 재생성 (2회) |
| **무한 루프** | 동일 에이전트 10회 연속 | 강제 종료 + 요약 |
| **치명적 에러** | API 키 없음, 권한 부족 | 즉시 중단 + 상세 로그 |

**재시도 로직**:
```python
class ErrorHandler:
    def handle_agent_error(
        self,
        agent: str,
        error: Exception,
        context: Dict
    ) -> RecoveryAction:
        """
        RecoveryAction:
        - RETRY: 같은 에이전트 재시도
        - FALLBACK: 대안 에이전트 호출
        - SKIP: 에이전트 건너뛰기
        - ABORT: 작업 중단
        - CHECKPOINT: 현재 상태 저장 후 중단
        """

    def exponential_backoff(self, attempt: int) -> float:
        # 1초 → 2초 → 4초
        return min(2 ** attempt, 10)
```

**체크포인트 저장**:
- 에러 발생 시 현재 대화 히스토리 + 상태를 DB에 저장
- 사용자가 나중에 `--resume <session_id>` 로 재개 가능

**수락 기준**:
- ✅ 일시적 에러 90% 자동 복구
- ✅ 복구 불가 에러 시 상세 로그 + 체크포인트 저장
- ✅ 무한 루프 0건

---

#### F10: 대화 히스토리 영속화 (SQLite) ⭐ (신규)

**설명**: 모든 세션을 SQLite에 저장하여 작업 재개 및 히스토리 분석 가능

**스키마**:
```sql
-- 세션
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,  -- UUID
    user_request TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT CHECK(status IN ('running', 'completed', 'failed', 'paused')),
    total_turns INTEGER DEFAULT 0,
    agents_used TEXT,  -- JSON array
    metadata TEXT      -- JSON (비용, 토큰 등)
);

-- 메시지
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn INTEGER NOT NULL,
    role TEXT CHECK(role IN ('user', 'agent', 'system')),
    agent_name TEXT,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,  -- JSON (도구 호출, 에러 등)
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- 에이전트 메트릭
CREATE TABLE agent_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    invocation_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_time_ms INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- 체크포인트
CREATE TABLE checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn INTEGER NOT NULL,
    state TEXT NOT NULL,  -- JSON (전체 상태)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

**인터페이스**:
```python
class SessionStore:
    def create_session(self, user_request: str) -> str:
        # 새 세션 생성, session_id 반환

    def save_message(self, session_id: str, message: Message):
        # 메시지 저장

    def get_session(self, session_id: str) -> Session:
        # 세션 로드

    def list_sessions(self, status: str = None, limit: int = 50) -> List[Session]:
        # 세션 목록

    def resume_session(self, session_id: str) -> ConversationHistory:
        # 중단된 세션 재개

    def save_checkpoint(self, session_id: str, state: Dict):
        # 체크포인트 저장
```

**사용 예시**:
```bash
# 새 세션 시작
$ python orchestrator.py "결제 시스템 구현"
[Session abc123] 시작...

# 중단 (Ctrl+C)
✅ 체크포인트 저장: sessions/abc123

# 나중에 재개
$ python orchestrator.py --resume abc123
[Session abc123] 재개...
Turn 5부터 계속합니다...
```

**수락 기준**:
- ✅ 모든 메시지 자동 저장
- ✅ 세션 재개 성공률 100%
- ✅ 세션 검색/필터링 (상태별, 날짜별)

---

#### F6-E: 웹 UI 인터페이스 ⭐ (신규)

**설명**: CLI 외에 브라우저 기반 인터페이스 제공

**기술 스택**:
- **백엔드**: FastAPI (Python)
- **프론트엔드**: React + TypeScript
- **실시간 통신**: WebSocket (에이전트 응답 스트리밍)
- **UI 라이브러리**: shadcn/ui + Tailwind CSS

**주요 화면**:

##### 1. 세션 목록 (Home)
```
┌─ 그룹 챗 오케스트레이터 ────────────────┐
│ [+ 새 세션]               [새로고침]     │
├────────────────────────────────────────┤
│ 🟢 Running                             │
│ • abc123 | 결제 시스템 구현 (Turn 5/?) │
│   시작: 10분 전 | coder 실행 중        │
│                                 [열기] │
│                                         │
│ 🟢 Running                             │
│ • def456 | 버그 수정 (Turn 2/?)        │
│   시작: 1시간 전 | tester 실행 중      │
│                                 [열기] │
│                                         │
│ ✅ Completed                            │
│ • xyz789 | 리팩토링 (3턴 완료)         │
│   완료: 어제 | 소요: 5분               │
│                          [히스토리 보기]│
└────────────────────────────────────────┘
```

##### 2. 세션 상세 (Chat View)
```
┌─ Session abc123 ─────────────────────────┐
│ 작업: 결제 시스템 구현                    │
│ 상태: 🟢 Running | Turn 5                │
│ 경과: 10분 32초                          │
├──────────────────────────────────────────┤
│ [Turn 1] 🧠 Planner (15:23:45)          │
│ 계획을 수립하겠습니다...                  │
│ 1. Payment 모델 설계                     │
│ 2. API 라우터 작성                       │
│ ...                                      │
│                                          │
│ [Turn 2] 💻 Coder (15:24:10)            │
│ 구현하겠습니다...                         │
│ ✅ src/payment.py 작성 완료              │
│ [코드 diff 보기]                         │
│                                          │
│ [Turn 3] 🧪 Tester (15:24:45)           │
│ 테스트 실행 중...                         │
│ ❌ 2 failed, 3 passed                   │
│ [테스트 결과 상세]                       │
│                                          │
│ [Turn 4] 💻 Coder (15:25:10)            │
│ 테스트 실패 수정 중...                    │
│                                          │
│ [Turn 5] 🧪 Tester (15:25:45)           │
│ ⏳ 테스트 재실행 중... (실시간)          │
│                                          │
├──────────────────────────────────────────┤
│ [사용자 입력]                             │
│ ┌──────────────────────────────────┐    │
│ │ 메시지 입력 또는 명령어...        │    │
│ └──────────────────────────────────┘    │
│ [Enter] 계속  [/pause] 일시정지          │
└──────────────────────────────────────────┘

[오른쪽 사이드바]
┌─ 에이전트 상태 ───┐
│ 🟢 coder         │
│ 🟢 tester        │
│ ⚪ planner       │
│ ⚪ reviewer      │
│ ⚪ security      │
│ ⚪ docs          │
└──────────────────┘

┌─ 메트릭 ──────────┐
│ 총 턴: 5          │
│ 토큰: 12.5K       │
│ 비용: $0.15       │
│ 파일 수정: 2      │
└──────────────────┘
```

##### 3. 에이전트 설정
```
┌─ 에이전트 관리 ──────────────────────┐
│ [+ 커스텀 에이전트 추가]              │
├──────────────────────────────────────┤
│ planner         [활성화 ✅] [편집]  │
│ coder           [활성화 ✅] [편집]  │
│ tester          [활성화 ✅] [편집]  │
│ reviewer        [활성화 ✅] [편집]  │
│ security        [활성화 ⚪] [편집]  │
│ docs            [활성화 ✅] [편집]  │
│                                      │
│ my-custom-agent [활성화 ✅] [편집]  │
│   (커스텀: DB 마이그레이션 전문)     │
└──────────────────────────────────────┘
```

**API 엔드포인트**:
```python
# FastAPI
@app.post("/api/sessions")
async def create_session(request: CreateSessionRequest) -> Session:
    # 새 세션 생성

@app.get("/api/sessions")
async def list_sessions(status: str = None) -> List[Session]:
    # 세션 목록

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> SessionDetail:
    # 세션 상세

@app.websocket("/ws/sessions/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    # 실시간 에이전트 응답 스트리밍
    while True:
        message = await get_next_agent_message(session_id)
        await websocket.send_json(message)

@app.post("/api/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    # 세션 일시정지

@app.post("/api/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    # 세션 재개
```

**수락 기준**:
- ✅ 웹 UI로 모든 CLI 기능 실행 가능
- ✅ 실시간 에이전트 응답 표시 (WebSocket)
- ✅ 세션 목록/검색/필터링
- ✅ 모바일 반응형 (Tailwind)

---

#### F11: 에이전트 성능 메트릭 ⭐ (신규)

**설명**: 각 에이전트의 성능을 측정하고 분석

**수집 메트릭**:
```python
@dataclass
class AgentMetrics:
    agent_name: str
    session_id: str

    # 호출 통계
    invocation_count: int
    success_count: int
    error_count: int

    # 시간
    total_time_ms: int
    avg_time_ms: float

    # 토큰
    total_tokens: int
    avg_tokens: float

    # 비용 (토큰 × 단가)
    total_cost_usd: float

    # 품질
    user_intervention_count: int  # 사용자가 수정 요청한 횟수
    handoff_success_rate: float   # 다음 에이전트로 성공적 전달 비율
```

**대시보드 (웹 UI)**:
```
┌─ 에이전트 성능 분석 (최근 30일) ─────────┐
│                                          │
│ [차트] 에이전트별 호출 횟수               │
│   coder    ████████ 45                  │
│   tester   ██████ 30                    │
│   planner  ████ 20                      │
│   reviewer ███ 15                       │
│                                          │
│ [차트] 평균 응답 시간                     │
│   coder    4.2초                        │
│   security 6.8초                        │
│   tester   3.1초                        │
│                                          │
│ [테이블] 에이전트 상세                    │
│ ┌────────┬──────┬────────┬──────────┐  │
│ │ 이름   │ 성공률│ 평균토큰│ 비용     │  │
│ ├────────┼──────┼────────┼──────────┤  │
│ │ coder  │ 92%  │ 2.5K   │ $1.23    │  │
│ │ tester │ 88%  │ 1.2K   │ $0.45    │  │
│ └────────┴──────┴────────┴──────────┘  │
└──────────────────────────────────────────┘
```

**수락 기준**:
- ✅ 모든 에이전트 호출 시 메트릭 자동 수집
- ✅ 웹 UI에서 시각화 차트 제공
- ✅ CSV 내보내기 기능

---

#### F12: 커스텀 에이전트 추가 ⭐ (신규)

**설명**: 사용자가 팀 워크플로우에 맞는 에이전트를 추가

**추가 방법**:

##### 1. 설정 파일 작성
```json
// config/agent_config.json
{
  "agents": [
    // 기본 에이전트들...
    {
      "name": "db-migrator",
      "role": "데이터베이스 마이그레이션 전문가",
      "system_prompt_file": "prompts/custom/db_migrator.txt",
      "tools": ["read", "write", "bash"],
      "model": "claude-sonnet-4",
      "enabled": true,
      "tags": ["database", "migration"]  // 라우팅 힌트
    }
  ]
}
```

##### 2. 프롬프트 작성
```
# prompts/custom/db_migrator.txt

당신은 데이터베이스 마이그레이션 전문가입니다.
Alembic (SQLAlchemy) 또는 Django 마이그레이션을 생성/실행하세요.

작업:
1. 모델 변경 사항 분석
2. 안전한 마이그레이션 파일 생성
3. Up/Down 마이그레이션 검증
4. 데이터 손실 위험 경고

규칙:
- 프로덕션 데이터 고려 (기본값, NULL 허용)
- 롤백 가능성 보장
- 인덱스 추가 시 CONCURRENT (PostgreSQL)

완료 시 "@tester please test the migration"
```

##### 3. 자동 로드
```bash
$ python orchestrator.py --reload-agents
✅ 6개 기본 에이전트 로드
✅ 1개 커스텀 에이전트 로드: db-migrator
```

**웹 UI에서 추가**:
```
┌─ 커스텀 에이전트 추가 ───────────────┐
│ 이름: ┌─────────────────────────┐  │
│       │ db-migrator              │  │
│       └─────────────────────────┘  │
│                                    │
│ 역할: ┌─────────────────────────┐  │
│       │ DB 마이그레이션 전문가    │  │
│       └─────────────────────────┘  │
│                                    │
│ 프롬프트:                           │
│ ┌──────────────────────────────┐  │
│ │ 당신은 데이터베이스...        │  │
│ │ (멀티라인 입력)              │  │
│ └──────────────────────────────┘  │
│                                    │
│ 도구 선택:                          │
│ ☑ read  ☑ write  ☑ bash           │
│ ☐ edit  ☐ glob   ☐ grep           │
│                                    │
│ 태그: database, migration          │
│                                    │
│ [취소] [저장]                       │
└────────────────────────────────────┘
```

**수락 기준**:
- ✅ 설정 파일로 에이전트 추가 후 즉시 사용 가능
- ✅ 웹 UI로 GUI 기반 추가 가능
- ✅ 커스텀 에이전트도 메트릭 수집

---

#### F13: 체크포인트 & 작업 재개 ⭐ (신규)

**설명**: 긴 작업 중 중단 후 나중에 재개

**사용 시나리오**:
```bash
# 1. 작업 시작
$ python orchestrator.py "대규모 리팩토링"
[Session abc123] 시작...
[Turn 1] Planner: 계획 수립...
[Turn 2] Coder: 파일 1/10 수정 중...

# 2. 사용자 중단 (Ctrl+C 또는 /pause)
^C
💾 체크포인트 저장 중...
✅ Turn 2까지 저장됨
세션 ID: abc123

# 3. 나중에 재개
$ python orchestrator.py --resume abc123
[Session abc123] 재개...
📂 Turn 2부터 계속합니다
[Turn 3] Coder: 파일 2/10 수정 중...
```

**자동 체크포인트**:
- 매 5턴마다 자동 저장
- 에러 발생 시 즉시 저장
- 사용자 `/pause` 명령 시 저장

**체크포인트 내용**:
```json
{
  "session_id": "abc123",
  "turn": 2,
  "state": {
    "conversation_history": [...],
    "current_agent": "coder",
    "agent_states": {
      "planner": {"status": "completed"},
      "coder": {"status": "in_progress", "progress": "2/10 files"}
    },
    "user_context": {...}
  },
  "timestamp": "2025-01-18T15:25:30Z"
}
```

**수락 기준**:
- ✅ 재개 성공률 100%
- ✅ 재개 시 컨텍스트 유지 (이전 메시지 기억)
- ✅ CLI와 웹 UI 모두 지원

---

## 5. 기술 스펙

### 5.1 시스템 아키텍처 (확장)

```
┌──────────────────────────────────────────────────────┐
│                   Frontend (React)                    │
│  - 세션 목록/상세                                     │
│  - 실시간 챗 (WebSocket)                             │
│  - 에이전트 설정                                      │
│  - 메트릭 대시보드                                    │
└───────────────────┬──────────────────────────────────┘
                    │ HTTP / WebSocket
    ┌───────────────▼───────────────────┐
    │   Backend (FastAPI)               │
    │  - REST API                       │
    │  - WebSocket 핸들러               │
    │  - 인증 (선택)                    │
    └───────────────┬───────────────────┘
                    │
    ┌───────────────▼───────────────────┐
    │   Orchestrator (Core)             │
    │  ┌────────────────────────────┐   │
    │  │ SmartChatManager           │   │
    │  │ - LLM 기반 라우팅          │   │
    │  │ - 규칙 기반 Fallback       │   │
    │  └────────────────────────────┘   │
    │  ┌────────────────────────────┐   │
    │  │ ErrorHandler               │   │
    │  │ - 재시도 로직              │   │
    │  │ - 체크포인트               │   │
    │  └────────────────────────────┘   │
    └───────────────┬───────────────────┘
                    │
    ┌───────────────▼───────────────────┐
    │  ConversationHistory              │
    │  - 메모리 캐시                    │
    │  - DB 동기화                      │
    └───────────────┬───────────────────┘
                    │
    ┌───────────────▼───────────────────┐
    │  SessionStore (SQLite)            │
    │  - sessions                       │
    │  - messages                       │
    │  - agent_metrics                  │
    │  - checkpoints                    │
    └───────────────┬───────────────────┘
                    │
    ┌───────────────▼───────────────────┐
    │  AgentPool (6 agents)             │
    │  ┌────┬────┬────┬────┬────┬────┐ │
    │  │Plan│Code│Test│Rev │Sec │Docs│ │
    │  └────┴────┴────┴────┴────┴────┘ │
    │  + Custom Agents                  │
    └───────────────┬───────────────────┘
                    │
    ┌───────────────▼───────────────────┐
    │  Claude API Client (Anthropic)    │
    │  - Agent LLM (claude-sonnet-4)    │
    │  - Router LLM (claude-sonnet-4)   │
    └───────────────────────────────────┘
```

### 5.2 기술 스택 (확장)

| 구성 요소 | MVP | Extended |
|-----------|-----|----------|
| 언어 | Python 3.10+ | Python 3.10+ |
| LLM SDK | anthropic 0.18+ | anthropic 0.18+ |
| CLI 프레임워크 | Click 8.0+ | Click 8.0+ |
| **웹 프레임워크** | - | **FastAPI 0.104+** |
| **DB** | - | **SQLite (SQLAlchemy 2.0+)** |
| **프론트엔드** | - | **React 18 + TypeScript** |
| **UI 라이브러리** | - | **shadcn/ui + Tailwind CSS** |
| **실시간 통신** | - | **WebSocket (Starlette)** |
| 설정 | JSON (stdlib) | JSON + Pydantic 검증 |
| 로깅 | logging (stdlib) | structlog (구조화 로깅) |

### 5.3 핵심 클래스 (확장)

```python
# models.py (Extended)
@dataclass
class Message:
    role: str
    content: str
    agent_name: Optional[str]
    timestamp: datetime
    metadata: Optional[Dict] = None  # ⭐ 추가: 도구 호출, 에러 등

@dataclass
class AgentConfig:
    name: str
    role: str
    system_prompt: str
    tools: List[str]
    model: str
    enabled: bool = True  # ⭐ 추가
    tags: List[str] = field(default_factory=list)  # ⭐ 추가

@dataclass
class AgentSelection:  # ⭐ 신규
    agent: str
    reason: str
    confidence: float

@dataclass
class RecoveryAction:  # ⭐ 신규
    action: str  # RETRY, FALLBACK, SKIP, ABORT, CHECKPOINT
    params: Dict

# agents.py
class Agent:
    def __init__(self, config: AgentConfig, client: Anthropic)
    def respond(self, history: List[Message]) -> str
    def get_metrics(self) -> AgentMetrics  # ⭐ 추가

# chat_manager.py (Extended)
class SmartChatManager:  # ⭐ MVP의 ChatManager 대체
    def __init__(self, agents: List[Agent], router_llm: Anthropic)
    def select_next_agent(self, history: List[Message]) -> AgentSelection
    def should_use_llm_routing(self, history: List[Message]) -> bool

# error_handler.py (⭐ 신규)
class ErrorHandler:
    def handle_agent_error(
        self, agent: str, error: Exception, context: Dict
    ) -> RecoveryAction
    def save_checkpoint(self, session_id: str, state: Dict)

# session_store.py (⭐ 신규)
class SessionStore:
    def create_session(self, user_request: str) -> str
    def save_message(self, session_id: str, message: Message)
    def get_session(self, session_id: str) -> Session
    def resume_session(self, session_id: str) -> ConversationHistory

# orchestrator.py (Extended)
class Orchestrator:
    def __init__(self, config_path: str, store: SessionStore)
    def run(self, user_request: str, session_id: str = None)
    def resume(self, session_id: str)  # ⭐ 추가

# web_api.py (⭐ 신규)
app = FastAPI()

@app.post("/api/sessions")
async def create_session(request: CreateSessionRequest) -> Session:
    ...
```

### 5.4 디렉토리 구조 (확장)

```
group-chat-orchestrator/
├── orchestrator.py              # CLI 진입점
├── requirements.txt
├── requirements-dev.txt         # ⭐ 추가
├── README.md
├── .env.example                 # ⭐ 추가
├── config/
│   ├── agent_config.json
│   └── routing_rules.json       # ⭐ 추가 (Fallback 규칙)
├── prompts/
│   ├── planner.txt
│   ├── coder.txt
│   ├── tester.txt
│   ├── reviewer.txt             # ⭐ 추가
│   ├── security.txt             # ⭐ 추가
│   ├── docs.txt                 # ⭐ 추가
│   └── custom/                  # ⭐ 추가 (커스텀 에이전트)
│       └── db_migrator.txt
├── src/
│   ├── __init__.py
│   ├── models.py
│   ├── agents.py
│   ├── chat_manager.py
│   ├── conversation.py
│   ├── error_handler.py         # ⭐ 추가
│   ├── session_store.py         # ⭐ 추가
│   ├── metrics.py               # ⭐ 추가
│   └── utils.py
├── backend/                     # ⭐ 신규
│   ├── __init__.py
│   ├── web_api.py              # FastAPI 앱
│   ├── websocket.py            # WebSocket 핸들러
│   ├── schemas.py              # Pydantic 스키마
│   └── dependencies.py
├── frontend/                    # ⭐ 신규
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── SessionList.tsx
│   │   │   ├── ChatView.tsx
│   │   │   ├── AgentSettings.tsx
│   │   │   └── MetricsDashboard.tsx
│   │   └── api/
│   │       └── client.ts
│   └── public/
├── tests/
│   ├── test_chat_manager.py
│   ├── test_agents.py
│   ├── test_conversation.py
│   ├── test_error_handler.py   # ⭐ 추가
│   ├── test_session_store.py   # ⭐ 추가
│   └── test_api.py             # ⭐ 추가
├── sessions/
│   └── orchestrator.db          # ⭐ SQLite DB
└── docs/                        # ⭐ 추가
    ├── architecture.md
    ├── agent-guide.md
    └── api-reference.md
```

---

## 6. 제약사항 및 가정

### 6.1 제약사항 (MVP 대비 완화)
- **컨텍스트 길이**: ~~50 메시지 제한~~ → **100 메시지** (+ 요약 기능)
- **동시성**: 순차 실행만 지원 (병렬 실행 v0.3)
- **에이전트 수**: ~~3개 고정~~ → **6개 기본 + 무제한 커스텀**
- **영속성**: ~~메모리만~~ → **SQLite 영속화**
- **에러 복구**: ~~수동 재시작~~ → **자동 재시도 + 체크포인트**

### 6.2 가정
- Claude API 키가 환경변수 또는 `.env`에 설정
- 사용자는 CLI 또는 웹 브라우저 사용 가능
- 프로젝트 디렉토리에서 실행 (도구 접근 권한)
- 인터넷 연결 안정적
- **[추가]** SQLite 쓰기 권한 (sessions/ 디렉토리)
- **[추가]** Node.js 18+ (프론트엔드 빌드 시)

---

## 7. 성공 시나리오 (Extended)

### 시나리오 1: 신규 기능 개발 (Full Pipeline)

**사용자 입력**:
```bash
$ python orchestrator.py "FastAPI로 /users CRUD 엔드포인트 구현하고 리뷰, 보안 검사, 문서화까지 완료해줘"
```

**기대 흐름**:
1. **Planner** → 요구사항 분석, 6단계 계획 (구현/테스트/리뷰/보안/문서)
2. **Coder** → 모델/라우터/스키마 구현
3. **Tester** → 단위 테스트 작성 및 실행 (✅ 통과)
4. **Reviewer** → 코드 리뷰 (⚠️ N+1 쿼리 발견 → @coder)
5. **Coder** → 쿼리 최적화 (select_related 추가)
6. **Tester** → 재테스트 (✅ 통과)
7. **Security** → 보안 검사 (✅ 문제 없음)
8. **Docs** → README.md 업데이트, API 문서 생성
9. **종료** → "COMPLETE - 모든 단계 완료"

**수락 기준**:
- ✅ 6개 에이전트 순차 실행
- ✅ Reviewer의 피드백이 Coder에 반영됨
- ✅ 사용자 개입 0회
- ✅ 히스토리 DB 저장

---

### 시나리오 2: 에러 자동 복구

**사용자 입력**:
```bash
$ python orchestrator.py "pytest 실행하고 실패하는 테스트 수정해줘"
```

**기대 흐름**:
1. **Tester** → pytest 실행 (❌ 5 failed)
2. **Coder** → 첫 번째 실패 수정 시도
   - ⚠️ **에러 발생**: 파일 경로 오타 (tests/test_user.py → tests/test_users.py)
   - **ErrorHandler** → 파일 목록 재확인 후 재시도
3. **Coder** → 올바른 파일 수정 (✅ 성공)
4. **Tester** → pytest 재실행 (✅ 5 passed)
5. **종료**

**수락 기준**:
- ✅ 에러 발생 시 자동 재시도
- ✅ 사용자 개입 없이 복구
- ✅ 에러 로그 저장 (metrics 테이블)

---

### 시나리오 3: 작업 중단 후 재개

**사용자 입력**:
```bash
# Day 1
$ python orchestrator.py "대규모 리팩토링: 10개 파일 타입 힌트 추가"
[Session abc123] 시작...
[Turn 1] Planner: 10개 파일 목록 작성
[Turn 2] Coder: file1.py 완료 (1/10)
[Turn 3] Coder: file2.py 완료 (2/10)
^C  # 사용자 중단
💾 체크포인트 저장: Turn 3

# Day 2
$ python orchestrator.py --resume abc123
[Session abc123] 재개...
[Turn 4] Coder: file3.py 완료 (3/10)
...
[Turn 11] Coder: file10.py 완료 (10/10)
[Turn 12] Tester: mypy 검사 (✅ 타입 에러 없음)
[Turn 13] TERMINATE - 작업 완료
```

**수락 기준**:
- ✅ 재개 시 이전 컨텍스트 유지 (2/10 파일 완료 상태)
- ✅ 세션 ID로 작업 재개
- ✅ 히스토리 연속성

---

### 시나리오 4: 웹 UI 사용 (멀티 세션)

**사용자 행동**:
1. 브라우저에서 `http://localhost:8000` 접속
2. **세션 1**: "로그인 버그 수정" (백그라운드 실행)
3. **세션 2**: "결제 API 구현" (백그라운드 실행)
4. 세션 목록에서 두 세션 모두 `🟢 Running` 표시
5. 세션 1 클릭 → 실시간으로 Coder가 버그 수정하는 과정 확인
6. 세션 2 클릭 → Planner가 계획 수립 중

**수락 기준**:
- ✅ 여러 세션 동시 실행
- ✅ 실시간 상태 업데이트 (WebSocket)
- ✅ 세션 간 독립적 실행

---

## 8. 마일스톤

### Phase 1: MVP 기반 구축 (Week 1-2)
- [ ] MVP v0.1 안정화 (버그 수정)
- [ ] SQLite 스키마 설계 및 SessionStore 구현
- [ ] 기본 에러 핸들링 추가 (재시도 로직)

### Phase 2: 지능형 라우팅 (Week 2-3)
- [ ] SmartChatManager 구현 (LLM 기반)
- [ ] 규칙 기반 Fallback 로직
- [ ] 라우팅 정확도 테스트 (95% 목표)

### Phase 3: 에이전트 확장 (Week 3-4)
- [ ] Reviewer, Security, Docs 에이전트 추가
- [ ] 6개 에이전트 통합 테스트
- [ ] 커스텀 에이전트 추가 기능 (설정 파일)

### Phase 4: 웹 UI (Week 4-6)
- [ ] FastAPI 백엔드 구현 (REST API + WebSocket)
- [ ] React 프론트엔드 기본 UI
- [ ] 세션 목록/상세 화면
- [ ] 실시간 챗 (WebSocket)

### Phase 5: 메트릭 & 체크포인트 (Week 6-7)
- [ ] 에이전트 메트릭 수집 및 DB 저장
- [ ] 웹 UI 메트릭 대시보드
- [ ] 체크포인트 저장/복구 로직
- [ ] `--resume` CLI 명령어

### Phase 6: 통합 테스트 (Week 7-8)
- [ ] End-to-end 시나리오 4개 테스트
- [ ] 에러 복구 시나리오 테스트
- [ ] 성능 테스트 (100 메시지 히스토리)
- [ ] 보안 검토 (SQL Injection, XSS)

### Phase 7: 문서화 및 릴리스 (Week 8-9)
- [ ] API 문서 (OpenAPI)
- [ ] 에이전트 작성 가이드
- [ ] 배포 가이드 (Docker 선택)
- [ ] v0.2.0 릴리스

---

## 9. 비기능 요구사항

### 9.1 성능
- 에이전트 응답 시간: 평균 5초 이하
- LLM 라우팅: <2초
- 웹 UI 로드: <2초
- 100 메시지 히스토리 처리: 1초 이내

### 9.2 신뢰성
- 무한 루프 발생률: 0%
- 에러 자동 복구율: 90%
- 작업 완료율: 95%
- 세션 재개 성공률: 100%

### 9.3 확장성
- 동시 세션 지원: 최소 10개
- SQLite 성능: 1K 세션, 10K 메시지 처리 가능
- 커스텀 에이전트: 무제한 추가

### 9.4 사용성
- 첫 실행까지 10분 이내 (설치 + 설정)
- 에러 메시지 한국어 지원
- 웹 UI 직관적 (첫 사용 학습 시간 <5분)

### 9.5 보안
- API 키 환경변수 관리
- SQL Injection 방지 (SQLAlchemy ORM)
- XSS 방지 (React 자동 이스케이핑)
- 웹 UI 인증 (선택, v0.3)

---

## 10. 위험 및 완화 전략

| 위험 | 확률 | 영향 | 완화 전략 |
|------|------|------|----------|
| LLM 라우팅 비용 증가 | 중 | 중 | 캐싱 + 규칙 기반 Fallback |
| SQLite 동시성 문제 | 중 | 중 | WAL 모드, 최대 10 동시 세션 제한 |
| 웹 UI 복잡도 증가 | 높음 | 중 | shadcn/ui 재사용 컴포넌트, MVP 기능만 |
| 에러 복구 무한 재시도 | 낮음 | 높음 | 최대 재시도 3회, 백오프 |
| 컨텍스트 길이 초과 | 중 | 높음 | 100 메시지 제한 + 요약 기능 |

---

## 11. 출시 기준 (Definition of Done)

Extended v0.2 출시를 위한 체크리스트:

**기능**:
- [ ] MVP 모든 기능 안정적 작동
- [ ] LLM 기반 라우팅 정확도 95%
- [ ] 6개 에이전트 정상 작동
- [ ] 에러 자동 복구율 90%
- [ ] SQLite 영속화 100% 성공
- [ ] 웹 UI 핵심 기능 (세션 목록/상세/실시간 챗)
- [ ] 체크포인트 & 재개 100% 성공

**품질**:
- [ ] 단위 테스트 커버리지 75% 이상
- [ ] 4개 E2E 시나리오 통과
- [ ] 크리티컬 버그 0건
- [ ] 보안 검토 완료 (SQL Injection, XSS 없음)

**문서**:
- [ ] README (설치/사용법)
- [ ] 에이전트 작성 가이드
- [ ] API 문서 (OpenAPI)
- [ ] 아키텍처 문서

**운영**:
- [ ] 알파 사용자 5명 이상 테스트
- [ ] 피드백 반영
- [ ] 성공 지표 목표치 달성

---

## 12. 향후 계획 (Post-Extended)

### v0.3 (Advanced)
- 병렬 에이전트 실행 (Coder + Tester 동시)
- PostgreSQL 지원 (대규모 팀)
- 에이전트 간 메시지 전달 (직접 통신)
- 고급 메트릭 (성공률 예측, 이상 탐지)

### v1.0 (Production)
- 엔터프라이즈 인증 (OAuth, SSO)
- 팀/역할 관리
- 감사 로그 (Audit Log)
- 클라우드 배포 (AWS, GCP)
- 에이전트 마켓플레이스

---

## 부록

### A. MVP 대비 주요 변경사항

| 영역 | MVP | Extended |
|------|-----|----------|
| 라우팅 | 규칙 기반 | LLM 기반 + 규칙 Fallback |
| 에이전트 | 3개 고정 | 6개 기본 + 커스텀 무제한 |
| 에러 처리 | 수동 재시작 | 자동 재시도 + 체크포인트 |
| 영속성 | JSON 파일 | SQLite DB |
| 인터페이스 | CLI만 | CLI + 웹 UI |
| 메트릭 | 없음 | 에이전트 성능 추적 |
| 작업 재개 | 불가 | 체크포인트 기반 재개 |

### B. 기술 부채
- SQLite → PostgreSQL 마이그레이션 경로 준비 (v0.3)
- 프론트엔드 상태 관리 (현재 useState → Zustand/Redux)
- 에이전트 도구 확장 (파일 시스템 외 API 호출)

### C. 용어 사전
- **턴 (Turn)**: 에이전트 또는 사용자의 한 번의 메시지
- **핸드오프 (Handoff)**: 에이전트 간 작업 전달
- **TERMINATE**: 작업 완료 신호
- **체크포인트 (Checkpoint)**: 작업 중단 시 저장된 상태
- **메트릭 (Metrics)**: 에이전트 성능 측정 데이터

### D. 참고 자료
- Microsoft Azure AI Agent Orchestration Patterns
- AutoGen Group Chat 구현
- LangGraph Multi-Agent Systems
- FastAPI WebSocket 가이드
- SQLAlchemy 2.0 문서

### E. 변경 이력
| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 2025-01-18 | 2.0.0 | MVP 확장 (Extended) PRD 작성 | - |

---

## 라이선스 및 기여

- **라이선스**: MIT (예정)
- **기여 가이드**: CONTRIBUTING.md (v0.2 릴리스 시)

---

**문서 끝**
