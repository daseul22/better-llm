"""
환경 검증 유틸리티

validate_environment: 환경변수 검증
get_claude_cli_path: Claude CLI 경로 반환
"""

import os
import logging
import platform
from pathlib import Path

# Optional dotenv support
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        """Fallback when python-dotenv is not installed"""
        pass

logger = logging.getLogger(__name__)


def validate_environment() -> None:
    """
    환경 변수 검증 (ANTHROPIC_API_KEY 또는 CLAUDE_CODE_OAUTH_TOKEN)

    .env 파일이 있으면 자동으로 로드합니다.

    Claude Agent SDK는 두 가지 인증 방식을 지원합니다:
    - ANTHROPIC_API_KEY: API 키 기반 (pay-as-you-go)
    - CLAUDE_CODE_OAUTH_TOKEN: OAuth 토큰 기반 (구독 사용자)

    Raises:
        ValueError: 인증 정보가 설정되지 않은 경우
    """
    # .env 파일 로드 (있을 경우)
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")

    if not api_key and not oauth_token:
        raise ValueError(
            "인증 정보가 설정되지 않았습니다.\n"
            "다음 중 하나의 방법으로 설정하세요:\n\n"
            "방법 1 - API 키 (pay-as-you-go):\n"
            "  export ANTHROPIC_API_KEY='sk-ant-...'\n\n"
            "방법 2 - OAuth 토큰 (Claude 구독 사용자):\n"
            "  export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token'\n\n"
            "또는 .env 파일에 추가하세요."
        )


def get_claude_cli_path() -> str:
    """
    Claude CLI 실행 파일 경로를 반환합니다.

    우선순위:
    1. 환경변수 CLAUDE_CLI_PATH (명시적 오버라이드)
    2. 자동 탐지 (~/.claude/local/claude)

    Returns:
        Claude CLI 실행 파일 경로

    Raises:
        FileNotFoundError: CLI를 찾을 수 없을 경우
    """
    # .env 파일 로드
    load_dotenv()

    # 1. 환경변수 확인
    env_path = os.getenv("CLAUDE_CLI_PATH")
    if env_path:
        cli_path = Path(env_path).expanduser()
        if cli_path.exists():
            return str(cli_path)
        else:
            logger.warning(f"환경변수 CLAUDE_CLI_PATH가 유효하지 않습니다: {env_path}")

    # 2. 자동 탐지
    home_dir = Path.home()
    system = platform.system()

    if system == "Windows":
        default_path = home_dir / ".claude" / "local" / "claude.exe"
    else:  # macOS, Linux
        default_path = home_dir / ".claude" / "local" / "claude"

    if default_path.exists():
        return str(default_path)

    # 찾을 수 없음
    raise FileNotFoundError(
        f"Claude CLI를 찾을 수 없습니다.\n"
        f"다음 중 하나의 방법으로 설정하세요:\n\n"
        f"방법 1 - 환경변수 설정:\n"
        f"  export CLAUDE_CLI_PATH='/path/to/claude'\n\n"
        f"방법 2 - 기본 경로에 설치:\n"
        f"  {default_path}\n\n"
        f"Claude CLI 설치 방법: https://docs.anthropic.com/en/docs/claude-code"
    )


def get_project_root() -> Path:
    """
    프로젝트 루트 디렉토리 반환

    orchestrator.py 또는 tui.py가 있는 디렉토리를 프로젝트 루트로 간주

    Returns:
        프로젝트 루트 디렉토리 (절대 경로)
    """
    # 현재 파일(validator.py)의 부모의 부모의 부모 = better-llm
    # better-llm/src/infrastructure/config/validator.py -> better-llm
    return Path(__file__).parent.parent.parent.parent.resolve()
