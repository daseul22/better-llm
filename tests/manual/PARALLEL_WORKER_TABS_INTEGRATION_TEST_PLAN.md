# 병렬 Worker 탭 통합 테스트 계획서

## 개요

**목적**: 병렬 Worker 탭 동적 생성/제거 기능의 실제 동작 검증
**테스트 대상**: TUI에서 병렬 실행 시 Worker 탭이 동적으로 생성되고, 완료 후 자동으로 정리되는지 확인
**테스트 환경**: TUI 실행 중 실제 사용자 요청 시나리오

---

## 전제 조건

### 1. 환경 설정
- [x] TUI가 정상적으로 실행 가능한 환경
- [x] Planner Agent가 병렬 실행 계획을 생성할 수 있는 환경
- [x] `config/system_config.json`에 병렬 실행 설정이 활성화되어 있는지 확인:
  ```json
  {
    "parallel_execution": {
      "enabled": true,
      "max_concurrent_tasks": 5,
      "continue_on_error": false,
      "min_tasks_for_parallel": 3
    },
    "parallel_tasks": {
      "auto_close_tabs": true,
      "auto_close_delay_seconds": 5
    }
  }
  ```

### 2. 필수 의존성
- [ ] Claude Agent SDK 설치 및 API 키 설정
- [ ] Textual 라이브러리 설치
- [ ] Python 3.10 이상

---

## 테스트 시나리오

### 시나리오 1: 병렬 Worker 탭 동적 생성 (기본 시나리오)

**목표**: 병렬 실행 시 각 Task별로 개별 탭이 생성되는지 확인

#### 테스트 단계

1. **TUI 실행**
   ```bash
   python -m better_llm tui
   ```

2. **병렬 실행 요청**
   - 사용자 입력: `"3개의 간단한 유틸리티 함수 파일을 병렬로 생성해줘 (date_utils.py, list_utils.py, number_utils.py)"`
   - 또는: `"src/utils/ 디렉토리에 문자열 처리, 날짜 변환, 리스트 필터링 유틸리티를 병렬로 작성해줘"`

3. **Planner 실행 확인**
   - [ ] Planner 탭이 생성되고, 계획이 표시되는지 확인
   - [ ] Planner가 병렬 실행 계획 JSON을 생성하는지 확인 (최소 3개 Task)
   - [ ] 예상 출력 예시:
     ```json
     {
       "tasks": [
         {"id": "task_1", "description": "date_utils.py 작성", "target_files": ["src/utils/date_utils.py"]},
         {"id": "task_2", "description": "list_utils.py 작성", "target_files": ["src/utils/list_utils.py"]},
         {"id": "task_3", "description": "number_utils.py 작성", "target_files": ["src/utils/number_utils.py"]}
       ]
     }
     ```

4. **Manager가 `execute_parallel_tasks` Tool 호출 확인**
   - [ ] Manager가 Planner의 계획을 받아 `execute_parallel_tasks` Tool을 호출하는지 확인
   - [ ] Manager 출력에 "병렬 실행 시작" 메시지가 표시되는지 확인

5. **병렬 Worker 탭 생성 확인**
   - [ ] Worker 탭 영역에 새로운 탭이 동적으로 생성되는지 확인
   - [ ] 탭 라벨 형식: `[Parallel] task_1 ▶️`, `[Parallel] task_2 ▶️`, `[Parallel] task_3 ▶️`
   - [ ] 최소 3개의 병렬 탭이 생성되는지 확인
   - [ ] 각 탭에 Task 시작 메시지가 표시되는지 확인:
     ```
     🚀 [Parallel Task task_1] 시작
     📝 설명: date_utils.py 작성
     📁 파일: src/utils/date_utils.py
     ```

