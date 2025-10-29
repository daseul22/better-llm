# Claude Flow

> 여러 Claude 에이전트가 협업하여 복잡한 소프트웨어 개발 작업을 자동화하는 오케스트레이션 시스템

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ 주요 특징

### 🏗️ Clean Architecture 기반
- **4-Layer 구조**: Domain, Application, Infrastructure, Presentation
- **의존성 역전**: 테스트 가능하고 확장 가능한 설계
- **타입 안전성**: 완전한 Type Hints 적용

### 🤖 Multi-Agent 협업
- **Planner**: 요구사항 분석 및 계획 수립
- **Coder**: 코드 작성 및 수정
- **Reviewer**: 코드 리뷰 및 품질 검증
- **Tester**: 테스트 실행 및 검증
- **Committer**: Git 커밋 및 PR 생성
- **Ideator**: 창의적 아이디어 생성
- **Product Manager**: 제품 기획 및 요구사항 정의

### 🔧 MCP (Model Context Protocol)
- Anthropic 표준 프로토콜 사용
- Manager Agent가 Worker Tools를 자동 호출
- 타입 안전한 Tool 인터페이스

### ⚡ 성능 최적화
- **프롬프트 캐싱**: API 호출 30-50% 절감
- **세션 압축**: 디스크 공간 30-50% 절감
- **백그라운드 저장**: 저장 시간 70% 단축
- **비동기 메트릭**: 메인 워크플로우 블로킹 제거
- **🚀 LLM 기반 Intelligent Summarizer**: Manager 컨텍스트 **90% 절감**, 중요 정보 손실 최소화
- **🚀 Performance Metrics**: Worker별 토큰 사용량 자동 추적, 비용 최적화
- **🚀 Context Metadata**: 작업 흐름 자동 추적, 디버깅 용이

### 📊 관찰 가능성 (Observability)
- **구조화된 로깅**: Structlog 기반 JSON 로깅
- **비동기 메트릭 수집**: 백그라운드 메트릭 처리
- **실시간 에러 추적**: 스레드 안전 에러 통계
- **TUI 워크플로우 시각화**: 실시간 Agent 상태 모니터링

---

## 🚀 빠른 시작

### 1. 설치

**pipx를 사용한 글로벌 설치 (권장):**

```bash
git clone https://github.com/simdaseul/claude-flow.git
cd claude-flow
./setup.sh
```

설치 스크립트가 자동으로:
- Python 3.10+ 버전 확인
- pipx 설치 (필요시)
- 설치 모드 선택 (일반/개발)
- claude-flow 설치
- 환경 변수 설정 안내
- 설치 검증

**수동 설치:**

```bash
# pipx 설치 (없는 경우)
brew install pipx  # macOS
# 또는
python3 -m pip install --user pipx

# claude-flow 설치
pipx install .           # 일반 모드
pipx install -e .        # 개발 모드 (코드 변경 시 바로 반영)
```

### 2. 환경 변수 설정

```bash
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'
```

또는 `.env` 파일 생성:

```bash
echo "CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here" > .env
```

### 3. 실행

#### TUI (Terminal User Interface) - 권장

```bash
claude-flow
```

**특징**: 대화형 터미널 UI, 실시간 로그 표시, 세션 관리

#### Web UI (Workflow Canvas) - NEW! 🎨

```bash
# 하나의 명령어로 모든 것 실행 (백엔드 + 프론트엔드)
claude-flow-web
```

**특징**:
- 🎯 드래그 앤 드롭으로 Worker Agent 배치
- 🔗 노드 간 연결로 데이터 흐름 정의
- ⚡ 실시간 실행 상태 표시
- 💾 워크플로우 저장/불러오기
- 🔄 자동 프론트엔드 의존성 설치

**접속**: http://localhost:5173 (자동 리다이렉트)

**레거시 UI**: http://127.0.0.1:8000/legacy (단일 Worker 실행)

#### CLI (Command Line Interface)

```bash
claude-flow-cli "FastAPI로 /users CRUD 엔드포인트 구현해줘"
```

**특징**: 스크립트 자동화, 단일 명령 실행

---

## 📖 문서

전체 문서는 [**docs/index.md**](docs/index.md)를 참조하세요.

### 빠른 링크

