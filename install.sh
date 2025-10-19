#!/bin/bash
# better-llm 글로벌 설치 스크립트

set -e  # 에러 발생 시 즉시 종료

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 헬퍼 함수
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
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
    echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  better-llm 설치 스크립트                 ${BLUE}║${NC}"
    echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
    echo ""
}

# 1. Python 버전 체크
check_python_version() {
    print_info "Python 버전 확인 중..."

    # Python 3.10 이상 체크
    if ! command -v python3 &> /dev/null; then
        print_error "Python3가 설치되지 않았습니다."
        echo "  Python 3.10 이상을 설치해주세요: https://www.python.org/downloads/"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.10"

    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        print_error "Python 버전이 너무 낮습니다: $PYTHON_VERSION"
        echo "  Python 3.10 이상이 필요합니다."
        exit 1
    fi

    print_success "Python $PYTHON_VERSION 확인됨"
}

# 2. 설치 방법 선택
choose_install_method() {
    echo ""
    print_info "설치 방법을 선택하세요:"
    echo "  1) pipx (권장) - 격리된 환경에 글로벌 설치"
    echo "  2) pip (개발자용) - editable 모드로 설치"
    echo ""

    read -p "선택 [1-2]: " choice

    case $choice in
        1)
            INSTALL_METHOD="pipx"
            ;;
        2)
            INSTALL_METHOD="pip"
            ;;
        *)
            print_warning "잘못된 선택입니다. pipx를 사용합니다."
            INSTALL_METHOD="pipx"
            ;;
    esac

    print_info "선택된 설치 방법: $INSTALL_METHOD"
}

# 3. pipx 설치 (필요시)
install_pipx() {
    if ! command -v pipx &> /dev/null; then
        print_warning "pipx가 설치되지 않았습니다. 설치 중..."

        if command -v brew &> /dev/null; then
            brew install pipx
        else
            python3 -m pip install --user pipx
        fi

        python3 -m pipx ensurepath
        print_success "pipx 설치 완료"
    else
        print_success "pipx가 이미 설치되어 있습니다."
    fi
}

# 4. better-llm 설치
install_better_llm() {
    echo ""
    print_info "better-llm 설치 중..."

    if [ "$INSTALL_METHOD" = "pipx" ]; then
        # pipx로 설치 (기존 설치 확인 후 재설치)
        if pipx list | grep -q "better-llm"; then
            print_warning "기존 설치를 제거하고 재설치합니다..."
            pipx uninstall better-llm || true
        fi
        pipx install -e .
        print_success "pipx로 설치 완료"

    else
        # pip editable 모드로 설치
        python3 -m pip install -e .
        print_success "pip editable 모드로 설치 완료"
    fi
}

# 5. 환경변수 체크
check_environment() {
    echo ""
    print_info "환경변수 확인 중..."

    # ANTHROPIC_API_KEY 체크
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        print_warning "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다."
        echo ""
        echo "다음 명령어로 API 키를 설정하세요:"
        echo ""
        echo "  export ANTHROPIC_API_KEY='your-api-key-here'"
        echo ""
        echo "영구 설정을 원하시면 ~/.bashrc 또는 ~/.zshrc에 추가하세요:"
        echo ""
        echo "  echo \"export ANTHROPIC_API_KEY='your-api-key-here'\" >> ~/.bashrc"
        echo "  echo \"export ANTHROPIC_API_KEY='your-api-key-here'\" >> ~/.zshrc"
        echo ""

        read -p "지금 API 키를 입력하시겠습니까? (y/n): " setup_key

        if [ "$setup_key" = "y" ] || [ "$setup_key" = "Y" ]; then
            read -sp "ANTHROPIC_API_KEY: " api_key
            echo ""
            export ANTHROPIC_API_KEY="$api_key"

            # 셸 설정 파일에 추가
            if [ -f ~/.zshrc ]; then
                echo "export ANTHROPIC_API_KEY='$api_key'" >> ~/.zshrc
                print_success "~/.zshrc에 API 키 추가됨"
            elif [ -f ~/.bashrc ]; then
                echo "export ANTHROPIC_API_KEY='$api_key'" >> ~/.bashrc
                print_success "~/.bashrc에 API 키 추가됨"
            fi
        fi
    else
        print_success "ANTHROPIC_API_KEY 확인됨"
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
        echo "다음을 확인해주세요:"
        echo "  1. 셸을 재시작하세요 (source ~/.bashrc 또는 source ~/.zshrc)"
        echo "  2. PATH에 Python 실행 경로가 포함되어 있는지 확인하세요"
        exit 1
    fi

    # better-llm-cli 명령어 확인
    if command -v better-llm-cli &> /dev/null; then
        print_success "better-llm-cli 명령어 사용 가능"
    else
        print_warning "better-llm-cli 명령어를 찾을 수 없습니다."
    fi

    # 헬프 메시지 테스트
    print_info "버전 정보:"
    better-llm --help | head -5 || true
}

# 7. 설치 완료 메시지
print_completion() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  설치가 완료되었습니다!                   ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    print_info "사용 방법:"
    echo ""
    echo "  # TUI 모드 (권장)"
    echo "  better-llm"
    echo ""
    echo "  # CLI 모드"
    echo "  better-llm-cli \"작업 설명\""
    echo ""
    echo "  # 도움말"
    echo "  better-llm --help"
    echo "  better-llm-cli --help"
    echo ""

    if [ -z "$ANTHROPIC_API_KEY" ]; then
        print_warning "주의: ANTHROPIC_API_KEY 환경변수를 설정해야 사용할 수 있습니다."
        echo ""
        echo "  export ANTHROPIC_API_KEY='your-api-key-here'"
        echo ""
    fi

    print_info "상세 문서는 README.md를 참고하세요."
    echo ""
}

# 메인 실행 흐름
main() {
    print_header

    check_python_version
    choose_install_method

    if [ "$INSTALL_METHOD" = "pipx" ]; then
        install_pipx
    fi

    install_better_llm
    check_environment
    verify_installation
    print_completion
}

# 스크립트 실행
main
