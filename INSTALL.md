# 설치 가이드

그룹 챗 오케스트레이션 시스템을 설치하고 실행하는 방법입니다.

## 빠른 시작

### 1. 가상 환경 생성 및 활성화

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 또는
.venv\Scripts\activate  # Windows
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

Anthropic API 키를 환경 변수로 설정하세요:

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

또는 `.env` 파일을 생성하세요:

```bash
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

### 4. 실행

```bash
python orchestrator.py "작업 설명"
```

## 예시 실행

```bash
# 가상 환경 활성화
source .venv/bin/activate

# 간단한 작업 실행
python orchestrator.py "Hello World를 출력하는 Python 스크립트 작성해줘"

# 상세 로깅과 함께 실행
python orchestrator.py --verbose "FastAPI로 간단한 REST API 만들어줘"
```

## 문제 해결

### ModuleNotFoundError: No module named 'click'

→ 가상 환경이 활성화되었는지 확인하세요:
```bash
which python  # .venv/bin/python이어야 함
```

→ 의존성을 다시 설치하세요:
```bash
pip install -r requirements.txt
```

### ValueError: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다

→ API 키를 설정하세요:
```bash
export ANTHROPIC_API_KEY='your-api-key'
```

→ 또는 `.env` 파일을 확인하세요:
```bash
cat .env
```

## 테스트

시스템이 정상적으로 설치되었는지 확인:

```bash
# CLI 도움말 확인
python orchestrator.py --help

# 설정 파일 검증
python -c "from pathlib import Path; from src.utils import load_agent_config; configs = load_agent_config(Path('config/agent_config.json')); print(f'{len(configs)}개 에이전트 로드됨')"
```

## 다음 단계

- [README.md](README.md)에서 전체 문서를 확인하세요
- [prd-group-chat-orchestration-mvp.md](prd-group-chat-orchestration-mvp.md)에서 제품 사양을 확인하세요
