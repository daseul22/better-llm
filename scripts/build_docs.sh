#!/usr/bin/env bash
# 문서 빌드 스크립트

set -e  # 에러 발생 시 중단

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# mkdocs 설치 확인
check_mkdocs() {
    log_info "Checking mkdocs installation..."

    if ! command -v mkdocs &> /dev/null; then
        log_warn "mkdocs not found. Installing..."
        python3 -m pip install mkdocs mkdocs-material "mkdocstrings[python]" pymdown-extensions
        log_info "mkdocs installed successfully."
    else
        log_info "mkdocs is already installed."
    fi
}

# 문서 빌드
build_docs() {
    log_info "Building documentation..."

    if mkdocs build --strict; then
        log_info "Documentation built successfully!"
        log_info "Output directory: site/"
    else
        log_error "Documentation build failed!"
        exit 1
    fi
}

# 문서 서버 실행
serve_docs() {
    log_info "Starting documentation server..."
    log_info "Server will be available at http://127.0.0.1:8000"
    log_info "Press Ctrl+C to stop the server."

    mkdocs serve
}

# 문서 검증
validate_docs() {
    log_info "Validating documentation..."

    # 링크 검증 (선택사항)
    if command -v linkchecker &> /dev/null; then
        log_info "Checking for broken links..."
        mkdocs build
        linkchecker site/index.html
    else
        log_warn "linkchecker not found. Skipping link validation."
        log_warn "Install with: pip install linkchecker"
    fi
}

# 문서 배포 (GitHub Pages)
deploy_docs() {
    log_info "Deploying documentation to GitHub Pages..."

    if mkdocs gh-deploy --force; then
        log_info "Documentation deployed successfully!"
        log_info "Visit: https://simdaseul.github.io/better-llm/"
    else
        log_error "Documentation deployment failed!"
        exit 1
    fi
}

# 도움말
show_help() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    build       Build documentation (default)
    serve       Start local documentation server
    validate    Validate documentation (check links, etc.)
    deploy      Deploy documentation to GitHub Pages
    clean       Clean build artifacts
    help        Show this help message

Examples:
    $0              # Build documentation
    $0 build        # Build documentation
    $0 serve        # Start local server
    $0 deploy       # Deploy to GitHub Pages

EOF
}

# 빌드 아티팩트 정리
clean_docs() {
    log_info "Cleaning build artifacts..."
    rm -rf site/
    log_info "Build artifacts cleaned."
}

# 메인 로직
main() {
    local command="${1:-build}"

    case "$command" in
        build)
            check_mkdocs
            build_docs
            ;;
        serve)
            check_mkdocs
            serve_docs
            ;;
        validate)
            check_mkdocs
            validate_docs
            ;;
        deploy)
            check_mkdocs
            build_docs
            deploy_docs
            ;;
        clean)
            clean_docs
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"
