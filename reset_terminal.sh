#!/bin/bash
# 터미널 상태 복원 스크립트
# TUI가 비정상 종료되어 마우스 트래킹 모드가 활성화된 상태로 남아있을 때 사용하세요.
#
# 사용법:
#   bash reset_terminal.sh
#   또는
#   source reset_terminal.sh

echo "터미널 상태를 복원합니다..."

# 마우스 트래킹 모드 해제
printf '\033[?1000l'  # Disable mouse tracking
printf '\033[?1003l'  # Disable all mouse tracking
printf '\033[?1015l'  # Disable urxvt mouse mode
printf '\033[?1006l'  # Disable SGR mouse mode

# 커서 표시
printf '\033[?25h'    # Show cursor

# 포커스 이벤트 해제
printf '\033[?1004l'  # Disable focus events

# Alternate screen 해제 (TUI 화면 모드)
printf '\033[?1049l'  # Disable alternate screen

# 터미널 리셋
reset

echo "✅ 터미널 상태가 복원되었습니다."
echo ""
echo "만약 여전히 문제가 있다면 다음 명령을 실행하세요:"
echo "  stty sane"
echo "  reset"
