"""
LayoutManager 단위 테스트
"""

import pytest

from src.presentation.tui.managers.layout_manager import (
    LayoutManager,
    LayoutMode,
    PanelDimensions,
    LayoutConfig,
)


class TestLayoutManager:
    """LayoutManager 테스트 클래스"""

    def test_init(self):
        """초기화 테스트"""
        manager = LayoutManager()
        assert manager is not None
        assert manager.get_current_mode() is None

    def test_calculate_layout_large(self):
        """Large 레이아웃 계산 테스트"""
        manager = LayoutManager()
        layout = manager.calculate_layout((120, 40))

        assert layout.mode == LayoutMode.LARGE
        assert layout.terminal_size == (120, 40)
        assert "output" in layout.panels
        assert "metrics" in layout.panels
        # Large 모드에서는 메트릭 패널이 보여야 함
        assert layout.panels["metrics"].width > 0

    def test_calculate_layout_medium(self):
        """Medium 레이아웃 계산 테스트"""
        manager = LayoutManager()
        layout = manager.calculate_layout((100, 30))

        assert layout.mode == LayoutMode.MEDIUM
        assert layout.terminal_size == (100, 30)
        # Medium 모드에서는 메트릭 패널이 숨겨져야 함
        assert layout.panels["metrics"].width == 0

    def test_calculate_layout_small(self):
        """Small 레이아웃 계산 테스트"""
        manager = LayoutManager()
        layout = manager.calculate_layout((60, 20))

        assert layout.mode == LayoutMode.SMALL
        assert layout.terminal_size == (60, 20)
        # Small 모드에서는 메트릭과 워크플로우 패널이 숨겨져야 함
        assert layout.panels["metrics"].width == 0
        assert layout.panels["workflow"].width == 0

    def test_resize_panels(self):
        """패널 크기 조정 테스트"""
        manager = LayoutManager()
        manager.calculate_layout((100, 30))

        manager.resize_panels("output", (80, 20))

        width, height = manager.get_panel_dimensions("output")
        assert width == 80
        assert height == 20

    def test_resize_panels_nonexistent(self):
        """존재하지 않는 패널 크기 조정 시 에러 발생 테스트"""
        manager = LayoutManager()

        with pytest.raises(KeyError) as exc_info:
            manager.resize_panels("nonexistent", (80, 20))

        assert "not found" in str(exc_info.value).lower()

    def test_resize_panels_below_minimum(self):
        """최소 크기보다 작게 조정 시 에러 발생 테스트"""
        manager = LayoutManager()
        manager.calculate_layout((100, 30))

        with pytest.raises(ValueError) as exc_info:
            manager.resize_panels("output", (10, 5))

        assert "at least" in str(exc_info.value).lower()

    def test_get_panel_dimensions(self):
        """패널 차원 조회 테스트"""
        manager = LayoutManager()
        manager.calculate_layout((100, 30))

        width, height = manager.get_panel_dimensions("output")
        assert width > 0
        assert height > 0

    def test_get_panel_dimensions_nonexistent(self):
        """존재하지 않는 패널 차원 조회 시 에러 발생 테스트"""
        manager = LayoutManager()
        manager.calculate_layout((100, 30))

        with pytest.raises(KeyError) as exc_info:
            manager.get_panel_dimensions("nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_get_panel_position(self):
        """패널 위치 조회 테스트"""
        manager = LayoutManager()
        manager.calculate_layout((100, 30))

        x, y = manager.get_panel_position("output")
        assert x >= 0
        assert y >= 0

    def test_is_panel_visible(self):
        """패널 표시 여부 확인 테스트"""
        manager = LayoutManager()
        manager.calculate_layout((60, 20))  # Small mode

        assert manager.is_panel_visible("output") is True
        assert manager.is_panel_visible("metrics") is False

    def test_is_panel_visible_nonexistent(self):
        """존재하지 않는 패널 표시 여부 확인 테스트"""
        manager = LayoutManager()
        manager.calculate_layout((100, 30))

        assert manager.is_panel_visible("nonexistent") is False

    def test_get_current_mode(self):
        """현재 레이아웃 모드 조회 테스트"""
        manager = LayoutManager()

        assert manager.get_current_mode() is None

        manager.calculate_layout((120, 40))
        assert manager.get_current_mode() == LayoutMode.LARGE

    def test_get_terminal_size(self):
        """터미널 크기 조회 테스트"""
        manager = LayoutManager()

        assert manager.get_terminal_size() is None

        manager.calculate_layout((100, 30))
        assert manager.get_terminal_size() == (100, 30)

    def test_list_panels(self):
        """패널 목록 조회 테스트"""
        manager = LayoutManager()
        manager.calculate_layout((100, 30))

        panels = manager.list_panels()
        assert len(panels) > 0
        assert "output" in panels
        assert "input" in panels

    def test_get_visible_panels(self):
        """표시되는 패널 목록 조회 테스트"""
        manager = LayoutManager()
        manager.calculate_layout((60, 20))  # Small mode

        visible = manager.get_visible_panels()
        assert "output" in visible
        assert "input" in visible
        assert "metrics" not in visible

    def test_reset_layout(self):
        """레이아웃 초기화 테스트"""
        manager = LayoutManager()
        manager.calculate_layout((100, 30))

        manager.reset_layout()

        assert manager.get_current_mode() is None
        assert len(manager.list_panels()) == 0

    def test_set_min_panel_size(self):
        """패널 최소 크기 설정 테스트"""
        manager = LayoutManager()
        manager.set_min_panel_size("output", (50, 15))

        min_size = manager.get_min_panel_size("output")
        assert min_size == (50, 15)

    def test_get_min_panel_size(self):
        """패널 최소 크기 조회 테스트"""
        manager = LayoutManager()

        min_size = manager.get_min_panel_size("output")
        assert min_size is not None
        assert min_size[0] > 0
        assert min_size[1] > 0

    def test_get_min_panel_size_nonexistent(self):
        """존재하지 않는 패널 최소 크기 조회 테스트"""
        manager = LayoutManager()

        min_size = manager.get_min_panel_size("nonexistent")
        assert min_size is None

    def test_layout_mode_detection(self):
        """레이아웃 모드 자동 감지 테스트"""
        manager = LayoutManager()

        # Large
        layout = manager.calculate_layout((120, 30))
        assert layout.mode == LayoutMode.LARGE

        # Medium
        layout = manager.calculate_layout((90, 25))
        assert layout.mode == LayoutMode.MEDIUM

        # Small
        layout = manager.calculate_layout((70, 20))
        assert layout.mode == LayoutMode.SMALL

    def test_panel_dimensions_dataclass(self):
        """PanelDimensions 데이터클래스 테스트"""
        dims = PanelDimensions(width=100, height=30, x=0, y=10)

        assert dims.width == 100
        assert dims.height == 30
        assert dims.x == 0
        assert dims.y == 10

    def test_layout_config_dataclass(self):
        """LayoutConfig 데이터클래스 테스트"""
        panels = {
            "output": PanelDimensions(100, 30, 0, 0)
        }
        config = LayoutConfig(
            mode=LayoutMode.LARGE,
            panels=panels,
            terminal_size=(120, 40)
        )

        assert config.mode == LayoutMode.LARGE
        assert len(config.panels) == 1
        assert config.terminal_size == (120, 40)

    def test_multiple_layout_calculations(self):
        """여러 번 레이아웃 계산 테스트"""
        manager = LayoutManager()

        # 첫 번째 계산
        layout1 = manager.calculate_layout((120, 40))
        assert layout1.mode == LayoutMode.LARGE

        # 두 번째 계산 (크기 변경)
        layout2 = manager.calculate_layout((80, 24))
        assert layout2.mode == LayoutMode.MEDIUM

        # 현재 모드가 업데이트되었는지 확인
        assert manager.get_current_mode() == LayoutMode.MEDIUM
