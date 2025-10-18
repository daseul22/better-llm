# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

**그룹 챗 오케스트레이션 시스템** - Manager Agent가 전문화된 Worker Agent들을 조율하여 복잡한 소프트웨어 개발 작업을 자동화하는 시스템입니다.

### 핵심 아키텍처: Worker Tools Pattern

```
사용자
  ↓
Manager Agent (ClaudeSDKClient)
  ↓
Worker Tools (MCP Server)
  ├─ execute_planner_task
  ├─ execute_coder_task
  ├─ execute_reviewer_task
  └─ execute_tester_task
  ↓
Worker Agents (ClaudeSDKClient)
  └─ 실제 작업 수행 (read, write, edit, bash 등)
```

**중요한 개념:**
- **Manager Agent**: 사용자와 대화, Worker Tools를 호출하여 작업 조율
- **Worker Tools**: Worker Agent를 `@tool` 데코레이터로 래핑한 MCP Server
- **Worker Agents**: 실제 작업 수행 (Planner, Coder, Reviewer, Tester)
- 모든 Agent는 `ClaudeSDKClient` 사용 (query() 대신)
- Worker Agent를 Tool로 래핑하여 Manager가 호출하는 구조

---

## 개발 환경 설정

### 필수 요구사항
- Python 3.10+
- Anthropic API 키
- Claude CLI (`~/.claude/local/claude`) - 자동 탐지됨

### 초기 설정

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. API 키 설정
export ANTHROPIC_API_KEY='your-api-key-here'

