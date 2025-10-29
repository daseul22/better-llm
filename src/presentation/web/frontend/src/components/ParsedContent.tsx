/**
 * 파싱된 로그 메시지 렌더링 컴포넌트
 *
 * logParser로 파싱된 메시지를 블럭 종류별로 다르게 표시합니다.
 */

import React, { useState } from 'react'
import { ChevronDown, ChevronRight, Brain } from 'lucide-react'
import { parseLogMessage } from '@/lib/logParser'

interface ParsedContentProps {
  content: string
  className?: string
}

/**
 * 파싱된 내용을 블럭 종류별로 렌더링
 */
export const ParsedContent: React.FC<ParsedContentProps> = ({ content, className = '' }) => {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!content || content.trim() === '') {
    return (
      <div className={`text-sm text-muted-foreground text-center py-4 ${className}`}>
        아직 실행되지 않았습니다
      </div>
    )
  }

  // 전체 content를 하나의 메시지로 파싱 시도
  const parsed = parseLogMessage(content)

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded)
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {(() => {

        switch (parsed.type) {
          case 'user_message':
            return (
              <div className="space-y-1">
                <div className="text-xs font-semibold text-blue-700">👤 사용자 메시지</div>
                <div className="text-sm whitespace-pre-wrap bg-blue-50 p-2 rounded border border-blue-200">
                  {parsed.content}
                </div>
              </div>
            )

          case 'assistant_message':
            return (
              <div className="space-y-1">
                <div className="text-xs font-semibold text-purple-700">🤖 어시스턴트 응답</div>
                <div className="text-sm whitespace-pre-wrap bg-purple-50 p-2 rounded border border-purple-200">
                  {parsed.content}
                </div>
              </div>
            )

          case 'tool_use':
            return (
              <div className="space-y-1">
                <div
                  className="flex items-center gap-2 cursor-pointer hover:bg-orange-50 p-1 rounded"
                  onClick={toggleExpanded}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-3 w-3 text-orange-600 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="h-3 w-3 text-orange-600 flex-shrink-0" />
                  )}
                  <div className="text-xs font-semibold text-orange-700 overflow-hidden text-ellipsis whitespace-nowrap">
                    🔧 도구 호출: {parsed.toolUse?.toolName}
                  </div>
                </div>

                {isExpanded && parsed.toolUse && (
                  <div className="ml-5 bg-orange-50 border border-orange-200 rounded p-2 space-y-2 max-h-[300px] overflow-y-auto">
                    {Object.keys(parsed.toolUse.input).length > 0 && (
                      <div>
                        <div className="text-xs font-medium text-gray-700 mb-1">입력 파라미터:</div>
                        <pre className="text-xs bg-white p-2 rounded overflow-x-auto break-words whitespace-pre-wrap">
                          {JSON.stringify(parsed.toolUse.input, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}

                {!isExpanded && (
                  <div className="ml-5 text-xs text-gray-600 overflow-hidden text-ellipsis whitespace-nowrap">
                    {Object.keys(parsed.toolUse?.input || {}).length}개 파라미터
                  </div>
                )}
              </div>
            )

          case 'tool_result':
            return (
              <div className="space-y-1">
                <div
                  className="flex items-center gap-2 cursor-pointer hover:bg-green-50 p-1 rounded"
                  onClick={toggleExpanded}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-3 w-3 text-green-600 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="h-3 w-3 text-green-600 flex-shrink-0" />
                  )}
                  <div className="text-xs font-semibold text-green-700 overflow-hidden text-ellipsis whitespace-nowrap">
                    ✅ 도구 결과: {parsed.toolUse?.toolName}
                  </div>
                </div>

                {isExpanded && (
                  <div className="ml-5 bg-green-50 border border-green-200 rounded p-2 space-y-2 max-h-[300px] overflow-y-auto">
                    <div>
                      <div className="text-xs font-medium text-gray-700 mb-1">결과:</div>
                      <div className="text-xs whitespace-pre-wrap bg-white p-2 rounded break-words">
                        {parsed.content}
                      </div>
                    </div>
                  </div>
                )}

                {!isExpanded && (
                  <div className="ml-5 text-xs text-gray-600 overflow-hidden text-ellipsis whitespace-nowrap">
                    {parsed.content.length > 100 ? `${parsed.content.substring(0, 100)}...` : parsed.content}
                  </div>
                )}
              </div>
            )

          case 'thinking':
            return (
              <div className="space-y-1">
                <div
                  className="flex items-center gap-2 cursor-pointer hover:bg-purple-50 p-1 rounded transition-colors"
                  onClick={toggleExpanded}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-3 w-3 text-purple-600 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="h-3 w-3 text-purple-600 flex-shrink-0" />
                  )}
                  <Brain className="h-3.5 w-3.5 text-purple-600 flex-shrink-0" />
                  <div className="text-xs font-semibold text-purple-700 overflow-hidden text-ellipsis whitespace-nowrap">
                    사고 과정 (Extended Thinking)
                  </div>
                </div>

                {isExpanded && (
                  <div className="ml-5 bg-purple-50 border border-purple-200 rounded p-3 max-h-[300px] overflow-y-auto">
                    <div className="text-xs whitespace-pre-wrap break-words text-purple-900">
                      {parsed.content}
                    </div>
                  </div>
                )}

                {!isExpanded && (
                  <div className="ml-5 text-xs text-purple-600 italic overflow-hidden text-ellipsis whitespace-nowrap">
                    {parsed.content.length > 80 ? `${parsed.content.substring(0, 80)}...` : parsed.content}
                  </div>
                )}
              </div>
            )

          case 'text':
          default:
            // 일반 텍스트는 그대로 표시 (줄바꿈 유지)
            return (
              <div className="text-sm font-mono whitespace-pre-wrap break-words bg-gray-50 p-3 rounded border">
                {parsed.content}
              </div>
            )
        }
      })()}
    </div>
  )
}
