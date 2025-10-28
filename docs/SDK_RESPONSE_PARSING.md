# SDK 응답 파싱 가이드

이 문서는 Claude Agent SDK의 응답을 파싱하는 과정을 시각적으로 설명합니다.

---

## 📊 전체 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Agent SDK                              │
│                   (스트리밍 응답 생성)                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   SDK Response Types          │
         │                               │
         │  1. AssistantMessage          │ ← Claude의 텍스트 응답
         │  2. ResultMessage             │ ← usage 정보 (토큰 사용량)
         │  3. SystemMessage             │ ← 시스템 메타데이터 (✅ 지원)
         │  4. UserMessage               │ ← 사용자 입력 (드물게)
         └───────────────┬───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   SDKResponseHandler          │ ← 추상 클래스
         │                               │
         │  • extract_text_from_response │ ← 텍스트 추출
         │  • extract_usage_info         │ ← 토큰 사용량 추출
         └───────┬───────────────────┬───┘
                 │                   │
     ┌───────────▼────────┐   ┌─────▼──────────────┐
     │ Manager Handler    │   │ Worker Handler     │
     │                    │   │                    │
     │ (ClaudeSDKClient)  │   │ (query 함수)       │
     └───────┬────────────┘   └─────┬──────────────┘
             │                      │
             ▼                      ▼
    ┌─────────────────────────────────────┐
    │        최종 텍스트 스트림            │
    │  (사용자에게 표시 + 토큰 추적)       │
    └─────────────────────────────────────┘
```

---

## 🔍 단계별 상세 설명

### 1단계: SDK 응답 타입 식별

Claude Agent SDK는 다음과 같은 응답 타입을 스트리밍으로 전송합니다:

#### 📨 AssistantMessage
- **내용**: Claude가 생성한 응답
- **포함 요소**:
  - `content`: TextBlock, ThinkingBlock, ToolUseBlock 등의 리스트
  - `usage` (선택): 토큰 사용량 정보
- **예시**:
  ```python
  AssistantMessage(
      content=[
          TextBlock(text="안녕하세요! 무엇을 도와드릴까요?"),
          ThinkingBlock(thinking="[사고 과정: 사용자가 인사를 건넴]", signature="...")
      ],
      usage={
          'input_tokens': 120,
          'output_tokens': 45
      }
  )
  ```

  **참고**: ThinkingBlock 필드
  - `thinking` (str): 사고 과정 텍스트
  - `signature` (str): 서명 정보

#### 📊 ResultMessage
- **내용**: 스트리밍 종료 시 전송되는 메타데이터
- **포함 요소**:
  - `usage`: 전체 토큰 사용량 통계
  - `stop_reason`: 종료 이유 (end_turn, max_tokens 등)
- **예시**:
  ```python
  ResultMessage(
      usage={
          'input_tokens': 1500,
          'output_tokens': 800,
          'cache_read_input_tokens': 500,  # 캐시에서 읽은 토큰
          'cache_creation_input_tokens': 200  # 캐시 생성 토큰
      },
      stop_reason='end_turn'
  )
  ```

#### 🔧 SystemMessage
- **내용**: SDK 내부 상태 정보 또는 시스템 메타데이터
- **포함 요소**:
  - `content`: 문자열 또는 TextBlock 리스트
  - `usage` (선택): 토큰 사용량 정보
- **예시**:
  ```python
  # 문자열 content
  SystemMessage(
      content="Agent 초기화 완료"
  )

  # TextBlock 리스트 content
  SystemMessage(
      content=[
          TextBlock(text="시스템 상태: 정상")
      ]
  )
  ```

---

### 2단계: 텍스트 추출 (extract_text_from_response)

```
┌─────────────────────────────────────────────────────────────────┐
│                   extract_text_from_response                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [1] AssistantMessage?                                           │
│      ├─ YES → content blocks 순회                               │
│      │        ├─ TextBlock 발견? → text 반환 ✓                  │
│      │        ├─ ThinkingBlock 발견? → text 반환 ✓              │
│      │        └─ ToolUseBlock? → 건너뛰기                       │
│      └─ NO → 다음 단계                                          │
│                                                                  │
│  [2] ResultMessage?                                              │
│      ├─ YES → 텍스트 없음, None 반환                            │
│      └─ NO → 다음 단계                                          │
│                                                                  │
│  [3] SystemMessage?                                              │
│      ├─ YES → content 타입 확인                                 │
│      │        ├─ 문자열? → 직접 반환 ✓                          │
│      │        └─ 리스트? → TextBlock 추출 ✓                     │
│      └─ NO → 다음 단계                                          │
│                                                                  │
│  [4] 폴백 처리 (하위 호환성)                                     │
│      ├─ hasattr(response, 'content')?                           │
│      │   └─ content 리스트 순회 → text 추출 시도                │
│      ├─ hasattr(response, 'text')?                              │
│      │   └─ 직접 text 반환                                      │
│      └─ 모두 실패 → None 반환                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**핵심 포인트**:
- ✅ **단계적 폴백**: 알려진 타입 → SystemMessage → 알 수 없는 타입 순서로 처리
- ✅ **첫 번째 텍스트만 반환**: 여러 블록 중 첫 텍스트만 사용
- ✅ **안전한 속성 접근**: hasattr()로 속성 존재 확인
- ✅ **SystemMessage 유연성**: content가 문자열 또는 리스트 모두 지원

---

### 3단계: Usage 정보 추출 (extract_usage_info)

