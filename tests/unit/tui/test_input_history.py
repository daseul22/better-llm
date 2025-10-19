"""
InputHistory 클래스 단위 테스트

테스트 항목:
- 히스토리 추가 및 중복 제거
- 최대 크기 제한
- 위/아래 네비게이션
- 임시 입력 저장 및 복원
- 초기화 및 리셋
"""

import pytest
from src.presentation.tui.utils.input_history import InputHistory


class TestInputHistory:
    """InputHistory 클래스 테스트"""

    def test_initialization(self):
        """초기화 테스트"""
        history = InputHistory(max_size=50)
        assert len(history) == 0
        assert history.get_all() == []

    def test_add_single_entry(self):
        """단일 항목 추가 테스트"""
        history = InputHistory()
        history.add("test command")

        assert len(history) == 1
        assert history.get_all() == ["test command"]

    def test_add_empty_entry(self):
        """빈 문자열 추가 시 무시되는지 테스트"""
        history = InputHistory()
        history.add("")
        history.add("   ")

        assert len(history) == 0

    def test_add_duplicate_entry(self):
        """연속 중복 항목 추가 시 무시되는지 테스트"""
        history = InputHistory()
        history.add("command1")
        history.add("command1")  # 중복
        history.add("command2")
        history.add("command1")  # 중복 아님 (마지막과 다름)

        assert len(history) == 3
        assert history.get_all() == ["command1", "command2", "command1"]

    def test_max_size_limit(self):
        """최대 크기 제한 테스트"""
        history = InputHistory(max_size=3)

        history.add("cmd1")
        history.add("cmd2")
        history.add("cmd3")
        history.add("cmd4")  # 가장 오래된 cmd1 제거됨

        assert len(history) == 3
        assert history.get_all() == ["cmd2", "cmd3", "cmd4"]

    def test_navigate_up_empty_history(self):
        """빈 히스토리에서 위로 네비게이션 테스트"""
        history = InputHistory()
        result = history.navigate_up()

        assert result is None

    def test_navigate_up_basic(self):
        """기본 위로 네비게이션 테스트"""
        history = InputHistory()
        history.add("cmd1")
        history.add("cmd2")
        history.add("cmd3")

        # 첫 번째 ↑: 마지막 항목
        assert history.navigate_up("current") == "cmd3"
        # 두 번째 ↑: 이전 항목
        assert history.navigate_up() == "cmd2"
        # 세 번째 ↑: 가장 오래된 항목
        assert history.navigate_up() == "cmd1"
        # 네 번째 ↑: 가장 오래된 항목 유지
        assert history.navigate_up() == "cmd1"

    def test_navigate_down_without_up(self):
        """위로 이동 없이 아래로 네비게이션 테스트"""
        history = InputHistory()
        history.add("cmd1")

        result = history.navigate_down()
        assert result is None

    def test_navigate_up_down_cycle(self):
        """위아래 네비게이션 순환 테스트"""
        history = InputHistory()
        history.add("cmd1")
        history.add("cmd2")
        history.add("cmd3")

        # ↑↑↑
        assert history.navigate_up("typing") == "cmd3"
        assert history.navigate_up() == "cmd2"
        assert history.navigate_up() == "cmd1"

        # ↓↓↓
        assert history.navigate_down() == "cmd2"
        assert history.navigate_down() == "cmd3"
        assert history.navigate_down() == "typing"  # 임시 입력 복원

    def test_temp_input_preservation(self):
        """임시 입력 보존 테스트"""
        history = InputHistory()
        history.add("previous")

        # 타이핑 중인 내용과 함께 ↑
        current_typing = "hello world"
        assert history.navigate_up(current_typing) == "previous"

        # ↓로 돌아왔을 때 타이핑 내용 복원
        assert history.navigate_down() == current_typing

    def test_reset_navigation(self):
        """네비게이션 리셋 테스트"""
        history = InputHistory()
        history.add("cmd1")
        history.add("cmd2")

        history.navigate_up("typing")
        history.reset_navigation()

        # 리셋 후 다시 위로 이동하면 마지막 항목부터 시작
        assert history.navigate_up() == "cmd2"

    def test_clear(self):
        """히스토리 초기화 테스트"""
        history = InputHistory()
        history.add("cmd1")
        history.add("cmd2")
        history.navigate_up()

        history.clear()

        assert len(history) == 0
        assert history.get_all() == []
        assert history.navigate_up() is None

    def test_get_all_returns_copy(self):
        """get_all()이 복사본을 반환하는지 테스트"""
        history = InputHistory()
        history.add("cmd1")

        all_items = history.get_all()
        all_items.append("cmd2")  # 복사본 수정

        # 원본은 변경되지 않아야 함
        assert len(history) == 1
        assert history.get_all() == ["cmd1"]

    def test_navigation_after_add(self):
        """항목 추가 후 네비게이션 상태 리셋 테스트"""
        history = InputHistory()
        history.add("cmd1")
        history.add("cmd2")

        # 네비게이션 시작
        history.navigate_up()

        # 새 항목 추가 (네비게이션 리셋됨)
        history.add("cmd3")

        # 다시 위로 이동하면 최신 항목부터 시작
        assert history.navigate_up() == "cmd3"

    def test_edge_case_single_item_navigation(self):
        """항목 1개일 때 네비게이션 테스트"""
        history = InputHistory()
        history.add("only_one")

        assert history.navigate_up() == "only_one"
        assert history.navigate_up() == "only_one"  # 계속 같은 값
        assert history.navigate_down() == ""  # 임시 입력이 빈 문자열
