# 2. MCP (Model Context Protocol) 프로토콜 사용

## Status

Accepted

## Context

Manager Agent가 Worker Agent를 호출하는 방법을 결정해야 했습니다.

초기에는 다음과 같은 방법들을 고려했습니다:

1. **HTTP API**: Worker Agent를 별도 서버로 실행하고 REST API로 통신
2. **gRPC**: 고성능 RPC 프레임워크 사용
3. **Message Queue**: RabbitMQ/Redis를 통한 비동기 메시지 전달
4. **MCP (Model Context Protocol)**: Anthropic의 표준 프로토콜 사용

각 방법의 문제점:

- **HTTP API**:
  - 별도 서버 관리 필요
  - 네트워크 오버헤드
  - 복잡한 배포 구조

- **gRPC**:
  - 프로토콜 정의(.proto) 관리 필요
  - Python에서 성능 이점이 크지 않음

- **Message Queue**:
  - 추가 인프라 필요 (RabbitMQ 설치)
  - 로컬 개발 환경 복잡도 증가

## Decision

**MCP (Model Context Protocol)를 Worker Tools 형태로 구현**하여 Manager Agent가 호출하도록 결정했습니다.

### 구현 방식

```python
# src/infrastructure/mcp/worker_tools.py

WORKER_TOOLS = [
    {
        "name": "planner",
        "description": "요구사항을 분석하고 구현 계획을 수립합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_request": {"type": "string", "description": "사용자 요청"}
            },
            "required": ["user_request"]
        }
    },
    {
        "name": "coder",
        "description": "계획에 따라 코드를 작성하거나 수정합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan": {"type": "string", "description": "구현 계획"}
            },
            "required": ["plan"]
        }
    },
    # ... 추가 Worker Tools
]
```

Manager Agent는 Claude SDK의 `tools` 파라미터에 WORKER_TOOLS를 전달하고, Claude가 자동으로 적절한 Worker를 선택하여 호출합니다.

### 실행 흐름

1. Manager Agent가 WORKER_TOOLS를 포함하여 Claude API 호출
2. Claude가 사용자 요청을 분석하고 적절한 Worker Tool 선택
3. Manager는 Claude의 tool_use 응답을 받아 해당 Worker Agent 실행
4. Worker 결과를 tool_result로 Manager에게 전달
5. Manager가 다음 작업 결정

## Consequences

### 긍정적 결과

- **표준 프로토콜**: Anthropic의 공식 권장 방식으로, 향후 호환성 보장
- **간단한 구조**: 별도 서버나 인프라 없이 단일 프로세스에서 실행
- **자동 라우팅**: Claude가 컨텍스트를 이해하고 적절한 Worker 선택
- **타입 안전성**: input_schema로 명확한 인터페이스 정의
- **로컬 개발 용이**: 복잡한 설정 없이 즉시 실행 가능

### 부정적 결과

- **단일 프로세스 제약**: Worker를 별도 서버로 분리 불가 (확장성 제한)
- **동기 실행**: Worker가 순차적으로 실행되어 병렬 처리 불가
- **메모리 공유**: 모든 Worker가 같은 메모리 공간 사용 (격리 부족)

### 트레이드오프

- **단순함 vs 확장성**:
  - 현재(v0.1): 단순한 구조로 빠른 개발
  - 향후(v0.3): 필요시 HTTP API로 전환 가능 (인터페이스는 동일)

- **성능 vs 유지보수성**:
  - 단일 프로세스로 네트워크 오버헤드 없음
  - 향후 트래픽 증가 시 병목 가능성 있음

- **자동화 vs 제어**:
  - Claude가 Worker 선택을 자동화 (편리함)
  - 명시적 라우팅 로직 부족 (디버깅 어려움)

## References

- [Model Context Protocol (MCP) Specification](https://modelcontextprotocol.io/)
- [Claude API - Tool Use](https://docs.anthropic.com/claude/docs/tool-use)
- [MCP Best Practices](https://github.com/anthropics/anthropic-sdk-python/tree/main/examples/tools)
