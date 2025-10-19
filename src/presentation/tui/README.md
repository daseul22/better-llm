# TUI (Terminal User Interface) - 개선 사항

## 개요

AI Orchestration System의 TUI를 4개 Phase에 걸쳐 전면 개선했습니다.
- Clean Architecture 4-Layer 준수
- Google 스타일 docstring
- Type Hints 사용
- 기존 코드와의 호환성 유지

---

## Phase 1: 핵심 UX 개선

### 1.1 히스토리 네비게이션 (↑↓ 키)

**파일**: `utils/input_history.py`

- 최대 100개의 입력 히스토리 유지
- ↑ 키: 이전 입력으로 이동
- ↓ 키: 다음 입력으로 이동
- 중복 제거 기능 (연속된 동일 입력 무시)

**사용법**:
```
입력 필드에서 ↑ 또는 ↓ 키를 눌러 이전 입력을 탐색
```

### 1.2 도움말 시스템 (/help + F1)

**파일**: `widgets/help_modal.py`

- F1 키 또는 `/help` 커맨드로 도움말 모달 표시
- 키 바인딩, 슬래시 커맨드, Worker Tools 정보 제공
- ESC 키로 닫기

**사용법**:
```
F1 키 누르기 또는 /help 입력
```

### 1.3 로그 저장 (Ctrl+S)

**파일**: `utils/log_exporter.py`

- Ctrl+S로 현재 세션 로그를 파일로 저장
- 텍스트 또는 Markdown 형식 지원
- Rich 마크업 자동 제거
- 기본 저장 위치: `logs/session_<id>_<timestamp>.log`

**사용법**:
```
Ctrl+S 누르기
저장 위치: logs/ 디렉토리
```

### 1.4 로그 검색 (Ctrl+F)

**파일**: `widgets/search_input.py`

- Ctrl+F로 검색 모달 열기
- 대소문자 구분 없이 검색
- 검색 결과 하이라이트 표시 (노란색 배경)
- 상위 10개 결과 표시

**사용법**:
```
Ctrl+F → 검색어 입력 → Enter
```

---

## Phase 2: 안정성 개선

### 2.1 로그 버퍼 관리

**파일**: `tui_app.py` - `_track_log_output()` 메서드

- 최대 1000줄 제한 (설정 가능)
- 메모리 최적화: 오래된 로그 자동 제거
- 모든 로그 출력 자동 추적

### 2.2 에러 핸들링 강화

**파일**: `tui_app.py` - 모든 async 메서드

- 모든 비동기 메서드에 try-except 블록 추가
- 사용자 친화적 에러 메시지 표시
- 로그에 traceback 기록
- 설정에 따라 알림 표시

### 2.3 실시간 입력 검증

**파일**: `tui_app.py` - `on_input_changed()` 메서드

- on_change 이벤트로 즉각 피드백
- 입력 글자 수 실시간 표시
- 4000자 초과 시 경고 메시지

**사용법**:
```
입력 필드에 타이핑하면 하단 상태바에 글자 수 표시
```

---

## Phase 3: 고급 기능

### 3.1 세션 복원 (/load <session_id>)

**파일**: `tui_app.py` - `load_session()` 메서드

- 이전 세션의 대화 히스토리 불러오기
- 세션 파일 자동 검색 (`sessions/` 디렉토리)
- 세션 ID 및 메트릭 복원

**사용법**:
```
/load <session_id>
예: /load 20231215_143022
```

### 3.2 Worker 상태 실시간 표시

**파일**: `tui_app.py` - 기존 메트릭 패널 활용

- Worker별 성공률, 평균 시간 실시간 업데이트
- 색상 코드: 초록(성공률 80%+), 노랑(50-80%), 빨강(50% 미만)
- 1초마다 자동 업데이트

### 3.3 설정 패널 (F2)

**파일**: `widgets/settings_modal.py`, `utils/tui_config.py`

- F2 키로 설정 모달 열기
- 설정 항목:
  - 로그 버퍼 크기
  - 히스토리 크기
  - Worker 타임아웃
  - 알림 활성화
  - 로그 저장 형식
- 설정 파일 위치: `~/.better-llm/tui_config.json`

**사용법**:
```
F2 키 → 설정 변경 → 저장 버튼 클릭
```

---

## Phase 4: 확장 기능

### 4.1 알림 시스템

**파일**: `tui_app.py` - `notify()` 메서드 활용

- 작업 완료 시 알림 (설정 가능)
- 에러 발생 시 알림 (설정 가능)
- textual의 내장 `notify()` 활용

### 4.2 자동 완성 (Tab)

**파일**: `utils/autocomplete.py`

- 슬래시 커맨드 자동 완성 엔진
- Tab 키로 자동 완성 (향후 구현 예정)
- 공통 접두사 완성 지원

**지원 커맨드**:
- `/help`
- `/init`
- `/load`
- `/clear`

