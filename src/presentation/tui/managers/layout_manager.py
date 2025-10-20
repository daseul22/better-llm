"""
LayoutManager 모듈

TUI 레이아웃 관리 책임:
- 반응형 레이아웃 계산
- 패널 크기 조정
- 패널 차원 조회
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from infrastructure.logging import get_logger

logger = get_logger(__name__, component="LayoutManager")


class LayoutMode(str, Enum):
    """레이아웃 모드 정의"""
    LARGE = "large"      # width >= 120, height >= 30 (모든 패널 표시)
    MEDIUM = "medium"    # width >= 80, height >= 24 (메트릭 패널 토글 가능)
    SMALL = "small"      # width < 80 or height < 24 (메트릭 패널 자동 숨김)


@dataclass
class PanelDimensions:
    """
    패널 차원 정보

    Attributes:
        width: 너비 (문자 수)
        height: 높이 (라인 수)
        x: X 좌표
        y: Y 좌표
    """
    width: int
    height: int
    x: int = 0
    y: int = 0

    def __str__(self) -> str:
        return f"PanelDimensions(w={self.width}, h={self.height}, x={self.x}, y={self.y})"


@dataclass
class LayoutConfig:
    """
    레이아웃 설정

    Attributes:
        mode: 레이아웃 모드
        panels: 패널별 차원 정보
        terminal_size: 터미널 크기
    """
    mode: LayoutMode
    panels: Dict[str, PanelDimensions]
    terminal_size: Tuple[int, int]

    def __str__(self) -> str:
        return f"LayoutConfig(mode={self.mode}, size={self.terminal_size})"


class LayoutManager:
    """
    TUI 레이아웃 관리자

    터미널 크기에 따라 반응형 레이아웃을 계산하고 패널 크기를 조정합니다.

    Example:
        >>> manager = LayoutManager()
        >>> layout = manager.calculate_layout((120, 40))
        >>> print(layout.mode)
        LayoutMode.LARGE
        >>> dims = manager.get_panel_dimensions("output")
        >>> print(dims.width > 0)
        True
    """

    def __init__(self) -> None:
        """LayoutManager 초기화"""
        self._current_layout: Optional[LayoutConfig] = None
        self._panel_dimensions: Dict[str, PanelDimensions] = {}
        self._min_panel_sizes: Dict[str, Tuple[int, int]] = {
            "output": (40, 10),        # 최소 40x10
            "worker": (40, 10),        # 최소 40x10
            "metrics": (30, 5),        # 최소 30x5
            "workflow": (40, 5),       # 최소 40x5
            "input": (20, 3),          # 최소 20x3
        }
        logger.info("LayoutManager initialized")

    def calculate_layout(self, terminal_size: Tuple[int, int]) -> LayoutConfig:
        """
        터미널 크기에 따라 레이아웃을 계산합니다.

        Args:
            terminal_size: (width, height) 터미널 크기

        Returns:
            계산된 레이아웃 설정

        Example:
            >>> manager = LayoutManager()
            >>> layout = manager.calculate_layout((100, 30))
            >>> print(layout.mode)
            LayoutMode.MEDIUM
        """
        width, height = terminal_size

        # 레이아웃 모드 결정
        if width >= 120 and height >= 30:
            mode = LayoutMode.LARGE
        elif width >= 80 and height >= 24:
            mode = LayoutMode.MEDIUM
        else:
            mode = LayoutMode.SMALL

        # 패널 차원 계산
        panels = self._calculate_panel_dimensions(width, height, mode)

        # 레이아웃 설정 생성
        layout = LayoutConfig(
            mode=mode,
            panels=panels,
            terminal_size=terminal_size
        )

        self._current_layout = layout
        self._panel_dimensions = panels

        logger.info(f"Layout calculated: {layout}")

        return layout

    def _calculate_panel_dimensions(
        self,
        width: int,
        height: int,
        mode: LayoutMode
    ) -> Dict[str, PanelDimensions]:
        """
        레이아웃 모드에 따라 패널 차원을 계산합니다.

        Args:
            width: 터미널 너비
            height: 터미널 높이
            mode: 레이아웃 모드

        Returns:
            패널별 차원 정보
        """
        panels = {}

        if mode == LayoutMode.LARGE:
            # Large: 모든 패널 표시, 메트릭과 워크플로우 포함
            output_height = int(height * 0.35)
            worker_height = int(height * 0.35)
            metrics_height = int(height * 0.10)
            workflow_height = int(height * 0.10)
            input_height = int(height * 0.10)

            panels["output"] = PanelDimensions(
                width=width,
                height=output_height,
                x=0,
                y=0
            )
            panels["worker"] = PanelDimensions(
                width=width,
                height=worker_height,
                x=0,
                y=output_height
            )
            panels["metrics"] = PanelDimensions(
                width=width,
                height=metrics_height,
                x=0,
                y=output_height + worker_height
            )
            panels["workflow"] = PanelDimensions(
                width=width,
                height=workflow_height,
                x=0,
                y=output_height + worker_height + metrics_height
            )
            panels["input"] = PanelDimensions(
                width=width,
                height=input_height,
                x=0,
                y=output_height + worker_height + metrics_height + workflow_height
            )

        elif mode == LayoutMode.MEDIUM:
            # Medium: 메트릭 패널은 토글 가능
            output_height = int(height * 0.40)
            worker_height = int(height * 0.40)
            workflow_height = int(height * 0.10)
            input_height = int(height * 0.10)

            panels["output"] = PanelDimensions(
                width=width,
                height=output_height,
                x=0,
                y=0
            )
            panels["worker"] = PanelDimensions(
                width=width,
                height=worker_height,
                x=0,
                y=output_height
            )
            panels["metrics"] = PanelDimensions(
                width=0,  # 숨김
                height=0,
                x=0,
                y=0
            )
            panels["workflow"] = PanelDimensions(
                width=width,
                height=workflow_height,
                x=0,
                y=output_height + worker_height
            )
            panels["input"] = PanelDimensions(
                width=width,
                height=input_height,
                x=0,
                y=output_height + worker_height + workflow_height
            )

        else:  # LayoutMode.SMALL
            # Small: 메트릭과 워크플로우 숨김
            output_height = int(height * 0.45)
            worker_height = int(height * 0.45)
            input_height = int(height * 0.10)

            panels["output"] = PanelDimensions(
                width=width,
                height=output_height,
                x=0,
                y=0
            )
            panels["worker"] = PanelDimensions(
                width=width,
                height=worker_height,
                x=0,
                y=output_height
            )
            panels["metrics"] = PanelDimensions(
                width=0,  # 숨김
                height=0,
                x=0,
                y=0
            )
            panels["workflow"] = PanelDimensions(
                width=0,  # 숨김
                height=0,
                x=0,
                y=0
            )
            panels["input"] = PanelDimensions(
                width=width,
                height=input_height,
                x=0,
                y=output_height + worker_height
            )

        return panels

    def resize_panels(self, panel_id: str, new_size: Tuple[int, int]) -> None:
        """
        특정 패널의 크기를 조정합니다.

        Args:
            panel_id: 패널 ID
            new_size: 새로운 크기 (width, height)

        Raises:
            KeyError: 존재하지 않는 패널 ID
            ValueError: 최소 크기보다 작은 경우

        Example:
            >>> manager = LayoutManager()
            >>> manager.calculate_layout((100, 30))
            >>> manager.resize_panels("output", (80, 20))
        """
        if panel_id not in self._panel_dimensions:
            logger.error(f"Panel not found: {panel_id}")
            raise KeyError(f"Panel '{panel_id}' not found")

        width, height = new_size

        # 최소 크기 검증
        if panel_id in self._min_panel_sizes:
            min_width, min_height = self._min_panel_sizes[panel_id]
            if width < min_width or height < min_height:
                logger.error(
                    f"Panel size too small: {panel_id} "
                    f"(min: {min_width}x{min_height}, got: {width}x{height})"
                )
                raise ValueError(
                    f"Panel size must be at least {min_width}x{min_height}, "
                    f"got {width}x{height}"
                )

        # 크기 업데이트
        current_dims = self._panel_dimensions[panel_id]
        self._panel_dimensions[panel_id] = PanelDimensions(
            width=width,
            height=height,
            x=current_dims.x,
            y=current_dims.y
        )

        logger.info(f"Panel resized: {panel_id} -> {width}x{height}")

    def get_panel_dimensions(self, panel_id: str) -> Tuple[int, int]:
        """
        특정 패널의 차원을 조회합니다.

        Args:
            panel_id: 패널 ID

        Returns:
            (width, height) 패널 크기

        Raises:
            KeyError: 존재하지 않는 패널 ID

        Example:
            >>> manager = LayoutManager()
            >>> manager.calculate_layout((100, 30))
            >>> width, height = manager.get_panel_dimensions("output")
            >>> print(width > 0 and height > 0)
            True
        """
        if panel_id not in self._panel_dimensions:
            logger.error(f"Panel not found: {panel_id}")
            raise KeyError(f"Panel '{panel_id}' not found")

        dims = self._panel_dimensions[panel_id]
        return (dims.width, dims.height)

    def get_panel_position(self, panel_id: str) -> Tuple[int, int]:
        """
        특정 패널의 위치를 조회합니다.

        Args:
            panel_id: 패널 ID

        Returns:
            (x, y) 패널 위치

        Raises:
            KeyError: 존재하지 않는 패널 ID

        Example:
            >>> manager = LayoutManager()
            >>> manager.calculate_layout((100, 30))
            >>> x, y = manager.get_panel_position("output")
            >>> print(x >= 0 and y >= 0)
            True
        """
        if panel_id not in self._panel_dimensions:
            logger.error(f"Panel not found: {panel_id}")
            raise KeyError(f"Panel '{panel_id}' not found")

        dims = self._panel_dimensions[panel_id]
        return (dims.x, dims.y)

    def is_panel_visible(self, panel_id: str) -> bool:
        """
        패널이 표시되는지 확인합니다.

        Args:
            panel_id: 패널 ID

        Returns:
            패널 표시 여부

        Example:
            >>> manager = LayoutManager()
            >>> manager.calculate_layout((60, 20))  # Small mode
            >>> print(manager.is_panel_visible("metrics"))
            False
        """
        if panel_id not in self._panel_dimensions:
            return False

        dims = self._panel_dimensions[panel_id]
        return dims.width > 0 and dims.height > 0

    def get_current_mode(self) -> Optional[LayoutMode]:
        """
        현재 레이아웃 모드를 반환합니다.

        Returns:
            현재 레이아웃 모드 (없으면 None)

        Example:
            >>> manager = LayoutManager()
            >>> manager.calculate_layout((120, 40))
            >>> mode = manager.get_current_mode()
            >>> print(mode)
            LayoutMode.LARGE
        """
        if self._current_layout:
            return self._current_layout.mode
        return None

    def get_terminal_size(self) -> Optional[Tuple[int, int]]:
        """
        현재 터미널 크기를 반환합니다.

        Returns:
            (width, height) 터미널 크기 (없으면 None)

        Example:
            >>> manager = LayoutManager()
            >>> manager.calculate_layout((100, 30))
            >>> size = manager.get_terminal_size()
            >>> print(size)
            (100, 30)
        """
        if self._current_layout:
            return self._current_layout.terminal_size
        return None

    def list_panels(self) -> list[str]:
        """
        모든 패널 ID 목록을 반환합니다.

        Returns:
            패널 ID 리스트

        Example:
            >>> manager = LayoutManager()
            >>> manager.calculate_layout((100, 30))
            >>> panels = manager.list_panels()
            >>> print("output" in panels)
            True
        """
        return list(self._panel_dimensions.keys())

    def get_visible_panels(self) -> list[str]:
        """
        현재 표시되는 패널 ID 목록을 반환합니다.

        Returns:
            표시되는 패널 ID 리스트

        Example:
            >>> manager = LayoutManager()
            >>> manager.calculate_layout((120, 40))
            >>> visible = manager.get_visible_panels()
            >>> print(len(visible) > 0)
            True
        """
        return [
            panel_id
            for panel_id in self._panel_dimensions.keys()
            if self.is_panel_visible(panel_id)
        ]

    def reset_layout(self) -> None:
        """
        레이아웃을 초기화합니다.

        Example:
            >>> manager = LayoutManager()
            >>> manager.calculate_layout((100, 30))
            >>> manager.reset_layout()
            >>> print(manager.get_current_mode())
            None
        """
        self._current_layout = None
        self._panel_dimensions.clear()
        logger.info("Layout reset")

    def set_min_panel_size(
        self,
        panel_id: str,
        min_size: Tuple[int, int]
    ) -> None:
        """
        패널의 최소 크기를 설정합니다.

        Args:
            panel_id: 패널 ID
            min_size: 최소 크기 (width, height)

        Example:
            >>> manager = LayoutManager()
            >>> manager.set_min_panel_size("output", (50, 15))
        """
        self._min_panel_sizes[panel_id] = min_size
        logger.info(f"Min panel size set: {panel_id} -> {min_size}")

    def get_min_panel_size(self, panel_id: str) -> Optional[Tuple[int, int]]:
        """
        패널의 최소 크기를 조회합니다.

        Args:
            panel_id: 패널 ID

        Returns:
            최소 크기 (width, height) 또는 None

        Example:
            >>> manager = LayoutManager()
            >>> min_size = manager.get_min_panel_size("output")
            >>> print(min_size)
            (40, 10)
        """
        return self._min_panel_sizes.get(panel_id)
