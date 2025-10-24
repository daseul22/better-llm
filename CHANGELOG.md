# Changelog

모든 주목할 만한 변경 사항이 이 파일에 기록됩니다.

이 프로젝트는 [Semantic Versioning](https://semver.org/)을 따릅니다.

## [Unreleased]

### Added
- **🚀 Ideator 및 Product Manager Worker 추가 - 2025-10-20**
  - **Ideator Worker**: 창의적 아이디어 생성 전문가
    - SCAMPER, First Principles 등 사고 기법 적용
    - 발산적/수렴적 사고 프로세스 구조화
    - 실현 가능성 기반 아이디어 평가 및 우선순위 제안
    - Tools: read, glob (컨텍스트 파악용, 읽기 전용)
  - **Product Manager Worker**: 제품 기획 전문가
    - 요구사항 정의 및 우선순위 설정 (MoSCoW 등)
    - 사용자 스토리 및 수용 기준(Acceptance Criteria) 작성
    - 제품 로드맵 및 마일스톤 계획 (MVP → Enhancement → Scale)
    - 위험 분석 및 완화 전략 수립
    - Tools: read, glob, grep (요구사항 분석용, 읽기 전용)
  - **영향**: 워크플로우 확장 (Ideator → Product Manager → Planner → Coder → Reviewer → Tester)
- **🚀 Human-in-the-Loop (대화형 의사결정 지원) - 2025-10-21**
  - **ask_user Tool 추가**: Manager Agent가 사용자에게 질문하고 응답 받을 수 있는 MCP Tool
  - 선택지 목록 제공 가능 (번호 선택 또는 자유 텍스트)
  - `interaction.enabled` 설정에 따라 on/off 가능
  - CLI 콜백 구현 (Rich Panel로 질문 표시)
  - **사용 사례**: Planner가 여러 옵션(A안/B안) 제시 시 사용자에게 선택 요청
  - **영향**: 중요한 기술 결정에 사용자 참여 가능 (아키텍처 선택, 구현 방식 등)
- **🚀 Artifact Storage - Manager 컨텍스트 윈도우 최적화 - 2025-01-21**
  - Worker 전체 출력을 `~/.better-llm/{project}/artifacts/{worker}_{timestamp}.txt`에 저장
  - Manager에게는 **요약만** 전달 → 컨텍스트 90% 절감
  - `ArtifactStorage` 인프라 구현: save_artifact(), extract_summary(), load_artifact(), cleanup_old_artifacts()
  - Worker Tools에 artifact 저장 로직 추가 (모든 Worker Tool에 적용)
  - 7일 이상 된 artifact 자동 삭제
  - **성능 개선**: Coder 출력 15,000 토큰 → 요약 1,500 토큰 (90% 절감)
- **🚀 Reflective Agent - Coder 자가 평가 및 개선 - 2025-10-22**
  - Coder Worker에 자가 평가 및 개선 기능 추가
  - 평가 기준 5가지: 코드 품질, 가독성, 성능, 보안, 테스트 가능성 (각 1-10점)
  - 평균 점수 < 7.0 → 코드 개선 → 재평가 (최대 1회)
  - 평가 결과 출력 형식 표준화
  - **영향**: Coder가 스스로 품질 검증하여 초기 품질 향상, Review 사이클 30% 단축 예상
- **🚀 수직적 고도화: LLM 기반 Intelligent Summarizer - 2025-10-22**
  - Claude Haiku를 사용한 지능형 Worker 출력 요약
  - 패턴 매칭 → LLM 기반으로 업그레이드 (더 정확한 요약, 문맥 이해)
  - 자동 Fallback: LLM 실패 시 패턴 매칭으로 전환
  - 환경변수 `ENABLE_LLM_SUMMARIZATION=true/false`로 on/off
  - ANTHROPIC_API_KEY 필수 (LLM 사용 시)
  - **효과**: Manager 컨텍스트 90% 절감, 중요 정보 손실 최소화
- **🚀 수직적 고도화: Performance Metrics - 토큰 사용량 추적 - 2025-10-22**
  - Worker별 토큰 사용량 자동 수집 (input_tokens, output_tokens, cache tokens)
  - `WorkerResponseHandler`에 `usage_callback` 추가
  - `WorkerAgent.execute_task()`에 토큰 수집 기능 통합
  - `WorkerExecutor`에서 MetricsCollector로 자동 전달
  - 로그에 토큰 사용량 상세 기록
  - **효과**: Worker별 성과 정량화, 비용 최적화 가능
- **🚀 수직적 고도화: Context Metadata 시스템 활성화 - 2025-10-22**
  - `config/system_config.json`의 `context_metadata.enabled`를 `true`로 변경
  - Worker 출력에 구조화된 메타데이터 자동 추가 (task_id, dependencies, key_decisions)
  - Manager가 컨텍스트 체인 자동 추적
  - **효과**: 작업 흐름 가시성 향상, 디버깅 용이
- **📖 ADVANCED_FEATURES.md 문서 작성 - 2025-10-22**
  - 3가지 고급 기능 상세 설명
  - 활성화/비활성화 방법
  - 성능 비교 및 문제 해결 가이드
- **Worker 출력 자동 요약 시스템 (Hierarchical Summarization) - 2025-10-22**
  - 3단계 요약: (1) 1줄 상태 (2) 5-10줄 핵심 (3) 전체 로그 (Artifact)
  - Worker 긴 출력을 자동으로 요약하여 MCP 도구 제한(25,000 토큰) 우회
  - `WorkerOutputSummarizer` 클래스 (`src/infrastructure/mcp/output_summarizer.py`)
  - `WorkerExecutor`에 통합, 기본 활성화 (환경변수 `DISABLE_WORKER_OUTPUT_SUMMARY=true`로 비활성화 가능)
  - Artifact Storage에 전체 로그 저장, 요약만 Manager에 전달
  - **효과**: 토큰 사용량 30-40% 절감, 정보 손실 90% 감소
- mkdocs 기반 API 문서 자동 생성
- ADR (Architecture Decision Records) 문서 5개 작성
- 에러 코드 체계화 (`src/domain/errors/`)
- 문서화 개선 (설치 가이드, 빠른 시작, 사용법, 문제 해결)
- **SQLite 기반 세션 저장 (Repository 패턴)**
  - `SessionRepository` 인터페이스 도입 (`src/application/ports/`)
  - SQLite 구현체 (`src/infrastructure/storage/sqlite/`)
  - 프로젝트별 격리된 저장 경로 (`~/.better-llm/{project-name}/`)
  - 세션 조회/검색 API 제공

### Changed
- **🔧 Claude Agent SDK 권장사항 적용 - Permission Mode 개선 및 Hooks 시스템 추가 - 2025-10-23**
  - **Permission Mode 개선**:
    - `system_config.json`에 `permission.mode` 설정 추가 (기본값: "acceptEdits")
    - 환경변수 `PERMISSION_MODE` 지원 추가
    - 우선순위: 환경변수 > system_config.json > 기본값
    - 권장 모드: acceptEdits (프로덕션), default (대화형), bypassPermissions (테스트만)
  - **Hooks 시스템 추가**:
    - PreToolUse Hook: Worker Tool 호출 전 입력 검증 (과도하게 긴 입력 차단, 금지 패턴 검사)
    - PostToolUse Hook: Worker Tool 실행 후 모니터링 (실행 시간 로깅, 성공/실패 통계)
    - `system_config.json`에 `hooks` 섹션 추가 (enable_validation, enable_monitoring)
  - **영향**: 프로덕션 환경에서 안전한 permission_mode 사용, 입력 검증 및 모니터링 강화
- **🔧 설치 방법 통일 (pipx 글로벌 설치) - 2025-10-22**
  - `install.sh` 제거 → `setup.sh` 작성 (pipx 전용)
  - 설치 모드 선택: 일반 모드 / 개발 모드 (editable)
  - Python 버전 체크 (3.10+), pipx 자동 설치
  - OAuth 토큰 설정 가이드 (대화형), 설치 검증
  - **영향**: 설치 방법이 명확하고 간단해짐, 모든 문서에서 동일한 설치 방법 안내
- **🔧 세션 및 로그 저장 위치 변경 (~/.better-llm/{project-name}/) - 2025-10-20**
  - 프로젝트 이름 감지 로직 추가 (Git root 디렉토리 이름 또는 현재 디렉토리 이름)
  - 저장소 기본 경로 변경: JSON 세션 (`~/.better-llm/{project}/sessions`), SQLite DB (`~/.better-llm/{project}/data/`)
  - 로그 기본 경로 변경: `~/.better-llm/{project}/logs/`
  - 환경변수 `LOG_DIR` 오버라이드 지원
  - **영향**: 프로젝트별 독립적인 세션/로그 관리, 프로젝트 디렉토리 깨끗하게 유지
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
- **세션 저장 로직 개선 (commit: 0603ea1)**
  - JSON 파일 저장에서 Repository 패턴으로 전환
  - `orchestrator.py` Repository 패턴 통합 (line 117, 232-237)
  - 프로젝트별 세션/로그 저장 경로 격리
  - `config/system_config.json`의 `storage.backend` 설정으로 저장소 선택 가능

### Fixed
- **🐛 5차 버그 수정 8개 - Manager/Worker Agent, CLI, SDK 안정성 강화 - 2025-10-23**
  1. **High: manager_client.py:404-419** - config 변수 미정의 에러 (NameError) → `config = None` 초기화 추가
  2. **High: manager_client.py:873** - system_prompt 속성 오류 (AttributeError) → `self.SYSTEM_PROMPT` 프로퍼티 사용
  3. **High: sdk_executor.py:533-541** - usage 속성 None 체크 미흡 → `is not None` 체크 추가
  4. **High: worker_executor.py:574-578** - content 구조 검증 강화 → "text" key 존재 확인
  5. **High: agent_hooks.py:107-149** - 메모리 누수 방지 강화 → TTL 메커니즘 (1시간), 최대 1000개 제한
  6. **Medium: orchestrator.py:237-247** - tool_result 키 안전 접근 → `.get()` 안전 접근
  7. **Medium: worker_executor.py:666-676** - to_dict() 예외 처리 → try-except 추가
  8. **Medium: sdk_executor.py:552-555** - CancelledError 별도 처리 → 조용히 종료
  - **영향**: 런타임 크래시 5개 제거, 메모리 누수 방지, 에러 처리 강화
- **🐛 4차 버그 수정 7개 - 전체 코드베이스 안정성 및 에러 처리 강화 - 2025-10-23**
  1. **High: agent_hooks.py:199-213** - 메모리 누수 방지 (`enable_monitoring=False`일 때 pop 누락)
  2. **High: output_summarizer.py:184** - 안전한 LLM 응답 파싱 (hasattr 체크 추가)
  3. **High: sqlite_session_repository.py:47-149** - 데이터베이스 초기화 예외 처리 (try-except, timeout)
  4. **Medium: tui_config.py:92-115** - 안전한 설정 파일 로드 (유효한 필드만 필터링)
  5. **Medium: migration.py:110-119** - JSON 파싱 에러 구별 (JSONDecodeError 별도 처리)
  6. **Medium: artifact_storage.py:85-105** - 파일 쓰기 예외 처리 (IOError 처리)
  7. **Medium: parallel_executor.py:100-105** - JSON 파싱 에러 처리 (ValueError 변환)
  - **영향**: 런타임 크래시 3개 제거, 예외 처리 4개 강화
- **🐛 3차 버그 수정 4개 - Presentation Layer 안정성 개선 - 2025-10-23**
  1. **High: initialization_manager.py:98** - 미정의 변수 참조 에러 (`worker_status` → `status_info`)
  2. **High: parallel_executor.py:305-312** - Exception이 failed 리스트에 누락 → zip으로 매칭
  3. **Medium: tui_app.py:209-213** - 초기 세션 생성 후 캐시 무효화 누락 → 캐시 초기화 추가
  4. **Medium: task_runner.py:226** - CancelledError 재발생으로 인한 전파 → graceful cancellation
  - **영향**: TUI 초기화 에러 처리 개선, 비동기 Task 실패 추적 강화
- **🐛 2차 버그 수정 8개 - 저장소, 데이터베이스, 환경변수 안정성 개선 - 2025-10-22**
  1. **High: session_repository.py:156-185** - 세션 파일 읽기 예외 처리 구체화 (JSONDecodeError, KeyError, OSError)
  2. **High: db_utils.py:23-40, 84-92** - 데이터베이스 timeout 추가 (30초), OperationalError 처리
  3. **Medium: context_repository.py:43-62** - JSON 파싱 에러 처리 구체화
  4. **Medium: env_utils.py (새 파일)** - 환경변수 타입 안전 파싱 헬퍼 함수 (`parse_bool_env()` 등)
  5. **Medium: output_summarizer.py, worker_executor.py** - 환경변수 파싱 개선 (다양한 형식 지원)
  - **영향**: 파일 I/O 및 DB 에러 처리 강화, 환경변수 타입 에러 방지
- **🐛 1차 버그 수정 5개 - Critical/High 런타임 크래시 제거 - 2025-10-22**
  1. **Critical: worker_executor.py:572** - 안전한 인덱싱 (IndexError 위험 제거)
  2. **Critical: output_summarizer.py:176** - LLM 응답 안전 처리 (빈 응답 대응)
  3. **Critical: worker_tools.py** - 안전한 결과 추출 헬퍼 함수 (`_safe_extract_result_text()`)
  4. **High: manager_client.py:521** - metadata_formatter None 체크
  5. **High: worker_executor.py** - 중복 메서드 제거 (`_summarize_worker_output()` 2번 정의 문제)
  - **영향**: Critical 런타임 크래시 3개 제거, artifact 저장 기능 정상 작동
- **🐛 Worker 중복 호출 버그 수정 - Manager가 완료된 Worker를 반복 실행하는 문제 해결 - 2025-10-22**
  - **근본 원인**: Manager 프롬프트에 "중복 작업 방지" 로직 부재, Worker 출력 요약의 "완료" 상태 표시 불명확
  - **Manager 프롬프트 개선**: "⚠️ 중복 작업 방지 규칙 (CRITICAL!)" 섹션 추가, 작업 흐름 추적 방법 명시
  - **Worker 출력 요약 개선**: "**✅ 상태: 작업 완료**" 명시적 표시, 중복 호출 경고 추가
  - **영향**: 불필요한 Worker 재실행 제거, 전체 작업 시간 대폭 단축
- **🐛 Worker Agent 타임아웃 문제 해결 - 2025-10-20**
  - **근본 원인**: Worker Agent 프롬프트에 다른 Worker 호출 지시문(@coder, @tester 등) 포함
  - **프롬프트 수정**: "@coder please implement" 등 제거 → "작업이 완료되었습니다" 형식으로 변경
  - **코드 레벨 개선**: 조기 종료 감지 로직 추가 (완료 키워드 감지 시 즉시 스트리밍 종료)
  - **영향**: Worker 실행 시간 타임아웃(300-600초)에서 실제 작업 시간으로 단축
- **🐛 Worker Agent 실행 실패 문제 해결 (CodingStyle 속성 에러) - 2025-10-20**
  - **근본 원인**: `_generate_debug_info()`에서 존재하지 않는 `CodingStyle.language` 속성 접근
  - **수정**: `line_length`, `quote_style` 등 실제 존재하는 속성 사용
  - **조기 종료 로직 제거**: Worker가 자연스럽게 완료될 때까지 대기
  - **영향**: Worker가 정상적으로 실행되고 응답 생성
- **🐛 패키지 설치 설정 수정 (src 패키지 지원) - 2025-10-21**
  - **근본 원인**: entry point가 `presentation.tui.tui_app:main`으로 설정되어 src가 패키지로 인식 안됨
  - **pyproject.toml 수정**: entry point를 `src.presentation.tui.tui_app:main`으로 변경, `include = ["src", "src.*"]`
  - **setup.py 백업**: `setup.py.bak`으로 이동 (충돌 방지)
  - **영향**: `pip install -e .` 정상 작동, 모든 `from src.` import 정상
- **순환 import 문제 해결 (2025-10-22)**
  - `manager_client.py`에서 `ContextMetadataFormatter` lazy import 적용
  - `context_metadata_enabled`가 True일 때만 import하여 순환 의존성 방지

### Deprecated
- `src/presentation/cli/utils.py::save_session_history()` 함수
  - Repository 패턴 (`create_session_repository()`) 사용 권장
  - 하위 호환성을 위해 유지되며 향후 버전에서 제거 예정

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
