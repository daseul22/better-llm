# Claude Agent SDK 기능 가이드

## 1. 개요

### 1.1 소개
Claude Agent SDK는 Anthropic의 공식 SDK로, Claude Code의 기반이 되는 agent harness를 활용하여 강력한 AI 에이전트를 구축할 수 있습니다. Python과 TypeScript 두 가지 버전으로 제공되며, 파일 작업, 코드 실행, 웹 검색 등 다양한 도구를 제공합니다.

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

### 1.2 주요 특징
- **자동 컨텍스트 관리**: 컨텍스트 한계 도달 시 자동 요약 및 압축
- **풍부한 도구 생태계**: 파일 작업, 코드 실행, 웹 검색, MCP 확장
- **세밀한 권한 제어**: 도구별 허용/거부 설정, 커스텀 검증 함수
- **프로덕션 필수 기능**: 에러 핸들링, 세션 관리, 모니터링 내장
- **최적화된 성능**: 자동 프롬프트 캐싱, 비용 절감

### 1.3 지원 플랫폼
- **Python SDK**: Python 3.10 이상
- **TypeScript SDK**: Node.js 환경

### 1.4 설치

**Python**:
```bash
pip install claude-agent-sdk
```

**TypeScript/Node.js**:
```bash
npm install @anthropic-ai/claude-agent-sdk
```

**필수 요구사항**:
- Claude Code CLI: `npm install -g @anthropic-ai/claude-code` (2.0.0 이상)
- Node.js 설치

---

## 2. 핵심 기능

### 2.1 기본 인터페이스

#### 2.1.1 query() 함수
**설명**: 가장 간단한 Claude 에이전트 호출 방법으로, 일회성 작업에 적합합니다.

**Python 예시**:
```python
import anyio
from claude_agent_sdk import query

async def main():
    async for message in query(prompt="What is 2 + 2?"):
        print(message)

anyio.run(main)
```

**TypeScript 예시**:
```typescript
import { query } from '@anthropic-ai/claude-agent-sdk';

for await (const message of query({ prompt: "What is 2 + 2?" })) {
  console.log(message);
}
```

**특징**:
- AsyncIterator로 메시지 스트리밍
- 옵션으로 커스터마이징 가능
- 단일 요청-응답에 최적화

**문서 링크**:
- Python: https://docs.claude.com/en/api/agent-sdk/python
- TypeScript: https://docs.claude.com/en/api/agent-sdk/typescript

---

#### 2.1.2 ClaudeSDKClient (Python) / SDK Client (TypeScript)
**설명**: 지속적인 대화 세션을 유지하고, 복잡한 상호작용을 관리할 수 있는 고급 클라이언트입니다.

**Python 예시**:
```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Bash"],
    permission_mode='acceptEdits'
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Create a hello.py file")
    async for message in client.receive_response():
        print(message)
```

**주요 메서드** (Python):
- `connect(prompt)`: 세션 연결 및 초기 메시지 전송
- `query(prompt, session_id)`: 스트리밍 모드로 요청 전송
- `receive_messages()`: 모든 메시지를 AsyncIterator로 수신
- `receive_response()`: ResultMessage까지 메시지 수신
- `interrupt()`: 실행 중인 작업 중단
- `disconnect()`: 세션 종료

**특징**:
- 대화 히스토리 유지
- 세션 재개 가능
- async context manager 지원
- 양방향 통신

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/python

---

### 2.2 설정 및 옵션

#### 2.2.1 ClaudeAgentOptions (Python) / Options (TypeScript)
**설명**: SDK 동작을 커스터마이징하는 설정 객체입니다.

**주요 옵션**:

| 옵션 | 타입 | 설명 |
|------|------|------|
| `allowed_tools` | List[str] | 허용할 도구 목록 |
| `disallowed_tools` | List[str] | 금지할 도구 목록 |
| `permission_mode` | str | "default", "acceptEdits", "plan", "bypassPermissions" |
| `system_prompt` | str | 커스텀 시스템 프롬프트 |
| `mcp_servers` | dict | MCP 서버 설정 |
| `max_turns` | int | 최대 대화 턴 수 |
| `cwd` | str/Path | 작업 디렉토리 |
| `can_use_tool` | Callable | 커스텀 권한 검증 함수 |
| `hooks` | dict | 이벤트 훅 설정 |
| `setting_sources` | List[str] | 설정 파일 로드 소스 ("user", "project", "local") |
| `model` | str | 사용할 모델 (TypeScript) |
| `fallbackModel` | str | 폴백 모델 (TypeScript) |
| `maxThinkingTokens` | int | 최대 사고 토큰 수 (TypeScript) |
| `continue` / `resume` | bool | 세션 재개 (TypeScript) |
| `forkSession` | str | 세션 분기 (TypeScript) |

**Python 예시**:
```python
from claude_agent_sdk import ClaudeAgentOptions
from pathlib import Path

options = ClaudeAgentOptions(
    system_prompt="You are a helpful coding assistant",
    allowed_tools=["Read", "Write", "Bash", "Grep"],
    permission_mode='acceptEdits',
    max_turns=5,
    cwd=Path("/path/to/project"),
    setting_sources=['project']
)
```

