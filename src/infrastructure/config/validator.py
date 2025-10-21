"""
환경 검증 유틸리티

validate_environment: 환경변수 검증
get_claude_cli_path: Claude CLI 경로 반환
"""

import os
import logging
import platform
from pathlib import Path
from typing import Optional

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
    환경 변수 검증 (CLAUDE_CODE_OAUTH_TOKEN)

    .env 파일이 있으면 자동으로 로드합니다.

    OAuth 토큰 기반 인증만 사용합니다 (Claude 구독 사용자).

    Raises:
        ValueError: OAuth 토큰이 설정되지 않은 경우
    """
    # .env 파일 로드 (있을 경우)
    load_dotenv()

    oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")

    if not oauth_token:
        raise ValueError(
            "CLAUDE_CODE_OAUTH_TOKEN이 설정되지 않았습니다.\n"
            "다음 방법으로 설정하세요:\n\n"
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


def get_project_name() -> str:
    """
    프로젝트 이름 감지

    우선순위:
    1. Git 저장소 이름 (git root directory 이름)
    2. 현재 작업 디렉토리 이름

    Returns:
        프로젝트 이름 (디렉토리명)

    Example:
        >>> get_project_name()
        'better-llm'
    """
    import subprocess

    try:
        # Git root 디렉토리 확인 시도
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode == 0:
            git_root = Path(result.stdout.strip())
            return git_root.name
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # git이 없거나 타임아웃
        pass

    # Git 저장소가 아니면 현재 작업 디렉토리 이름 사용
    return Path.cwd().name


def get_data_dir(subdir: Optional[str] = None) -> Path:
    """
    데이터 디렉토리 경로 반환 (~/.better-llm/{project-name}/)

    프로젝트별 세션, 로그 등을 저장하는 디렉토리를 반환합니다.
    디렉토리가 없으면 자동으로 생성합니다.

    Args:
        subdir: 하위 디렉토리 이름 (예: "sessions", "logs")

    Returns:
        데이터 디렉토리 경로 (절대 경로)

    Example:
        >>> get_data_dir()
        Path('/Users/daniel/.better-llm/better-llm')
        >>> get_data_dir("sessions")
        Path('/Users/daniel/.better-llm/better-llm/sessions')
    """
    home_dir = Path.home()
    project_name = get_project_name()

    if subdir:
        data_path = home_dir / ".better-llm" / project_name / subdir
    else:
        data_path = home_dir / ".better-llm" / project_name

    # 디렉토리 생성 (없으면)
    data_path.mkdir(parents=True, exist_ok=True)

    return data_path
