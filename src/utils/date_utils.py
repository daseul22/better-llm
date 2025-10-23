"""
날짜 변환 유틸리티 함수

날짜 형식 변환, 날짜 계산, 주말 확인 등의 날짜 관련 유틸리티를 제공합니다.
"""

from datetime import datetime, timedelta


def format_date(date_str: str, input_format: str, output_format: str) -> str:
    """
    날짜 문자열을 다른 형식으로 변환합니다.

    Args:
        date_str: 변환할 날짜 문자열 (예: "2025-01-15")
        input_format: 입력 날짜의 형식 (예: "%Y-%m-%d")
        output_format: 출력 날짜의 형식 (예: "%d/%m/%Y")

    Returns:
        변환된 날짜 문자열

    Raises:
        ValueError: 날짜 문자열이 입력 형식과 맞지 않을 때

    Examples:
        >>> format_date("2025-01-15", "%Y-%m-%d", "%d/%m/%Y")
        '15/01/2025'

        >>> format_date("15/01/2025", "%d/%m/%Y", "%Y-%m-%d")
        '2025-01-15'

        >>> format_date("2025-01-15", "%Y-%m-%d", "%B %d, %Y")
        'January 15, 2025'

    Notes:
        - 날짜 형식 지시자는 Python datetime.strftime() 규칙을 따릅니다.
        - 자주 사용되는 형식:
          - "%Y-%m-%d": ISO 8601 형식 (2025-01-15)
          - "%d/%m/%Y": DD/MM/YYYY 형식 (15/01/2025)
          - "%m/%d/%Y": MM/DD/YYYY 형식 (01/15/2025)
          - "%B %d, %Y": 전체 월 이름 (January 15, 2025)
          - "%Y-%m-%d %H:%M:%S": ISO 8601 날짜/시간 형식
    """
    try:
        # 입력 형식으로 파싱
        date_obj = datetime.strptime(date_str, input_format)
        # 출력 형식으로 변환
        return date_obj.strftime(output_format)
    except ValueError as e:
        raise ValueError(
            f"날짜 문자열 '{date_str}'이(가) 입력 형식 '{input_format}'과(와) "
            f"맞지 않습니다: {e}"
        ) from e


def days_between(start: str, end: str, date_format: str = "%Y-%m-%d") -> int:
    """
    두 날짜 사이의 일수를 계산합니다.

    Args:
        start: 시작 날짜 문자열 (예: "2025-01-01")
        end: 종료 날짜 문자열 (예: "2025-01-15")
        date_format: 날짜 형식 (기본값: "%Y-%m-%d")

    Returns:
        두 날짜 사이의 일수 (양수: end가 미래, 음수: end가 과거)

    Raises:
        ValueError: 날짜 문자열이 형식과 맞지 않을 때

    Examples:
        >>> days_between("2025-01-01", "2025-01-15")
        14

        >>> days_between("2025-01-15", "2025-01-01")
        -14

        >>> days_between("01/01/2025", "15/01/2025", "%d/%m/%Y")
        14

        >>> days_between("2025-01-01", "2025-01-01")
        0

    Notes:
        - 시간 정보는 무시되고 날짜만 비교됩니다.
        - 결과는 정수로 반환됩니다 (부분일 무시).
        - end가 start보다 미래이면 양수, 과거이면 음수를 반환합니다.
        - 같은 날짜면 0을 반환합니다.
    """
    try:
        # 날짜 문자열을 datetime 객체로 변환
        start_date = datetime.strptime(start, date_format)
        end_date = datetime.strptime(end, date_format)

        # 일수 차이 계산
        delta = end_date - start_date
        return delta.days
    except ValueError as e:
        raise ValueError(
            f"날짜 문자열이 형식 '{date_format}'과(와) 맞지 않습니다: {e}"
        ) from e


def is_weekend(date_str: str, date_format: str = "%Y-%m-%d") -> bool:
    """
    주어진 날짜가 주말(토요일 또는 일요일)인지 확인합니다.

    Args:
        date_str: 확인할 날짜 문자열 (예: "2025-01-15")
        date_format: 날짜 형식 (기본값: "%Y-%m-%d")

    Returns:
        주말이면 True, 평일이면 False

    Raises:
        ValueError: 날짜 문자열이 형식과 맞지 않을 때

    Examples:
        >>> is_weekend("2025-01-18")  # 토요일
        True

        >>> is_weekend("2025-01-19")  # 일요일
        True

        >>> is_weekend("2025-01-20")  # 월요일
        False

        >>> is_weekend("18/01/2025", "%d/%m/%Y")  # 토요일
        True

    Notes:
        - 토요일: weekday() == 5
        - 일요일: weekday() == 6
        - 월요일~금요일: weekday() == 0~4
        - weekday() 메서드는 0(월요일)부터 6(일요일)까지의 값을 반환합니다.
    """
    try:
        # 날짜 문자열을 datetime 객체로 변환
        date_obj = datetime.strptime(date_str, date_format)

        # 요일 확인 (0=월요일, 6=일요일)
        # 토요일(5) 또는 일요일(6)이면 True
        return date_obj.weekday() in (5, 6)
    except ValueError as e:
        raise ValueError(
            f"날짜 문자열 '{date_str}'이(가) 형식 '{date_format}'과(와) "
            f"맞지 않습니다: {e}"
        ) from e