**TypeScript 예시**:
```typescript
import { query, Options } from '@anthropic-ai/claude-agent-sdk';

const options: Options = {
  systemPrompt: "You are a helpful coding assistant",
  allowedTools: ["Read", "Write", "Bash", "Grep"],
  permissionMode: 'acceptEdits',
  maxTurns: 5,
  cwd: "/path/to/project",
  model: "claude-sonnet-4-5-20250929"
};

for await (const message of query({ prompt: "Help me", options })) {
  console.log(message);
}
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/python

---

### 2.3 메시지 타입

#### 2.3.1 메시지 클래스
**설명**: SDK는 다양한 메시지 타입을 스트리밍합니다.

**Python 메시지 타입**:
- `UserMessage`: 사용자 입력
- `AssistantMessage`: Claude의 응답 (content blocks 포함)
- `SystemMessage`: 메타데이터 메시지
- `ResultMessage`: 최종 결과 (비용/사용량 데이터 포함)

**TypeScript 메시지 타입**:
- `SDKUserMessage`: 사용자 입력
- `SDKAssistantMessage`: Claude의 응답
- `SDKSystemMessage`: 초기화 및 메타데이터
- `SDKResultMessage`: 최종 결과 및 통계
- `SDKPartialAssistantMessage`: 스트리밍 청크 (선택적)

**Content Block 타입**:
- `TextBlock`: 텍스트 응답
- `ThinkingBlock`: 모델의 추론 과정 (extended thinking)
- `ToolUseBlock`: 도구 호출 요청
- `ToolResultBlock`: 도구 실행 결과

**Python 예시**:
```python
from claude_agent_sdk import query, AssistantMessage, TextBlock

async for message in query(prompt="Hello Claude"):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(block.text)
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/python

---

### 2.4 내장 도구 (Built-in Tools)

#### 2.4.1 파일 작업 도구
**설명**: 파일 시스템을 조작하는 도구들입니다.

| 도구 | 설명 | 주요 파라미터 |
|------|------|----------------|
| `Read` | 파일 읽기 | `file_path`, `offset`, `limit` |
| `Write` | 파일 쓰기 (덮어쓰기) | `file_path`, `content` |
| `Edit` | 파일 편집 (부분 수정) | `file_path`, `old_string`, `new_string`, `replace_all` |
| `Glob` | 파일 패턴 검색 | `pattern`, `path` |
| `Grep` | 파일 내용 검색 | `pattern`, `path`, `output_mode`, `glob`, `type` |

**사용 예시**:
```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],
    permission_mode='acceptEdits'
)

async for message in query(
    prompt="Find all Python files and add a docstring to the main function",
    options=options
):
    pass
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

---

#### 2.4.2 코드 실행 도구
**설명**: 코드를 실행하고 노트북을 편집하는 도구들입니다.

| 도구 | 설명 | 주요 파라미터 |
|------|------|----------------|
| `Bash` | Bash 명령어 실행 | `command`, `timeout`, `run_in_background` |
| `NotebookEdit` | Jupyter 노트북 셀 편집 | `notebook_path`, `cell_id`, `new_source`, `edit_mode` |

**사용 예시**:
```python
options = ClaudeAgentOptions(
    allowed_tools=["Bash"],
    permission_mode='default'
)

async for message in query(
    prompt="Run pytest and show me the results",
    options=options
):
    pass
```

**특징**:
- `Bash`는 타임아웃 설정 가능 (기본 2분, 최대 10분)
- 백그라운드 실행 지원 (`run_in_background=True`)
- `NotebookEdit`는 code/markdown 셀 타입 지원

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

---

#### 2.4.3 웹 접근 도구
**설명**: 웹 검색 및 페이지 가져오기 도구입니다.

| 도구 | 설명 | 주요 파라미터 |
|------|------|----------------|
| `WebSearch` | 웹 검색 (미국 한정) | `query`, `allowed_domains`, `blocked_domains` |
| `WebFetch` | URL에서 콘텐츠 가져오기 | `url`, `prompt` |

**사용 예시**:
```python
options = ClaudeAgentOptions(
    allowed_tools=["WebSearch", "WebFetch"]
)

async for message in query(
    prompt="Search for the latest Python best practices in 2025",
    options=options
):
    pass
```

**특징**:
- `WebFetch`는 HTML을 Markdown으로 변환
- 15분 캐시 지원
- `WebSearch`는 도메인 필터링 가능

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

---

#### 2.4.4 MCP 리소스 도구
**설명**: Model Context Protocol 리소스를 관리하는 도구입니다.

| 도구 | 설명 | 주요 파라미터 |
|------|------|----------------|
| `ListMcpResources` | MCP 리소스 목록 조회 | MCP 서버 설정 |
| `ReadMcpResource` | MCP 리소스 읽기 | `resource_uri` |

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

---

### 2.5 커스텀 도구 (Custom Tools)

#### 2.5.1 In-Process MCP Tools
**설명**: Python 함수나 TypeScript 함수를 Claude가 사용할 수 있는 도구로 변환합니다. 별도 프로세스 없이 동일 프로세스에서 실행되어 성능이 우수합니다.

**중요**: MCP 도구는 **스트리밍 입력 모드 필수**입니다. `prompt` 매개변수에 async generator/iterable을 사용해야 하며, 단순 문자열은 작동하지 않습니다.

**도구 네이밍 규칙**:
- 형식: `mcp__{server_name}__{tool_name}`
- 예시: 서버 "my-tools"의 "get_weather" 도구 → `mcp__my-tools__get_weather`

**Python 예시**:
```python
from claude_agent_sdk import (
    tool, create_sdk_mcp_server, ClaudeAgentOptions, ClaudeSDKClient
)

@tool("greet", "Greet a user", {"name": str})
async def greet_user(args):
    """사용자에게 인사하는 도구."""
    return {
        "content": [
            {"type": "text", "text": f"Hello, {args['name']}!"}
        ]
    }

# MCP 서버 생성
server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=[greet_user]
)

# 클라이언트에서 사용
options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__greet"]
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Greet Alice")
    async for msg in client.receive_response():
        print(msg)
