# Claude Code 프로젝트 기록

그룹 챗 오케스트레이션 시스템의 개발 히스토리 및 주요 결정 사항을 기록합니다.

---

## 작업 기록

### feat. Worker Tools Architecture 구현 및 검증 완료

- 날짜: 2025-10-18 14:35 (Asia/Seoul)
- 컨텍스트:
  - 사용자가 "각 agent들을 tool로 만들고 매니저 agent에는 각 agent를 랩핑한 툴과 read 툴만 넣어주면 되잖아"라고 제안
  - Claude Agent SDK 공식 문서 확인 결과 `@tool` 데코레이터와 `create_sdk_mcp_server` 발견
  - `query()` 대신 `ClaudeSDKClient`를 사용해야 툴 지원 가능함을 확인

- 변경사항:
  - `src/worker_tools.py` (신규): 각 Worker Agent를 `@tool` 데코레이터로 래핑, MCP Server 생성
    - `execute_planner_task`: Planner Agent를 Tool로 래핑
    - `execute_coder_task`: Coder Agent를 Tool로 래핑
    - `execute_tester_task`: Tester Agent를 Tool로 래핑
    - `create_worker_tools_server()`: Worker Tools MCP Server 생성
  - `src/manager_agent.py`: `query()` → `ClaudeSDKClient` 변경, Worker Tools MCP Server 등록
    - `ClaudeAgentOptions`로 `mcp_servers`, `allowed_tools`, `permission_mode` 설정
    - `async with ClaudeSDKClient` 패턴 사용
  - `orchestrator.py`: Worker Tools 초기화 및 Manager에 전달, 라우팅 로직 단순화
  - `tui.py`: `self.workers` → `self.worker_agents` 변경 (Textual App의 workers property 충돌 해결)
  - `test_worker_tools.py` (신규): Worker Tools 단독 테스트 스크립트

- 영향범위:
  - 기능: ✅ Manager Agent가 Worker Tool들을 성공적으로 호출하여 작업 수행
  - 성능: ✅ 전체 실행 시간 ~4.75분 (multiply 함수 작성 + 테스트 포함)
  - 보안: ✅ `permission_mode="bypassPermissions"` 설정으로 자동 승인
  - 문서: ✅ README.md에 Worker Tools Architecture 설명 추가됨

- 테스트:
  - 단위: ✅ `test_worker_tools.py` 성공 (Planner Tool 호출 및 응답 확인, ~45초)
  - 통합: ✅ `orchestrator.py` 실행 테스트 성공
    - 테스트 1: add 함수 확인 (기존 코드 검증, 11 테스트 통과)
    - 테스트 2: multiply 함수 작성 (신규 코드 + 테스트 작성, 11 테스트 통과)
  - 수동: ✅ `pytest tests/unit/test_math_utils.py::TestMultiply -v` 성공 (11 passed in 0.02s)

- 후속 조치:
  - TODO: TUI 인터페이스를 Worker Tools Architecture로 업데이트 필요
  - 모니터링: 실제 복잡한 프로젝트에서 성능 및 비용 측정

---

## 아키텍처 결정 사항

### Worker Tools Architecture (v3.0)

**선택 이유**:
1. Claude Agent SDK의 툴 기반 아키텍처에 완벽히 부합
2. Manager가 Worker를 일반 Tool처럼 호출 가능 (통일된 인터페이스)
3. 명확한 책임 분리 (Manager: 조율, Worker: 실행)
4. 확장 가능 (새 Worker Tool 추가 용이)

**구현 상세**:
```python
# Worker Agent를 Tool로 래핑
@tool("execute_planner_task", "설명", {"task_description": str})
async def execute_planner_task(args: Dict[str, Any]) -> Dict[str, Any]:
    worker = _WORKER_AGENTS.get("planner")
    result = ""
    async for chunk in worker.execute_task(task):
        result += chunk
    return {"content": [{"type": "text", "text": result}]}

# MCP Server 생성
server = create_sdk_mcp_server(
    name="workers",
    version="1.0.0",
    tools=[execute_planner_task, execute_coder_task, execute_tester_task]
)

# Manager Agent에 등록
options = ClaudeAgentOptions(
    model="claude-sonnet-4-5-20250929",
    mcp_servers={"workers": worker_tools_server},
    allowed_tools=[
        "mcp__workers__execute_planner_task",
        "mcp__workers__execute_coder_task",
        "mcp__workers__execute_tester_task",
        "read"
    ],
    cli_path="/Users/simdaseul/.claude/local/claude",
    permission_mode="bypassPermissions"
)
```

**대안 검토**:
- ❌ Messages API 직접 사용: 툴 지원 없음, 복잡한 수동 구현 필요
- ❌ `query()` 함수 사용: 툴 지원 없음, 단순 텍스트 생성만 가능
- ✅ `ClaudeSDKClient` + Worker Tools: 툴 기반 아키텍처, 깔끔한 구현

### 주요 이슈 및 해결

**이슈 1: query()는 툴을 지원하지 않음**
- 발견: Manager Agent가 `query()` 사용 시 Worker Tools 호출 불가
- 해결: `ClaudeSDKClient` 사용으로 변경
- 참고: [Claude Agent SDK 공식 문서](https://docs.anthropic.com/en/docs/agent-sdk/python/query-vs-client)

**이슈 2: Textual App의 workers property 충돌**
- 발견: TUI에서 `self.workers` 사용 시 `AttributeError: property 'workers' of 'OrchestratorTUI' object has no setter`
- 해결: `self.workers` → `self.worker_agents`로 변수명 변경 (9개 위치)

---

## 성능 메트릭

### Worker Tools Architecture (v3.0)

**multiply 함수 작성 테스트** (2025-10-18):
- 총 실행 시간: 285.5초 (~4.75분)
- Manager 턴 수: 1회
- Worker Tool 호출: 3회 (Planner → Coder → Tester)
- 비용: $0.147 USD
- API 호출 시간: 64.3초
- 토큰 사용량:
  - Input: 45 tokens
  - Cache creation: 13,310 tokens
  - Cache read: 169,339 tokens
  - Output: 2,970 tokens

**add 함수 확인 테스트** (2025-10-18):
- 총 실행 시간: 153.5초 (~2.5분)
- Manager 턴 수: 1회
- Worker Tool 호출: 3회 (Planner → Coder → Tester)
- 비용: $0.133 USD

---

## 향후 개선 사항

1. **TUI 업데이트**: Worker Tools Architecture로 변경 필요
2. **성능 최적화**: 캐싱 전략 개선, 불필요한 Tool 호출 최소화
3. **에러 핸들링**: Worker Tool 실패 시 재시도 로직 추가
4. **로깅 개선**: 각 Tool 호출의 입출력 상세 로깅
5. **문서화**: 아키텍처 다이어그램 및 사용 예제 추가
