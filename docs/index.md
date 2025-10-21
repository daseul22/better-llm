# Better-LLM Documentation

여러 Claude 에이전트가 협업하여 복잡한 소프트웨어 개발 작업을 자동화하는 오케스트레이션 시스템입니다.

## 🚀 빠른 시작

시작하기 전에 읽어야 할 문서:

1. [**설치 가이드**](guides/installation.md) - 시스템 설치 및 설정
2. [**빠른 시작**](guides/quickstart.md) - 첫 번째 작업 실행
3. [**사용법**](guides/usage.md) - 상세한 사용 가이드

## 📚 문서 구조

### 사용자 가이드 (`guides/`)

실제 사용법 및 활용 팁을 담은 문서입니다.

- [**설치 가이드**](guides/installation.md) - 시스템 요구사항 및 설치 방법
- [**빠른 시작**](guides/quickstart.md) - 30초 안에 시작하기
- [**사용법**](guides/usage.md) - TUI/CLI 사용법, 고급 기능, Best Practices
- [**사용 사례**](guides/use_cases.md) - 실전 시나리오별 활용법
- [**CLI 개선**](guides/cli_improvements.md) - CLI 출력 및 UX 개선
- [**안정성 가이드**](guides/resilience.md) - Circuit Breaker, 재시도 정책

### 아키텍처 문서

시스템 설계 및 구조를 설명하는 문서입니다.

- [**아키텍처 개요**](architecture.md) - Clean Architecture 4계층 구조
- [**에러 참조**](errors.md) - 에러 코드 및 처리 방법
- [**디버그 모드**](debug_mode.md) - 디버깅 팁 및 설정
- [**문제 해결**](troubleshooting.md) - 일반적인 문제 및 해결 방법

### ADR (Architecture Decision Records)

주요 설계 결정의 배경과 근거를 기록합니다.

- [**템플릿**](adr/0000-template.md) - ADR 작성 템플릿
- [**0001: Clean Architecture 채택**](adr/0001-clean-architecture.md) - 아키텍처 선택 배경
- [**0002: MCP 프로토콜**](adr/0002-mcp-protocol.md) - Model Context Protocol 도입
- [**0003: Worker Agent 분리**](adr/0003-worker-agents.md) - Agent 역할 분리 설계
- [**0004: 구조화된 로깅**](adr/0004-structured-logging.md) - Structlog 도입 배경
- [**0005: 비동기 메트릭 수집**](adr/0005-async-metrics.md) - 성능 최적화 설계

### API Reference (`api/`)

코드 레벨 API 문서입니다.

#### Domain Layer
- [**Models**](api/domain/models.md) - 도메인 모델 (Message, Task, AgentConfig 등)
- [**Agents**](api/domain/agents.md) - Agent 인터페이스
- [**Errors**](api/domain/errors.md) - 도메인 에러 정의

#### Infrastructure Layer
- [**Manager Agent**](api/infrastructure/manager.md) - Manager Agent 클라이언트
- [**Worker Agent**](api/infrastructure/worker.md) - Worker Agent 클라이언트
- [**Worker Tools**](api/infrastructure/worker_tools.md) - MCP Worker Tools
- [**Config**](api/infrastructure/config.md) - 설정 로더
- [**Storage**](api/infrastructure/storage.md) - 세션 저장소
- [**Logging**](api/infrastructure/logging.md) - 구조화된 로깅
- [**Metrics**](api/infrastructure/metrics.md) - 메트릭 수집
- [**Cache**](api/infrastructure/cache.md) - 프롬프트 캐시

### 개발 문서 (`development/`)

개발 히스토리, 구현 상세, 리팩토링 기록을 담고 있습니다.

