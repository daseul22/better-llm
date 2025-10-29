"""
경로 유틸리티 함수

프로젝트별 데이터 디렉토리 경로를 관리합니다.
"""

import subprocess
from pathlib import Path
from typing import Optional


def get_project_name() -> str:
    """
    프로젝트 이름을 자동으로 감지합니다.

    우선순위:
    1. Git repository name (git remote로부터 추출)
    2. Git repository root directory name
    3. 현재 작업 디렉토리 이름

    Returns:
        프로젝트 이름 (예: "claude-flow")

    Examples:
        >>> get_project_name()
        'claude-flow'
    """
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
            # URL에서 프로젝트 이름 추출
            # 예: https://github.com/user/claude-flow.git -> claude-flow
            # 예: git@github.com:user/claude-flow.git -> claude-flow
            if remote_url:
                # .git 확장자 제거
                if remote_url.endswith(".git"):
                    remote_url = remote_url[:-4]
                # 마지막 / 이후 문자열 추출
                project_name = remote_url.split("/")[-1]
                if project_name:
                    return project_name
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # git이 없거나 timeout
        pass

    try:
        # 2. Git repository root directory name 사용 시도
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False
        )

        if result.returncode == 0:
            repo_root = result.stdout.strip()
            if repo_root:
                return Path(repo_root).name
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # git이 없거나 timeout
        pass

    # 3. 현재 작업 디렉토리 이름 사용 (fallback)
    return Path.cwd().name


def get_data_dir(subdir: str = "") -> Path:
    """
    프로젝트별 데이터 디렉토리 경로를 반환합니다.

    경로 형식: ~/.claude-flow/{project-name}/{subdir}/

    디렉토리가 없으면 자동으로 생성합니다.

    Args:
        subdir: 하위 디렉토리 이름 (예: "sessions", "logs", "cache")
               빈 문자열이면 프로젝트 루트 디렉토리 반환

    Returns:
        데이터 디렉토리 경로 (Path 객체)

    Examples:
        >>> get_data_dir("sessions")
        Path('/Users/username/.claude-flow/my-project/sessions')

        >>> get_data_dir("logs")
        Path('/Users/username/.claude-flow/my-project/logs')

        >>> get_data_dir()
        Path('/Users/username/.claude-flow/my-project')

    Notes:
        - 프로젝트 이름은 get_project_name()으로 자동 감지됩니다.
        - 디렉토리가 없으면 자동으로 생성됩니다 (parents=True, exist_ok=True).
        - 멀티 프로젝트 환경에서도 각 프로젝트의 데이터가 격리됩니다.
    """
    # 프로젝트 이름 자동 감지
    project_name = get_project_name()

    # 기본 데이터 디렉토리: ~/.claude-flow/{project-name}/
    home = Path.home()
    base_dir = home / ".claude-flow" / project_name

    # 하위 디렉토리가 지정되면 추가
    if subdir:
        data_dir = base_dir / subdir
    else:
        data_dir = base_dir

    # 디렉토리 생성 (없으면)
    data_dir.mkdir(parents=True, exist_ok=True)

    return data_dir