# 3. 구문 검사 (코드 변경 후)
python3 -m py_compile src/*.py *.py
```

---

## 주요 명령어

### 실행

```bash
# TUI (권장)
python tui.py

# CLI
python orchestrator.py "작업 설명"

# 옵션 포함
python orchestrator.py --verbose "작업 설명"
python orchestrator.py --config custom_config.json "작업 설명"
```

### 테스트

```bash
# 통합 테스트
python test_integration.py

# 개선사항 테스트
python test_improvements.py

# Worker Tools 단독 테스트
python test_worker_tools.py

# 특정 모듈 테스트 (예시)
pytest tests/unit/test_math_utils.py -v
pytest tests/unit/test_math_utils.py::TestMultiply -v
```

### Git 작업

```bash
# 변경사항 커밋 (Conventional Commits)
git add <files>
git commit -m "feat: 새 기능 추가

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 타입: feat, fix, refactor, docs, test, chore
```

---

## 코드 아키텍처

### 주요 모듈

**orchestrator.py** - 메인 실행 파일
- `Orchestrator` 클래스: Manager Agent + Worker Tools 초기화 및 실행
- `run()`: 사용자 입력 검증 → Manager 실행 → 에러 통계 출력

**src/manager_agent.py** - Manager Agent 구현
- `ClaudeSDKClient` 사용 (query() 대신)
- Worker Tools MCP Server 등록
- 프롬프트 히스토리 슬라이딩 윈도우 (max_history_messages=20)
- `allowed_tools`: Worker Tools + read
- `permission_mode`: "bypassPermissions"

**src/worker_tools.py** - Worker Tools MCP Server 🔑
- `@tool` 데코레이터로 Worker Agent 래핑
- `_execute_worker_task()`: 공통 실행 로직 (코드 중복 제거)
- `retry_with_backoff()`: 지수 백오프 재시도 (max 3회)
- `_ERROR_STATS`: Worker별 에러 통계 수집
- `create_worker_tools_server()`: MCP Server 생성

**src/worker_agent.py** - Worker Agent 구현
- `ClaudeSDKClient` 사용
- `execute_task()`: 스트리밍 실행 (async generator)
- 프로젝트 컨텍스트 자동 로드 (.context.json)

**src/project_context.py** - 프로젝트 컨텍스트 관리
- `ProjectContextManager`: .context.json 로드/저장
- `to_prompt_context()`: Worker 프롬프트에 주입할 컨텍스트 생성

**src/utils.py** - 유틸리티
- `get_claude_cli_path()`: 환경변수 + 자동 탐지 (하드코딩 제거)
- `validate_user_input()`: 프롬프트 인젝션 방어
- `sanitize_user_input()`: 공백 정제
- `load_system_config()`: config/system_config.json 로드

### 설정 파일

**config/agent_config.json** - Worker Agent 설정
- 각 Worker의 name, role, system_prompt_file, tools, model 정의
- Planner: read, glob
- Coder: read, write, edit, glob, grep, bash
- Reviewer: read, glob, grep
- Tester: read, bash, write

**config/system_config.json** - 시스템 설정
- manager: max_history_messages, max_turns
- performance: enable_caching, worker_retry 관련
- security: max_input_length, enable_input_validation
- logging: level, format, enable_structured_logging

**.context.json** - 프로젝트 컨텍스트
- 프로젝트 메타데이터, 코딩 스타일, 테스팅 방침
- Worker Agent 초기화 시 자동 로드

**prompts/*.txt** - Worker Agent 시스템 프롬프트
- planner.txt: 계획 수립 전문가
- coder.txt: 코드 작성 전문가
- reviewer.txt: 코드 리뷰 전문가 (심각도 분류: 🔴 Critical, 🟡 Warning, 🔵 Info)
- tester.txt: 테스트 및 검증 전문가

---

## 워크플로우

### 일반적인 작업 흐름

```
사용자 요청
  ↓
[Manager Agent] 작업 분석 및 Worker Tool 호출
  ↓
[Planner Tool] 요구사항 분석 및 계획 수립
  ↓
[Coder Tool] 코드 작성/수정
  ↓
[Reviewer Tool] 코드 품질 검증
  ↓ (Critical 이슈 있으면)
[Coder Tool] 수정 후 재검토
  ↓
[Tester Tool] 테스트 실행 및 검증
  ↓
작업 완료
```

### Manager Agent 동작

1. 사용자 입력 검증 (`validate_user_input`)
2. 프롬프트 히스토리 빌드 (슬라이딩 윈도우)
3. ClaudeSDKClient로 스트리밍 실행
4. Manager가 Worker Tool 호출 결정
5. Worker Tool 실행 (재시도 로직 포함)
6. 결과를 Manager에게 반환
7. Manager가 최종 응답 생성

### Worker Tool 실행

```python
# Worker Tools에서
@tool("execute_planner_task", "설명", {"task_description": str})
async def execute_planner_task(args: Dict[str, Any]) -> Dict[str, Any]:
    # 1. _WORKER_AGENTS에서 Worker 가져오기
    worker = _WORKER_AGENTS.get("planner")

    # 2. execute_task() 스트리밍 실행
    result = ""
    async for chunk in worker.execute_task(task):
        result += chunk

    # 3. Tool 응답 형식으로 반환
    return {"content": [{"type": "text", "text": result}]}
```

---

## 일반적인 작업 패턴

### 새 Worker Agent 추가

1. **프롬프트 작성**: `prompts/new_agent.txt`
2. **설정 추가**: `config/agent_config.json`에 agent 정의
3. **Worker Tool 추가**: `src/worker_tools.py`에 `@tool` 데코레이터 함수 추가
4. **MCP Server 등록**: `create_worker_tools_server()`에 tool 추가
5. **Manager 설정**: `allowed_tools`에 tool 추가
6. **테스트**: `test_worker_tools.py`에 테스트 추가

### 설정 변경

- **모델 변경**: `config/agent_config.json`의 `model` 필드
- **프롬프트 수정**: `prompts/*.txt` 파일 직접 수정
- **재시도 설정**: `config/system_config.json`의 `performance` 섹션
- **입력 검증**: `config/system_config.json`의 `security` 섹션

### 디버깅

```bash
# 상세 로깅
python orchestrator.py --verbose "작업"

# Worker Tools 단독 테스트
python test_worker_tools.py

# 에러 통계 확인
# orchestrator.py 실행 후 자동 출력됨
```

---

## 중요한 제약사항

### 절대 하지 말아야 할 것

1. **query() 사용 금지**: Worker Tools를 호출하려면 반드시 `ClaudeSDKClient` 사용
2. **CLI 경로 하드코딩 금지**: `get_claude_cli_path()` 사용
3. **입력 검증 생략 금지**: `validate_user_input()` 필수
4. **시크릿 하드코딩 금지**: 환경변수 사용 (.env 또는 export)

### 알려진 제약

- 순차 실행만 지원 (병렬 Worker Tool 실행 미지원)
- 최대 턴 수: 10턴 (system_config.json에서 변경 가능)
- 최대 히스토리: 20 메시지 (슬라이딩 윈도우)
- 최대 입력 길이: 5000자 (프롬프트 인젝션 방어)

---

## 문제 해결

### "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다"
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

### "Claude CLI not found"
```bash
# 환경변수 설정
export CLAUDE_CLI_PATH='/path/to/claude'

# 또는 ~/.claude/local/claude 에 설치
```

### "Worker Tool 호출 실패"
- `test_worker_tools.py` 실행하여 Worker Tools 단독 테스트
- Worker Agent 설정 확인 (`config/agent_config.json`)
- 프롬프트 파일 존재 확인 (`prompts/*.txt`)

### "프롬프트 파일 로드 실패"
```bash
# 파일 존재 확인
ls -la prompts/
```

---

## 보안 및 성능

### 보안 체크리스트

- [x] CLI 경로 하드코딩 제거 (환경변수 + 자동 탐지)
- [x] 사용자 입력 검증 (프롬프트 인젝션 방어)
- [x] 시크릿 하드코딩 금지 (환경변수 사용)
- [x] 최대 입력 길이 제한 (5000자)
- [ ] 파일 접근 화이트리스트 (TODO)

### 성능 최적화

- 프롬프트 캐싱 활성화 (`enable_caching: true`)
- 슬라이딩 윈도우로 토큰 비용 절감 (max_history_messages: 20)
- Worker Tool 재시도 로직 (지수 백오프, max 3회)
- 에러 통계 수집 및 모니터링

---

## 향후 개선 계획

### 단기 (우선순위 1)
- 병렬 실행 지원: 독립적인 Worker Tool 병렬 실행
- Worker Tool 동적 로딩: 플러그인 아키텍처
- 파일 접근 화이트리스트: 보안 강화

### 중기 (우선순위 2)
- 캐싱 전략 개선: Worker Agent 파일 캐싱
- 구조화된 로깅: JSON 로그 및 모니터링 도구 연동
- 메트릭 수집: Worker별 평균 실행 시간, 토큰 사용량, 성공률

### 장기 (우선순위 3)
- 아키텍처 다이어그램: 시각적 문서화
- 자동 복구: 에러 패턴 분석 후 자동 복구 로직
- 마이크로서비스 아키텍처: Worker Tool 분산 실행

---

## 참고 자료

- [Claude Agent SDK 공식 문서](https://docs.anthropic.com/en/docs/agent-sdk/python)
- [query() vs ClaudeSDKClient](https://docs.anthropic.com/en/docs/agent-sdk/python/query-vs-client)
- [MCP Server 가이드](https://docs.anthropic.com/en/docs/agent-sdk/python/mcp-servers)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

**개발 히스토리**: 상세한 개발 히스토리는 `CLAUDE_HISTORY.md` 참조

**최종 업데이트**: 2025-10-18
