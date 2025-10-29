#!/bin/bash
# claude-flow 설치 스크립트 (pipx 글로벌 설치)

set -e  # 에러 발생 시 즉시 종료

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 헬퍼 함수
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}      Claude Flow Web UI 설치              ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""
}

# 1. Python 버전 체크
check_python() {
    print_info "Python 버전 확인 중..."

    # Python 3.10 이상 버전 찾기 (우선순위: python3.12 > python3.11 > python3.10)
    PYTHON_CMD=""
    for py_cmd in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$py_cmd" &> /dev/null; then
            # 버전 체크
            if $py_cmd -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
                PYTHON_CMD="$py_cmd"
                break
            fi
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        print_error "Python 3.10 이상을 찾을 수 없습니다."
        echo ""
        echo "  현재 설치된 Python 버전:"
        for py_cmd in python3.9 python3.10 python3.11 python3.12 python3; do
            if command -v "$py_cmd" &> /dev/null; then
                version=$($py_cmd --version 2>&1)
                echo "    - $py_cmd: $version"
            fi
        done
        echo ""
        echo "  Python 3.10 이상을 설치해주세요:"
        echo "  https://www.python.org/downloads/"
        exit 1
    fi

    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
    print_success "Python $PYTHON_VERSION ($PYTHON_CMD) 확인됨"
}

# 2. pipx 설치
install_pipx() {
    print_info "pipx 확인 중..."

    if command -v pipx &> /dev/null; then
        print_success "pipx가 이미 설치되어 있습니다."
        return
    fi

    print_warning "pipx가 설치되지 않았습니다. 설치 중..."

    # macOS - Homebrew 사용
    if command -v brew &> /dev/null; then
        brew install pipx
        pipx ensurepath
        print_success "pipx 설치 완료 (Homebrew)"

    # Linux/macOS - pip 사용 (올바른 Python 버전 사용)
    else
        $PYTHON_CMD -m pip install --user pipx
        $PYTHON_CMD -m pipx ensurepath
        print_success "pipx 설치 완료 (pip)"
    fi

    # PATH 갱신을 위한 안내
    print_warning "셸을 재시작하거나 다음 명령어를 실행하세요:"
    if [ -f ~/.zshrc ]; then
        echo "  source ~/.zshrc"
    elif [ -f ~/.bashrc ]; then
        echo "  source ~/.bashrc"
    fi
    echo ""
}

# 3. 설치 모드 선택
choose_install_mode() {
    echo ""
    print_info "설치 모드를 선택하세요:"
    echo ""
    echo -e "  ${CYAN}1)${NC} 일반 모드 - 일반 사용자용 (권장)"
    echo "     코드가 고정되어 안정적으로 동작합니다."
    echo ""
    echo -e "  ${CYAN}2)${NC} 개발 모드 - 개발자용"
    echo "     소스 코드 변경사항이 바로 반영됩니다."
    echo ""

    read -p "선택 [1-2] (기본값: 1): " mode_choice

    case $mode_choice in
        2)
            INSTALL_MODE="editable"
            print_info "개발 모드로 설치합니다."
            ;;
        *)
            INSTALL_MODE="normal"
            print_info "일반 모드로 설치합니다."
            ;;
    esac
}

# 4. claude-flow 설치
install_claude_flow() {
    echo ""
    print_info "claude-flow 설치 중 (Python $PYTHON_VERSION 사용)..."

    # 기존 설치 확인
    if pipx list 2>/dev/null | grep -q "claude-flow"; then
        print_warning "기존 설치를 제거하고 재설치합니다..."
        pipx uninstall claude-flow || true
    fi

    # 설치 모드에 따라 설치 (올바른 Python 버전 명시)
    if [ "$INSTALL_MODE" = "editable" ]; then
        pipx install --python "$PYTHON_CMD" -e .
        print_success "claude-flow 설치 완료 (개발 모드)"
    else
        pipx install --python "$PYTHON_CMD" .
        print_success "claude-flow 설치 완료 (일반 모드)"
    fi
}