```

**TypeScript 예시 (스트리밍 모드 필수)**:
```typescript
import { tool, createSdkMcpServer, query } from '@anthropic-ai/claude-agent-sdk';
import { z } from 'zod';

const greetTool = tool({
  name: "greet",
  description: "Greet a user",
  inputSchema: z.object({
    name: z.string()
  }),
  async handler(args) {
    return {
      content: [
        { type: "text", text: `Hello, ${args.name}!` }
      ]
    };
  }
});

const server = createSdkMcpServer({
  name: "my-tools",
  version: "1.0.0",
  tools: [greetTool]
});

// 스트리밍 입력 제너레이터 (MCP 도구 사용 시 필수!)
async function* generateMessages() {
  yield {
    type: "user" as const,
    message: {
      role: "user" as const,
      content: "Greet Alice"
    }
  };
}

const options = {
  mcpServers: { tools: server },
  allowedTools: ["mcp__tools__greet"]
};

for await (const message of query({ prompt: generateMessages(), options })) {
  console.log(message);
}
```

**특징**:
- **고성능**: 서브프로세스 오버헤드 없음
- **타입 안전성**: Python은 dict 스키마, TypeScript는 Zod 스키마 사용
- **간단한 디버깅**: 단일 프로세스 내에서 실행
- **JSON Schema 검증**: 입력 자동 검증

**문서 링크**:
- Python: https://docs.claude.com/en/api/agent-sdk/python
- TypeScript: https://docs.claude.com/en/api/agent-sdk/typescript

---

#### 2.5.2 External MCP Servers
**설명**: 외부 프로세스로 실행되는 MCP 서버를 연결합니다 (Slack, GitHub, Asana 등).

**Python 예시**:
```python
options = ClaudeAgentOptions(
    mcp_servers={
        "internal": sdk_server,  # In-process 서버
        "external": {
            "type": "stdio",
            "command": "external-server",
            "args": ["--config", "config.json"]
        }
    }
)
```

**TypeScript 예시**:
```typescript
const options = {
  mcpServers: {
    internal: sdkServer,
    external: {
      type: "stdio",
      command: "external-server",
      args: ["--config", "config.json"]
    }
  }
};
```

**특징**:
- In-process와 external 서버 혼합 사용 가능
- 표준 MCP 프로토콜 준수
- OAuth 및 인증 자동 처리

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

---

### 2.6 훅 (Hooks)

#### 2.6.1 Hook 개요
**설명**: Claude 에이전트 루프의 특정 시점에 실행되는 Python/TypeScript 함수입니다. 도구 사용 전후, 세션 시작/종료 등의 이벤트에 반응할 수 있습니다.

**지원하는 Hook 이벤트**:
- `PreToolUse`: 도구 사용 전
- `PostToolUse`: 도구 사용 후
- `UserPromptSubmit`: 사용자 프롬프트 제출 시
- `SessionStart`: 세션 시작 시
- `SessionEnd`: 세션 종료 시
- `Stop`: 중단 시
- `SubagentStop`: 서브에이전트 중단 시
- `PreCompact`: 컨텍스트 압축 전 (TypeScript)
- `Notification`: 알림 발생 시 (TypeScript)

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/python

---

#### 2.6.2 PreToolUse Hook (권한 제어)
**설명**: 도구 사용 전에 실행되어 허용/거부를 결정할 수 있습니다.

**Python 예시**:
```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

async def check_bash_command(input_data, tool_use_id, context):
    """Bash 명령어를 검증하는 훅."""
    tool_name = input_data["tool_name"]
    tool_input = input_data["tool_input"]

    if tool_name != "Bash":
        return {}

    command = tool_input.get("command", "")

    # foo.sh 실행 금지
    if "foo.sh" in command:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Executing foo.sh is not allowed"
            }
        }

    return {}

options = ClaudeAgentOptions(
    allowed_tools=["Bash"],
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[check_bash_command]),
        ],
    }
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Run: ./foo.sh --help")
    async for msg in client.receive_response():
        print(msg)
```

**TypeScript 예시**:
```typescript
import { query, Options } from '@anthropic-ai/claude-agent-sdk';

const options: Options = {
  allowedTools: ["Bash"],
  hooks: {
    PreToolUse: [
      {
        matcher: "Bash",
        async hook(inputData, toolUseId, context) {
          const command = inputData.tool_input.command;

          if (command.includes("foo.sh")) {
            return {
              hookSpecificOutput: {
                hookEventName: "PreToolUse",
                permissionDecision: "deny",
                permissionDecisionReason: "Executing foo.sh is not allowed"
              }
            };
          }

          return {};
        }
      }
    ]
  }
};

for await (const message of query({ prompt: "Run: ./foo.sh --help", options })) {
  console.log(message);
}
```

**특징**:
- **결정론적 검증**: LLM이 아닌 코드로 권한 제어
- **세밀한 제어**: 도구별, 명령어별 허용/거부
- **안전성 향상**: 위험한 작업 차단

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/python

---

#### 2.6.3 PostToolUse Hook (로깅 및 모니터링)
**설명**: 도구 사용 후에 실행되어 결과를 로깅하거나 검증할 수 있습니다.

**Python 예시**:
```python
async def log_tool_result(input_data, tool_use_id, context):
    """도구 실행 결과를 로깅하는 훅."""
    tool_name = input_data["tool_name"]
    print(f"Tool {tool_name} executed with ID {tool_use_id}")
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PostToolUse": [
            HookMatcher(matcher="*", hooks=[log_tool_result]),
        ],
    }
)
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/python

---

### 2.7 서브에이전트 (Subagents)

#### 2.7.1 서브에이전트 개요
**설명**: 특정 작업을 병렬로 처리하거나 독립적인 컨텍스트 윈도우를 유지하는 전문화된 에이전트입니다.

