"""
AutocompleteEngine 클래스 단위 테스트

테스트 항목:
- 슬래시 커맨드 자동 완성
- 공통 접두사 찾기
- 엣지 케이스 처리
"""

import pytest
from src.presentation.tui.utils.autocomplete import AutocompleteEngine


class TestAutocompleteEngine:
    """AutocompleteEngine 클래스 테스트"""

    def test_get_completions_empty_input(self):
        """빈 입력에 대한 자동 완성 테스트"""
        result = AutocompleteEngine.get_completions("")
        assert result == []

    def test_get_completions_no_slash(self):
        """슬래시가 없는 입력 테스트"""
        result = AutocompleteEngine.get_completions("help")
        assert result == []

    def test_get_completions_single_slash(self):
        """슬래시만 입력했을 때 모든 커맨드 반환"""
        result = AutocompleteEngine.get_completions("/")
        assert len(result) == 4
        assert "/help" in result
        assert "/init" in result
        assert "/load" in result
        assert "/clear" in result

    def test_get_completions_partial_match(self):
        """부분 일치 테스트"""
        # /h로 시작하는 커맨드
        result = AutocompleteEngine.get_completions("/h")
        assert result == ["/help"]

        # /l로 시작하는 커맨드
        result = AutocompleteEngine.get_completions("/l")
        assert result == ["/load"]

        # /c로 시작하는 커맨드
        result = AutocompleteEngine.get_completions("/c")
        assert result == ["/clear"]

    def test_get_completions_full_match(self):
        """완전 일치 테스트"""
        result = AutocompleteEngine.get_completions("/help")
        assert result == ["/help"]

    def test_get_completions_no_match(self):
        """일치하는 커맨드가 없는 경우"""
        result = AutocompleteEngine.get_completions("/xyz")
        assert result == []

    def test_complete_single_match(self):
        """단일 매칭 자동 완성 테스트"""
        result = AutocompleteEngine.complete("/h")
        assert result == "/help"

        result = AutocompleteEngine.complete("/ini")
        assert result == "/init"

    def test_complete_multiple_matches(self):
        """여러 매칭 시 공통 접두사 반환 테스트"""
        # 현재 커맨드 목록에서는 각 커맨드가 unique하므로
        # 슬래시만 입력 시 공통 접두사는 "/"
        result = AutocompleteEngine.complete("/")
        assert result == "/"

    def test_complete_no_match(self):
        """매칭 없을 때 None 반환"""
        result = AutocompleteEngine.complete("/xyz")
        assert result is None

    def test_complete_empty_input(self):
        """빈 입력에 대한 완성 테스트"""
        result = AutocompleteEngine.complete("")
        assert result is None

    def test_complete_exact_match(self):
        """정확히 일치하는 경우"""
        result = AutocompleteEngine.complete("/help")
        assert result == "/help"

    def test_get_common_prefix_empty_list(self):
        """빈 리스트의 공통 접두사"""
        result = AutocompleteEngine._get_common_prefix([])
        assert result == ""

    def test_get_common_prefix_single_string(self):
        """단일 문자열의 공통 접두사"""
        result = AutocompleteEngine._get_common_prefix(["/help"])
        assert result == "/help"

    def test_get_common_prefix_multiple_strings(self):
        """여러 문자열의 공통 접두사"""
        test_cases = [
            (["/help", "/hello"], "/hel"),
            (["/init", "/info"], "/in"),
            (["/clear", "/clean"], "/clea"),  # 수정: 실제 공통 접두사는 /clea
            (["/abc", "/def"], "/"),  # 수정: 공통 접두사는 /
            (["/same", "/same"], "/same"),
        ]

        for input_list, expected in test_cases:
            result = AutocompleteEngine._get_common_prefix(input_list)
            assert result == expected, f"Failed for input: {input_list}"

    def test_case_insensitive_matching(self):
        """대소문자 무시 매칭 테스트"""
        # 입력은 소문자로 변환되어야 함
        result = AutocompleteEngine.get_completions("/H")
        assert result == ["/help"]

        result = AutocompleteEngine.get_completions("/HELP")
        assert result == ["/help"]

    def test_complete_with_extra_text(self):
        """커맨드 뒤에 추가 텍스트가 있는 경우"""
        # /help 뒤에 공백이나 인자가 있으면 매칭 안됨
        result = AutocompleteEngine.get_completions("/help ")
        assert result == []

        result = AutocompleteEngine.get_completions("/load session123")
        assert result == []

    def test_slash_commands_immutability(self):
        """SLASH_COMMANDS 리스트가 변경되지 않는지 확인"""
        original_commands = AutocompleteEngine.SLASH_COMMANDS.copy()

        # 자동 완성 실행
        AutocompleteEngine.get_completions("/h")
        AutocompleteEngine.complete("/help")

        # 원본 리스트가 변경되지 않았는지 확인
        assert AutocompleteEngine.SLASH_COMMANDS == original_commands
