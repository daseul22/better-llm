"""
통합 유틸리티 테스트

4개 유틸리티 모듈(string_utils, number_utils, date_utils, list_utils)의
주요 함수들을 통합적으로 테스트합니다.
"""

from datetime import datetime

import pytest

from src.utils.date_utils import days_between, format_date, is_weekend
from src.utils.list_utils import chunk, flatten, unique
from src.utils.number_utils import factorial, fibonacci, is_prime
from src.utils.string_utils import count_words, reverse, truncate


# ===========================
# String Utils Tests
# ===========================


def test_reverse_basic() -> None:
    """
    reverse 함수가 기본 문자열을 올바르게 뒤집는지 확인합니다.

    Examples:
        >>> reverse("hello")
        'olleh'
        >>> reverse("Python")
        'nohtyP'
    """
    assert reverse("hello") == "olleh"
    assert reverse("Python") == "nohtyP"


def test_reverse_unicode() -> None:
    """
    reverse 함수가 유니코드 문자열(한글)을 올바르게 뒤집는지 확인합니다.

    Examples:
        >>> reverse("안녕하세요")
        '요세하녕안'
        >>> reverse("")
        ''
    """
    assert reverse("안녕하세요") == "요세하녕안"
    assert reverse("") == ""


def test_truncate_basic() -> None:
    """
    truncate 함수가 긴 문자열을 올바르게 자르는지 확인합니다.

    Examples:
        >>> truncate("Hello, World!", 10)
        'Hello, ...'
        >>> truncate("Short", 10)
        'Short'
    """
    assert truncate("Hello, World!", 10) == "Hello, ..."
    assert truncate("Short", 10) == "Short"


def test_truncate_edge_cases() -> None:
    """
    truncate 함수의 엣지 케이스를 테스트합니다.

    Examples:
        >>> truncate("Hello", 5)
        'Hello'
        >>> truncate("Hello", 3)
        '...'
    """
    assert truncate("Hello", 5) == "Hello"
    assert truncate("Hello", 3) == "..."


def test_count_words_basic() -> None:
    """
    count_words 함수가 일반적인 문자열의 단어 수를 올바르게 세는지 확인합니다.

    Examples:
        >>> count_words("Hello world")
        2
        >>> count_words("Python is awesome")
        3
    """
    assert count_words("Hello world") == 2
    assert count_words("Python is awesome") == 3


def test_count_words_whitespace() -> None:
    """
    count_words 함수가 공백 및 빈 문자열을 올바르게 처리하는지 확인합니다.

    Examples:
        >>> count_words("  Multiple   spaces   ")
        2
        >>> count_words("")
        0
    """
    assert count_words("  Multiple   spaces   ") == 2
    assert count_words("") == 0


# ===========================
# Number Utils Tests
# ===========================


def test_fibonacci_basic() -> None:
    """
    fibonacci 함수가 기본 케이스를 올바르게 계산하는지 확인합니다.

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
    """
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1


def test_fibonacci_larger_values() -> None:
    """
    fibonacci 함수가 더 큰 값을 올바르게 계산하는지 확인합니다.

    Examples:
        >>> fibonacci(5)
        5
        >>> fibonacci(10)
        55
    """
    assert fibonacci(5) == 5
    assert fibonacci(10) == 55


def test_factorial_basic() -> None:
    """
    factorial 함수가 기본 케이스를 올바르게 계산하는지 확인합니다.

    Examples:
        >>> factorial(0)
        1
        >>> factorial(1)
        1
    """
    assert factorial(0) == 1
    assert factorial(1) == 1


def test_factorial_larger_values() -> None:
    """
    factorial 함수가 더 큰 값을 올바르게 계산하는지 확인합니다.

    Examples:
        >>> factorial(5)
        120
        >>> factorial(10)
        3628800
    """
    assert factorial(5) == 120
    assert factorial(10) == 3628800


def test_is_prime_true_cases() -> None:
    """
    is_prime 함수가 소수를 올바르게 판별하는지 확인합니다.

    Examples:
        >>> is_prime(2)
        True
        >>> is_prime(17)
        True
    """
    assert is_prime(2) is True
    assert is_prime(17) is True


def test_is_prime_false_cases() -> None:
    """
    is_prime 함수가 합성수와 특수 케이스를 올바르게 판별하는지 확인합니다.

    Examples:
        >>> is_prime(1)
        False
        >>> is_prime(4)
        False
    """
    assert is_prime(1) is False
    assert is_prime(4) is False


