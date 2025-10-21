"""
Presentation Layer

User interfaces (CLI, TUI)
"""

# CLI는 선택적 의존성 (click 필요)
try:
    from . import cli
    __all__ = ["cli", "tui"]
except ImportError:
    # click이 설치되지 않은 경우 TUI만 사용
    __all__ = ["tui"]

from . import tui
