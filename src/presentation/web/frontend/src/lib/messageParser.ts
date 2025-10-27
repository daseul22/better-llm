/**
 * Claude Agent SDK 메시지 파서
 *
 * Worker 출력에서 UserMessage, AssistantMessage, ToolResultBlock 등을
 * 파싱하여 보기 좋은 형식으로 변환합니다.
 *
 * 참고: https://docs.claude.com/en/api/agent-sdk/python
 */

/**
 * ToolResultBlock 파싱 및 포맷팅
 *
 * 예시 입력:
 * ToolResultBlock(tool_use_id='toolu_123', content='Success', is_error=None)
 *
 * 예시 출력:
 * ✅ Tool Result: Success
 */
function parseToolResultBlock(text: string): string | null {
  const regex = /ToolResultBlock\(tool_use_id='([^']+)',\s*content='([^']*)'(?:,\s*is_error=(\w+))?\)/g
  const matches = [...text.matchAll(regex)]

  if (matches.length === 0) return null

  return matches
    .map((match) => {
      const [, toolId, content, isError] = match
      const icon = isError === 'True' ? '❌' : '✅'
      const shortId = toolId.substring(0, 12)
      return `${icon} Tool Result [${shortId}]: ${content || '(empty)'}`
    })
    .join('\n')
}

/**
 * ToolUseBlock 파싱 및 포맷팅
 *
 * 예시 입력:
 * ToolUseBlock(id='toolu_123', name='read', input={'file_path': '/path/to/file'})
 *
 * 예시 출력:
 * 🔧 Tool: read
 *    file_path: /path/to/file
 */
function parseToolUseBlock(text: string): string | null {
  const regex = /ToolUseBlock\(id='([^']+)',\s*name='([^']+)',\s*input=(\{[^}]+\})\)/g
  const matches = [...text.matchAll(regex)]

  if (matches.length === 0) return null

  return matches
    .map((match) => {
      const [, toolId, toolName, inputStr] = match
      const shortId = toolId.substring(0, 12)

      // input 파싱 (간단한 dict 파싱)
      const inputPairs = inputStr
        .replace(/[{}]/g, '')
        .split(',')
        .map((pair) => pair.trim())
        .filter((pair) => pair.length > 0)
        .map((pair) => {
          const [key, value] = pair.split(':').map((s) => s.trim())
          return `   ${key}: ${value?.replace(/'/g, '')}`
        })

      return `🔧 Tool: ${toolName} [${shortId}]\n${inputPairs.join('\n')}`
    })
    .join('\n')
}

/**
 * TextBlock 파싱 및 포맷팅
 *
 * 예시 입력:
 * TextBlock(text='Hello world')
 *
 * 예시 출력:
 * Hello world
 */
function parseTextBlock(text: string): string | null {
  const regex = /TextBlock\(text='([^']*)'\)/g
  const matches = [...text.matchAll(regex)]

  if (matches.length === 0) return null

  return matches.map((match) => match[1]).join('\n')
}

/**
 * ThinkingBlock 파싱 및 포맷팅
 *
 * 예시 입력:
 * ThinkingBlock(thinking='I need to analyze...', signature='...')
 *
 * 예시 출력:
 * 💭 Thinking: I need to analyze...
 */
function parseThinkingBlock(text: string): string | null {
  const regex = /ThinkingBlock\(thinking='([^']*)'(?:,\s*signature='[^']*')?\)/g
  const matches = [...text.matchAll(regex)]

  if (matches.length === 0) return null

  return matches.map((match) => `💭 Thinking: ${match[1]}`).join('\n')
}

/**
 * UserMessage 파싱 및 포맷팅
 *
 * 예시 입력:
 * UserMessage(content=[ToolResultBlock(...), ToolResultBlock(...)], parent_tool_use_id=None)
 *
 * 예시 출력:
 * 📨 User Message:
 *    ✅ Tool Result [...]: ...
 *    ✅ Tool Result [...]: ...
 */