6. **Worker 출력 스트리밍 확인**
   - [ ] 각 탭에 해당 Task의 출력이 실시간으로 스트리밍되는지 확인
   - [ ] 서로 다른 Task의 출력이 섞이지 않고, 각 탭에 독립적으로 표시되는지 확인
   - [ ] 탭을 전환하면서 각 Task의 진행 상황을 확인할 수 있는지 확인

7. **Task 완료 시 탭 라벨 업데이트 확인**
   - [ ] Task가 완료되면 탭 라벨이 `[Parallel] task_1 ✅`로 변경되는지 확인
   - [ ] 완료 메시지가 탭에 표시되는지 확인:
     ```
     ✅ [Parallel Task task_1] 완료 (소요 시간: 12.3초)
     ```

8. **탭 자동 정리 확인**
   - [ ] Task 완료 후 5초 대기
   - [ ] 완료된 탭이 자동으로 제거되는지 확인
   - [ ] 제거 순서: 완료 시간 순서대로 제거

9. **모든 탭 제거 후 "No active workers" 탭 표시 확인**
   - [ ] 모든 병렬 Worker 탭이 제거되면 "No active workers" 탭이 다시 표시되는지 확인

#### 예상 결과

**실행 중 (T+0초)**
```
Worker Tabs:
┌─────────────────────────┐
│ [Parallel] task_1 ▶️   │  ← 실행 중
│ [Parallel] task_2 ▶️   │  ← 실행 중
│ [Parallel] task_3 ▶️   │  ← 실행 중
└─────────────────────────┘
```

**Task 1 완료 (T+12초)**
```
Worker Tabs:
┌─────────────────────────┐
│ [Parallel] task_1 ✅   │  ← 완료 (5초 후 제거 예정)
│ [Parallel] task_2 ▶️   │  ← 실행 중
│ [Parallel] task_3 ▶️   │  ← 실행 중
└─────────────────────────┘
```

**5초 후 (T+17초)**
```
Worker Tabs:
┌─────────────────────────┐
│ [Parallel] task_2 ✅   │  ← task_1 탭 제거됨
│ [Parallel] task_3 ▶️   │  ← 실행 중
└─────────────────────────┘
```

**모든 Task 완료 + 5초 (T+35초)**
```
Worker Tabs:
┌─────────────────────────┐
│ No active workers       │  ← 모든 병렬 탭 제거됨
└─────────────────────────┘
```

---

### 시나리오 2: 병렬 Worker 탭 자동 정리 비활성화

**목표**: `auto_close_tabs` 설정을 비활성화하면 탭이 자동으로 제거되지 않는지 확인

#### 테스트 단계

1. **설정 변경**
   - `config/system_config.json` 파일 수정:
     ```json
     {
       "parallel_tasks": {
         "auto_close_tabs": false,
         "auto_close_delay_seconds": 5
       }
     }
     ```

2. **TUI 재시작 및 병렬 실행**
   - 시나리오 1과 동일한 요청 수행

3. **탭 자동 정리 비활성화 확인**
   - [ ] Task 완료 후 5초 이상 대기
   - [ ] 완료된 탭이 제거되지 않고 남아있는지 확인 (`[Parallel] task_1 ✅` 상태 유지)
   - [ ] 모든 Task 완료 후에도 탭이 남아있는지 확인

#### 예상 결과

**모든 Task 완료 + 10초 후**
```
Worker Tabs:
┌─────────────────────────┐
│ [Parallel] task_1 ✅   │  ← 제거되지 않음 (히스토리 보존)
│ [Parallel] task_2 ✅   │  ← 제거되지 않음
│ [Parallel] task_3 ✅   │  ← 제거되지 않음
└─────────────────────────┘
```

---

### 시나리오 3: 병렬 Worker 탭 자동 정리 지연 시간 변경

**목표**: `auto_close_delay_seconds` 설정을 변경하면 대기 시간이 조정되는지 확인

#### 테스트 단계