**주요 이점**:
- **병렬화**: 여러 작업 동시 처리
- **컨텍스트 격리**: 무관한 정보로 인한 오염 방지
- **전문화**: 특정 도메인에 특화된 에이전트

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

---

#### 2.7.2 파일 기반 서브에이전트 (Claude Code 스타일)
**설명**: `.claude/agents/` 디렉토리에 Markdown 파일로 정의된 서브에이전트입니다.

**파일 예시** (`.claude/agents/code-reviewer.md`):
```markdown
---
name: code-reviewer
description: Review code for bugs and suggest improvements
---

You are a code review expert. Analyze the provided code and:
1. Identify potential bugs
2. Suggest performance improvements
3. Check for security vulnerabilities
4. Recommend best practices
```

**사용 방법**:
- SDK가 자동으로 `.claude/agents/` 디렉토리에서 로드
- `setting_sources`에 "project" 포함 시 활성화
- Claude가 필요 시 자동으로 서브에이전트 호출

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

---

#### 2.7.3 프로그래밍 방식 서브에이전트
**설명**: 코드로 직접 정의하는 서브에이전트입니다.

**Python 예시** (AgentDefinition):
```python
from claude_agent_sdk import ClaudeAgentOptions, AgentDefinition

code_reviewer = AgentDefinition(
    name="code-reviewer",
    description="Review code for bugs and improvements",
    system_prompt="You are a code review expert...",
    allowed_tools=["Read", "Grep"],
    model="claude-sonnet-4-5-20250929"
)

options = ClaudeAgentOptions(
    agents=[code_reviewer]
)
```

**TypeScript 예시**:
```typescript
const options = {
  agents: [
    {
      name: "code-reviewer",
      description: "Review code for bugs and improvements",
      systemPrompt: "You are a code review expert...",
      allowedTools: ["Read", "Grep"],
      model: "claude-sonnet-4-5-20250929"
    }
  ]
};
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/typescript

---

### 2.8 컨텍스트 관리

#### 2.8.1 자동 컨텍스트 압축 (Compaction)
**설명**: 컨텍스트 한계 도달 시 이전 메시지를 자동으로 요약하여 대화를 계속할 수 있게 합니다.

**특징**:
- Claude Code의 `/compact` 명령어 기반
- 장기 실행 에이전트에 필수
- 자동으로 활성화됨

**TypeScript PreCompact Hook**:
```typescript
const options: Options = {
  hooks: {
    PreCompact: [
      {
        matcher: "*",
        async hook(inputData, toolUseId, context) {
          console.log("Context compaction about to occur");
          // 압축 전 로직 실행
          return {};
        }
      }
    ]
  }
};
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

---

#### 2.8.2 세션 관리
**설명**: 대화 세션을 재개하거나 분기할 수 있습니다.

**Python 예시**:
```python
options = ClaudeAgentOptions(
    continue_conversation=True  # 이전 세션 재개
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Continue from where we left off")
    async for msg in client.receive_response():
        print(msg)
```

**TypeScript 예시**:
```typescript
const options = {
  continue: true,  // 세션 재개
  resume: "session_id_123",  // 특정 세션 재개
  forkSession: "session_id_456"  // 세션 분기
};

for await (const message of query({ prompt: "Continue", options })) {
  console.log(message);
}
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/typescript

---

### 2.9 권한 관리

#### 2.9.1 Permission Mode
**설명**: 도구 사용 시 권한 처리 방식을 결정합니다.

**모드 종류**:
- `default`: 사용자에게 승인 요청 (대화형)
- `acceptEdits`: 파일 편집 자동 승인
- `bypassPermissions`: 모든 작업 자동 승인 (주의!)
- `plan`: 계획 모드 (실행하지 않고 계획만 수립)

**Python 예시**:
```python
options = ClaudeAgentOptions(
    permission_mode='acceptEdits',  # 파일 편집 자동 승인
    allowed_tools=["Read", "Write", "Edit"]
)
```

**TypeScript 예시**:
```typescript
const options = {
  permissionMode: 'acceptEdits',
  allowedTools: ["Read", "Write", "Edit"]
};
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/python

---

#### 2.9.2 can_use_tool / canUseTool 함수
**설명**: 커스텀 권한 검증 로직을 구현할 수 있습니다.

**Python 예시**:
```python
def custom_permission_check(tool_name: str, tool_input: dict) -> bool:
    """특정 도구/입력에 대한 커스텀 권한 검증."""
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        # rm 명령어 금지
        if "rm " in command:
            return False
    return True

options = ClaudeAgentOptions(
    can_use_tool=custom_permission_check
)
```

**TypeScript 예시**:
```typescript
const options = {
  canUseTool(toolName: string, toolInput: any): boolean {
    if (toolName === "Bash") {
      const command = toolInput.command || "";
      if (command.includes("rm ")) {
        return false;
      }
    }
    return true;
  }
};
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/typescript

---

### 2.10 슬래시 커맨드 (Slash Commands)

#### 2.10.1 슬래시 커맨드 개요
**설명**: `.claude/commands/` 디렉토리에 Markdown 파일로 정의된 빠른 작업 명령어입니다.

**파일 예시** (`.claude/commands/review.md`):
```markdown
---
description: Review the current pull request
---

Review the code changes in the current pull request and provide feedback on:
1. Code quality
2. Potential bugs
3. Performance issues
4. Security vulnerabilities
```

**사용 방법**:
- SDK가 자동으로 `.claude/commands/` 디렉토리에서 로드
- `setting_sources`에 "project" 포함 시 활성화
- Claude가 필요 시 자동으로 커맨드 실행

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

---

### 2.11 메모리 (CLAUDE.md)

#### 2.11.1 프로젝트 컨텍스트 파일
**설명**: 프로젝트 루트의 `CLAUDE.md` 파일로 프로젝트 전체 컨텍스트를 유지합니다.

**예시** (`CLAUDE.md`):
```markdown
# Project Context

