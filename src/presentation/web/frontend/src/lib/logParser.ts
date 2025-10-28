/**
 * 로그 메시지 파싱 유틸리티
 *
 * Claude SDK 응답 메시지를 파싱하여 보기 좋게 표시합니다.
 */

export interface ParsedLogMessage {
  type: 'user_message' | 'tool_result' | 'assistant_message' | 'tool_use' | 'thinking' | 'text'
  content: string
  toolUse?: {
    toolName: string
    input: Record<string, any>
    output?: string
  }
}

/**
 * Python 문자열 리터럴에서 내용 추출 (작은따옴표 이스케이프 처리)
 * 예: 'Hello \\'world\\'' → Hello 'world'
 */
function extractPythonString(str: string, startIndex: number): { content: string; endIndex: number } | null {
  let content = ''
  let i = startIndex
  let escaped = false

  while (i < str.length) {
    const char = str[i]

    if (escaped) {
      // 이스케이프된 문자 처리
      switch (char) {
        case 'n':
          content += '\n'
          break
        case 't':
          content += '\t'
          break
        case 'r':
          content += '\r'
          break
        case '\\':
          content += '\\'
          break
        case "'":
          content += "'"
          break
        case '"':
          content += '"'
          break
        default:
          content += char
      }
      escaped = false
    } else if (char === '\\') {
      escaped = true
    } else if (char === "'") {
      // 문자열 끝
      return { content, endIndex: i + 1 }
    } else {
      content += char
    }

    i++
  }

  // 문자열이 닫히지 않음
  return null
}

/**
 * UserMessage Python repr 형식 파싱
 * 예: UserMessage(content=[ToolResultBlock(tool_use_id='...', content='...', is_error=None)], parent_tool_use_id=None)
 */
function parseUserMessageRepr(message: string): ParsedLogMessage | null {
  // UserMessage 시작 확인
  if (!message.startsWith('UserMessage(')) {
    return null
  }

  // ToolResultBlock 파싱 시도
  if (message.includes('ToolResultBlock(')) {
    const toolUseIdMatch = message.match(/tool_use_id='([^']+)'/)
    if (!toolUseIdMatch) return null

    const toolUseId = toolUseIdMatch[1]

    // content=' 위치 찾기
    const contentStartIndex = message.indexOf("content='")
    if (contentStartIndex === -1) return null

    // content 문자열 추출 (작은따옴표 이스케이프 처리)
    const extracted = extractPythonString(message, contentStartIndex + 9)
    if (!extracted) return null

    return {
      type: 'tool_result',
      content: extracted.content,
      toolUse: {
        toolName: '도구 실행',  // ToolResultBlock에는 도구 이름이 없음
        input: {},
        output: extracted.content,
      }
    }
  }

  // TextBlock 파싱 시도
  if (message.includes('TextBlock(')) {
    const textStartIndex = message.indexOf("text='")
    if (textStartIndex === -1) return null

    // text 문자열 추출 (작은따옴표 이스케이프 처리)
    const extracted = extractPythonString(message, textStartIndex + 6)
    if (!extracted) return null

    return {
      type: 'user_message',
      content: extracted.content,
    }
  }

  return null
}

/**
 * JSON 형식의 메시지 파싱 (Pydantic model_dump 출력)
 */
function parseJSONMessage(message: string): ParsedLogMessage | null {
  try {
    const data = JSON.parse(message)

    // AssistantMessage 형식
    if (data.role === 'assistant' && data.content) {
      const blocks = Array.isArray(data.content) ? data.content : [data.content]

      for (const block of blocks) {
        // TextBlock
        if (block.type === 'text' && block.text) {
          return {
            type: 'assistant_message',
            content: block.text,
          }
        }

        // ThinkingBlock (Extended Thinking)
        // SDK에서 thinking 필드로 전송 (text가 아님)
        if (block.type === 'thinking' && (block.thinking || block.text)) {
          return {
            type: 'thinking',
            content: block.thinking || block.text,  // 하위 호환성 유지
          }
        }

        // ToolUseBlock
        if (block.type === 'tool_use' && block.name) {
          return {
            type: 'tool_use',
            content: `도구 호출: ${block.name}`,
            toolUse: {
              toolName: block.name,
              input: block.input || {},
            }
          }
        }
      }
    }

    // UserMessage 형식
    if (data.role === 'user' && data.content) {
      const blocks = Array.isArray(data.content) ? data.content : [data.content]

      for (const block of blocks) {
        if (block.type === 'text' && block.text) {
          return {
            type: 'user_message',
            content: block.text,
          }
        }
      }
    }

    // SystemMessage 형식
    if (data.role === 'system') {
      if (typeof data.content === 'string') {
        return {
          type: 'text',
          content: data.content,
        }
      } else if (Array.isArray(data.content)) {
        for (const block of data.content) {
          if (block.type === 'text' && block.text) {
            return {
              type: 'text',
              content: block.text,
            }
          }
        }
      }
    }

    // ToolResultBlock (content blocks 안에 있을 수 있음)
    if (data.type === 'tool_result' && data.content) {
      const content = typeof data.content === 'string' ? data.content : JSON.stringify(data.content, null, 2)
      return {
        type: 'tool_result',
        content,
        toolUse: {
          toolName: data.tool_name || 'Unknown',
          input: {},
          output: content,
        }
      }
    }

    // 파싱 가능했지만 알 수 없는 형식
    return {
      type: 'text',
      content: JSON.stringify(data, null, 2),
    }
  } catch (e) {
    // JSON 파싱 실패
    return null
  }
}

/**
 * 로그 메시지 파싱 (메인 함수)
 */
export function parseLogMessage(message: string): ParsedLogMessage {
  // 1. UserMessage Python repr 파싱 (우선순위 최상)
  const userMessageRepr = parseUserMessageRepr(message)
  if (userMessageRepr) return userMessageRepr

  // 2. JSON 형식 파싱 시도
  const jsonParsed = parseJSONMessage(message)
  if (jsonParsed) return jsonParsed

  // 3. 파싱 실패 시 원본 반환
  return {
    type: 'text',
    content: message,
  }
}
