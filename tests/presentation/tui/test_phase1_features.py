"""
Phase 1 TUI 개선 기능 통합 테스트

테스트 대상:
1. 명령 팔레트 (Ctrl+P) - command_palette.py
2. 스마트 로그 필터링 (Ctrl+Shift+F) - log_filter.py, log_filter_modal.py
3. 실시간 토큰 사용량 시각화 - token_usage_widget.py

테스트 도구:
- pytest: 기본 테스트 프레임워크
- pytest-asyncio: 비동기 테스트
- unittest.mock: 모킹
"""

import pytest
from datetime import time, datetime
from typing import List, Set
from unittest.mock import Mock, MagicMock, patch

# 명령 팔레트 관련
from src.presentation.tui.widgets.command_palette import CommandItem, CommandPaletteModal

# 로그 필터링 관련
from src.presentation.tui.utils.log_filter import LogFilter, LogEntry
from src.presentation.tui.widgets.log_filter_modal import LogFilterModal, FilterConfig

# 토큰 위젯 관련
from src.presentation.tui.widgets.token_usage_widget import TokenUsageWidget


# ============================================================================
# 1. 명령 팔레트 테스트
# ============================================================================

class TestCommandPalette:
    """명령 팔레트 기능 테스트"""

    def test_command_item_creation(self):
        """CommandItem 객체 생성 테스트"""
        cmd = CommandItem(
            label="새 세션",
            description="새 대화 세션 시작",
            keybinding="Ctrl+N",
            action="new_session",
            item_type="keybinding"
        )

        assert cmd.label == "새 세션"
        assert cmd.description == "새 대화 세션 시작"
        assert cmd.keybinding == "Ctrl+N"
        assert cmd.action == "new_session"
        assert cmd.item_type == "keybinding"

    def test_command_item_get_search_text(self):
        """CommandItem 검색 텍스트 생성 테스트"""
        cmd = CommandItem(
            label="Help",
            description="Show help message",
            keybinding="Ctrl+H",
            action="/help"
        )

        search_text = cmd.get_search_text()
        assert "Help" in search_text
        assert "Show help message" in search_text

    def test_command_item_get_display_text(self):
        """CommandItem 표시 텍스트 생성 테스트"""
        cmd = CommandItem(
            label="도움말",
            description="도움말 표시",
            keybinding="Ctrl+H",
            action="/help",
            item_type="keybinding"
        )

        display_text = cmd.get_display_text()
        # Rich Text 객체 반환 확인
        assert display_text is not None
        # 텍스트 내용 확인
        text_str = display_text.plain
        assert "도움말" in text_str

    def test_command_palette_modal_init(self):
        """CommandPaletteModal 초기화 테스트"""
        commands = [
            CommandItem("Help", "Show help", keybinding="Ctrl+H", action="/help"),
            CommandItem("Clear", "Clear logs", keybinding="Ctrl+L", action="/clear"),
        ]

        on_execute_mock = Mock()
        modal = CommandPaletteModal(commands=commands, on_execute=on_execute_mock)

        assert modal.all_commands == commands
        assert len(modal.all_commands) == 2
        assert modal.on_execute == on_execute_mock


# ============================================================================
# 2. 로그 필터링 유틸리티 테스트
# ============================================================================