## Tech Stack
- Python 3.10+
- FastAPI
- PostgreSQL
- Redis

## Architecture
Clean Architecture with 4 layers:
- Domain
- Application
- Infrastructure
- Presentation

## Coding Standards
- Use type hints
- Google-style docstrings
- Max line length: 100
- Double quotes for strings
```

**사용 방법**:
```python
options = ClaudeAgentOptions(
    setting_sources=['project']  # CLAUDE.md 로드
)
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

---

### 2.12 에러 핸들링

#### 2.12.1 예외 클래스
**설명**: SDK가 제공하는 에러 타입입니다.

**Python 예외**:
- `ClaudeSDKError`: 기본 예외 클래스
- `CLINotFoundError`: Claude Code CLI 미설치
- `ProcessError`: 프로세스 실행 실패 (exit code 포함)
- `CLIJSONDecodeError`: 응답 파싱 실패

**에러 핸들링 예시**:
```python
from claude_agent_sdk import (
    query, CLINotFoundError, ProcessError, CLIJSONDecodeError
)

try:
    async for message in query(prompt="Hello"):
        print(message)
except CLINotFoundError:
    print("Please install Claude Code: npm install -g @anthropic-ai/claude-code")
except ProcessError as e:
    print(f"Process failed with exit code: {e.exit_code}")
    print(f"Error: {e}")
except CLIJSONDecodeError as e:
    print(f"Failed to parse response: {e}")
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/python

---

### 2.13 인증 옵션

#### 2.13.1 지원 인증 방식
**설명**: Claude API에 접근하기 위한 다양한 인증 방법을 지원합니다.

**인증 방식**:
1. **직접 API 키**: `ANTHROPIC_API_KEY` 환경 변수
2. **Amazon Bedrock**: AWS 통합
3. **Google Vertex AI**: Google Cloud 통합

**환경 변수 설정**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**문서 링크**: https://docs.claude.com/en/api/agent-sdk/overview

---

## 3. 고급 기능 및 베스트 프랙티스

### 3.1 에이전트 루프 아키텍처

**설명**: Claude 에이전트는 구조화된 피드백 사이클로 동작합니다.

**에이전트 루프 단계**:
1. **컨텍스트 수집** (Gather context): 관련 정보 탐색 및 수집
2. **액션 실행** (Take action): 도구를 사용하여 작업 수행
3. **검증** (Verify work): 결과 평가 및 개선
4. **반복** (Iterate): 피드백 기반으로 개선

**Mermaid 다이어그램**:
```mermaid
graph LR
    A[컨텍스트 수집] --> B[액션 실행]
    B --> C[검증]
    C --> D[반복]
    D --> A
```

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

### 3.2 컨텍스트 관리 전략

#### 3.2.1 에이전트 검색 (Agentic Search)
**설명**: 파일 시스템을 계층적으로 구조화하고, `grep`, `tail` 등의 Bash 유틸리티를 사용하여 선택적으로 정보를 검색합니다.

**장점**:
- **투명성**: 검색 과정이 명확함
- **유지보수성**: 디버깅 및 개선이 쉬움
- **확장성**: 대규모 코드베이스에 적합

**예시**:
```python
options = ClaudeAgentOptions(
    allowed_tools=["Bash", "Grep", "Read"],
    permission_mode='default'
)

async for message in query(
    prompt="Find all TODO comments in Python files",
    options=options
):
    pass
```

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

#### 3.2.2 시맨틱 검색 (Semantic Search)
**설명**: 벡터 기반 검색으로 개념적으로 유사한 정보를 빠르게 찾습니다.

**사용 시기**:
- 성능이 중요한 경우
- 개념적 유사성 매칭이 필요한 경우

**권장사항**:
- 에이전트 검색으로 시작
- 성능 문제 발생 시 시맨틱 검색 추가

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

#### 3.2.3 서브에이전트를 통한 병렬화
**설명**: 여러 서브에이전트를 동시에 실행하여 작업을 병렬 처리합니다.

**장점**:
- **효율성**: 동시에 여러 작업 수행
- **컨텍스트 격리**: 무관한 정보로 인한 오염 방지
- **모듈화**: 각 서브에이전트가 특정 작업에 집중

**예시**:
```python
# .claude/agents/tester.md
# .claude/agents/documenter.md
# .claude/agents/code-reviewer.md

options = ClaudeAgentOptions(
    setting_sources=['project']
)

async for message in query(
    prompt="Review, test, and document the new feature",
    options=options
):
    pass
```

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

### 3.3 액션 실행 패턴

#### 3.3.1 도구 설계 원칙
**설명**: 효과적인 도구를 설계하기 위한 지침입니다.

**원칙**:
- **명확성**: 도구 이름과 설명이 명확해야 함
- **주요 작업 우선**: 자주 사용하는 작업을 도구로 제공
- **조합 가능성**: 작은 도구들을 조합하여 복잡한 작업 수행
- **정확성**: 일관된 결과 보장

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

#### 3.3.2 코드 생성 활용
**설명**: 복잡한 작업에 코드를 생성하여 정확성과 재사용성을 높입니다.

**사용 사례**:
- 파일 생성
- 데이터 변환
- 복잡한 계산
- 반복 작업

**예시**:
```python
async for message in query(
    prompt="Write a Python script to convert CSV to JSON with type inference",
    options=ClaudeAgentOptions(allowed_tools=["Write", "Bash"])
):
    pass
