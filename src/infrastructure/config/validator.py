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
    1. Git remote URL에서 프로젝트 이름 추출
    2. Git root directory 이름
    3. 현재 작업 디렉토리 이름

    Returns:
        프로젝트 이름 (디렉토리명)

    Example:
        >>> get_project_name()
        'better-llm'

    Notes:
        - Git URL 파싱 지원 형식:
          * HTTPS: https://github.com/user/repo.git
          * SSH: git@github.com:user/repo.git
          * SSH with port: ssh://git@github.com:22/user/repo.git
          * With query params: https://github.com/user/repo.git?ref=main
    """
    import subprocess
    import re

    try:
        # 1. Git remote URL에서 프로젝트 이름 추출 시도
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False
        )

        if result.returncode == 0:
            remote_url = result.stdout.strip()
            if remote_url:
                # Query params 제거 (예: ?ref=main)
                remote_url = remote_url.split("?")[0]
                # Fragment 제거 (예: #branch)
                remote_url = remote_url.split("#")[0]
                # .git 확장자 제거
                if remote_url.endswith(".git"):
                    remote_url = remote_url[:-4]

                # URL에서 프로젝트 이름 추출
                # SSH URL with port: ssh://git@github.com:22/user/repo -> repo
                # SSH URL: git@github.com:user/repo -> repo
                # HTTPS URL: https://github.com/user/repo -> repo

                # SSH with port 형식 처리
                if remote_url.startswith("ssh://"):
                    # ssh://git@github.com:22/user/repo
                    match = re.search(r"ssh://[^/]+/(.+)", remote_url)
                    if match:
                        path = match.group(1)
                        project_name = path.split("/")[-1]
                        if project_name:
                            return project_name

                # 일반 SSH 형식 (git@github.com:user/repo)
                if "@" in remote_url and ":" in remote_url:
                    # git@github.com:user/repo -> user/repo
                    parts = remote_url.split(":")
                    if len(parts) >= 2:
                        project_name = parts[-1].split("/")[-1]
                        if project_name:
                            return project_name

                # HTTPS 형식 또는 기타 형식
                project_name = remote_url.split("/")[-1]
                if project_name:
                    return project_name
        else:
            # Git 명령 실패 시 debug 레벨로 기록
            logger.debug(
                f"Git remote command failed (code {result.returncode}): "
                f"{result.stderr.strip()}"
            )
    except subprocess.TimeoutExpired:
        logger.debug("Git remote command timed out")
    except FileNotFoundError:
        logger.debug("Git command not found")
    except Exception as e:
        logger.debug(f"Unexpected error while getting git remote: {e}")

    try:
        # 2. Git root 디렉토리 확인 시도
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False
        )

        if result.returncode == 0:
            git_root = Path(result.stdout.strip())
            return git_root.name
        else:
            logger.debug(
                f"Git rev-parse command failed (code {result.returncode}): "
                f"{result.stderr.strip()}"
            )
    except subprocess.TimeoutExpired:
        logger.debug("Git rev-parse command timed out")
    except FileNotFoundError:
        logger.debug("Git command not found")
    except Exception as e:
        logger.debug(f"Unexpected error while getting git root: {e}")

    # 3. Git 저장소가 아니면 현재 작업 디렉토리 이름 사용
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

    Raises:
        OSError: 디렉토리 생성에 실패한 경우

    Example:
        >>> get_data_dir()
        Path('/Users/daniel/.better-llm/better-llm')
        >>> get_data_dir("sessions")
        Path('/Users/daniel/.better-llm/better-llm/sessions')

    Notes:
        - 프로젝트 이름은 get_project_name()으로 자동 감지됩니다.
        - 디렉토리가 없으면 자동으로 생성됩니다 (parents=True, exist_ok=True).
        - 멀티 프로젝트 환경에서도 각 프로젝트의 데이터가 격리됩니다.
    """
    home_dir = Path.home()
    project_name = get_project_name()

    if subdir:
        data_path = home_dir / ".better-llm" / project_name / subdir
    else:
        data_path = home_dir / ".better-llm" / project_name

    # 디렉토리 생성 (없으면)
    try:
        data_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Data directory ensured: {data_path}")
    except OSError as e:
        current_dir = Path.cwd()
        error_msg = (
            f"Failed to create data directory: {data_path}\n"
            f"Current working directory: {current_dir}\n"
            f"Project name: {project_name}\n"
            f"Error: {e}"
        )
        logger.error(error_msg)
        raise OSError(error_msg) from e

    return data_path