class TestLogFilter:
    """LogFilter 유틸리티 클래스 테스트"""

    def test_parse_log_line_full_format(self):
        """완전한 형식의 로그 라인 파싱 테스트"""
        log_filter = LogFilter()
        line = "14:30:45 [INFO] [Coder] 코드 작성 완료"

        entry = log_filter.parse_log_line(line, 0)

        assert entry.raw_line == line
        assert entry.timestamp == time(14, 30, 45)
        assert entry.level == "INFO"
        assert entry.worker == "Coder"
        assert "코드 작성 완료" in entry.message
        assert entry.line_number == 0

    def test_parse_log_line_minimal_format(self):
        """최소 형식의 로그 라인 파싱 테스트"""
        log_filter = LogFilter()
        line = "[ERROR] 오류 발생"

        entry = log_filter.parse_log_line(line, 1)

        assert entry.raw_line == line
        assert entry.timestamp is None
        assert entry.level == "ERROR"
        assert "오류 발생" in entry.message
        assert entry.line_number == 1

    def test_parse_log_line_empty(self):
        """빈 로그 라인 파싱 테스트"""
        log_filter = LogFilter()
        line = ""

        entry = log_filter.parse_log_line(line, 2)

        assert entry.raw_line == line
        assert entry.timestamp is None
        assert entry.level is None
        assert entry.worker is None
        assert entry.message == line

    def test_parse_log_line_long_line_truncation(self):
        """긴 로그 라인 truncation 테스트 (ReDoS 방지)"""
        log_filter = LogFilter()
        # MAX_LOG_LINE_LENGTH(10000) 초과하는 라인
        long_line = "A" * 15000

        entry = log_filter.parse_log_line(long_line, 3)

        # truncation 확인
        assert len(entry.raw_line) == 10000 + len("... [truncated]")
        assert entry.raw_line.endswith("... [truncated]")

    def test_filter_by_level_single_level(self):
        """단일 로그 레벨 필터링 테스트"""
        log_filter = LogFilter()
        lines = [
            "14:30:00 [DEBUG] 디버그 메시지",
            "14:30:01 [INFO] 정보 메시지",
            "14:30:02 [ERROR] 에러 메시지",
            "14:30:03 [INFO] 또 다른 정보",
        ]

        filtered = log_filter.filter_by_level(lines, {"INFO"})

        assert len(filtered) == 2
        assert "[INFO]" in filtered[0]
        assert "[INFO]" in filtered[1]

    def test_filter_by_level_multiple_levels(self):
        """복수 로그 레벨 필터링 테스트"""
        log_filter = LogFilter()
        lines = [
            "14:30:00 [DEBUG] 디버그",
            "14:30:01 [INFO] 정보",
            "14:30:02 [ERROR] 에러",
            "14:30:03 [WARNING] 경고",
        ]

        filtered = log_filter.filter_by_level(lines, {"INFO", "ERROR"})

        assert len(filtered) == 2
        assert any("[INFO]" in line for line in filtered)
        assert any("[ERROR]" in line for line in filtered)

    def test_filter_by_level_empty_levels(self):
        """빈 레벨 집합일 때 모든 라인 반환 테스트"""
        log_filter = LogFilter()
        lines = [
            "14:30:00 [DEBUG] 디버그",
            "14:30:01 [INFO] 정보",
        ]

        filtered = log_filter.filter_by_level(lines, set())

        assert len(filtered) == 2

    def test_filter_by_worker_single_worker(self):
        """단일 Worker 필터링 테스트"""
        log_filter = LogFilter()
        lines = [
            "14:30:00 [INFO] [Coder] 코드 작성",
            "14:30:01 [INFO] [Reviewer] 코드 리뷰",
            "14:30:02 [INFO] [Coder] 수정 완료",
            "14:30:03 [INFO] 일반 메시지",
        ]

        filtered = log_filter.filter_by_worker(lines, "Coder")

        # Coder 로그 2개 + Worker 없는 라인 1개 = 3개
        assert len(filtered) == 3
        assert "[Coder]" in filtered[0]
        assert "[Coder]" in filtered[1]

    def test_filter_by_worker_case_insensitive(self):
        """Worker 필터링 대소문자 무시 테스트"""
        log_filter = LogFilter()
        lines = [
            "14:30:00 [INFO] [Coder] 작업",
            "14:30:01 [INFO] [CODER] 작업",
            "14:30:02 [INFO] [coder] 작업",
        ]

        filtered = log_filter.filter_by_worker(lines, "coder")

        assert len(filtered) == 3

    def test_filter_by_worker_all(self):
        """Worker='All'일 때 모든 라인 반환 테스트"""
        log_filter = LogFilter()
        lines = [
            "14:30:00 [INFO] [Coder] 작업",
            "14:30:01 [INFO] [Reviewer] 작업",
        ]

        filtered = log_filter.filter_by_worker(lines, "All")

        assert len(filtered) == 2

    def test_filter_by_time_range(self):
        """시간 범위 필터링 테스트"""
        log_filter = LogFilter()
        lines = [
            "14:00:00 [INFO] 메시지 1",
            "14:30:00 [INFO] 메시지 2",
            "15:00:00 [INFO] 메시지 3",
            "15:30:00 [INFO] 메시지 4",
        ]

        start_time = time(14, 30, 0)
        end_time = time(15, 0, 0)

        filtered = log_filter.filter_by_time_range(lines, start_time, end_time)

        assert len(filtered) == 2
        assert "14:30:00" in filtered[0]
        assert "15:00:00" in filtered[1]

    def test_filter_by_time_range_no_bounds(self):
        """시간 범위 제한 없을 때 모든 라인 반환 테스트"""
        log_filter = LogFilter()
        lines = [
            "14:00:00 [INFO] 메시지 1",
            "15:00:00 [INFO] 메시지 2",
        ]

        filtered = log_filter.filter_by_time_range(lines, None, None)

        assert len(filtered) == 2

    def test_apply_filters_combined(self):
        """복합 필터 적용 테스트 (레벨 + Worker + 시간)"""
        log_filter = LogFilter()
        lines = [
            "14:00:00 [DEBUG] [Coder] 디버그 메시지",
            "14:30:00 [INFO] [Coder] 정보 메시지",
            "15:00:00 [INFO] [Reviewer] 리뷰 시작",
            "15:30:00 [ERROR] [Coder] 에러 발생",
        ]

        filtered = log_filter.apply_filters(
            lines,
            levels={"INFO", "ERROR"},
            worker="Coder",
            start_time=time(14, 0, 0),
            end_time=time(16, 0, 0)
        )

        # INFO + Coder + 시간 범위 내: 14:30:00 라인
        # ERROR + Coder + 시간 범위 내: 15:30:00 라인
        assert len(filtered) == 2
        assert "[INFO] [Coder]" in filtered[0]
        assert "[ERROR] [Coder]" in filtered[1]

    def test_extract_workers(self):
        """Worker 이름 추출 테스트"""
        log_filter = LogFilter()
        lines = [
            "14:00:00 [INFO] [Coder] 작업",
            "14:01:00 [INFO] [Reviewer] 작업",
            "14:02:00 [INFO] [Coder] 작업",
            "14:03:00 [INFO] [Tester] 작업",
            "14:04:00 [INFO] 일반 메시지",
        ]

        workers = log_filter.extract_workers(lines)

        # 정렬된 고유한 Worker 이름 리스트
        assert workers == ["Coder", "Reviewer", "Tester"]

    def test_max_lines_limit(self):
        """MAX_LINES 제한 테스트 (성능 최적화)"""
        log_filter = LogFilter()
        # 1500개 라인 생성 (MAX_LINES=1000 초과)
        lines = [f"14:00:00 [INFO] 메시지 {i}" for i in range(1500)]

        filtered = log_filter.filter_by_level(lines, {"INFO"})

        # 최근 1000개만 처리되므로 결과도 최대 1000개
        assert len(filtered) <= 1000