```

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

#### 3.3.3 Bash의 유연성
**설명**: Bash 명령어를 사용하여 범용적이고 임시적인 작업을 수행합니다.

**사용 사례**:
- 파일 다운로드
- 포맷 변환
- 내용 검색

**예시**:
```python
async for message in query(
    prompt="Download the latest release from GitHub and extract it",
    options=ClaudeAgentOptions(allowed_tools=["Bash"])
):
    pass
```

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

#### 3.3.4 Model Context Protocol (MCP)
**설명**: 외부 서비스 (Slack, GitHub, Asana 등)를 표준화된 방식으로 통합합니다.

**장점**:
- OAuth 자동 처리
- 표준 프로토콜
- 다양한 서비스 지원

**예시**:
```python
options = ClaudeAgentOptions(
    mcp_servers={
        "slack": {
            "type": "stdio",
            "command": "slack-mcp-server"
        },
        "github": {
            "type": "stdio",
            "command": "github-mcp-server"
        }
    },
    allowed_tools=["mcp__slack__send_message", "mcp__github__create_issue"]
)
```

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

### 3.4 검증 및 품질 보장

#### 3.4.1 규칙 기반 피드백
**설명**: 명시적인 검증 규칙을 정의하여 결과를 평가합니다.

**예시**:
- 코드 린팅 (TypeScript > JavaScript)
- 유닛 테스트
- 정적 분석

**장점**:
- **조기 오류 감지**: 명확한 규칙으로 빠른 피드백
- **다층 피드백**: 여러 단계의 검증

**예시**:
```python
async for message in query(
    prompt="Write a TypeScript function and ensure it passes ESLint",
    options=ClaudeAgentOptions(allowed_tools=["Write", "Bash"])
):
    pass
```

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

#### 3.4.2 시각적 검증
**설명**: UI 작업의 경우 스크린샷을 생성하여 모델에게 제공하고 반복적으로 개선합니다.

**검증 항목**:
- 레이아웃
- 스타일링
- 콘텐츠 계층
- 반응형 디자인

**예시**:
```python
async for message in query(
    prompt="Create a responsive login page and verify the layout with screenshots",
    options=ClaudeAgentOptions(allowed_tools=["Write", "Bash"])
):
    pass
```

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

#### 3.4.3 LLM-as-Judge 패턴
**설명**: 별도의 모델 인스턴스를 사용하여 퍼지한 기준으로 출력 품질을 평가합니다.

**주의사항**:
- **지연 시간**: 추가 모델 호출로 인한 지연
- **견고성**: 결정론적 검증보다 덜 견고함

**사용 시기**:
- 규칙으로 정의하기 어려운 품질 기준
- 창의성이나 일관성 평가

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

### 3.5 평가 및 반복

#### 3.5.1 체계적 테스트
**설명**: 초기 배포 후 실패 사례를 분석하여 에이전트를 개선합니다.

**프로세스**:
1. **실패 사례 검토**: 누락된 컨텍스트나 도구 식별
2. **패턴 분석**: 반복되는 실패 패턴 찾기
3. **규칙 추가**: 명확한 검증 규칙 추가
4. **도구 확장**: 구조적 한계 해결
5. **테스트 세트 구축**: 실제 사용 패턴 기반 테스트

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

#### 3.5.2 관찰 가능성 (Observability)
**설명**: 도구 사용 패턴을 모니터링하여 최적화 기회를 식별합니다.

**모니터링 항목**:
- 도구 사용 빈도
- 실행 시간
- 에러 발생률
- 성능 병목

**예시**:
```python
async def log_tool_usage(input_data, tool_use_id, context):
    """도구 사용 로깅."""
    tool_name = input_data["tool_name"]
    print(f"[MONITOR] Tool: {tool_name}, ID: {tool_use_id}")
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [HookMatcher(matcher="*", hooks=[log_tool_usage])]
    }
)
```

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

### 3.6 프로덕션 고려사항

#### 3.6.1 작업 경계 구조화
**설명**: 명확한 작업 경계를 설정하여 에이전트를 배포합니다.

**원칙**:
- 각 에이전트는 명확한 책임을 가짐
- 고위험 작업은 별도의 검증 에이전트로 분리
- 작업 단위를 작게 유지

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

#### 3.6.2 점진적 확장
**설명**: 에이전트 기능을 확장할 때 성능 저하를 조기에 감지합니다.

**권장사항**:
- 작은 기능부터 시작
- 각 확장 후 테스트
- 성능 메트릭 모니터링

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

## 4. 사용 사례

### 4.1 금융 에이전트
**설명**: API와 코드 실행을 통해 포트폴리오를 분석합니다.

**기능**:
- 실시간 시장 데이터 조회
- 포트폴리오 성과 분석
- 투자 추천

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

### 4.2 개인 비서
**설명**: 플랫폼 간 캘린더 및 데이터를 관리합니다.

**기능**:
- 일정 관리
- 이메일 자동화
- 작업 추적

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

### 4.3 고객 지원
**설명**: 모호한 요청을 처리하고 에스컬레이션합니다.

**기능**:
- 자연어 문의 처리
- 지식 베이스 검색
- 복잡한 문제 에스컬레이션

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

### 4.4 연구 에이전트
**설명**: 대규모 문서 컬렉션을 종합합니다.

**기능**:
- 문서 검색 및 분석
- 요약 생성
- 인사이트 추출

**문서 링크**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

## 5. 참고 자료

### 5.1 공식 문서
- **SDK 개요**: https://docs.claude.com/en/api/agent-sdk/overview
- **Python SDK 레퍼런스**: https://docs.claude.com/en/api/agent-sdk/python
- **TypeScript SDK 레퍼런스**: https://docs.claude.com/en/api/agent-sdk/typescript

### 5.2 GitHub 저장소
- **Python SDK**: https://github.com/anthropics/claude-agent-sdk-python
- **TypeScript SDK**: https://github.com/anthropics/claude-agent-sdk-typescript

### 5.3 공식 블로그
- **Building agents with the Claude Agent SDK**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

### 5.4 튜토리얼 및 가이드
- **DataCamp Tutorial**: https://www.datacamp.com/tutorial/how-to-use-claude-agent-sdk
- **Jimmy Song's Guide**: https://jimmysong.io/en/ai/claude-agent-sdk-python/
- **Bind AI Blog**: https://blog.getbind.co/2025/10/03/how-to-create-agents-with-claude-agents-sdk/
- **PromptLayer Blog**: https://blog.promptlayer.com/building-agents-with-claude-codes-sdk/

### 5.5 패키지 저장소
- **PyPI**: https://pypi.org/project/claude-agent-sdk/
- **npm**: `@anthropic-ai/claude-agent-sdk`

---

## 6. 빠른 참조

### 6.1 설치 명령어
```bash
# Python
pip install claude-agent-sdk

