#!/bin/bash

# 웹 프론트엔드 빌드 자동화 스크립트
# npm install 체크 및 빌드 실행

set -e  # 에러 발생 시 즉시 종료

FRONTEND_DIR="src/presentation/web/frontend"
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Claude Flow 웹 프론트엔드 빌드 ==="
echo ""

# 프론트엔드 디렉토리 존재 확인
if [ ! -d "$PROJECT_ROOT/$FRONTEND_DIR" ]; then
    echo "✗ 오류: 프론트엔드 디렉토리를 찾을 수 없습니다"
    echo "  경로: $PROJECT_ROOT/$FRONTEND_DIR"
    exit 1
fi

cd "$PROJECT_ROOT/$FRONTEND_DIR"
echo "작업 디렉토리: $FRONTEND_DIR"
echo ""

# package.json 존재 확인
if [ ! -f "package.json" ]; then
    echo "✗ 오류: package.json 파일이 없습니다"
    exit 1
fi

# node_modules 체크
if [ ! -d "node_modules" ]; then
    echo "📦 node_modules가 없습니다. npm install을 실행합니다..."
    echo ""
    npm install
    echo ""
    echo "✓ npm install 완료"
    echo ""
else
    # package.json이 node_modules보다 최신인지 확인
    if [ "package.json" -nt "node_modules" ]; then
        echo "⚠ package.json이 변경되었습니다. npm install을 실행합니다..."
        echo ""
        npm install
        echo ""
        echo "✓ npm install 완료"
        echo ""
    else
        echo "✓ node_modules가 최신 상태입니다"
        echo ""
    fi
fi

# 빌드 실행
echo "🔨 프로덕션 빌드를 시작합니다..."
echo ""

if npm run build; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✓ 빌드 완료!"
    echo ""
    echo "빌드 출력 위치: src/presentation/web/static-react"
    echo ""
    echo "웹 서버 실행 방법:"
    echo "  claude-flow-web"
    echo "  또는"
    echo "  python -m src.presentation.web.app"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo ""
    echo "✗ 빌드 실패"
    exit 1
fi