# ============================================================================
# 3. 로그 필터 모달 테스트
# ============================================================================

class TestLogFilterModal:
    """LogFilterModal 위젯 테스트"""

    def test_filter_config_creation(self):
        """FilterConfig 객체 생성 테스트"""
        config = FilterConfig(
            levels={"DEBUG", "INFO"},
            worker="Coder",
            start_time=time(14, 0, 0),
            end_time=time(15, 0, 0)
        )

        assert config.levels == {"DEBUG", "INFO"}
        assert config.worker == "Coder"
        assert config.start_time == time(14, 0, 0)
        assert config.end_time == time(15, 0, 0)

    def test_log_filter_modal_init(self):
        """LogFilterModal 초기화 테스트"""
        log_lines = [
            "14:00:00 [INFO] [Coder] 작업",
            "14:01:00 [INFO] [Reviewer] 작업",
        ]
        workers = ["Coder", "Reviewer"]

        modal = LogFilterModal(log_lines=log_lines, available_workers=workers)

        assert modal.log_lines == log_lines
        assert modal.available_workers == workers
        assert modal.log_filter is not None
        # 기본 설정 확인
        assert modal.current_config.levels == {"DEBUG", "INFO", "WARNING", "ERROR"}
        assert modal.current_config.worker == "All"
        assert modal.current_config.start_time is None
        assert modal.current_config.end_time is None


# ============================================================================
# 4. 토큰 사용량 위젯 테스트
# ============================================================================

