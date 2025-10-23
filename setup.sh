#!/bin/bash
# better-llm 설치 스크립트 (pipx 글로벌 설치)

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
    echo -e "${CYAN}║${NC}        Better-LLM 설치 (pipx)            ${CYAN}║${NC}"
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
    echo "  ${CYAN}1)${NC} 일반 모드 - 일반 사용자용 (권장)"
    echo "     코드가 고정되어 안정적으로 동작합니다."
    echo ""
    echo "  ${CYAN}2)${NC} 개발 모드 - 개발자용"
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

# 4. better-llm 설치
install_better_llm() {
    echo ""
    print_info "better-llm 설치 중 (Python $PYTHON_VERSION 사용)..."

    # 기존 설치 확인
    if pipx list 2>/dev/null | grep -q "better-llm"; then
        print_warning "기존 설치를 제거하고 재설치합니다..."
        pipx uninstall better-llm || true
    fi

    # 설치 모드에 따라 설치 (올바른 Python 버전 명시)
    if [ "$INSTALL_MODE" = "editable" ]; then
        pipx install --python "$PYTHON_CMD" -e .
        print_success "better-llm 설치 완료 (개발 모드)"
    else
        pipx install --python "$PYTHON_CMD" .
        print_success "better-llm 설치 완료 (일반 모드)"
    fi
}

# 5. 환경변수 안내
setup_environment() {
    echo ""
    print_info "환경변수 설정이 필요합니다:"
    echo ""
    echo "  ${CYAN}CLAUDE_CODE_OAUTH_TOKEN${NC} - Claude Code OAuth 토큰"
    echo ""

    if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
        print_warning "CLAUDE_CODE_OAUTH_TOKEN이 설정되지 않았습니다."
        echo ""
        echo "다음 명령어로 설정하세요:"
        echo ""
        echo "  ${GREEN}export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'${NC}"
        echo ""
        echo "영구 설정 (권장):"
        echo ""
        if [ -f ~/.zshrc ]; then
            echo "  ${GREEN}echo \"export CLAUDE_CODE_OAUTH_TOKEN='your-token'\" >> ~/.zshrc${NC}"
            echo "  ${GREEN}source ~/.zshrc${NC}"
        elif [ -f ~/.bashrc ]; then
            echo "  ${GREEN}echo \"export CLAUDE_CODE_OAUTH_TOKEN='your-token'\" >> ~/.bashrc${NC}"
            echo "  ${GREEN}source ~/.bashrc${NC}"
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

# 6. 설치 검증
verify_installation() {
    echo ""
    print_info "설치 검증 중..."

    # better-llm 명령어 확인
    if command -v better-llm &> /dev/null; then
        print_success "better-llm 명령어 사용 가능"
    else
        print_error "better-llm 명령어를 찾을 수 없습니다."
        echo ""
        echo "셸을 재시작하고 다시 시도하세요:"
        echo "  exec \$SHELL"
        echo ""
        exit 1
    fi

    # better-llm-cli 명령어 확인
    if command -v better-llm-cli &> /dev/null; then
        print_success "better-llm-cli 명령어 사용 가능"
    else
        print_warning "better-llm-cli 명령어를 찾을 수 없습니다."
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
    echo "  ${CYAN}# TUI 모드 (권장)${NC}"
    echo "  better-llm"
    echo ""
    echo "  ${CYAN}# CLI 모드${NC}"
    echo "  better-llm-cli \"작업 설명\""
    echo ""
    echo "  ${CYAN}# 도움말${NC}"
    echo "  better-llm --help"
    echo ""

    if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
        print_warning "주의: CLAUDE_CODE_OAUTH_TOKEN 환경변수를 설정해야 사용할 수 있습니다."
        echo ""
        echo "  export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'"
        echo ""
    fi

    print_info "상세 문서: ${CYAN}README.md${NC} 또는 ${CYAN}docs/index.md${NC}"
    echo ""
}

# 메인 실행 흐름
main() {
    print_header

    check_python
    install_pipx
    choose_install_mode
    install_better_llm
    setup_environment
    verify_installation
    print_completion
}

# 스크립트 실행
main
