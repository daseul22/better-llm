# 설치 가이드

Better-LLM을 설치하는 여러 방법을 안내합니다.

## 시스템 요구사항

- **Python**: 3.10 이상
- **운영 체제**: macOS, Linux, Windows (WSL2 권장)
- **메모리**: 최소 4GB RAM
- **디스크 공간**: 500MB 이상

## 방법 1: 자동 설치 (권장)

가장 간단하고 권장하는 방법입니다. pipx를 사용해 격리된 환경에 글로벌로 설치합니다.

### 1. 저장소 클론

```bash
git clone https://github.com/simdaseul/better-llm.git
cd better-llm
```

### 2. 설치 스크립트 실행

```bash
./setup.sh
```

설치 스크립트는 다음을 자동으로 수행합니다:

1. **Python 버전 체크** (3.10+)
2. **pipx 설치** (없는 경우 자동 설치)
3. **설치 모드 선택**:
   - 일반 모드: 안정적인 글로벌 설치
   - 개발 모드: 소스 코드 변경 시 바로 반영
4. **better-llm 설치**
5. **환경 변수 설정 가이드**
6. **설치 검증**

### 3. 환경 변수 설정

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

또는 셸 설정 파일에 영구 추가:

```bash
# bash 사용자
echo "export ANTHROPIC_API_KEY='your-api-key-here'" >> ~/.bashrc
source ~/.bashrc

# zsh 사용자
echo "export ANTHROPIC_API_KEY='your-api-key-here'" >> ~/.zshrc
source ~/.zshrc
```

### 4. 설치 확인

```bash
better-llm --help
better-llm-cli --help
```

## 방법 2: pipx 수동 설치

setup.sh를 사용하지 않고 직접 설치하는 방법입니다.

### 1. pipx 설치

```bash
# macOS (Homebrew)
brew install pipx
pipx ensurepath

# Ubuntu/Debian
sudo apt install pipx
pipx ensurepath

# Python pip 사용
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

### 2. Better-LLM 설치

```bash
git clone https://github.com/simdaseul/better-llm.git
cd better-llm

# 일반 모드 (권장)
pipx install .

# 개발 모드 (소스 코드 변경 시 바로 반영)
pipx install -e .
```

### 3. 환경 변수 설정

```bash
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'

# 영구 설정 (권장)
echo "export CLAUDE_CODE_OAUTH_TOKEN='your-token'" >> ~/.zshrc  # zsh
echo "export CLAUDE_CODE_OAUTH_TOKEN='your-token'" >> ~/.bashrc  # bash
```

## 방법 3: pip 사용 (개발자용, 로컬 테스트)

가상 환경을 사용한 로컬 개발을 위한 방법입니다. pipx 글로벌 설치와 달리, 프로젝트별로 격리된 환경에서 개발할 수 있습니다.

### 1. 가상 환경 생성

```bash
# 저장소 클론
git clone https://github.com/simdaseul/better-llm.git
cd better-llm

# 가상 환경 생성
python3 -m venv .venv

# 가상 환경 활성화
# macOS/Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 2. 의존성 설치

```bash
# editable 모드로 설치 (코드 변경 시 바로 반영)
pip install -e .

# 개발 의존성 추가 (선택사항)
pip install -e ".[dev]"
```

### 3. 환경 변수 설정

```bash
# .env 파일 생성
echo "CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here" > .env
```

### 4. 실행

가상 환경이 활성화된 상태에서:

```bash
# TUI 실행
python -m src.presentation.tui.tui_app

# CLI 실행
python -m src.presentation.cli.orchestrator "작업 설명"
```

## OAuth 토큰 발급

Better-LLM은 Claude Code OAuth 토큰을 사용합니다.

### 1. Claude Code 설치

[https://claude.ai/code](https://claude.ai/code)에서 Claude Code를 설치하세요.

### 2. OAuth 토큰 획득

Claude Code 설치 후 OAuth 토큰을 획득할 수 있습니다.

### 3. 환경 변수 설정

```bash
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'

# 영구 설정 (권장)
echo "export CLAUDE_CODE_OAUTH_TOKEN='your-token'" >> ~/.zshrc  # zsh
echo "export CLAUDE_CODE_OAUTH_TOKEN='your-token'" >> ~/.bashrc  # bash
```

## 설치 확인

### 명령어 확인

```bash
# TUI 실행 가능 확인
better-llm --help

# CLI 실행 가능 확인
better-llm-cli --help
```

### 간단한 테스트

```bash
# CLI로 간단한 작업 테스트
better-llm-cli "Hello world를 출력하는 Python 스크립트 작성"
```

## 문제 해결

### Python 버전 확인

```bash
python --version  # 3.10 이상이어야 함
```

Python 3.10 미만이면:

```bash
# macOS (Homebrew)
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11

# pyenv 사용
pyenv install 3.11.0
pyenv global 3.11.0
```

### pipx 경로 문제

```bash
# pipx 경로 재설정
pipx ensurepath

# 셸 재시작
exec $SHELL
```

### 권한 에러

```bash
# macOS/Linux
chmod +x install.sh

# 또는 sudo 없이 설치
pip install --user -e .
```

### OAuth 토큰 에러

```bash
# 환경 변수 확인
echo $CLAUDE_CODE_OAUTH_TOKEN

# 비어있으면 다시 설정
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'
```

## 다음 단계

설치가 완료되었다면:

1. [빠른 시작](quickstart.md) - 첫 작업 실행
2. [사용법](usage.md) - 상세한 사용 가이드
3. [아키텍처](../architecture.md) - 시스템 구조 이해