# ===========================
# Date Utils Tests
# ===========================


def test_format_date_iso_to_slash() -> None:
    """
    format_date 함수가 ISO 형식을 슬래시 형식으로 변환하는지 확인합니다.

    Examples:
        >>> format_date("2025-01-15", "%Y-%m-%d", "%d/%m/%Y")
        '15/01/2025'
    """
    assert format_date("2025-01-15", "%Y-%m-%d", "%d/%m/%Y") == "15/01/2025"


def test_format_date_slash_to_iso() -> None:
    """
    format_date 함수가 슬래시 형식을 ISO 형식으로 변환하는지 확인합니다.

    Examples:
        >>> format_date("15/01/2025", "%d/%m/%Y", "%Y-%m-%d")
        '2025-01-15'
    """
    assert format_date("15/01/2025", "%d/%m/%Y", "%Y-%m-%d") == "2025-01-15"


def test_days_between_positive() -> None:
    """
    days_between 함수가 미래 날짜까지의 일수를 올바르게 계산하는지 확인합니다.

    Examples:
        >>> days_between("2025-01-01", "2025-01-15")
        14
    """
    assert days_between("2025-01-01", "2025-01-15") == 14


def test_days_between_negative() -> None:
    """
    days_between 함수가 과거 날짜까지의 일수를 올바르게 계산하는지 확인합니다.

    Examples:
        >>> days_between("2025-01-15", "2025-01-01")
        -14
    """
    assert days_between("2025-01-15", "2025-01-01") == -14


def test_is_weekend_true() -> None:
    """
    is_weekend 함수가 주말을 올바르게 판별하는지 확인합니다.

    Note:
        2025-01-18은 토요일, 2025-01-19는 일요일입니다.
    """
    assert is_weekend("2025-01-18") is True  # 토요일
    assert is_weekend("2025-01-19") is True  # 일요일


def test_is_weekend_false() -> None:
    """
    is_weekend 함수가 평일을 올바르게 판별하는지 확인합니다.

    Note:
        2025-01-20은 월요일, 2025-01-17은 금요일입니다.
    """
    assert is_weekend("2025-01-20") is False  # 월요일
    assert is_weekend("2025-01-17") is False  # 금요일


# ===========================
# List Utils Tests
# ===========================


def test_flatten_nested() -> None:
    """
    flatten 함수가 중첩 리스트를 올바르게 평탄화하는지 확인합니다.

    Examples:
        >>> flatten([1, [2, 3], [4, [5, 6]]])
        [1, 2, 3, 4, 5, 6]
    """
    assert flatten([1, [2, 3], [4, [5, 6]]]) == [1, 2, 3, 4, 5, 6]


def test_flatten_simple() -> None:
    """
    flatten 함수가 단순 리스트를 올바르게 처리하는지 확인합니다.

    Examples:
        >>> flatten([[1, 2], [3, 4]])
        [1, 2, 3, 4]
        >>> flatten([1, 2, 3])
        [1, 2, 3]
    """
    assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]
    assert flatten([1, 2, 3]) == [1, 2, 3]


def test_unique_basic() -> None:
    """
    unique 함수가 중복을 제거하고 순서를 유지하는지 확인합니다.

    Examples:
        >>> unique([1, 2, 2, 3, 1, 4])
        [1, 2, 3, 4]
    """
    assert unique([1, 2, 2, 3, 1, 4]) == [1, 2, 3, 4]


def test_unique_strings() -> None:
    """
    unique 함수가 문자열 리스트에서 중복을 제거하는지 확인합니다.

    Examples:
        >>> unique(["a", "b", "a", "c"])
        ['a', 'b', 'c']
        >>> unique([])
        []
    """
    assert unique(["a", "b", "a", "c"]) == ["a", "b", "c"]
    assert unique([]) == []


def test_chunk_basic() -> None:
    """
    chunk 함수가 리스트를 올바르게 분할하는지 확인합니다.

    Examples:
        >>> chunk([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_exact_division() -> None:
    """
    chunk 함수가 정확히 나누어떨어지는 경우를 올바르게 처리하는지 확인합니다.

    Examples:
        >>> chunk([1, 2, 3, 4, 5, 6], 3)
        [[1, 2, 3], [4, 5, 6]]
        >>> chunk([1, 2, 3], 5)
        [[1, 2, 3]]
    """
    assert chunk([1, 2, 3, 4, 5, 6], 3) == [[1, 2, 3], [4, 5, 6]]
    assert chunk([1, 2, 3], 5) == [[1, 2, 3]]
