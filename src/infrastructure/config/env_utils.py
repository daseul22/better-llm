"""환경변수 파싱 유틸리티

환경변수를 타입 안전하게 파싱하는 헬퍼 함수들을 제공합니다.
"""

import os
from typing import Optional


def parse_bool_env(var_name: str, default: bool = False) -> bool:
    """
    환경변수를 bool로 파싱

    다양한 형식을 지원합니다:
    - True: "true", "True", "TRUE", "1", "yes", "YES", "on", "ON"
    - False: "false", "False", "FALSE", "0", "no", "NO", "off", "OFF"
    - 기타: default 값 반환

    Args:
        var_name: 환경변수 이름
        default: 기본값 (환경변수가 없거나 파싱 실패 시)

    Returns:
        파싱된 bool 값

    Examples:
        >>> os.environ["MY_FLAG"] = "true"
        >>> parse_bool_env("MY_FLAG")
        True

        >>> os.environ["MY_FLAG"] = "FALSE"
        >>> parse_bool_env("MY_FLAG")
        False

        >>> parse_bool_env("NOT_SET", default=True)
        True
    """
    value = os.getenv(var_name, "").lower().strip()

    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False

    return default


def parse_int_env(var_name: str, default: int = 0) -> int:
    """
    환경변수를 int로 파싱

    Args:
        var_name: 환경변수 이름
        default: 기본값 (환경변수가 없거나 파싱 실패 시)

    Returns:
        파싱된 int 값

    Examples:
        >>> os.environ["PORT"] = "8080"
        >>> parse_int_env("PORT")
        8080

        >>> parse_int_env("NOT_SET", default=3000)
        3000
    """
    value = os.getenv(var_name, "").strip()

    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def parse_float_env(var_name: str, default: float = 0.0) -> float:
    """
    환경변수를 float로 파싱

    Args:
        var_name: 환경변수 이름
        default: 기본값 (환경변수가 없거나 파싱 실패 시)

    Returns:
        파싱된 float 값

    Examples:
        >>> os.environ["TIMEOUT"] = "30.5"
        >>> parse_float_env("TIMEOUT")
        30.5

        >>> parse_float_env("NOT_SET", default=60.0)
        60.0
    """
    value = os.getenv(var_name, "").strip()

    if not value:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def parse_str_env(var_name: str, default: str = "") -> str:
    """
    환경변수를 str로 파싱 (공백 제거)

    Args:
        var_name: 환경변수 이름
        default: 기본값 (환경변수가 없을 때)

    Returns:
        파싱된 str 값

    Examples:
        >>> os.environ["API_KEY"] = "  my-secret-key  "
        >>> parse_str_env("API_KEY")
        'my-secret-key'

        >>> parse_str_env("NOT_SET", default="default-key")
        'default-key'
    """
    return os.getenv(var_name, default).strip()
