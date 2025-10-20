#!/usr/bin/env python3
"""
TUI 파일 리팩토링 스크립트

레거시 메서드들을 매니저로 위임하는 간단한 래퍼로 교체하여
파일 크기를 2,400줄에서 800줄 이하로 감소시킵니다.
"""

import re
from pathlib import Path


def refactor_tui_file(file_path: Path) -> None:
    """TUI 파일을 리팩토링합니다."""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_lines = len(content.splitlines())

    # 1. _create_worker_tab 메서드를 간단한 위임으로 교체
    pattern1 = r'    def _create_worker_tab\(self, worker_name: str\) -> None:.*?(?=\n    def |\nclass |\Z)'
    replacement1 = '''    def _create_worker_tab(self, worker_name: str) -> None:
        """Worker 탭 생성 (WorkerOutputManager로 위임)."""
        self.worker_output_manager.create_worker_tab(worker_name)
'''
    content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)

    # 2. _update_worker_tab_status 메서드를 간단한 위임으로 교체
    pattern2 = r'    def _update_worker_tab_status\(self, worker_name: str, status: str\) -> None:.*?(?=\n    def |\nclass |\Z)'
    replacement2 = '''    def _update_worker_tab_status(self, worker_name: str, status: str) -> None:
        """Worker 탭 상태 업데이트 (WorkerOutputManager로 위임)."""
        self.worker_output_manager.update_worker_tab_status(worker_name, status)
'''
    content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)

    # 3. on_worker_output 메서드를 간단한 위임으로 교체
    pattern3 = r'    def on_worker_output\(self, worker_name: str, chunk: str\) -> None:.*?(?=\n    def |\nclass |\Z)'
    replacement3 = '''    def on_worker_output(self, worker_name: str, chunk: str) -> None:
        """Worker 출력 콜백 (WorkerOutputManager로 위임)."""
        self.worker_output_manager.handle_worker_output(worker_name, chunk)
'''
    content = re.sub(pattern3, replacement3, content, flags=re.DOTALL)

    # 4. _write_worker_output 메서드를 간단한 위임으로 교체
    pattern4 = r'    def _write_worker_output\(self, worker_name: str, chunk: str\) -> None:.*?(?=\n    def |\nclass |\Z)'
    replacement4 = '''    def _write_worker_output(self, worker_name: str, chunk: str) -> None:
        """Worker 출력 작성 (WorkerOutputManager로 위임)."""
        self.worker_output_manager.write_worker_output(worker_name, chunk)
'''
    content = re.sub(pattern4, replacement4, content, flags=re.DOTALL)

    # 5. update_metrics_panel 메서드를 간단한 위임으로 교체
    pattern5 = r'    def update_metrics_panel\(self\) -> None:.*?(?=\n    def |\nclass |\Z)'
    replacement5 = '''    def update_metrics_panel(self) -> None:
        """메트릭 패널 업데이트 (MetricsUIManager로 위임)."""
        self.metrics_ui_manager.update_metrics_display()
'''
    content = re.sub(pattern5, replacement5, content, flags=re.DOTALL)

    # 6. on_resize 메서드를 간단한 위임으로 교체
    pattern6 = r'    def on_resize\(self, event: events\.Resize\) -> None:.*?(?=\n    def |\nclass |\Z)'
    replacement6 = '''    def on_resize(self, event: events.Resize) -> None:
        """화면 크기 변경 이벤트 (LayoutManager로 위임)."""
        self.layout_manager.handle_resize(event)
'''
    content = re.sub(pattern6, replacement6, content, flags=re.DOTALL)

    # 7. update_layout_for_size 메서드를 간단한 위임으로 교체
    pattern7 = r'    def update_layout_for_size\(self, width: int, height: int\) -> None:.*?(?=\n    def |\nclass |\Z)'
    replacement7 = '''    def update_layout_for_size(self, width: int, height: int) -> None:
        """레이아웃 크기 업데이트 (LayoutManager로 위임)."""
        self.layout_manager.update_layout_for_size(width, height)
'''
    content = re.sub(pattern7, replacement7, content, flags=re.DOTALL)

    # 8. _apply_layout_mode 메서드를 간단한 위임으로 교체
    pattern8 = r'    def _apply_layout_mode\(self\) -> None:.*?(?=\n    def |\nclass |\Z)'
    replacement8 = '''    def _apply_layout_mode(self) -> None:
        """레이아웃 모드 적용 (LayoutManager로 위임)."""
        self.layout_manager.apply_layout_mode()
'''
    content = re.sub(pattern8, replacement8, content, flags=re.DOTALL)

    # 9. on_input_changed 메서드를 간단한 위임으로 교체
    pattern9 = r'    def on_input_changed\(self, event: Input\.Changed\) -> None:.*?(?=\n    def |\nclass |\Z)'
    replacement9 = '''    def on_input_changed(self, event: Input.Changed) -> None:
        """입력 변경 이벤트 (InputHandler로 위임)."""
        self.input_handler.handle_input_changed(event)
'''
    content = re.sub(pattern9, replacement9, content, flags=re.DOTALL)

    # 파일에 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    new_lines = len(content.splitlines())
    print(f"리팩토링 완료:")
    print(f"  - 원본: {original_lines}줄")
    print(f"  - 결과: {new_lines}줄")
    print(f"  - 감소: {original_lines - new_lines}줄 ({(original_lines - new_lines) / original_lines * 100:.1f}%)")


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    tui_file = project_root / "src" / "presentation" / "tui" / "tui_app.py"

    if not tui_file.exists():
        print(f"Error: {tui_file} not found")
        exit(1)

    print(f"리팩토링 시작: {tui_file}")
    refactor_tui_file(tui_file)
    print("완료!")