1. **설정 변경**
   - `config/system_config.json` 파일 수정:
     ```json
     {
       "parallel_tasks": {
         "auto_close_tabs": true,
         "auto_close_delay_seconds": 10
       }
     }
     ```

2. **TUI 재시작 및 병렬 실행**
   - 시나리오 1과 동일한 요청 수행

3. **대기 시간 확인**
   - [ ] Task 완료 후 5초 대기 → 탭이 아직 남아있는지 확인
   - [ ] Task 완료 후 10초 대기 → 탭이 제거되는지 확인

#### 예상 결과

- 5초 후: 탭이 여전히 존재 (`[Parallel] task_1 ✅`)
- 10초 후: 탭이 제거됨

---

### 시나리오 4: 대규모 병렬 실행 (10개 Task)

**목표**: 대규모 병렬 실행 시 성능 및 UI 안정성 확인

#### 테스트 단계

1. **병렬 실행 요청**
   - 사용자 입력: `"10개의 간단한 유틸리티 함수 파일을 병렬로 생성해줘"`

2. **성능 확인**
   - [ ] TUI가 렉 없이 정상 동작하는지 확인
   - [ ] 10개의 탭이 정상적으로 생성되는지 확인
   - [ ] 탭 전환이 부드럽게 동작하는지 확인
   - [ ] 메모리 사용량이 과도하게 증가하지 않는지 확인 (Activity Monitor 확인)

3. **자동 정리 확인**
   - [ ] Task가 완료되는 순서대로 탭이 제거되는지 확인
   - [ ] 타이머가 중복 생성되지 않는지 확인 (로그 확인)

#### 예상 결과

- 10개의 탭이 정상적으로 생성되고, 각 탭에 독립적인 출력이 표시됨
- 완료 순서대로 5초 간격으로 탭이 제거됨
- UI가 안정적으로 동작함 (렉, 크래시 없음)

---

### 시나리오 5: Task 실패 시 탭 라벨 업데이트

**목표**: Task가 실패하면 탭 라벨이 `❌`로 변경되는지 확인

#### 테스트 단계

1. **의도적인 실패 요청**
   - 사용자 입력: `"존재하지 않는 파일을 읽어서 처리하는 3개의 Task를 병렬로 실행해줘"`
   - 또는: `"잘못된 구문의 Python 코드를 3개 병렬로 작성해줘"`

2. **실패 탭 라벨 확인**
   - [ ] Task 실패 시 탭 라벨이 `[Parallel] task_1 ❌`로 변경되는지 확인
   - [ ] 에러 메시지가 탭에 표시되는지 확인

3. **자동 정리 확인**
   - [ ] 실패한 탭도 5초 후에 제거되는지 확인 (현재 구현은 completed만 자동 제거)
   - **예상 동작**: 현재 코드는 `status == "completed"`인 경우만 자동 제거하므로, 실패한 탭은 제거되지 않음

#### 예상 결과

**실패 시**
```
Worker Tabs:
┌─────────────────────────┐
│ [Parallel] task_1 ❌   │  ← 실패 (자동 제거 안 됨)
│ [Parallel] task_2 ✅   │  ← 완료 (5초 후 제거)
│ [Parallel] task_3 ✅   │  ← 완료 (5초 후 제거)
└─────────────────────────┘
```

**개선 사항 제안**: 실패한 탭도 일정 시간 후 자동 제거하도록 수정 필요 (코드 개선 제안)

---

### 시나리오 6: 비병렬 Worker와 병렬 Worker 혼재

**목표**: 일반 Worker (Planner, Reviewer 등)와 병렬 Worker가 동시에 실행될 때 탭 구분 확인

#### 테스트 단계

1. **혼재 요청**
   - 사용자 입력: `"병렬로 3개의 파일을 작성하고, Reviewer에게 코드 리뷰를 요청해줘"`