class TestTokenUsageWidget:
    """TokenUsageWidget 클래스 테스트"""

    def test_token_widget_init_default(self):
        """TokenUsageWidget 기본 초기화 테스트"""
        widget = TokenUsageWidget()

        assert widget.token_budget == 50000
        assert widget.warn_threshold == 0.5
        assert widget.alert_threshold == 0.7
        assert widget._total_tokens == 0
        assert widget._manager_tokens == 0
        assert widget._worker_tokens == 0

    def test_token_widget_init_custom(self):
        """TokenUsageWidget 커스텀 초기화 테스트"""
        widget = TokenUsageWidget(
            token_budget=100000,
            warn_threshold=0.6,
            alert_threshold=0.8
        )

        assert widget.token_budget == 100000
        assert widget.warn_threshold == 0.6
        assert widget.alert_threshold == 0.8

    def test_update_token_info_manager_only(self):
        """Manager 토큰만 업데이트 테스트"""
        widget = TokenUsageWidget(token_budget=50000)

        manager_usage = {
            "total_tokens": 10000,
            "input_tokens": 8000,
            "output_tokens": 2000
        }

        widget.update_token_info(manager_usage, session_summary=None)

        assert widget._manager_tokens == 10000
        assert widget._worker_tokens == 0
        assert widget._total_tokens == 10000

    def test_update_token_info_with_workers(self):
        """Manager + Worker 토큰 업데이트 테스트"""
        widget = TokenUsageWidget(token_budget=50000)

        manager_usage = {
            "total_tokens": 10000,
            "input_tokens": 8000,
            "output_tokens": 2000
        }

        # Mock SessionMetrics
        mock_worker_metric = Mock()
        mock_worker_metric.input_tokens = 3000
        mock_worker_metric.output_tokens = 2000
        mock_worker_metric.cache_read_tokens = 500
        mock_worker_metric.cache_creation_tokens = 100

        mock_session_summary = Mock()
        mock_session_summary.workers_metrics = [mock_worker_metric]

        widget.update_token_info(manager_usage, session_summary=mock_session_summary)

        assert widget._manager_tokens == 10000
        assert widget._worker_tokens == 5000  # 3000 + 2000
        assert widget._total_tokens == 15000  # 10000 + 5000
        assert widget._cache_read_tokens == 500
        assert widget._cache_creation_tokens == 100

    def test_set_budget_valid(self):
        """토큰 예산 설정 테스트 (유효한 값)"""
        widget = TokenUsageWidget(token_budget=50000)

        widget.set_budget(100000)

        assert widget.token_budget == 100000

    def test_set_budget_too_low(self):
        """토큰 예산 설정 테스트 (너무 낮은 값)"""
        widget = TokenUsageWidget(token_budget=50000)

        # 최소값(1000) 미만
        widget.set_budget(500)

        # 변경되지 않아야 함
        assert widget.token_budget == 50000

    def test_set_thresholds_valid(self):
        """경고 임계값 설정 테스트 (유효한 값)"""
        widget = TokenUsageWidget()

        widget.set_thresholds(0.6, 0.8)

        assert widget.warn_threshold == 0.6
        assert widget.alert_threshold == 0.8

    def test_set_thresholds_invalid_range(self):
        """경고 임계값 설정 테스트 (범위 초과)"""
        widget = TokenUsageWidget(warn_threshold=0.5, alert_threshold=0.7)

        # warn >= alert (잘못된 값)
        widget.set_thresholds(0.8, 0.6)

        # 변경되지 않아야 함
        assert widget.warn_threshold == 0.5
        assert widget.alert_threshold == 0.7

    def test_set_thresholds_out_of_bounds(self):
        """경고 임계값 설정 테스트 (0.0~1.0 범위 외)"""
        widget = TokenUsageWidget(warn_threshold=0.5, alert_threshold=0.7)

        # 범위 초과
        widget.set_thresholds(1.5, 2.0)

        # 변경되지 않아야 함
        assert widget.warn_threshold == 0.5
        assert widget.alert_threshold == 0.7

    def test_get_usage_summary(self):
        """토큰 사용량 요약 정보 반환 테스트"""
        widget = TokenUsageWidget(token_budget=50000)

        manager_usage = {"total_tokens": 10000}
        widget.update_token_info(manager_usage)

        summary = widget.get_usage_summary()

        assert summary["total_tokens"] == 10000
        assert summary["manager_tokens"] == 10000
        assert summary["worker_tokens"] == 0
        assert summary["budget"] == 50000
        assert summary["usage_ratio"] == 0.2  # 10000 / 50000
        assert summary["usage_percent"] == 20.0
        assert summary["is_warning"] is False  # 0.2 < 0.5
        assert summary["is_alert"] is False  # 0.2 < 0.7

    def test_usage_color_green(self):
        """사용량 < 50% → 녹색 테스트"""
        widget = TokenUsageWidget(
            token_budget=50000,
            warn_threshold=0.5,
            alert_threshold=0.7
        )

        manager_usage = {"total_tokens": 20000}  # 40%
        widget.update_token_info(manager_usage)

        summary = widget.get_usage_summary()

        assert summary["is_warning"] is False
        assert summary["is_alert"] is False
        # 렌더링 결과에 녹색 포함 확인 (간접 테스트)
        # 실제 렌더링은 _render_token_display()에서 수행

    def test_usage_color_yellow(self):
        """사용량 50% ~ 70% → 노랑 테스트"""
        widget = TokenUsageWidget(
            token_budget=50000,
            warn_threshold=0.5,
            alert_threshold=0.7
        )

        manager_usage = {"total_tokens": 30000}  # 60%
        widget.update_token_info(manager_usage)

        summary = widget.get_usage_summary()

        assert summary["is_warning"] is True  # 0.6 >= 0.5
        assert summary["is_alert"] is False  # 0.6 < 0.7

    def test_usage_color_red(self):
        """사용량 > 70% → 빨강 테스트"""
        widget = TokenUsageWidget(
            token_budget=50000,
            warn_threshold=0.5,
            alert_threshold=0.7
        )

        manager_usage = {"total_tokens": 40000}  # 80%
        widget.update_token_info(manager_usage)

        summary = widget.get_usage_summary()

        assert summary["is_warning"] is True  # 0.8 >= 0.5
        assert summary["is_alert"] is True  # 0.8 >= 0.7


