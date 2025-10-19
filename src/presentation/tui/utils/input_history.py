"""
입력 히스토리 관리 모듈

사용자가 입력한 명령어 히스토리를 관리하고, ↑↓ 키로 탐색할 수 있는 기능 제공
"""

from typing import List, Optional


class InputHistory:
    """
    입력 히스토리 관리 클래스

    최대 100개의 입력 히스토리를 유지하며, ↑↓ 키로 탐색 가능
    """

    def __init__(self, max_size: int = 100):
        """
        Args:
            max_size: 최대 히스토리 크기 (기본값: 100)
        """
        self._history: List[str] = []
        self._max_size = max_size
        self._current_index: Optional[int] = None  # None = 현재 입력 중
        self._temp_input: str = ""  # 임시로 저장된 현재 입력

    def add(self, entry: str) -> None:
        """
        히스토리에 항목 추가

        Args:
            entry: 추가할 입력 문자열
        """
        if not entry or not entry.strip():
            return

        # 중복 제거: 마지막 항목과 같으면 추가하지 않음
        if self._history and self._history[-1] == entry:
            return

        self._history.append(entry)

        # 최대 크기 초과 시 가장 오래된 항목 제거
        if len(self._history) > self._max_size:
            self._history.pop(0)

        # 인덱스 리셋
        self._current_index = None
        self._temp_input = ""

    def navigate_up(self, current_input: str = "") -> Optional[str]:
        """
        히스토리에서 이전 항목으로 이동 (↑ 키)

        Args:
            current_input: 현재 입력 중인 문자열

        Returns:
            이전 히스토리 항목, 없으면 None
        """
        if not self._history:
            return None

        # 처음 ↑ 누를 때: 현재 입력을 임시 저장
        if self._current_index is None:
            self._temp_input = current_input
            self._current_index = len(self._history) - 1
            return self._history[self._current_index]

        # 이미 탐색 중: 더 이전 항목으로 이동
        if self._current_index > 0:
            self._current_index -= 1
            return self._history[self._current_index]

        # 가장 오래된 항목에 도달
        return self._history[self._current_index]

    def navigate_down(self) -> Optional[str]:
        """
        히스토리에서 다음 항목으로 이동 (↓ 키)

        Returns:
            다음 히스토리 항목 또는 임시 저장된 현재 입력, 없으면 None
        """
        if self._current_index is None:
            return None

        # 다음 항목으로 이동
        if self._current_index < len(self._history) - 1:
            self._current_index += 1
            return self._history[self._current_index]

        # 마지막 항목에 도달: 임시 저장된 현재 입력 복원
        self._current_index = None
        temp = self._temp_input
        self._temp_input = ""
        return temp

    def reset_navigation(self) -> None:
        """히스토리 탐색 상태 리셋"""
        self._current_index = None
        self._temp_input = ""

    def get_all(self) -> List[str]:
        """
        전체 히스토리 반환

        Returns:
            히스토리 리스트 (복사본)
        """
        return self._history.copy()

    def clear(self) -> None:
        """히스토리 초기화"""
        self._history.clear()
        self._current_index = None
        self._temp_input = ""

    def __len__(self) -> int:
        """히스토리 크기 반환"""
        return len(self._history)
