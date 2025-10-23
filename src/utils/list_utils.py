"""
리스트 조작 유틸리티 함수

리스트의 평탄화, 중복 제거, 분할 등 자주 사용되는 유틸리티 함수를 제공합니다.
"""

from typing import Any, List, TypeVar


T = TypeVar("T")


def flatten(nested_list: List[Any]) -> List[Any]:
    """
    중첩된 리스트를 1차원 리스트로 평탄화합니다.

    재귀적으로 모든 중첩 레벨을 평탄화하며, 리스트가 아닌 요소는 그대로 유지됩니다.

    Args:
        nested_list: 평탄화할 중첩 리스트 (임의의 깊이 지원)

    Returns:
        1차원으로 평탄화된 리스트

    Examples:
        >>> flatten([1, [2, 3], [4, [5, 6]]])
        [1, 2, 3, 4, 5, 6]

        >>> flatten([[1, 2], [3, 4]])
        [1, 2, 3, 4]

        >>> flatten([1, 2, 3])
        [1, 2, 3]

        >>> flatten([])
        []

        >>> flatten([[[]]])
        []

    Notes:
        - 문자열은 리스트로 간주하지 않습니다 (문자열을 쪼개지 않음).
        - 딕셔너리, 세트 등 다른 컬렉션은 평탄화하지 않습니다.
    """
    result = []
    for item in nested_list:
        # 문자열은 리스트처럼 보이지만 평탄화하지 않음
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def unique(items: List[T]) -> List[T]:
    """
    리스트에서 중복을 제거하되 원래 순서를 유지합니다.

    set()과 달리 삽입 순서를 보존하며, 해시 불가능한 객체도 처리할 수 있습니다.

    Args:
        items: 중복을 제거할 리스트

    Returns:
        중복이 제거된 리스트 (순서 유지)

    Examples:
        >>> unique([1, 2, 2, 3, 1, 4])
        [1, 2, 3, 4]

        >>> unique(["a", "b", "a", "c"])
        ['a', 'b', 'c']

        >>> unique([])
        []

        >>> unique([1])
        [1]

        >>> unique([{"id": 1}, {"id": 2}, {"id": 1}])  # dict는 순서 유지하며 중복 제거
        [{'id': 1}, {'id': 2}]

    Notes:
        - 해시 가능한 객체는 dict를 사용하여 O(n) 성능 보장
        - 해시 불가능한 객체는 선형 탐색으로 처리 (성능 저하 가능)
        - 첫 번째 등장한 요소만 유지됩니다
    """
    seen = {}
    result = []
    for item in items:
        try:
            # 해시 가능한 객체 (int, str, tuple 등)
            if item not in seen:
                seen[item] = True
                result.append(item)
        except TypeError:
            # 해시 불가능한 객체 (dict, list 등)
            if item not in result:
                result.append(item)
    return result


def chunk(items: List[T], size: int) -> List[List[T]]:
    """
    리스트를 지정된 크기의 청크(덩어리)로 분할합니다.

    마지막 청크는 size보다 작을 수 있습니다.

    Args:
        items: 분할할 리스트
        size: 각 청크의 크기 (양의 정수)

    Returns:
        size 크기의 청크로 분할된 리스트

    Raises:
        ValueError: size가 1보다 작은 경우

    Examples:
        >>> chunk([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]

        >>> chunk([1, 2, 3, 4, 5, 6], 3)
        [[1, 2, 3], [4, 5, 6]]

        >>> chunk([1, 2, 3], 5)
        [[1, 2, 3]]

        >>> chunk([], 2)
        []

        >>> chunk([1, 2, 3], 1)
        [[1], [2], [3]]

    Notes:
        - size가 리스트 길이보다 크면 전체 리스트를 하나의 청크로 반환
        - 빈 리스트는 빈 리스트로 반환
    """
    if size < 1:
        raise ValueError(f"Chunk size must be at least 1, got {size}")

    result = []
    for i in range(0, len(items), size):
        result.append(items[i:i + size])
    return result