# ============================================================================
# 엣지 케이스 및 보안 테스트
# ============================================================================

class TestEdgeCases:
    """엣지 케이스 및 보안 취약점 테스트"""

    def test_log_filter_redos_prevention(self):
        """ReDoS 공격 방지 테스트 (긴 로그 라인)"""
        log_filter = LogFilter()

        # 매우 긴 반복 패턴 (ReDoS 취약점 테스트)
        malicious_line = "[INFO] " + "A" * 50000

        # 타임아웃 없이 정상 처리되어야 함
        entry = log_filter.parse_log_line(malicious_line, 0)

        # truncation 확인
        assert len(entry.raw_line) <= 10100  # MAX_LOG_LINE_LENGTH + truncated message

    def test_log_filter_invalid_time_format(self):
        """잘못된 시간 형식 처리 테스트"""
        log_filter = LogFilter()
        line = "99:99:99 [INFO] Invalid time"

        entry = log_filter.parse_log_line(line, 0)

        # 타임스탬프 파싱 실패 시 None
        assert entry.timestamp is None
        assert entry.level == "INFO"

    def test_token_widget_zero_budget(self):
        """토큰 예산 0일 때 division by zero 방지 테스트"""
        widget = TokenUsageWidget(token_budget=0)

        manager_usage = {"total_tokens": 1000}
        widget.update_token_info(manager_usage)

        summary = widget.get_usage_summary()

        # 0으로 나누지 않고 0 반환
        assert summary["usage_ratio"] == 0

    def test_command_palette_empty_commands(self):
        """명령 팔레트에 명령이 없을 때 테스트"""
        modal = CommandPaletteModal(commands=[], on_execute=Mock())

        assert len(modal.all_commands) == 0
        assert len(modal.filtered_commands) == 0

    def test_log_filter_special_characters(self):
        """특수 문자 포함 로그 라인 파싱 테스트"""
        log_filter = LogFilter()
        line = '14:30:00 [INFO] [Coder] 특수문자: <>"\'&;()[]{}!'

        entry = log_filter.parse_log_line(line, 0)

        assert entry.level == "INFO"
        assert entry.worker == "Coder"
        assert "특수문자" in entry.message
