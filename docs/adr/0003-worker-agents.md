# 3. Worker Agent 역할 분리

## Status

Accepted

## Context

초기에는 단일 Claude Agent가 모든 작업(계획, 코딩, 테스트)을 수행했습니다.

### 단일 Agent의 문제점

1. **컨텍스트 혼잡**: 하나의 Agent가 여러 역할을 수행하면서 프롬프트가 복잡해짐
2. **성능 저하**: 모든 작업을 한 번에 처리하려다 보니 응답 속도가 느림
3. **에러 전파**: 한 단계 실패 시 전체 작업 재시도 필요
4. **역할 불명확**: 어떤 단계에서 문제가 발생했는지 추적 어려움

### 고려한 대안

1. **단일 Agent with 단계별 프롬프트**:
   - 같은 Agent를 여러 번 호출하되, 매번 다른 시스템 프롬프트 사용
   - 문제: Agent 상태 관리 복잡, 컨텍스트 유지 어려움

2. **Multi-Agent 시스템 (전문화)**:
   - 각 역할별로 독립적인 Agent 생성
   - Planner, Coder, Tester, Reviewer, Committer 등

3. **Hierarchical Agent**:
   - 상위 Coordinator Agent가 하위 Worker Agent 관리
   - 문제: 구조 복잡도 증가

## Decision

**역할별로 전문화된 Worker Agent를 분리**하고, **Manager Agent가 오케스트레이션**하는 구조를 채택했습니다.

### Worker Agent 구성

```python
# config/agent_config.json
{
  "agents": [
    {
      "name": "planner",
      "role": "요구사항 분석 및 계획 수립",
      "system_prompt_file": "prompts/planner.txt",
      "tools": ["read", "glob", "grep"],
      "model": "claude-sonnet-4"
    },
    {
      "name": "coder",
      "role": "코드 작성 및 수정",
      "system_prompt_file": "prompts/coder.txt",
      "tools": ["read", "write", "edit", "glob", "grep", "bash"],
      "model": "claude-sonnet-4"
    },
    {
      "name": "tester",
      "role": "테스트 실행 및 검증",
      "system_prompt_file": "prompts/tester.txt",
      "tools": ["read", "bash"],
      "model": "claude-sonnet-4"
    },
    {
      "name": "reviewer",
      "role": "코드 리뷰 및 품질 검증",
      "system_prompt_file": "prompts/reviewer.txt",
      "tools": ["read", "glob", "grep"],
      "model": "claude-sonnet-4"
    },
    {
      "name": "committer",
      "role": "Git 커밋 및 PR 생성",
      "system_prompt_file": "prompts/committer.txt",
      "tools": ["bash"],
      "model": "claude-sonnet-4"
    }
  ]
}
```

### 각 Worker의 책임

| Worker | 책임 | 필수 도구 |
|--------|------|----------|
| **Planner** | 요구사항 분석, 계획 수립, 파일 탐색 | read, glob, grep |
| **Coder** | 코드 작성/수정, 파일 생성, 빌드 실행 | read, write, edit, bash |
| **Tester** | 테스트 실행, 결과 검증 | read, bash |
| **Reviewer** | 코드 품질 검토, 베스트 프랙티스 확인 | read, glob, grep |
| **Committer** | Git 커밋, PR 생성, 릴리스 관리 | bash |

### Manager Agent 역할

- Worker Tool 제공 및 실행
- 에러 처리 및 재시도
- 무한 루프 방지
- 메트릭 수집

## Consequences

### 긍정적 결과

- **명확한 책임 분리**: 각 Worker가 하나의 역할만 수행 (Single Responsibility)
- **컨텍스트 효율성**: 각 Worker가 필요한 정보만 처리하여 토큰 사용량 감소
- **독립적 재시도**: 특정 단계 실패 시 해당 Worker만 재실행
- **병렬화 가능성**: 독립적인 Worker는 병렬 실행 가능 (향후 구현)
- **테스트 용이성**: 각 Worker를 독립적으로 테스트 가능

### 부정적 결과

- **오케스트레이션 복잡도**: Manager Agent의 라우팅 로직 복잡
- **컨텍스트 단절**: Worker 간 정보 전달 시 컨텍스트 손실 가능
- **API 호출 증가**: 각 Worker마다 별도 API 호출로 비용 증가
- **설정 파일 관리**: 5개 Worker의 프롬프트 파일 유지보수 필요

### 트레이드오프

- **세분화 vs 복잡도**:
  - 현재: 5개 Worker로 적절한 세분화
  - 대안: 3개 Worker (Planner, Developer, Tester)로 단순화 가능
  - 선택 이유: 역할 명확성을 우선

- **성능 vs 품질**:
  - 단일 Agent: 빠르지만 품질 불안정
  - 다중 Worker: 느리지만 각 단계에서 품질 검증

- **자동화 vs 제어**:
  - Manager가 자동으로 Worker 선택 (편리)
  - 사용자가 `@agent_name`으로 명시적 호출 가능 (제어)

## References

- [Multi-Agent Systems Design Patterns](https://microsoft.github.io/autogen/docs/tutorial/introduction)
- [LangGraph Multi-Agent Workflows](https://python.langchain.com/docs/langgraph)
- [Agentic AI Best Practices - Anthropic](https://docs.anthropic.com/claude/docs/agentic-ai)
