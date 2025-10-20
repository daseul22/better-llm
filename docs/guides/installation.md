# 설치 가이드

Better-LLM을 설치하는 여러 방법을 안내합니다.

## 시스템 요구사항

- **Python**: 3.10 이상
- **운영 체제**: macOS, Linux, Windows (WSL2 권장)
- **메모리**: 최소 4GB RAM
- **디스크 공간**: 500MB 이상

## 방법 1: 자동 설치 (권장)

가장 간단한 방법입니다. 설치 스크립트가 모든 과정을 자동으로 처리합니다.

### 1. 저장소 클론

```bash
git clone https://github.com/simdaseul/better-llm.git
cd better-llm
```

### 2. 설치 스크립트 실행

```bash
./install.sh
```

설치 스크립트는 다음을 자동으로 수행합니다:

1. Python 버전 체크 (3.10+)
2. 설치 방법 선택 (pipx 또는 pip)
3. 의존성 설치
4. 환경 변수 설정 가이드
5. 설치 검증

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

## 방법 2: pipx 사용 (권장)

pipx는 Python 애플리케이션을 격리된 환경에 설치합니다.

### 1. pipx 설치

```bash
# macOS
brew install pipx
pipx ensurepath

# Ubuntu/Debian
sudo apt install pipx
pipx ensurepath

# Python pip 사용
python -m pip install --user pipx
python -m pipx ensurepath
```

### 2. Better-LLM 설치

```bash
git clone https://github.com/simdaseul/better-llm.git
cd better-llm
pipx install -e .
```

### 3. 환경 변수 설정

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

## 방법 3: pip 사용 (개발자용)

가상 환경을 사용하는 것을 권장합니다.

### 1. 가상 환경 생성

```bash
# 저장소 클론
git clone https://github.com/simdaseul/better-llm.git
cd better-llm

# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화
# macOS/Linux
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

### 2. 의존성 설치

```bash
# 프로덕션 의존성
pip install -e .

# 개발 의존성 (테스트, 린트 등)
pip install -r requirements-dev.txt
```

### 3. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

## API 키 발급

### 1. Anthropic Console 접속

[https://console.anthropic.com/](https://console.anthropic.com/)

### 2. API 키 생성

1. 로그인 또는 회원가입
2. **API Keys** 메뉴로 이동
3. **Create Key** 클릭
4. 키 이름 입력 (예: "better-llm")
5. 생성된 키 복사 (한 번만 표시됨!)

### 3. 환경 변수 설정

```bash
export ANTHROPIC_API_KEY='sk-ant-api...'
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

### API 키 에러

```bash
# 환경 변수 확인
echo $ANTHROPIC_API_KEY

# 비어있으면 다시 설정
export ANTHROPIC_API_KEY='your-api-key-here'
```

## 다음 단계

설치가 완료되었다면:

1. [빠른 시작](quickstart.md) - 첫 작업 실행
2. [사용법](usage.md) - 상세한 사용 가이드
3. [아키텍처](../architecture.md) - 시스템 구조 이해
