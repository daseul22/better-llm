# 워크플로우 비주얼라이저 구현 완료

## 개요
Worker Tool 호출 흐름을 실시간으로 시각화하는 워크플로우 비주얼라이저를 TUI에 구현했습니다.

## 구현 내용

### 1. WorkflowVisualizer 위젯 (`src/presentation/tui/widgets/workflow_visualizer.py`)
- **WorkflowNode 데이터 클래스**: Worker 상태 추적
  - worker_name: Worker 이름
  - status: 현재 상태 (PENDING, RUNNING, COMPLETED, FAILED)
  - start_time, end_time: 시작/종료 시간
  - error_message: 에러 메시지 (실패 시)
  - get_duration(), format_duration(): 소요 시간 계산 및 포맷팅

- **WorkflowVisualizer 위젯**: Tree 형태로 워크플로우 표시
  - Tree 위젯 기반 계층 구조
  - 상태별 아이콘 및 색상:
    - 대기: ⏸ (dim)
    - 진행 중: ⚙️ (yellow)
    - 완료: ✅ (green)
    - 실패: ❌ (red)
  - Worker별 이모지:
    - Manager: 🤖
    - Planner: 🧠
    - Coder: 💻
    - Reviewer: 🔍
    - Tester: 🧪
  - 실시간 소요 시간 표시 (예: "2.5s", "1m 30s")

### 2. TUI 통합 (`src/presentation/tui/tui_app.py`)
- **UI 구성**:
  - workflow-container 추가
  - WorkflowVisualizer 위젯 추가
  - CSS 스타일링 (max-height: 20, 스크롤 가능)

- **F4 키 바인딩**:
  - action_toggle_workflow_panel() 메서드 구현
  - 패널 표시/숨김 토글
  - 설정 자동 저장

- **워크플로우 상태 추적**:
  - on_workflow_update() 콜백 메서드
  - Worker Tool 호출 시작/완료/실패 시 상태 업데이트
  - 상태 문자열 → WorkerStatus enum 변환

- **초기화**:
  - apply_workflow_panel_visibility() 메서드
  - set_workflow_callback() 호출로 콜백 등록

### 3. Worker Tools 통합 (`src/infrastructure/mcp/worker_tools.py`)
- **워크플로우 콜백 메커니즘**:
  - _WORKFLOW_CALLBACK 전역 변수 추가
  - set_workflow_callback() 함수 구현
  - _execute_worker_task()에 콜백 호출 추가:
    - 시작 시: callback(worker_name, "running", None)
    - 완료 시: callback(worker_name, "completed", None)
    - 실패 시: callback(worker_name, "failed", error_message)

### 4. 설정 시스템 (`src/presentation/tui/utils/tui_config.py`)
- **TUISettings에 필드 추가**:
  - show_workflow_panel: bool = True
  - 설정 파일에 자동 저장/로드

### 5. 도움말 업데이트 (`src/presentation/tui/widgets/help_modal.py`)
- F4 키 바인딩 추가: "워크플로우 패널 토글"

## 파일 수정 목록

### 새 파일
- ✅ `src/presentation/tui/widgets/workflow_visualizer.py`

### 수정된 파일
- ✅ `src/presentation/tui/widgets/__init__.py` - WorkflowVisualizer 추가
- ✅ `src/presentation/tui/tui_app.py` - 워크플로우 패널 통합
- ✅ `src/presentation/tui/widgets/help_modal.py` - F4 키 바인딩 추가
- ✅ `src/presentation/tui/utils/tui_config.py` - show_workflow_panel 설정 추가
- ✅ `src/infrastructure/mcp/worker_tools.py` - 워크플로우 콜백 추가
- ✅ `src/infrastructure/mcp/__init__.py` - set_workflow_callback 내보내기

## 사용법

### 키 바인딩
- **F4**: 워크플로우 패널 표시/숨김 토글

### 워크플로우 시각화
1. TUI 실행 시 워크플로우 패널이 자동으로 표시됩니다
2. Worker Tool 실행 시 실시간으로 상태가 업데이트됩니다:
   - Manager Agent가 Worker Tool 호출
   - Worker 노드가 Tree에 추가됨
   - 상태 변경 (대기 → 진행 중 → 완료/실패)
   - 소요 시간 실시간 표시
3. F4 키로 패널을 숨기거나 다시 표시할 수 있습니다

### 설정 저장
- 워크플로우 패널 표시 상태는 `~/.better-llm/tui_config.json`에 자동 저장됩니다
- 다음 실행 시 마지막 설정이 복원됩니다

## 기술적 특징

### 아키텍처
- **Clean Architecture 준수**:
  - Presentation Layer: WorkflowVisualizer 위젯
  - Infrastructure Layer: 워크플로우 콜백 메커니즘
  - 느슨한 결합: 콜백 함수를 통한 통신

### 실시간 업데이트
- Worker Tool 실행 전후로 콜백 호출
- 비동기 안전: try-except로 예외 처리
- 타임스탬프 기록 및 소요 시간 계산

### 에러 처리
- 워크플로우 콜백 실패 시 로그만 남기고 계속 실행
- Worker Tool 실패 시 FAILED 상태로 표시
- 에러 메시지를 트리 노드에 표시

### UI/UX
- Rich Text 기반 색상 및 아이콘
- Tree 위젯으로 계층 구조 표현
- 스크롤 가능한 컨테이너
- 반응형 레이아웃 (max-height: 20)

## 테스트 권장사항

### 기본 동작 테스트
1. TUI 실행: `python -m src.presentation.tui.tui_app`
2. 작업 입력 및 실행
3. 워크플로우 패널에서 Worker 상태 확인
4. F4 키로 패널 토글 테스트

### 에지 케이스
1. Worker Tool 실패 시나리오
2. 여러 Worker가 순차 실행되는 경우
3. 재시도 로직이 발동하는 경우
4. 패널 숨김 상태에서 작업 실행

### 성능 테스트
1. 긴 작업 실행 시 소요 시간 표시
2. 여러 세션에서 워크플로우 초기화
3. 설정 저장/로드 정확성

## 향후 개선 사항

### 가능한 기능 추가
1. **워크플로우 히스토리**:
   - 이전 실행 이력 저장
   - 세션별 워크플로우 비교

2. **애니메이션 개선**:
   - 진행 중 상태에 스피너 애니메이션
   - 상태 전환 시 부드러운 전환 효과

3. **상세 정보 표시**:
   - Worker Tool 입력 파라미터
   - 출력 요약
   - 토클하여 상세 정보 보기

4. **필터링 및 검색**:
   - Worker별 필터링
   - 상태별 필터링
   - 실행 시간 기준 정렬

5. **통계 집계**:
   - Worker별 평균 실행 시간
   - 성공률 표시
   - 병목 구간 하이라이트

## 결론

워크플로우 비주얼라이저가 성공적으로 구현되었습니다.

**주요 성과**:
- ✅ Tree 형태로 워크플로우 실시간 시각화
- ✅ 상태별 아이콘 및 색상 표시
- ✅ 소요 시간 실시간 업데이트
- ✅ F4 키 바인딩으로 패널 토글
- ✅ 설정 자동 저장/로드
- ✅ Clean Architecture 준수
- ✅ 에러 처리 및 안정성 확보

이제 사용자는 Manager Agent가 어떤 Worker Tool을 언제, 어떻게 호출하는지
명확하게 파악할 수 있으며, 작업 진행 상황을 직관적으로 모니터링할 수 있습니다.
