# 1. Clean Architecture 채택

## Status

Accepted

## Context

Better-LLM은 여러 Claude 에이전트를 오케스트레이션하는 복잡한 시스템으로, 다음과 같은 요구사항이 있었습니다:

- **확장성**: 새로운 Worker Agent를 쉽게 추가할 수 있어야 함
- **테스트 가능성**: 각 계층을 독립적으로 테스트할 수 있어야 함
- **유지보수성**: 코드 변경이 다른 부분에 영향을 최소화해야 함
- **기술 독립성**: Claude SDK 외의 다른 LLM SDK로 전환 가능해야 함

초기에는 단순한 절차형 코드로 시작했으나, 에이전트 수가 늘어나면서 다음과 같은 문제가 발생했습니다:

- 비즈니스 로직과 인프라 코드가 뒤섞임
- 테스트 작성이 어려움
- 새로운 기능 추가 시 여러 파일을 수정해야 함

## Decision

Clean Architecture의 4-Layer 구조를 채택하여 시스템을 재구성했습니다.

```
better-llm/
├── src/
│   ├── domain/              # 비즈니스 로직 (순수 Python)
│   │   ├── models/          # 도메인 모델
│   │   ├── agents/          # 에이전트 인터페이스
│   │   └── services/        # 도메인 서비스
│   ├── application/         # 유스케이스
│   │   └── ports/           # 인터페이스 정의
│   ├── infrastructure/      # 외부 시스템 연동
│   │   ├── claude/          # Claude SDK 클라이언트
│   │   ├── mcp/             # MCP Worker Tools
│   │   ├── config/          # 설정 로더
│   │   └── storage/         # 세션 저장소
│   └── presentation/        # UI 계층
│       ├── cli/             # CLI 인터페이스
│       └── tui/             # TUI 인터페이스
```

### 계층별 책임

1. **Domain Layer**: 비즈니스 규칙 (외부 의존성 없음)
   - 에이전트 역할 정의
   - 메시지 라우팅 규칙
   - 세션 상태 관리

2. **Application Layer**: 유스케이스 오케스트레이션
   - 에이전트 실행 흐름 제어
   - 에러 처리 및 재시도
   - 메트릭 수집

3. **Infrastructure Layer**: 외부 시스템 구현
   - Claude API 호출
   - MCP 프로토콜 구현
   - 파일 시스템 저장

4. **Presentation Layer**: 사용자 인터페이스
   - CLI 명령 처리
   - TUI 렌더링
   - 입력 검증

### 의존성 규칙

- 내부 계층 → 외부 계층 의존성 금지
- 외부 계층 → 내부 계층 의존성 허용
- 인터페이스를 통한 의존성 역전 (Dependency Inversion)

## Consequences

### 긍정적 결과

- **테스트 용이성**: 각 계층을 독립적으로 테스트 가능 (Mock 객체 사용)
- **확장성 향상**: 새로운 Worker Agent 추가 시 Infrastructure 계층만 수정
- **기술 독립성**: Claude SDK를 OpenAI SDK로 교체 가능 (Infrastructure만 변경)
- **코드 가독성**: 계층별 책임이 명확하여 코드 이해가 쉬움
- **병렬 개발**: 계층별로 독립적인 개발 가능

### 부정적 결과

- **초기 학습 곡선**: 팀원들이 Clean Architecture 개념 학습 필요
- **보일러플레이트 증가**: 인터페이스와 구현체를 분리하여 코드량 증가
- **간단한 기능에 오버엔지니어링**: 단순 CRUD도 여러 계층을 거침

### 트레이드오프

- **복잡성 vs 유연성**: 초기 구조는 복잡하지만, 장기적으로 유지보수와 확장이 쉬움
- **개발 속도 vs 품질**: 초기 개발 속도는 느리지만, 버그가 적고 리팩토링이 쉬움
- **코드량 vs 응집도**: 코드량은 늘어나지만, 각 모듈의 응집도가 높아짐

## References

- [Clean Architecture - Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Python Clean Architecture Example](https://github.com/cosmic-python/code)
