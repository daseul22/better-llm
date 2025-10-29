# Claude Flow

<div align="center">

**워크플로우 기반 AI 개발 자동화 시스템**

전문화된 AI Agent를 노드로 연결하여 복잡한 소프트웨어 개발 작업을 자동화합니다

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Agent SDK](https://img.shields.io/badge/Claude-Agent%20SDK-5A67D8)](https://docs.anthropic.com/en/docs/claude-code/sdk)

[빠른 시작](#-빠른-시작) • [문서](docs/index.md) • [예시](#-사용-예시) • [기여하기](#-기여하기)

</div>

---

## 🎯 주요 특징

### 🎨 비주얼 워크플로우 에디터 (Web UI)

<div align="center">

**드래그 앤 드롭으로 AI 워크플로우를 구성하세요**

</div>

- **노드 기반 설계**: Worker Agent를 노드로 배치하고 연결
- **실시간 실행**: 각 노드의 진행 상황을 실시간으로 모니터링
- **Manager 노드**: 여러 Worker를 병렬로 실행하여 **20-50% 속도 향상**
- **워크플로우 저장**: 재사용 가능한 워크플로우를 저장하고 공유
- **템플릿 변수**: `{{input}}`, `{{parent}}`, `{{node_<id>}}`로 동적 데이터 전달

```
Input 노드 → Planner → Coder → Reviewer → Tester → Committer
            ↓
         Manager (병렬 실행)
         ├─ Security Reviewer
         ├─ Architecture Reviewer
         └─ Style Reviewer
```

### 🤖 전문화된 Worker Agent

각 Agent는 특정 역할에 최적화되어 있습니다:

| Worker | 역할 | 주요 도구 |
|--------|------|-----------|
| **Planner** | 요구사항 분석 및 계획 수립 | read, glob |
| **Coder** | 코드 작성 및 수정 | read, write, edit, glob, grep |
| **Reviewer** | 코드 리뷰 및 품질 검증 | read, glob, grep |
| **Tester** | 테스트 실행 및 검증 | read, bash, glob |
| **Committer** | Git 커밋 및 PR 생성 | bash, read |
| **Ideator** | 창의적 아이디어 생성 | read |
| **Product Manager** | 제품 기획 및 요구사항 정의 | read |

**+ 커스텀 워커**: Web UI에서 AI가 도와주는 커스텀 워커 생성 기능 제공

### 🏗️ Clean Architecture

- **4계층 구조**: Domain → Application → Infrastructure → Presentation
- **의존성 역전**: 테스트 가능하고 확장 가능한 설계
- **타입 안전성**: 전체 코드베이스에 Type Hints 적용

### ⚡ 성능 최적화

- **LLM 기반 Intelligent Summarizer**: Manager 컨텍스트 **90% 절감**
- **프롬프트 캐싱**: API 호출 30-50% 절감
- **병렬 실행**: Manager 노드로 여러 Worker 동시 실행
- **백그라운드 저장**: 저장 시간 70% 단축
- **비동기 메트릭**: 메인 워크플로우 블로킹 제거

---

## 🚀 빠른 시작

### 1️⃣ 설치

**자동 설치 (권장):**

```bash
git clone https://github.com/simdaseul/claude-flow.git
cd claude-flow
./setup.sh
```

설치 스크립트가 자동으로 처리합니다:
- Python 3.10+ 버전 확인
- pipx 설치 (필요시)
- claude-flow 설치
- 환경 변수 설정 안내

**수동 설치:**

```bash
# pipx 설치
brew install pipx  # macOS
# 또는
python3 -m pip install --user pipx

# claude-flow 설치
pipx install .           # 일반 모드
pipx install -e .        # 개발 모드 (코드 변경 즉시 반영)
```

### 2️⃣ 환경 변수 설정

```bash
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'
```

또는 `.env` 파일 생성:

```bash
echo "CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here" > .env
```

> **OAuth 토큰 발급**: [Claude Code 문서](https://docs.claude.com/en/docs/claude-code/getting-started) 참조

### 3️⃣ 실행

#### 🎨 Web UI (워크플로우 캔버스) - **권장**

```bash
claude-flow-web
```

브라우저에서 **http://localhost:5173** 열기

**기능:**
- 드래그 앤 드롭으로 워크플로우 구성
- 노드 간 연결로 데이터 흐름 정의
- 실시간 실행 상태 확인
- 워크플로우 저장/불러오기
- 커스텀 워커 생성

#### 🖥️ TUI (터미널 UI)

```bash
claude-flow
```

**기능:**
- 대화형 터미널 인터페이스
- 실시간 로그 표시
- 세션 관리

#### ⌨️ CLI (명령줄 인터페이스)

```bash
claude-flow-cli "FastAPI로 /users CRUD 엔드포인트 구현해줘"
```

**기능:**
- 단일 명령 실행
- 스크립트 자동화

---

## 📖 사용 예시

### 예시 1: 신규 기능 개발

**요구사항**: JWT 기반 사용자 인증 시스템 구현

**Web UI 워크플로우:**

```
Input → Planner → Coder → Reviewer → Tester → Committer
```

**실행 흐름:**
1. **Input**: "FastAPI로 JWT 기반 사용자 인증 시스템 구현. /login, /register, /me 엔드포인트 필요"
2. **Planner**: 요구사항 분석 및 구현 계획 수립
3. **Coder**: 계획에 따라 코드 작성 (auth.py, models.py, routes.py)
4. **Reviewer**: 코드 품질 및 보안 검토
5. **Tester**: pytest로 테스트 실행 및 검증
6. **Committer**: Git 커밋 및 PR 생성

### 예시 2: 코드 리뷰 (병렬 실행)

**요구사항**: 다양한 관점에서 코드 리뷰

**Web UI 워크플로우:**

```
Input → Manager (병렬 실행)
         ├─ Security Reviewer    → Merge → Output
         ├─ Architecture Reviewer
         └─ Style Reviewer
```

**장점:**
- **속도**: 3개의 리뷰를 동시에 실행 (3배 빠름)
- **관점**: 보안, 아키텍처, 스타일을 각각 전문화된 Agent가 검토
- **통합**: Merge 노드로 모든 리뷰 결과를 하나로 통합

### 예시 3: 반복 작업 (Loop 노드)

**요구사항**: 테스트가 통과할 때까지 코드 수정 반복

**Web UI 워크플로우:**

```
Input → Coder → Tester → Condition (성공?)
                  ↑         ├─ True → Committer
                  └─────────└─ False (Loop)
```

---

## 🛠️ 시스템 요구사항

| 항목 | 요구사항 |
|------|----------|
| **Python** | 3.10 이상 |
| **운영체제** | macOS, Linux, Windows (WSL 권장) |
| **API 키** | Anthropic API 키 또는 Claude Code OAuth 토큰 |
| **메모리** | 최소 4GB RAM |
| **디스크** | 500MB 이상 |

---

## 📂 프로젝트 구조

```
claude-flow/
├── src/                           # 소스 코드
│   ├── domain/                   # Domain Layer (순수 Python)
│   │   ├── models/              # Message, AgentConfig, Task
│   │   ├── services/            # ConversationHistory, ProjectContext
│   │   └── agents/              # BaseAgent (인터페이스)
│   ├── application/              # Application Layer (Use Cases)
│   │   └── ports/               # IAgentClient, IConfigLoader
│   ├── infrastructure/           # Infrastructure Layer (외부 의존성)
│   │   ├── claude/              # Manager/Worker Agent 클라이언트
│   │   ├── mcp/                 # Worker Tools MCP Server
│   │   ├── storage/             # JSON/SQLite 저장소
│   │   └── config/              # 설정 로더, 환경 검증
│   └── presentation/             # Presentation Layer (UI)
│       ├── cli/                 # CLI 인터페이스
│       ├── tui/                 # TUI 인터페이스 (Textual)
│       └── web/                 # Web UI (FastAPI + React)
├── config/                       # 설정 파일
│   ├── agent_config.json        # Worker Agent 설정
│   └── system_config.json       # 시스템 설정
├── prompts/                      # Worker Agent 시스템 프롬프트
│   ├── planner.txt
│   ├── coder.txt
│   ├── reviewer.txt
│   └── ...
├── docs/                         # 문서
│   ├── guides/                  # 사용자 가이드
│   ├── adr/                     # Architecture Decision Records
│   └── api/                     # API Reference
└── tests/                        # 테스트
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## 📚 문서

### 사용자 가이드

- [**🎨 Workflow Canvas 가이드**](docs/workflow-canvas-guide.md) - 웹 UI 워크플로우 에디터 사용법
- [**⚡ 빠른 시작 (웹)**](docs/quickstart-web.md) - 5분 안에 시작하기
- [**🌐 웹 사용 가이드**](docs/web-usage.md) - claude-flow-web 상세 사용법
- [**📖 사용법**](docs/guides/usage.md) - TUI/CLI 사용법
- [**💡 사용 사례**](docs/guides/use_cases.md) - 실전 시나리오별 활용법
- [**🔧 문제 해결**](docs/troubleshooting.md) - 일반적인 문제 및 해결 방법

### 개발자 가이드

- [**🏗️ 아키텍처**](docs/architecture.md) - 시스템 설계 및 구조
- [**🚀 고급 기능**](ADVANCED_FEATURES.md) - LLM 기반 요약, Performance Metrics
- [**📝 ADR**](docs/adr/0001-clean-architecture.md) - Architecture Decision Records
- [**🔌 API Reference**](docs/api/domain/models.md) - 코드 레벨 API 문서
- [**🤝 기여 가이드**](CONTRIBUTING.md) - 기여 방법

---

## 🤝 기여하기

Claude Flow는 오픈소스 프로젝트입니다. 모든 기여를 환영합니다!

### 기여 방법

1. Fork the repository
2. Create your feature branch
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. Commit your changes (Conventional Commits 사용)
   ```bash
   git commit -m 'feat: Add some amazing feature'
   ```
4. Push to the branch
   ```bash
   git push origin feature/amazing-feature
   ```
5. Open a Pull Request

### 개발 환경 설정

```bash
# 저장소 클론
git clone https://github.com/simdaseul/claude-flow.git
cd claude-flow

# 개발 모드로 설치
pipx install -e .

# 개발 의존성 설치
pipx inject claude-flow pytest pytest-asyncio black ruff

# 테스트 실행
pytest
```

자세한 내용은 [**CONTRIBUTING.md**](CONTRIBUTING.md)를 참조하세요.

---

## 🐛 버그 리포트 & 기능 요청

- **버그 리포트**: [GitHub Issues](https://github.com/simdaseul/claude-flow/issues)
- **기능 요청**: [GitHub Discussions](https://github.com/simdaseul/claude-flow/discussions)
- **질문**: [Discussions Q&A](https://github.com/simdaseul/claude-flow/discussions/categories/q-a)

---

## 📝 라이선스

이 프로젝트는 **MIT 라이선스** 하에 배포됩니다. 자유롭게 사용, 수정, 배포할 수 있습니다.

자세한 내용은 [**LICENSE**](LICENSE) 파일을 참조하세요.

---

## 🙏 감사의 말

Claude Flow는 다음 프로젝트들의 도움으로 만들어졌습니다:

- [**Anthropic**](https://www.anthropic.com/) - Claude API 및 Agent SDK 제공
- [**Textual**](https://textual.textualize.io/) - 아름다운 TUI 프레임워크
- [**FastAPI**](https://fastapi.tiangolo.com/) - 현대적인 웹 프레임워크
- [**React Flow**](https://reactflow.dev/) - 노드 기반 워크플로우 에디터

그리고 모든 기여자 및 사용자분들께 진심으로 감사드립니다! 🙇

---

## 🌟 Star History

이 프로젝트가 도움이 되었다면 ⭐️ Star를 눌러주세요!

---

<div align="center">

**Made with ❤️ using Claude API**

[시작하기](#-빠른-시작) • [문서](docs/index.md) • [기여하기](#-기여하기)

</div>
