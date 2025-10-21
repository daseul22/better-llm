# Changelog

모든 주목할 만한 변경 사항이 이 파일에 기록됩니다.

이 프로젝트는 [Semantic Versioning](https://semver.org/)을 따릅니다.

## [Unreleased]

### Added
- mkdocs 기반 API 문서 자동 생성
- ADR (Architecture Decision Records) 문서 5개 작성
- 에러 코드 체계화 (`src/domain/errors/`)
- 문서화 개선 (설치 가이드, 빠른 시작, 사용법, 문제 해결)

### Changed
- **TUI 리팩토링 (2025-01-20)**
  - SessionManager 캡슐화 강화
  - 세션 생성 로직 중앙화 (팩토리 메서드 패턴)
  - 순환 의존성 제거 (의존성 역전 원칙 적용)
  - 복잡한 메서드 분리 (switch_to_session 56줄 → 27줄)
  - 타입 힌팅 완성 (mypy 에러 0개 달성)
  - 예외 처리 개선 (try-except: pass 패턴 제거)
  - 프로퍼티 캐싱 최적화 (LRU 캐시 적용)
- README.md 개선 (Quick Start, 문서 링크 추가)
- CONTRIBUTING.md 작성 (기여 가이드)

## [0.1.0] - 2025-01-20

### Added
- **Clean Architecture 기반 4-Layer 구조**
  - Domain Layer: 비즈니스 로직
  - Application Layer: 유스케이스
  - Infrastructure Layer: 외부 시스템 연동
  - Presentation Layer: UI (TUI, CLI)

- **Multi-Agent 오케스트레이션**
  - Manager Agent: Worker Tools 호출
  - 5개 Worker Agent (Planner, Coder, Tester, Reviewer, Committer)
  - MCP (Model Context Protocol) 기반 통신

- **TUI (Terminal User Interface)**
  - Claude Code 스타일 인터페이스
  - 실시간 Markdown 렌더링
  - Syntax highlighting
  - 세션 관리

- **CLI (Command Line Interface)**
  - 간단한 명령어 실행
  - `@agent_name`으로 특정 Worker 호출
  - 다양한 옵션 (--verbose, --config 등)

- **구조화된 로깅 (Structlog)**
  - JSON 형식 로그
  - 파일명/함수명/줄번호 자동 추가
  - 로그 레벨별 파일 분리
  - 로그 로테이션

- **에러 추적 시스템**
  - 에러 타입별 추적
  - 컨텍스트 정보 자동 수집
  - 통계 API 제공
  - 멀티스레드 안전

- **성능 최적화**
  - 비동기 메트릭 수집 (큐 기반)
  - 프롬프트 캐싱 (LRU, TTL)
  - 세션 압축 저장 (gzip)
  - 백그라운드 세션 저장

- **워크플로우 안정성**
  - Worker별 타임아웃 설정
  - 자동 재시도 (지수 백오프)
  - 무한 루프 방지 (최대 반복 횟수)
  - 리소스 자동 정리

- **설정 관리**
  - Agent 설정 (`config/agent_config.json`)
  - 시스템 설정 (`config/system_config.json`)
  - 환경 변수 지원 (`.env`)

- **세션 히스토리**
  - 자동 저장 (`sessions/` 디렉토리)
  - JSON 형식 (압축 가능)
  - 세션 로드 및 재실행

- **테스트**
  - 단위 테스트 (pytest)
  - 통합 테스트
  - E2E 테스트
  - Mock 객체 (Claude API)

- **문서**
  - README.md (Quick Start, 사용법)
  - 사용 가이드 (docs/use_cases_guide.md)
  - CLI 출력 개선 가이드 (docs/CLI_OUTPUT_IMPROVEMENTS.md)
  - 안정성 가이드 (docs/resilience.md)

- **글로벌 설치**
  - 자동 설치 스크립트 (`install.sh`)
  - pipx 지원
  - `better-llm` 및 `better-llm-cli` 명령어

### Changed
- Manager Agent가 Worker를 직접 호출하는 방식에서 Worker Tools 방식으로 변경
- 절차형 코드에서 Clean Architecture 기반 객체지향 코드로 리팩토링

### Fixed
- Worker 타임아웃 시 좀비 프로세스 생성 문제 해결
- 세션 저장 시 메인 워크플로우 블로킹 문제 해결
- 메트릭 수집 시 성능 저하 문제 해결
- 로그 파일 크기 무한 증가 문제 해결 (로테이션)

## [0.0.1] - 2025-01-10

### Added
- 초기 프로토타입
- 3개 Agent (Planner, Coder, Tester)
- 기본 CLI 인터페이스
- 간단한 대화 히스토리 관리

---

## 버전 규칙

### 주 버전 (Major)
- 호환성을 깨는 변경 (Breaking Changes)
- 아키텍처 전면 개편

### 부 버전 (Minor)
- 새로운 기능 추가 (하위 호환 유지)
- 새로운 Worker Agent 추가

### 패치 버전 (Patch)
- 버그 수정
- 문서 업데이트
- 성능 개선

---

## 타입별 변경 사항 분류

### Added
새로운 기능 추가

### Changed
기존 기능 변경

### Deprecated
곧 제거될 기능 (하위 호환 유지)

### Removed
제거된 기능

### Fixed
버그 수정

### Security
보안 관련 수정

---

[Unreleased]: https://github.com/simdaseul/better-llm/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/simdaseul/better-llm/releases/tag/v0.1.0
[0.0.1]: https://github.com/simdaseul/better-llm/releases/tag/v0.0.1
