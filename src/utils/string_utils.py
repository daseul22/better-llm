"""
문자열 처리 유틸리티

기본적인 문자열 조작 함수들을 제공합니다.
"""


def reverse(text: str) -> str:
    """
    문자열을 뒤집습니다.

    Args:
        text: 뒤집을 문자열

    Returns:
        뒤집힌 문자열

    Examples:
        >>> reverse("hello")
        'olleh'

        >>> reverse("Python")
        'nohtyP'

        >>> reverse("안녕하세요")
        '요세하녕안'

        >>> reverse("")
        ''

    Notes:
        - 빈 문자열도 안전하게 처리됩니다.
        - 유니코드 문자열(한글, 이모지 등)도 올바르게 뒤집습니다.
    """
    return text[::-1]


def truncate(text: str, max_length: int) -> str:
    """
    문자열을 지정된 최대 길이로 자릅니다.

    max_length를 초과하는 경우 '...'를 추가하여 잘렸음을 표시합니다.
    '...'는 max_length에 포함되므로 실제 텍스트는 (max_length - 3)까지만 표시됩니다.

    Args:
        text: 자를 문자열
        max_length: 최대 길이 (양의 정수, 최소 4 이상 권장)

    Returns:
        잘린 문자열 (필요시 '...' 포함)

    Raises:
        ValueError: max_length가 0 이하인 경우

    Examples:
        >>> truncate("Hello, World!", 10)
        'Hello, ...'

        >>> truncate("Short", 10)
        'Short'

        >>> truncate("안녕하세요, 반갑습니다!", 8)
        '안녕하세...'

        >>> truncate("Hello", 5)
        'Hello'

        >>> truncate("Hello", 3)
        '...'

    Notes:
        - max_length가 텍스트 길이보다 크거나 같으면 원본을 그대로 반환합니다.
        - max_length가 3 이하인 경우 '...'만 반환됩니다.
        - 단어 경계를 고려하지 않으므로 단어 중간에서 잘릴 수 있습니다.
    """
    if max_length <= 0:
        raise ValueError(f"max_length must be positive, got {max_length}")

    if len(text) <= max_length:
        return text

    # max_length가 3 이하면 '...'만 반환
    if max_length <= 3:
        return "..."

    # (max_length - 3)까지 자르고 '...' 추가
    return text[: max_length - 3] + "..."


def count_words(text: str) -> int:
    """
    문자열의 단어 개수를 셉니다.

    공백(스페이스, 탭, 줄바꿈 등)으로 구분된 단어들을 셉니다.
    연속된 공백은 하나로 처리되며, 빈 문자열은 0을 반환합니다.

    Args:
        text: 단어를 셀 문자열

    Returns:
        단어 개수 (음이 아닌 정수)

    Examples:
        >>> count_words("Hello world")
        2

        >>> count_words("Python is awesome")
        3

        >>> count_words("  Multiple   spaces   ")
        2

        >>> count_words("")
        0

        >>> count_words("   ")
        0

        >>> count_words("안녕하세요 반갑습니다")
        2

        >>> count_words("one\\ntwo\\nthree")
        3

    Notes:
        - 공백 문자는 스페이스, 탭, 줄바꿈 등 모든 whitespace를 포함합니다.
        - 한글이나 다른 유니코드 문자도 공백으로 구분되면 별도 단어로 계산됩니다.
        - 구두점은 단어의 일부로 간주됩니다 (예: "hello," -> 1 단어).
    """
    # strip()으로 앞뒤 공백 제거 후 split()으로 분리
    # split()은 연속된 공백을 하나로 처리하고, 빈 문자열은 빈 리스트 반환
    words = text.strip().split()
    return len(words)