- [**🎨 Workflow Canvas 가이드**](docs/workflow-canvas-guide.md) - **NEW!** 웹 UI 워크플로우 에디터
- [**🌐 웹 사용 가이드**](docs/web-usage.md) - **NEW!** claude-flow-web 사용법 (워크플로우 캔버스 + 레거시 UI)
- [**⚡ 빠른 시작 (웹)**](docs/quickstart-web.md) - **NEW!** 5분 안에 시작하기
- [**🚀 고급 기능 (Advanced Features)**](ADVANCED_FEATURES.md) - LLM 기반 요약, Performance Metrics, Context Metadata
- [**설치 가이드**](docs/guides/installation.md) - 상세한 설치 방법
- [**사용법**](docs/guides/usage.md) - TUI/CLI 사용법, 고급 기능
- [**사용 사례**](docs/guides/use_cases.md) - 실전 시나리오별 활용법
- [**아키텍처**](docs/architecture.md) - 시스템 설계 및 구조
- [**문제 해결**](docs/troubleshooting.md) - 일반적인 문제 및 해결 방법

### 개발자 문서

- [**ADR (Architecture Decision Records)**](docs/adr/0001-clean-architecture.md) - 설계 결정 배경
- [**API Reference**](docs/api/domain/models.md) - 코드 레벨 API 문서
- [**개발 히스토리**](docs/development/history.md) - 개발 과정 기록
- [**기여 가이드**](CONTRIBUTING.md) - 기여 방법

---

## 🎯 사용 예시

### 신규 기능 개발

```bash
claude-flow-cli "FastAPI로 JWT 기반 사용자 인증 시스템 구현해줘. /login, /register, /me 엔드포인트 필요해."
```

**워크플로우:**
1. **Planner**: 요구사항 분석 및 구현 계획 수립
2. **Coder**: 계획에 따라 코드 작성
3. **Reviewer**: 코드 품질 검토
4. **Tester**: 테스트 실행 및 검증
5. **완료**: 결과 반환

### 버그 수정

```bash
claude-flow-cli "로그인 API에서 500 에러 발생. routes/auth.py의 login 함수에서 NoneType 에러. 원인 찾고 수정해줘."
```

### 코드 리팩토링

```bash
claude-flow-cli "payment.py 모듈을 클래스 기반으로 리팩토링해줘. 단일 책임 원칙 적용하고, 테스트도 같이 리팩토링해야 해."
```

---

## 🛠️ 시스템 요구사항

- **Python**: 3.10 이상
- **운영체제**: macOS, Linux, Windows (WSL 권장)
- **API 키**: Anthropic API 키 또는 Claude Code OAuth 토큰
- **메모리**: 최소 4GB RAM
- **디스크 공간**: 500MB 이상

---

## 🏗️ 프로젝트 구조

```
claude-flow/
├── src/                    # 소스 코드
│   ├── domain/            # Domain Layer (순수 Python)
│   ├── application/       # Application Layer (Use Cases)
│   ├── infrastructure/    # Infrastructure Layer (외부 의존성)
│   └── presentation/      # Presentation Layer (CLI, TUI)
├── config/                # 설정 파일
│   ├── agent_config.json  # Worker Agent 설정
│   └── system_config.json # 시스템 설정
├── prompts/               # Worker Agent 시스템 프롬프트
│   ├── planner.txt
│   ├── coder.txt
│   ├── reviewer.txt
│   └── tester.txt
├── docs/                  # 문서
│   ├── guides/           # 사용자 가이드
│   ├── development/      # 개발 문서
│   ├── adr/              # Architecture Decision Records
│   └── api/              # API Reference
├── tests/                 # 테스트
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── sessions/              # 세션 히스토리 (자동 생성)
```

---

## 🤝 기여하기

Claude Flow는 오픈소스 프로젝트입니다. 기여를 환영합니다!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

자세한 내용은 [**CONTRIBUTING.md**](CONTRIBUTING.md)를 참조하세요.

---

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [**LICENSE**](LICENSE)를 참조하세요.

---

## 📞 문의 및 지원

- **GitHub Issues**: [https://github.com/simdaseul/claude-flow/issues](https://github.com/simdaseul/claude-flow/issues)
- **Discussions**: [https://github.com/simdaseul/claude-flow/discussions](https://github.com/simdaseul/claude-flow/discussions)

---

## 🙏 감사의 말

- [Anthropic](https://www.anthropic.com/) - Claude API 및 Agent SDK 제공
- [Textual](https://textual.textualize.io/) - 아름다운 TUI 프레임워크
- 모든 기여자 및 사용자분들께 감사드립니다!

---

**Made with ❤️ using Claude API**
