# 그룹 챗 오케스트레이션 시스템 (MVP v0.1)

여러 Claude 에이전트가 하나의 대화 공간에서 협업하여 복잡한 소프트웨어 개발 작업을 자동화하는 오케스트레이션 시스템입니다.

## 특징

- **특수화된 에이전트**: 계획(Planner), 구현(Coder), 테스트(Tester) 역할 분리
- **자동 라우팅**: 키워드 기반 및 순차 진행 규칙으로 에이전트 자동 선택
- **Human-in-the-loop**: 언제든 사용자 개입 가능
- **대화 히스토리**: 모든 에이전트가 공유 컨텍스트에서 협업
- **CLI 인터페이스**: 간단하고 직관적인 명령줄 인터페이스

## 시스템 요구사항

- Python 3.10 이상
- Anthropic API 키

## 설치

### 1. 저장소 클론 및 이동

```bash
cd /path/to/better-llm
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

또는 `.env` 파일 생성:

```bash
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

## 사용법

### 방법 1: 웹 UI (권장) 🌐

```bash
streamlit run app.py
```

브라우저에서 http://localhost:8501 로 접속하세요.

**웹 UI 기능:**
- 🖥️ 사용자 친화적인 인터페이스
- 📊 실시간 스트리밍 출력
- 📜 세션 히스토리 조회
- 🔄 새 세션 시작
- 💾 자동 세션 저장

### 방법 2: CLI (Command Line Interface)

```bash
python orchestrator.py "작업 설명"
```

### 예시

```bash
# 신규 기능 개발
python orchestrator.py "FastAPI로 /users CRUD 엔드포인트 구현해줘"

# 버그 수정
python orchestrator.py "로그인 API에서 500 에러 나는 버그 수정해줘"

# 리팩토링
python orchestrator.py "payment.py 모듈을 클래스 기반으로 리팩토링해줘"
```

### 옵션

```bash
# 상세 로깅 활성화
python orchestrator.py --verbose "작업 설명"

# 커스텀 설정 파일 사용
python orchestrator.py --config custom_config.json "작업 설명"

# 도움말
python orchestrator.py --help
```

## 사용자 개입

각 에이전트 응답 후 5초 대기하며, 다음 옵션을 선택할 수 있습니다:

- **Enter**: 다음 에이전트로 자동 진행
- **/pause**: 일시정지하고 메시지 입력
- **/stop**: 즉시 종료

## 작업 흐름

일반적인 작업은 다음과 같이 진행됩니다:

```
사용자 요청
    ↓
[1] 🧠 Planner: 요구사항 분석 및 계획 수립
    ↓
[2] 💻 Coder: 코드 작성/수정
    ↓
[3] 🧪 Tester: 테스트 실행 및 검증
    ↓
작업 완료 (TERMINATE)
```

### 에이전트 명시 요청

메시지에 `@agent_name`을 포함하여 특정 에이전트를 직접 호출할 수 있습니다:

```
@coder 결제 모듈에 refund 함수 추가해줘
@tester 통합 테스트도 실행해줘
```

## 프로젝트 구조

```
better-llm/
├── orchestrator.py          # 메인 실행 파일
├── requirements.txt         # 의존성
├── README.md                # 이 파일
├── config/
│   └── agent_config.json    # 에이전트 설정
├── prompts/
│   ├── planner.txt          # Planner 시스템 프롬프트
│   ├── coder.txt            # Coder 시스템 프롬프트
│   └── tester.txt           # Tester 시스템 프롬프트
├── src/
│   ├── __init__.py
│   ├── models.py            # 데이터 모델
│   ├── agents.py            # Agent 클래스
│   ├── chat_manager.py      # 라우팅 로직
│   ├── conversation.py      # 대화 히스토리
│   └── utils.py             # 유틸리티
├── tests/                   # 테스트 (TODO)
└── sessions/                # 세션 히스토리 저장
```

## 설정

### 에이전트 설정 (config/agent_config.json)

```json
{
  "agents": [
    {
      "name": "planner",
      "role": "계획 수립",
      "system_prompt_file": "prompts/planner.txt",
      "tools": ["read", "glob"],
      "model": "claude-sonnet-4"
    }
  ]
}
```

### 시스템 프롬프트 커스터마이징

`prompts/` 디렉토리의 `.txt` 파일을 수정하여 각 에이전트의 행동을 변경할 수 있습니다.

## 세션 히스토리

각 작업 완료 후 `sessions/` 디렉토리에 JSON 파일로 저장됩니다:

```json
{
  "session_id": "abc123",
  "created_at": "2025-01-18T10:23:45Z",
  "completed_at": "2025-01-18T10:24:30Z",
  "user_request": "작업 설명",
  "total_turns": 3,
  "agents_used": ["planner", "coder", "tester"],
  "messages": [...],
  "result": {
    "status": "completed",
    "tests_passed": true
  }
}
```

## 제약사항

- **순차 실행**: 병렬 에이전트 실행 미지원 (v0.2에서 지원 예정)
- **메모리 내 저장**: 프로세스 종료 시 히스토리 휘발 (JSON 파일 제외)
- **최대 턴 수**: 50턴 제한 (무한 루프 방지)
- **컨텍스트 길이**: 50 메시지 제한

## 문제 해결

### API 키 에러

```
ValueError: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.
```

→ 환경 변수를 확인하세요: `echo $ANTHROPIC_API_KEY`

### 설정 파일 에러

```
FileNotFoundError: 설정 파일을 찾을 수 없습니다
```

→ `config/agent_config.json` 파일이 존재하는지 확인하세요.

### 프롬프트 파일 로드 실패

```
⚠️  프롬프트 파일 없음: prompts/planner.txt
```

→ `prompts/` 디렉토리에 필요한 `.txt` 파일이 있는지 확인하세요.

## 향후 계획 (Roadmap)

### v0.2 (Enhanced)
- [ ] 에러 핸들링 및 자동 재시도
- [ ] LLM 기반 동적 라우팅
- [ ] 대화 히스토리 영속화 (SQLite)
- [ ] 추가 에이전트 (Reviewer, DevOps)

### v0.3 (Advanced)
- [ ] 병렬 에이전트 실행
- [ ] 웹 UI (실시간 대시보드)
- [ ] 에이전트 성능 메트릭
- [ ] 커스텀 에이전트 추가 지원

## 라이선스

MIT License

## 문의

이슈나 질문은 GitHub Issues를 사용해주세요.

---

**Made with ❤️ using Claude API**
