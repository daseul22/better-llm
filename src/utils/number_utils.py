"""숫자 계산 유틸리티 모듈.

이 모듈은 피보나치 수열, 팩토리얼, 소수 판별 등 기본적인 수학 함수를 제공합니다.
"""


def fibonacci(n: int) -> int:
    """n번째 피보나치 수를 계산합니다 (0-indexed).

    피보나치 수열은 F(0) = 0, F(1) = 1이며, F(n) = F(n-1) + F(n-2)로 정의됩니다.
    반복문을 사용하여 O(n) 시간 복잡도로 계산합니다.

    Args:
        n: 계산할 피보나치 수의 인덱스 (0 이상의 정수)

    Returns:
        n번째 피보나치 수

    Raises:
        ValueError: n이 음수인 경우

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(5)
        5
        >>> fibonacci(10)
        55
    """
    if n < 0:
        raise ValueError(f"n은 0 이상이어야 합니다. 입력값: {n}")

    if n == 0:
        return 0
    if n == 1:
        return 1

    # 반복문으로 구현 (재귀보다 효율적)
    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr

    return curr


def factorial(n: int) -> int:
    """n의 팩토리얼(n!)을 계산합니다.

    팩토리얼은 n! = n × (n-1) × ... × 2 × 1로 정의되며, 0! = 1입니다.
    반복문을 사용하여 O(n) 시간 복잡도로 계산합니다.

    Args:
        n: 팩토리얼을 계산할 정수 (0 이상)

    Returns:
        n의 팩토리얼 값

    Raises:
        ValueError: n이 음수인 경우

    Examples:
        >>> factorial(0)
        1
        >>> factorial(1)
        1
        >>> factorial(5)
        120
        >>> factorial(10)
        3628800
    """
    if n < 0:
        raise ValueError(f"n은 0 이상이어야 합니다. 입력값: {n}")

    if n == 0 or n == 1:
        return 1

    result = 1
    for i in range(2, n + 1):
        result *= i

    return result


def is_prime(n: int) -> bool:
    """주어진 수가 소수인지 판별합니다.

    소수는 1보다 크고 1과 자기 자신으로만 나누어떨어지는 자연수입니다.
    √n까지만 확인하는 최적화된 알고리즘을 사용합니다 (O(√n) 시간 복잡도).

    Args:
        n: 소수 여부를 판별할 정수

    Returns:
        n이 소수이면 True, 아니면 False

    Examples:
        >>> is_prime(2)
        True
        >>> is_prime(17)
        True
        >>> is_prime(1)
        False
        >>> is_prime(4)
        False
        >>> is_prime(-5)
        False
        >>> is_prime(0)
        False
    """
    # 2보다 작은 수는 소수가 아님
    if n < 2:
        return False

    # 2는 유일한 짝수 소수
    if n == 2:
        return True

    # 짝수는 소수가 아님 (2 제외)
    if n % 2 == 0:
        return False

    # 3부터 √n까지 홀수로만 확인
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2

    return True