- [**개발 히스토리**](development/history.md) - 전체 개발 과정 기록
- [**구현 상세**](development/README.md#-구현-상세) - 새 기능 구현 문서
  - [CLI 출력 개선](development/implementations/cli-output.md)
  - [워크플로우 비주얼라이저](development/implementations/workflow-visualizer.md)
  - [테스트 보고서 UI](development/implementations/test-report-ui.md)
- [**리팩토링 기록**](development/README.md#-리팩토링-기록) - 코드 개선 작업
  - [Import 수정](development/refactoring/import-fixes.md)
  - [Phase 1 리팩토링](development/refactoring/phase1.md)
  - [구현 요약](development/refactoring/implementation-summary.md)

### 가이드라인

코드 작성 및 에러 처리 가이드라인입니다.

- [**에러 처리 가이드라인**](ERROR_HANDLING_GUIDELINES.md) - 에러 처리 모범 사례
- [**Import 가이드라인**](IMPORT_GUIDELINES.md) - Import 규칙 및 패턴

## 🎯 사용자별 추천 경로

### 초보자
1. [설치 가이드](guides/installation.md)
2. [빠른 시작](guides/quickstart.md)
3. [사용법](guides/usage.md)
4. [문제 해결](troubleshooting.md)

### 일반 사용자
1. [사용 사례](guides/use_cases.md) - 실전 시나리오
2. [안정성 가이드](guides/resilience.md) - 고급 설정
3. [CLI 개선](guides/cli_improvements.md) - 효율적인 사용법

### 개발자
1. [아키텍처 개요](architecture.md)
2. [ADR 모음](adr/0001-clean-architecture.md)
3. [API Reference](api/domain/models.md)
4. [개발 히스토리](development/history.md)

### 기여자
1. [기여 가이드](../CONTRIBUTING.md)
2. [에러 처리 가이드라인](ERROR_HANDLING_GUIDELINES.md)
3. [Import 가이드라인](IMPORT_GUIDELINES.md)
4. [개발 문서](development/README.md)

## 🔗 관련 링크

### 외부 문서
- [Anthropic API 문서](https://docs.anthropic.com/)
- [Claude Agent SDK](https://docs.anthropic.com/en/docs/agent-sdk/python)
- [MCP 프로토콜](https://modelcontextprotocol.io/)
- [Textual 문서](https://textual.textualize.io/)

### 프로젝트 문서
- [메인 README](../README.md) - 프로젝트 개요
- [변경 이력](../CHANGELOG.md) - 버전별 변경사항
- [라이선스](../LICENSE) - MIT License

## 💡 주요 특징

### 🏗️ Clean Architecture 기반
- 4-Layer 구조 (Domain, Application, Infrastructure, Presentation)
- 테스트 가능하고 확장 가능한 설계
- 의존성 역전 원칙 (Dependency Inversion) 준수

### 🤖 Multi-Agent 협업
- **Planner**: 요구사항 분석 및 계획 수립
- **Coder**: 코드 작성 및 수정
- **Tester**: 테스트 실행 및 검증
- **Reviewer**: 코드 리뷰 및 품질 검증
- **Committer**: Git 커밋 및 PR 생성
- **Ideator**: 창의적 아이디어 생성
- **Product Manager**: 제품 기획 및 요구사항 정의

### 🔧 MCP (Model Context Protocol)
- Anthropic의 표준 프로토콜 사용
- Manager Agent가 Worker Tools를 자동 호출
- 타입 안전한 인터페이스

### 📊 구조화된 로깅 및 메트릭
- Structlog 기반 JSON 로깅
- 비동기 메트릭 수집
- 실시간 에러 추적

### ⚡ 성능 최적화
- 프롬프트 캐싱 (API 호출 30-50% 절감)
- 세션 압축 저장 (디스크 공간 30-50% 절감)
- 백그라운드 저장 (저장 시간 70% 단축)

## 📞 문의 및 지원

- **GitHub Issues**: [https://github.com/simdaseul/better-llm/issues](https://github.com/simdaseul/better-llm/issues)
- **Discussions**: [https://github.com/simdaseul/better-llm/discussions](https://github.com/simdaseul/better-llm/discussions)

---

**Made with ❤️ using Claude API**
