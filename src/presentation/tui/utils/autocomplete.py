"""
자동 완성 엔진 모듈

슬래시 커맨드 자동 완성 기능 제공
"""

from typing import List, Optional


class AutocompleteEngine:
    """
    자동 완성 엔진 클래스

    Tab 키로 슬래시 커맨드를 자동 완성
    """

    # 사용 가능한 슬래시 커맨드 목록
    SLASH_COMMANDS = [
        "/help",
        "/init",
        "/load",
        "/clear",
    ]

    @staticmethod
    def get_completions(partial_input: str) -> List[str]:
        """
        부분 입력에 대한 자동 완성 후보 반환

        Args:
            partial_input: 부분 입력 문자열

        Returns:
            자동 완성 후보 리스트
        """
        if not partial_input or not partial_input.startswith("/"):
            return []

        # 부분 입력과 일치하는 커맨드 찾기
        matches = [
            cmd for cmd in AutocompleteEngine.SLASH_COMMANDS
            if cmd.startswith(partial_input.lower())
        ]

        return matches

    @staticmethod
    def complete(partial_input: str) -> Optional[str]:
        """
        부분 입력을 자동 완성

        Args:
            partial_input: 부분 입력 문자열

        Returns:
            자동 완성된 문자열, 후보가 없거나 여러 개면 None
        """
        matches = AutocompleteEngine.get_completions(partial_input)

        if len(matches) == 1:
            return matches[0]

        # 여러 후보가 있으면 공통 접두사까지만 완성
        if len(matches) > 1:
            return AutocompleteEngine._get_common_prefix(matches)

        return None

    @staticmethod
    def _get_common_prefix(strings: List[str]) -> str:
        """
        문자열 리스트의 공통 접두사 찾기

        Args:
            strings: 문자열 리스트

        Returns:
            공통 접두사
        """
        if not strings:
            return ""

        # 첫 번째 문자열을 기준으로 비교
        prefix = strings[0]

        for s in strings[1:]:
            # 공통 접두사 길이 찾기
            i = 0
            while i < len(prefix) and i < len(s) and prefix[i] == s[i]:
                i += 1
            prefix = prefix[:i]

            if not prefix:
                break

        return prefix