2. **탭 구분 확인**
   - [ ] 일반 Worker 탭: `Planner ▶️`, `Reviewer ▶️` (기존 형식)
   - [ ] 병렬 Worker 탭: `[Parallel] task_1 ▶️`, `[Parallel] task_2 ▶️` (새 형식)
   - [ ] 두 형식이 명확하게 구분되는지 확인

3. **자동 정리 확인**
   - [ ] 병렬 Worker 탭만 자동 제거되는지 확인
   - [ ] 일반 Worker 탭은 제거되지 않고 남아있는지 확인

#### 예상 결과

**병렬 Task 완료 + 5초 후**
```
Worker Tabs:
┌─────────────────────────┐
│ Planner ✅             │  ← 일반 Worker (제거 안 됨)
│ Reviewer ▶️            │  ← 일반 Worker (실행 중)
│ (병렬 탭 모두 제거됨)   │
└─────────────────────────┘
```

---

## 엣지 케이스 테스트

### 엣지 케이스 1: 설정 파일 없음

**테스트**: `config/system_config.json` 파일을 임시로 이름 변경

**예상 결과**:
- [x] 기본값 적용 (`auto_close_tabs=True`, `auto_close_delay_seconds=5`)
- [x] 로그에 경고 메시지 출력: "병렬 탭 자동 정리 설정 로드 실패, 기본값 사용"

---

### 엣지 케이스 2: 설정 값이 범위를 벗어남

**테스트**: `auto_close_delay_seconds`를 `100`으로 설정

**예상 결과**:
- [x] 기본값 5초로 대체
- [x] 로그에 경고 메시지 출력: "병렬 탭 자동 정리 대기 시간이 유효하지 않음: 100, 기본값 5초 사용"

---

### 엣지 케이스 3: 타이머 중복 시작

**테스트**: 동일한 Task에 대해 여러 번 완료 메시지가 전송되는 경우 (비정상 시나리오)

**예상 결과**:
- [x] 이전 타이머가 취소되고, 새 타이머가 시작됨
- [x] 탭이 중복 제거되지 않음 (한 번만 제거)
- [x] 로그에 디버그 메시지 출력: "기존 제거 타이머 취소: coder_task_1"

---

### 엣지 케이스 4: 탭이 이미 제거된 경우

**테스트**: 타이머 실행 중 사용자가 수동으로 탭을 제거하는 경우

**예상 결과**:
- [x] `NoMatches` 예외가 발생하고, 정상적으로 처리됨
- [x] 로그에 디버그 메시지 출력: "제거 대상 탭이 이미 없음: coder_task_1"
- [x] 에러가 발생하지 않음

---

## 체크리스트 요약

### 기능 검증
- [ ] 병렬 Worker ID가 `coder_task_*` 패턴으로 생성됨
- [ ] 병렬 Worker 탭이 `[Parallel] task_* {emoji}` 형식으로 표시됨
- [ ] Task별로 독립적인 탭이 생성됨
- [ ] 각 탭에 해당 Task의 출력이 스트리밍됨
- [ ] Task 완료 시 탭 라벨이 업데이트됨 (`▶️` → `✅`)
- [ ] 5초 후 탭이 자동으로 제거됨
- [ ] 모든 탭 제거 후 "No active workers" 탭이 표시됨

### 설정 검증
- [ ] `auto_close_tabs` 설정이 정상 동작함
- [ ] `auto_close_delay_seconds` 설정이 정상 동작함
- [ ] 설정 파일 없음/오류 시 기본값이 적용됨
- [ ] 유효 범위 밖 값이 기본값으로 대체됨

### 성능 검증
- [ ] 10개 이상의 병렬 Task 실행 시 성능 저하 없음
- [ ] 메모리 사용량이 합리적임
- [ ] UI가 렙 없이 부드럽게 동작함

### 안정성 검증
- [ ] 타이머 중복 시작 시 정상 처리됨
- [ ] 탭이 이미 제거된 경우 예외 처리됨
- [ ] 실패한 Task의 탭 라벨이 정상 표시됨