# TypeScript
npm install @anthropic-ai/claude-agent-sdk

# Claude Code CLI (필수)
npm install -g @anthropic-ai/claude-code
```

### 6.2 기본 사용 패턴

**Python (간단한 쿼리)**:
```python
import anyio
from claude_agent_sdk import query

async def main():
    async for message in query(prompt="Hello Claude"):
        print(message)

anyio.run(main)
```

**Python (고급 클라이언트)**:
```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async with ClaudeSDKClient(options=ClaudeAgentOptions()) as client:
    await client.query("Help me with coding")
    async for msg in client.receive_response():
        print(msg)
```

**TypeScript (기본)**:
```typescript
import { query } from '@anthropic-ai/claude-agent-sdk';

for await (const message of query({ prompt: "Hello Claude" })) {
  console.log(message);
}
```

### 6.3 주요 옵션 빠른 설정

**파일 편집 자동 승인**:
```python
options = ClaudeAgentOptions(permission_mode='acceptEdits')
```

**특정 도구만 허용**:
```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Bash"]
)
```

**작업 디렉토리 설정**:
```python
options = ClaudeAgentOptions(cwd="/path/to/project")
```

**최대 턴 제한**:
```python
options = ClaudeAgentOptions(max_turns=5)
```

### 6.4 내장 도구 전체 목록

Claude Agent SDK는 다음 16가지 내장 도구를 제공합니다:

| 도구 | 카테고리 | 설명 |
|------|----------|------|
| **Read** | 파일 작업 | 파일 읽기 (이미지, PDF 지원) |
| **Write** | 파일 작업 | 파일 생성 또는 덮어쓰기 |
| **Edit** | 파일 작업 | 파일 내 정확한 문자열 치환 |
| **MultiEdit** | 파일 작업 | 단일 파일에 여러 편집 일괄 수행 |
| **Glob** | 검색 | 패턴 매칭으로 파일 빠르게 검색 |
| **Grep** | 검색 | 정규식을 활용한 파일 내용 검색 |
| **LS** | 검색 | 디렉토리 파일 및 폴더 목록화 |
| **Bash** | 시스템 | 지속적인 셸 세션에서 bash 명령 실행 |
| **WebSearch** | 웹 | 웹 검색 수행 (미국 한정) |
| **WebFetch** | 웹 | URL 콘텐츠 조회 및 AI 처리 |
| **NotebookRead** | 노트북 | Jupyter 노트북 셀 및 결과 읽기 |
| **NotebookEdit** | 노트북 | Jupyter 노트북 셀 편집/삽입/삭제 |
| **Agent** | 에이전트 | 서브에이전트 실행 |
| **TodoRead** | 작업 관리 | 현재 세션의 할 일 목록 조회 |
| **TodoWrite** | 작업 관리 | 작업 목록 생성 및 관리 |
| **exit_plan_mode** | 시스템 | 계획 모드 종료 |

**도구 제어 방법**:
```python
# 특정 도구만 허용
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Bash", "Grep"]
)

# 특정 도구 차단
options = ClaudeAgentOptions(
    disallowed_tools=["Bash", "WebSearch"]
)

# 모든 도구 허용 (주의!)
options = ClaudeAgentOptions(
    permission_mode='bypassPermissions'
)
```

### 6.5 권한 시스템 처리 순서

SDK의 권한 시스템은 다음 순서로 도구 사용을 평가합니다:

```
1. PreToolUse Hook 실행
   ↓
2. Deny 규칙 확인 (settings.json)
   ↓
3. Allow 규칙 확인 (settings.json)
   ↓
4. Ask 규칙 확인 (settings.json)
   ↓
5. Permission Mode 평가 (default/acceptEdits/bypassPermissions)
   ↓
6. canUseTool 콜백 실행
   ↓
7. PostToolUse Hook 실행
```

**중요**:
- Deny 규칙은 모든 권한 모드를 무시합니다
- Hooks는 모든 단계에서 도구 사용을 제어할 수 있습니다

### 6.6 Permission Modes 상세

| 모드 | 동작 | 자동 승인 작업 | 사용 시나리오 |
|------|------|---------------|-------------|
| `default` | 표준 권한 체크 | 없음 | 제어된 실행 환경, 대화형 작업 |
| `acceptEdits` | 파일 편집 자동 승인 | 파일 편집, mkdir, rm, mv, cp | 신뢰할 수 있는 파일 작업 |
| `bypassPermissions` | 모든 도구 자동 승인 | 모든 작업 | 테스트 환경 (프로덕션 회피!) |
| `plan` | 읽기 전용 도구만 사용 | 없음 | 계획 수립 단계 (현재 SDK 미지원) |

**동적 모드 변경 (스트리밍 전용)**:
```typescript
const q = query({
  prompt: streamInput(),
  options: { permissionMode: 'default' }
});