# 5. 환경변수 안내
setup_environment() {
    echo ""
    print_info "환경변수 설정이 필요합니다:"
    echo ""
    echo -e "  ${CYAN}CLAUDE_CODE_OAUTH_TOKEN${NC} - Claude Code OAuth 토큰"
    echo ""

    # .env 파일에서 토큰 로드 시도
    if [ -f ".env" ] && [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
        print_info ".env 파일에서 OAuth 토큰 확인 중..."

        # .env 파일에서 CLAUDE_CODE_OAUTH_TOKEN 추출
        TOKEN_FROM_ENV=$(grep -E "^CLAUDE_CODE_OAUTH_TOKEN=" .env | cut -d '=' -f2- | tr -d '"' | tr -d "'")

        if [ -n "$TOKEN_FROM_ENV" ]; then
            export CLAUDE_CODE_OAUTH_TOKEN="$TOKEN_FROM_ENV"
            print_success ".env 파일에서 OAuth 토큰 로드됨"
        fi
    fi

    if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
        print_warning "CLAUDE_CODE_OAUTH_TOKEN이 설정되지 않았습니다."
        echo ""
        echo "다음 명령어로 설정하세요:"
        echo ""
        echo -e "  ${GREEN}export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'${NC}"
        echo ""
        echo "영구 설정 (권장):"
        echo ""
        if [ -f ~/.zshrc ]; then
            echo -e "  ${GREEN}echo \"export CLAUDE_CODE_OAUTH_TOKEN='your-token'\" >> ~/.zshrc${NC}"
            echo -e "  ${GREEN}source ~/.zshrc${NC}"
        elif [ -f ~/.bashrc ]; then
            echo -e "  ${GREEN}echo \"export CLAUDE_CODE_OAUTH_TOKEN='your-token'\" >> ~/.bashrc${NC}"
            echo -e "  ${GREEN}source ~/.bashrc${NC}"
        fi
        echo ""

        read -p "지금 OAuth 토큰을 설정하시겠습니까? (y/n): " setup_now

        if [ "$setup_now" = "y" ] || [ "$setup_now" = "Y" ]; then
            read -sp "CLAUDE_CODE_OAUTH_TOKEN: " oauth_token
            echo ""
            export CLAUDE_CODE_OAUTH_TOKEN="$oauth_token"

            # 셸 설정 파일에 추가
            if [ -f ~/.zshrc ]; then
                echo "export CLAUDE_CODE_OAUTH_TOKEN='$oauth_token'" >> ~/.zshrc
                print_success "~/.zshrc에 OAuth 토큰 추가됨"
            elif [ -f ~/.bashrc ]; then
                echo "export CLAUDE_CODE_OAUTH_TOKEN='$oauth_token'" >> ~/.bashrc
                print_success "~/.bashrc에 OAuth 토큰 추가됨"
            fi
        fi
    else
        print_success "CLAUDE_CODE_OAUTH_TOKEN 확인됨"
    fi
}

# 6. 웹 프론트엔드 설치 및 빌드
install_web_frontend() {
    echo ""
    print_info "웹 프론트엔드 설정 중..."

    # Node.js 및 npm 확인
    if ! command -v npm &> /dev/null; then
        print_warning "npm이 설치되지 않았습니다. 웹 UI를 사용하려면 Node.js를 설치하세요."
        echo ""
        echo "  Node.js 설치: https://nodejs.org/"
        echo ""
        return
    fi

    NODE_VERSION=$(node --version 2>/dev/null || echo "unknown")
    print_success "Node.js $NODE_VERSION 확인됨"

    # frontend 디렉토리로 이동
    FRONTEND_DIR="src/presentation/web/frontend"
    if [ ! -d "$FRONTEND_DIR" ]; then
        print_warning "웹 프론트엔드 디렉토리를 찾을 수 없습니다: $FRONTEND_DIR"
        return
    fi

    cd "$FRONTEND_DIR" || return

    # npm install
    print_info "웹 의존성 설치 중... (시간이 다소 걸릴 수 있습니다)"
    if npm install --silent 2>&1 | grep -q "audited"; then
        print_success "웹 의존성 설치 완료"
    else
        print_warning "웹 의존성 설치 중 경고가 발생했습니다 (정상 동작 가능)"
    fi

    # npm run build
    print_info "웹 프론트엔드 빌드 중..."
    if npm run build > /dev/null 2>&1; then
        print_success "웹 프론트엔드 빌드 완료"
    else
        print_error "웹 빌드 실패"
        cd - > /dev/null
        return 1
    fi

    cd - > /dev/null
}

# 7. 설치 검증
verify_installation() {
    echo ""
    print_info "설치 검증 중..."

    # claude-flow-web 명령어 확인
    if command -v claude-flow-web &> /dev/null; then
        print_success "claude-flow-web 명령어 사용 가능"
    else
        print_error "claude-flow-web 명령어를 찾을 수 없습니다."
        echo ""
        echo "셸을 재시작하고 다시 시도하세요:"
        echo "  exec \$SHELL"
        echo ""
        exit 1
    fi

    # Web UI 빌드 확인 (static-react 디렉토리)
    FRONTEND_DIST="src/presentation/web/static-react"
    if [ -d "$FRONTEND_DIST" ] && [ -f "$FRONTEND_DIST/index.html" ]; then
        print_success "Web UI 빌드 파일 확인됨"
    else
        print_warning "Web UI 빌드 파일을 찾을 수 없습니다. 수동 빌드가 필요할 수 있습니다."
        echo ""
        echo "  수동 빌드 방법:"
        echo "    cd src/presentation/web/frontend"
        echo "    npm run build"
    fi
}

# 7. 설치 완료 메시지
print_completion() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}        설치가 완료되었습니다!             ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    print_info "사용 방법:"
    echo ""
    echo -e "  ${CYAN}# Web UI 시작 (드래그 앤 드롭 워크플로우 에디터)${NC}"
    echo "  claude-flow-web"
    echo ""
    echo -e "  ${CYAN}# 웹 브라우저에서 접속${NC}"
    echo "  http://localhost:5173"
    echo ""
    echo -e "  ${CYAN}# 개발 모드 (소스 변경 시)${NC}"
    echo "  cd src/presentation/web/frontend"
    echo "  npm run dev"
    echo ""

    if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
        print_warning "주의: CLAUDE_CODE_OAUTH_TOKEN 환경변수를 설정해야 사용할 수 있습니다."
        echo ""
        echo "  export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'"
        echo ""
    fi

    echo -e "  ${CYAN}상세 문서:${NC} CLAUDE.md 또는 README.md"
    echo ""
}

# 메인 실행 흐름
main() {
    print_header

    check_python
    install_pipx
    choose_install_mode
    install_claude_flow
    install_web_frontend
    setup_environment
    verify_installation
    print_completion
}

# 스크립트 실행
main