### 4.3 키 커스터마이징

**파일**: `utils/tui_config.py` - `TUISettings` 클래스

- 설정 파일에서 키 바인딩 변경 가능
- 기본 키 바인딩:
  - `ctrl+c`: 중단/종료
  - `ctrl+n`: 새 세션
  - `ctrl+s`: 로그 저장
  - `ctrl+f`: 로그 검색
  - `f1`: 도움말
  - `f2`: 설정

---

## 파일 구조

```
src/presentation/tui/
├── tui_app.py                 # 메인 TUI 애플리케이션 (수정됨)
├── widgets/
│   ├── __init__.py
│   ├── help_modal.py          # 도움말 모달 (NEW)
│   ├── search_input.py        # 검색 모달 (NEW)
│   └── settings_modal.py      # 설정 모달 (NEW)
└── utils/
    ├── __init__.py
    ├── input_history.py       # 히스토리 네비게이션 (NEW)
    ├── log_exporter.py        # 로그 내보내기 (NEW)
    ├── autocomplete.py        # 자동 완성 엔진 (NEW)
    └── tui_config.py          # 설정 관리 (NEW)
```

---

## 새로운 키 바인딩

| 키 | 기능 |
|----|------|
| ↑ / ↓ | 히스토리 탐색 |
| Enter | 작업 실행 |
| Ctrl+C | 작업 중단 / 프로그램 종료 (2초 내 2번) |
| Ctrl+N | 새 세션 시작 |
| Ctrl+S | 로그 저장 |
| Ctrl+F | 로그 검색 |
| F1 | 도움말 표시 |
| F2 | 설정 패널 |
| ESC | 모달 닫기 |

---

## 새로운 슬래시 커맨드

| 커맨드 | 설명 |
|--------|------|
| `/help` | 도움말 표시 |
| `/init` | 프로젝트 분석 및 context 초기화 |
| `/load <session_id>` | 이전 세션 불러오기 |
| `/clear` | 로그 화면 지우기 |

---

## 설정 항목

설정 파일: `~/.better-llm/tui_config.json`

```json
{
  "theme": "dark",
  "worker_timeout": 300,
  "max_worker_timeout": 1800,
  "max_log_lines": 1000,
  "max_history_size": 100,
  "enable_notifications": true,
  "notify_on_completion": true,
  "notify_on_error": true,
  "search_case_sensitive": false,
  "search_context_lines": 2,
  "enable_autocomplete": true,
  "log_export_format": "text",
  "log_export_dir": "logs"
}
```

---

## 사용 예시

### 1. 작업 실행 및 로그 저장

```bash
# TUI 실행
python -m src.presentation.tui.tui_app

# 작업 입력
> "TUI에 검색 기능을 추가해주세요"

# 작업 완료 후 로그 저장
Ctrl+S
```

### 2. 이전 세션 불러오기

```bash
# 세션 목록 확인
ls sessions/

# 세션 불러오기
> /load 20231215_143022
```

### 3. 로그 검색

```bash
# 검색 모달 열기
Ctrl+F

# 검색어 입력
"error" → Enter
```

---

## 테스트 방법

```bash
# 구문 검사
python -m py_compile src/presentation/tui/tui_app.py
python -m py_compile src/presentation/tui/utils/*.py
python -m py_compile src/presentation/tui/widgets/*.py

# TUI 실행
python -m src.presentation.tui.tui_app

# 또는
python orchestrator.py --mode tui
```

---

## 향후 개선 사항

1. **Tab 키 자동 완성 통합** - 현재는 엔진만 구현됨
2. **검색 결과 네비게이션** - 검색 결과 간 이동 기능
3. **테마 지원** - 라이트/다크 테마 전환
4. **로그 필터링** - Worker별, 시간대별 필터링
5. **세션 관리 UI** - 세션 목록 조회 및 삭제

---

## 주의사항

- 모든 설정은 `~/.better-llm/tui_config.json`에 저장됩니다
- 로그 파일은 `logs/` 디렉토리에 저장됩니다
- 세션 파일은 `sessions/` 디렉토리에 저장됩니다
- 최대 로그 라인 수를 초과하면 오래된 로그가 자동 삭제됩니다

---

## 문제 해결

### 1. 모달이 열리지 않음
- textual 버전 확인: `pip install --upgrade textual`

### 2. 로그 저장 실패
- `logs/` 디렉토리 권한 확인
- 디스크 공간 확인

### 3. 세션 불러오기 실패
- `sessions/` 디렉토리 확인
- 세션 ID 정확성 확인

---

## 개발자 정보

- **아키텍처**: Clean Architecture (4-Layer)
- **코딩 스타일**: Google Docstring, Type Hints, Line Length 100
- **주요 의존성**: textual, rich, click, python-dotenv

---

## 라이선스

프로젝트 라이선스를 따릅니다.