---

## 테스트 실행 방법

### 1. 자동 테스트 (단위 테스트)
```bash
source .venv/bin/activate
python -m pytest tests/unit/tui/test_parallel_worker_tabs.py -v
```

### 2. 수동 테스트 (통합 테스트)
```bash
# 1. TUI 실행
python -m better_llm tui

# 2. 사용자 요청 입력
# "3개의 간단한 유틸리티 함수 파일을 병렬로 생성해줘"

# 3. 위 체크리스트를 따라 동작 확인
```

### 3. 로그 확인
```bash
# 실시간 로그 모니터링 (TUI 실행 중)
tail -f logs/better-llm.log | grep -E "(병렬|Parallel|탭 제거|Timer)"
```

---

## 알려진 제한 사항

### 1. 실패한 탭 자동 정리 미지원
- **현상**: `status == "completed"`인 경우만 자동 제거되므로, 실패한 탭은 수동으로 제거해야 함
- **개선 방안**: `status == "failed"`인 경우에도 일정 시간 후 자동 제거하도록 수정 필요

### 2. Boolean 값 타입 검증 미흡
- **현상**: `auto_close_delay_seconds`에 `True` (boolean)를 설정하면 `1`로 처리됨
- **원인**: Python에서 `bool`은 `int`의 서브클래스이므로 `isinstance(True, int)` → `True`
- **개선 방안**: `isinstance(delay, bool)` 체크를 먼저 수행하여 boolean을 명시적으로 거부

### 3. 탭 순서 보장 없음
- **현상**: 병렬 실행 시 탭이 생성되는 순서가 Task ID 순서와 다를 수 있음
- **원인**: 비동기 실행 특성상 Worker 시작 타이밍이 다름
- **영향**: 기능에는 영향 없으나, 시각적으로 순서가 뒤바뀔 수 있음

---

## 참고 파일

- 구현 파일:
  - `src/infrastructure/mcp/worker_tools.py` (line 1238-1277)
  - `src/presentation/tui/managers/callback_handlers.py`
  - `config/system_config.json` (line 91-94)

- 테스트 파일:
  - `tests/unit/tui/test_parallel_worker_tabs.py`

- 관련 문서:
  - 이 문서: `tests/manual/PARALLEL_WORKER_TABS_INTEGRATION_TEST_PLAN.md`

---

## 테스트 완료 기준

### 성공 기준
- [x] 모든 단위 테스트 통과 (24개)
- [ ] 시나리오 1-6 모두 통과
- [ ] 엣지 케이스 1-4 모두 통과
- [ ] 성능 테스트 통과 (10개 Task 실행 시 렉 없음)
- [ ] 알려진 제한 사항을 제외한 모든 기능 정상 동작

### 실패 기준
- [ ] 단위 테스트 1개 이상 실패
- [ ] 필수 시나리오 (1, 2, 3) 중 하나 이상 실패
- [ ] TUI 크래시 또는 심각한 성능 저하 발생
- [ ] 자동 정리 기능이 동작하지 않음

---

## 테스트 결과 보고 양식

### 테스트 일시
- 날짜: YYYY-MM-DD
- 실행자: [이름]
- 환경: macOS / Linux / Windows

### 테스트 결과 요약
- 단위 테스트: ✅ / ❌ (통과 / 실패 개수)
- 시나리오 1: ✅ / ❌
- 시나리오 2: ✅ / ❌
- 시나리오 3: ✅ / ❌
- 시나리오 4: ✅ / ❌
- 시나리오 5: ✅ / ❌
- 시나리오 6: ✅ / ❌

### 발견된 버그
1. [버그 설명]
2. [버그 설명]

### 개선 제안
1. [제안 사항]
2. [제안 사항]

---

**작성일**: 2025-10-23
**작성자**: QA Engineer (Claude Code)
**버전**: 1.0