function parseUserMessage(text: string): string | null {
  const regex = /UserMessage\(content=\[(.*?)\](?:,\s*parent_tool_use_id=\w+)?\)/g
  const matches = [...text.matchAll(regex)]

  if (matches.length === 0) return null

  return matches
    .map((match) => {
      const contentStr = match[1]

      // content 내부의 ToolResultBlock 파싱
      const toolResults = parseToolResultBlock(contentStr)
      if (toolResults) {
        return `📨 User Message:\n${toolResults
          .split('\n')
          .map((line) => '   ' + line)
          .join('\n')}`
      }

      return `📨 User Message: ${contentStr.substring(0, 100)}...`
    })
    .join('\n')
}

/**
 * AssistantMessage 파싱 및 포맷팅
 *
 * 예시 입력:
 * AssistantMessage(content=[TextBlock(...), ToolUseBlock(...)])
 *
 * 예시 출력:
 * 🤖 Assistant:
 *    (파싱된 content)
 */
function parseAssistantMessage(text: string): string | null {
  const regex = /AssistantMessage\(content=\[(.*?)\](?:,\s*model='[^']*')?\)/g
  const matches = [...text.matchAll(regex)]

  if (matches.length === 0) return null

  return matches
    .map((match) => {
      const contentStr = match[1]

      // content 내부의 블록들 파싱
      const textBlocks = parseTextBlock(contentStr)
      const toolUseBlocks = parseToolUseBlock(contentStr)
      const thinkingBlocks = parseThinkingBlock(contentStr)

      const parts = [textBlocks, toolUseBlocks, thinkingBlocks].filter(Boolean)

      if (parts.length > 0) {
        return `🤖 Assistant:\n${parts
          .join('\n')
          .split('\n')
          .map((line) => '   ' + line)
          .join('\n')}`
      }

      return `🤖 Assistant: ${contentStr.substring(0, 100)}...`
    })
    .join('\n')
}

/**
 * 메시지 타입 감지
 */
export interface ParsedMessage {
  type: 'user' | 'assistant' | 'tool_result' | 'tool_use' | 'text' | 'thinking' | 'raw'
  content: string
  isCollapsible: boolean
}

/**
 * Claude Agent SDK 메시지 파싱 (메인 함수)
 *
 * Worker 출력 텍스트에서 SDK 메시지 타입을 감지하고 보기 좋게 변환합니다.
 *
 * @param text - Worker 출력 텍스트
 * @returns 파싱된 메시지 객체
 */
export function parseClaudeMessage(text: string): ParsedMessage {
  if (!text || typeof text !== 'string') {
    return { type: 'raw', content: text, isCollapsible: false }
  }

  // UserMessage 파싱 시도 (접을 수 있음)
  const userMsg = parseUserMessage(text)
  if (userMsg) {
    return { type: 'user', content: userMsg, isCollapsible: true }
  }

  // AssistantMessage 파싱 시도
  const assistantMsg = parseAssistantMessage(text)
  if (assistantMsg) {
    return { type: 'assistant', content: assistantMsg, isCollapsible: false }
  }

  // 개별 블록 파싱 시도
  const toolResult = parseToolResultBlock(text)
  if (toolResult) {
    return { type: 'tool_result', content: toolResult, isCollapsible: true }
  }

  const toolUse = parseToolUseBlock(text)
  if (toolUse) {
    return { type: 'tool_use', content: toolUse, isCollapsible: false }
  }

  const textBlock = parseTextBlock(text)
  if (textBlock) {
    return { type: 'text', content: textBlock, isCollapsible: false }
  }

  const thinkingBlock = parseThinkingBlock(text)
  if (thinkingBlock) {
    return { type: 'thinking', content: thinkingBlock, isCollapsible: false }
  }

  // 파싱 실패 시 원본 반환
  return { type: 'raw', content: text, isCollapsible: false }
}