```
┌─────────────────────────────────────────────────────────────────┐
│                     extract_usage_info                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  입력: usage_obj (dict 또는 object)                              │
│                                                                  │
│  [방법 1] dict 타입?                                             │
│      ├─ YES → .get() 메서드로 안전하게 추출                     │
│      │        • input_tokens                                    │
│      │        • output_tokens                                   │
│      │        • cache_read_input_tokens                         │
│      │        • cache_creation_input_tokens                     │
│      └─ NO → 방법 2                                             │
│                                                                  │
│  [방법 2] object 타입                                            │
│      └─ hasattr()로 각 속성 존재 확인 후 추출                   │
│         • hasattr(usage, 'input_tokens')?                       │
│         • hasattr(usage, 'output_tokens')?                      │
│         • hasattr(usage, 'cache_read_tokens')?                  │
│         • hasattr(usage, 'cache_creation_tokens')?              │
│                                                                  │
│  출력: usage_dict (정규화된 딕셔너리)                            │
│  {                                                               │
│      'input_tokens': 1500,                                       │
│      'output_tokens': 800,                                       │
│      'cache_read_tokens': 500,                                   │
│      'cache_creation_tokens': 200                                │
│  }                                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**핵심 포인트**:
- ✅ **타입 유연성**: dict와 object 모두 지원
- ✅ **안전한 추출**: 속성이 없어도 오류 없이 처리
- ✅ **정규화**: 항상 동일한 키 이름으로 반환

---

### 4단계: Response Handler 처리 흐름

#### ManagerResponseHandler / WorkerResponseHandler

```
┌─────────────────────────────────────────────────────────────────┐
│                    process_response()                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [1단계] ResultMessage?                                          │
│      ├─ usage 정보 추출 (extract_usage_info)                    │
│      ├─ 콜백 함수 호출 (usage_callback)                         │
│      └─ return (텍스트 없음, 종료)                              │
│                                                                  │
│  [2단계] AssistantMessage?                                       │
│      ├─ (2-1) usage 정보 추출 및 콜백 호출                      │
│      ├─ (2-2) 텍스트 추출 (extract_text_from_response)          │
│      └─ yield text (스트리밍으로 텍스트 반환)                   │
│                                                                  │
│  [3단계] SystemMessage?                                          │
│      ├─ (3-1) usage 정보 추출 및 콜백 호출 (있으면)             │
│      ├─ (3-2) 텍스트 추출 (extract_text_from_response)          │
│      └─ yield text (스트리밍으로 텍스트 반환)                   │
│                                                                  │
│  [4단계] 알 수 없는 타입 (폴백)                                  │
│      ├─ (4-1) usage 정보 추출 시도                              │
│      ├─ (4-2) 텍스트 추출 시도                                  │
│      └─ yield text (있으면)                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**핵심 포인트**:
- ✅ **순서 보장**: ResultMessage → AssistantMessage → SystemMessage → 폴백
- ✅ **usage 우선**: 텍스트보다 usage 정보를 먼저 처리
- ✅ **스트리밍**: yield로 텍스트를 청크 단위로 반환
- ✅ **SystemMessage 지원**: 시스템 메타데이터를 정상적으로 표시

---

## 💡 사용 예시

### 예시 1: Manager Agent 응답 처리

```python
# Manager Agent 실행
async for response in manager_client.receive_response():
    # ManagerResponseHandler가 자동으로 처리
    async for text in response_handler.process_response(response):
        print(text)  # "코드를 작성했습니다..."

# usage 정보는 콜백으로 자동 수집됨
# → manager_client.total_input_tokens: 1500
# → manager_client.total_output_tokens: 800
```

### 예시 2: Worker Agent 응답 처리

```python
# Worker Agent 실행
async for response in query(prompt="코드 작성"):
    # WorkerResponseHandler가 자동으로 처리
    async for text in response_handler.process_response(response):
        print(text)  # "```python\ndef hello():\n    print('Hello')\n```"

# usage 정보는 콜백으로 자동 수집됨
# → worker_agent.total_input_tokens: 500
# → worker_agent.total_output_tokens: 200
```

---

## 🐛 디버깅 팁

### 로그 확인

로그 레벨을 DEBUG로 설정하면 상세한 파싱 과정을 확인할 수 있습니다:

```bash
export LOG_LEVEL=DEBUG
python orchestrator.py "작업 설명"
```

**주요 로그 메시지**:
- `[Manager] Processing ResultMessage (usage info)` - ResultMessage 처리 시작
- `[Manager] Processing AssistantMessage` - AssistantMessage 처리 시작
- `[Manager] Token usage (ResultMessage): {...}` - usage 정보 추출 성공
- `Extracted text from TextBlock #0` - 텍스트 추출 성공
- `Unknown response type: XYZ` - 알 수 없는 타입 발견 (폴백 처리)

### 문제 해결

#### 1. 텍스트가 추출되지 않음
- **증상**: yield된 텍스트가 없음
- **원인**: content blocks에 TextBlock이 없음
- **해결**: 로그에서 content blocks 구조 확인

#### 2. usage 정보가 누락됨
- **증상**: 토큰 사용량이 0으로 표시
- **원인**: usage 콜백이 호출되지 않음
- **해결**: usage_callback 설정 확인

#### 3. 알 수 없는 응답 타입
- **증상**: "Unknown response type" 경고
- **원인**: SDK 버전 변경 또는 새로운 응답 타입
- **해결**: 폴백 처리로 자동 대응 (정상 동작)

---

## 📚 참고 자료

- **Claude Agent SDK 공식 문서**: https://docs.claude.com/en/api/agent-sdk/overview
- **코드 위치**: `src/infrastructure/claude/sdk_executor.py`
- **관련 문서**: `claude-agent-sdk-features.md`