// 실행 중 모드 변경
await q.setPermissionMode('acceptEdits');
```

### 6.7 유용한 패턴

**에러 핸들링**:
```python
from claude_agent_sdk import CLINotFoundError, ProcessError

try:
    async for message in query(prompt="Hello"):
        print(message)
except CLINotFoundError:
    print("Install Claude Code: npm install -g @anthropic-ai/claude-code")
except ProcessError as e:
    print(f"Error: {e.exit_code}")
```

**커스텀 도구 생성**:
```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("my_tool", "Description", {"param": str})
async def my_tool(args):
    return {"content": [{"type": "text", "text": "Result"}]}

server = create_sdk_mcp_server("tools", "1.0.0", [my_tool])
```

**권한 제어 훅**:
```python
async def check_permission(input_data, tool_use_id, context):
    if "dangerous" in input_data.get("tool_input", {}).get("command", ""):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Dangerous command blocked"
            }
        }
    return {}

options = ClaudeAgentOptions(
    hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[check_permission])]}
)
```

---

## 부록: 버전 및 업데이트

### 최신 정보
- **Claude Sonnet 4.5**: 2025년 9월 출시
- **Claude Agent SDK**: 이전 Claude Code SDK에서 이름 변경
- **Python 요구사항**: 3.10 이상
- **Claude Code CLI**: 2.0.0 이상

### 주요 변경사항
- 이름 변경: Claude Code SDK → Claude Agent SDK
- In-process MCP 서버 지원 추가
- TypeScript SDK와 Python SDK 동등한 기능 제공
- 성능 최적화 및 자동 프롬프트 캐싱

---

---

## 7. 추가 참고 자료 및 링크

### 7.1 모든 내장 도구 상세 정보
- **Claude Code Tools Gist**: https://gist.github.com/wong2/e0f34aac66caf890a332f7b6f9e2ba8f
  - 16가지 내장 도구의 전체 파라미터 및 설명

### 7.2 권한 시스템 상세 가이드
- **Handling Permissions**: https://docs.claude.com/en/api/agent-sdk/permissions
  - Permission Modes 상세 설명
  - Hooks, canUseTool 콜백, settings.json 규칙
  - 권한 처리 순서

### 7.3 Custom Tools & MCP 통합
- **Custom Tools Documentation**: https://docs.claude.com/en/api/agent-sdk/custom-tools
  - In-process MCP 서버 생성 방법
  - tool() 함수 및 createSdkMcpServer() 사용법
  - 스트리밍 모드 요구사항
  - 도구 네이밍 규칙

### 7.4 Model Context Protocol (MCP) 리소스
- **MCP 공식 문서**: Model Context Protocol의 표준 및 사양
- **MCP 생태계**: Slack, GitHub, Asana 등 외부 MCP 서버 통합 예제

### 7.5 Subagents 가이드
- **Subagents Documentation**: https://docs.claude.com/en/docs/claude-code/sub-agents
- **Best Practices**: https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/
- **Slash Commands vs Subagents**: https://jxnl.co/writing/2025/08/29/context-engineering-slash-commands-subagents/

### 7.6 실전 튜토리얼
- **DataCamp Tutorial**: https://www.datacamp.com/tutorial/how-to-use-claude-agent-sdk
  - Claude Sonnet 4.5를 사용한 에이전트 생성 튜토리얼
- **eesel AI Guide**: https://www.eesel.ai/blog/python-claude-code-sdk
  - Python Claude Code SDK 실용 가이드 (2025)
- **Skywork AI Guides**:
  - https://skywork.ai/blog/building-your-first-coding-agent-with-claude-code-sdk/
  - https://skywork.ai/blog/claude-code-sdk-tutorial-how-to-set-it-up-in-minutes/
  - https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/

### 7.7 고급 아티클
- **Anthropic Engineering Blog**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
  - 에이전트 아키텍처 및 베스트 프랙티스
- **Promptfoo Integration**: https://www.promptfoo.dev/docs/providers/claude-agent-sdk/
  - Claude Agent SDK 테스트 및 평가

### 7.8 커뮤니티 리소스
- **Discord 커뮤니티**: https://anthropic.com/discord
- **GitHub Issues**:
  - Python: https://github.com/anthropics/claude-agent-sdk-python/issues
  - TypeScript: https://github.com/anthropics/claude-agent-sdk-typescript/issues
- **GitHub 예제 저장소**:
  - https://github.com/kenneth-liao/claude-agent-sdk-intro
  - https://github.com/webdevtodayjason/sub-agents
  - https://github.com/davepoon/claude-code-subagents-collection

---

## 8. 문서 변경 이력

### 2025-01-23 업데이트
- 16가지 내장 도구 전체 목록 추가
- 권한 시스템 처리 순서 상세 설명
- Permission Modes 비교 표 추가
- MCP 도구 스트리밍 모드 요구사항 명시
- 도구 네이밍 규칙 추가
- 추가 참고 자료 섹션 확장

### 초기 작성
- Claude Agent SDK 핵심 기능 정리
- Python/TypeScript API 레퍼런스
- 사용 예제 및 베스트 프랙티스

---

이 문서는 Claude Agent SDK의 모든 주요 기능을 체계적으로 정리한 가이드입니다. 각 섹션에는 공식 문서 링크가 포함되어 있으며, 실제 사용 예시와 함께 제공됩니다.
