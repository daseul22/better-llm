#!/bin/bash
# Better-LLM Workflow Canvas 개발 모드 실행 스크립트 (고급 사용자용)
#
# ⚠️  일반 사용자는 `better-llm-web` 명령어를 사용하세요!
#
# 이 스크립트는 다음과 같은 경우에만 사용하세요:
#   1. 프론트엔드/백엔드를 별도 터미널에서 실행하고 싶을 때
#   2. 프론트엔드 로그를 상세히 확인하고 싶을 때
#   3. 특정 환경변수를 세밀하게 제어하고 싶을 때
#
# 일반적인 사용:
#   better-llm-web
#
# 개발 모드 특징:
#   - 백엔드: 코드 변경 시 자동 리로드 (--reload)
#   - 프론트엔드: HMR (Hot Module Replacement) 지원
#   - 정적 파일 캐시 무효화

set -e

# 색상 코드
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}   Better-LLM Workflow Canvas (고급)      ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}⚠️  일반 사용자는 'better-llm-web' 명령어를 사용하세요!${NC}"
echo ""
echo -e "${YELLOW}이 스크립트는 고급 사용자를 위한 개발 모드입니다:${NC}"
echo "  - 프론트엔드/백엔드를 별도 프로세스로 실행"
echo "  - 상세한 로그 출력"
echo "  - 환경변수 세밀 제어"
echo ""
echo -e "${YELLOW}일반적인 사용: better-llm-web${NC}"
echo ""

# .env 파일 로드
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} .env 파일 발견, 환경변수 로드 중..."
    export $(grep -v '^#' .env | xargs)
fi

# CLAUDE_CODE_OAUTH_TOKEN 체크
if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  경고: CLAUDE_CODE_OAUTH_TOKEN 환경변수가 설정되지 않았습니다.${NC}"
    echo "   Worker Agent 실행 시 오류가 발생할 수 있습니다."
    echo ""
    echo "   설정 방법:"
    echo "   1. .env 파일에 추가: echo 'CLAUDE_CODE_OAUTH_TOKEN=your-token' >> .env"
    echo "   2. 환경변수로 설정: export CLAUDE_CODE_OAUTH_TOKEN='your-token'"
    echo ""
    read -p "계속 진행하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 프론트엔드 디렉토리 확인
FRONTEND_DIR="src/presentation/web/frontend"
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}❌ 프론트엔드 디렉토리를 찾을 수 없습니다: $FRONTEND_DIR${NC}"
    exit 1
fi

# 프론트엔드 의존성 설치 확인
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}📦 프론트엔드 의존성 설치 중...${NC}"
    cd "$FRONTEND_DIR"
    npm install
    cd - > /dev/null
    echo -e "${GREEN}✓${NC} 의존성 설치 완료"
    echo ""
fi

# Python 버전 체크 (pipx 가상환경 우선)
PYTHON_CMD=""

# 1. pipx 가상환경 Python 우선 확인
PIPX_VENV_PYTHON="$HOME/.local/pipx/venvs/better-llm/bin/python"
if [ -f "$PIPX_VENV_PYTHON" ]; then
    if $PIPX_VENV_PYTHON -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
        PYTHON_CMD="$PIPX_VENV_PYTHON"
        echo -e "${GREEN}✓${NC} pipx 가상환경 Python 사용"
    fi
fi

# 2. 시스템 Python으로 폴백
if [ -z "$PYTHON_CMD" ]; then
    for py_cmd in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$py_cmd" &> /dev/null; then
            if $py_cmd -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
                PYTHON_CMD="$py_cmd"
                echo -e "${GREEN}✓${NC} 시스템 Python 사용"
                break
            fi
        fi
    done
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ Python 3.10 이상을 찾을 수 없습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python: $PYTHON_CMD ($($PYTHON_CMD --version))"
echo ""

# 환경변수 설정 (개발 모드 강제)
export WEB_RELOAD=true  # 개발 모드: 코드 변경 시 자동 리로드
export WEB_HOST=${WEB_HOST:-127.0.0.1}
export WEB_PORT=${WEB_PORT:-8000}
export WEB_LOG_LEVEL=${WEB_LOG_LEVEL:-info}

echo -e "${CYAN}🚀 개발 서버 시작...${NC}"
echo ""
echo -e "${GREEN}✓${NC} 백엔드: http://$WEB_HOST:$WEB_PORT (FastAPI + 자동 리로드)"
echo -e "${GREEN}✓${NC} 프론트엔드: http://localhost:5173 (Vite + HMR)"
echo ""
echo -e "${YELLOW}📝 개발 모드 특징:${NC}"
echo "   - 백엔드/프론트엔드 코드 변경 시 자동 리로드"
echo "   - 정적 파일 캐시 무효화"
echo "   - 상세한 로그 출력"
echo ""
echo "   Ctrl+C 로 종료"
echo ""

# 백그라운드 프로세스 정리 함수
cleanup() {
    echo ""
    echo -e "${YELLOW}⏹️  서버 종료 중...${NC}"

    # 백엔드 종료
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi

    # 프론트엔드 종료
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    echo -e "${GREEN}✓${NC} 종료 완료"
    exit 0
}

# Ctrl+C 시 정리 함수 실행
trap cleanup INT TERM

# 백엔드 실행 (백그라운드)
echo -e "${CYAN}[백엔드]${NC} FastAPI 서버 시작 중..."
$PYTHON_CMD -m uvicorn src.presentation.web.app:app \
    --host "$WEB_HOST" \
    --port "$WEB_PORT" \
    --reload \
    --log-level "$WEB_LOG_LEVEL" &
BACKEND_PID=$!

# 백엔드 시작 대기 (3초)
sleep 3

# 프론트엔드 실행 (백그라운드)
echo -e "${CYAN}[프론트엔드]${NC} Vite 개발 서버 시작 중..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
cd - > /dev/null

# 로그 표시 (프론트엔드가 터미널 출력)
wait $FRONTEND_PID $BACKEND_PID
