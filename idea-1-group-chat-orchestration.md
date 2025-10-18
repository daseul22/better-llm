# 아이디어 1: 그룹 챗 오케스트레이션 인터페이스

## 개요
여러 Claude Code 에이전트가 공유 대화 스레드에서 협업하며, 챗 매니저가 에이전트 간 상호작용을 조정하는 패턴

## 핵심 구성요소

### 1. 공유 대화 스레드
- 모든 에이전트와 사용자가 참여하는 단일 대화 공간
- 각 메시지는 발신자(사용자/에이전트) 태깅
- 대화 히스토리 전체가 컨텍스트로 공유됨

### 2. 챗 매니저 (Chat Manager)
- **역할**: 다음 응답할 에이전트 결정
- **모드**:
  - **자동 모드**: LLM이 다음 에이전트 자동 선택
  - **수동 모드**: 사용자가 직접 지정
  - **라운드 로빈**: 순차적 에이전트 호출
- **책임**: 무한 루프 방지, 종료 조건 관리

### 3. 특수화된 에이전트
```
예시 에이전트 구성:
- Planner: 작업 분해 및 계획
- Coder: 코드 작성/수정
- Tester: 테스트 실행 및 검증
- Reviewer: 코드 리뷰 및 피드백
- DevOps: 빌드/배포 자동화
```

## 아키텍처

```
┌─────────────────────────────────────┐
│     사용자 인터페이스 (CLI/GUI)      │
└──────────────┬──────────────────────┘
               │
    ┌──────────▼──────────┐
    │   Chat Manager      │
    │  - 라우팅 로직       │
    │  - 상태 관리         │
    │  - 종료 조건 감지     │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────────────┐
    │  공유 대화 스레드 (Store)    │
    └──────────┬──────────────────┘
               │
    ┌──────────▼──────────────────┐
    │  Agent Pool                 │
    │  ┌─────┬─────┬─────┬─────┐  │
    │  │ A1  │ A2  │ A3  │ A4  │  │
    │  └─────┴─────┴─────┴─────┘  │
    └─────────────────────────────┘
```

## 구현 예시 (의사코드)

```python
class ChatManager:
    def __init__(self, agents: list[Agent]):
        self.agents = {a.name: a for a in agents}
        self.conversation_history = []
        self.max_turns = 50

    def orchestrate(self, user_message: str):
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        turn = 0
        while turn < self.max_turns:
            # 다음 에이전트 선택
            next_agent = self.select_next_agent()

            if next_agent == "TERMINATE":
                break

            # 에이전트 실행
            response = self.agents[next_agent].respond(
                self.conversation_history
            )

            self.conversation_history.append({
                "role": "agent",
                "agent_name": next_agent,
                "content": response
            })

            turn += 1

    def select_next_agent(self) -> str:
        # LLM을 사용해 다음 에이전트 선택
        prompt = f"""
        대화 히스토리: {self.conversation_history}
        사용 가능 에이전트: {list(self.agents.keys())}

        다음 응답할 에이전트를 선택하거나 TERMINATE를 반환하세요.
        """
        return llm_call(prompt)
```

## 장점
- **Human-in-the-loop 최적화**: 사용자가 자연스럽게 개입 가능
- **투명성**: 모든 에이전트 상호작용이 대화에 노출
- **유연성**: 동적으로 에이전트 추가/제거 가능
- **컨텍스트 공유**: 전체 대화가 모든 에이전트에게 공유됨

## 단점
- **컨텍스트 길이 폭발**: 대화가 길어질수록 토큰 사용량 급증
- **의존성 복잡도**: 에이전트 간 순환 의존성 관리 필요
- **디버깅 난이도**: 다중 에이전트 상호작용 추적 어려움

## 사용 사례
- 복잡한 기능 개발 (계획 → 구현 → 테스트 → 리뷰 파이프라인)
- 버그 수정 (재현 → 분석 → 패치 → 검증)
- 리팩토링 (분석 → 제안 → 실행 → 검증)

## 참고자료
- Microsoft Azure AI Agent Orchestration Patterns
- Adobe AI Assistant (70% 고객 채택)
- CrewAI, LangGraph 그룹 챗 구현
