import { X, Maximize2, Send, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { LogItem, useWorkflowStore } from '@/stores/workflowStore'
import { ParsedContent } from './ParsedContent'
import { AutoScrollContainer } from './AutoScrollContainer'
import { Button } from './ui/button'
import { continueNodeConversation, API_BASE } from '@/lib/api'

interface NodeLogSection {
  nodeId: string
  nodeName: string
  logs: LogItem[]
}

interface LogDetailModalProps {
  isOpen: boolean
  onClose: () => void
  sections: NodeLogSection[]
  title?: string
}

export function LogDetailModal({ isOpen, onClose, sections, title = "실행 로그 상세" }: LogDetailModalProps) {
  if (!isOpen) return null

  const hasSections = sections.length > 0
  const singleSection = sections.length === 1

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full h-full max-w-7xl max-h-[90vh] flex flex-col shadow-2xl border border-gray-200">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center gap-2">
            <Maximize2 className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            {hasSections && (
              <span className="text-sm text-gray-600">
                ({sections.length}개 노드)
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* 로그 내용 */}
        <div className="flex-1 overflow-hidden">
          {!hasSections ? (
            <div className="h-full flex items-center justify-center text-gray-500">
              로그가 없습니다
            </div>
          ) : singleSection ? (
            // 단일 노드: 전체 화면
            <div className="h-full p-4 bg-gray-50">
              <LogSection section={sections[0]} />
            </div>
          ) : (
            // 다중 노드: 좌우 분할 또는 그리드
            <div className={`h-full grid ${sections.length === 2 ? 'grid-cols-2' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'} gap-4 p-4 overflow-y-auto bg-gray-50`}>
              {sections.map((section) => (
                <div key={section.nodeId} className="border border-gray-200 rounded-lg overflow-hidden bg-white">
                  <LogSection section={section} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 푸터 */}
        <div className="p-4 border-t border-gray-200 bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-900 rounded-lg transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  )
}

function LogSection({ section }: { section: NodeLogSection }) {
  // 추가 프롬프트 입력 상태
  const [userInput, setUserInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const [_continueSessionId, setContinueSessionId] = useState<string | null>(null)

  // Zustand store
  const addLog = useWorkflowStore((state) => state.addLog)

  // 로그 타입별 분류
  const inputLogs = section.logs.filter(log => log.type === 'input')
  const executionLogs = section.logs.filter(log => log.type === 'execution')
  const outputLogs = section.logs.filter(log => log.type === 'output')
  const errorLogs = section.logs.filter(log => log.type === 'error')
  const otherLogs = section.logs.filter(log => !['input', 'execution', 'output', 'error'].includes(log.type))

  // 추가 프롬프트 전송
  const handleSendPrompt = async () => {
    if (!userInput.trim() || isSending) return

    setIsSending(true)
    setSendError(null)

    try {
      // API 호출
      const apiResponse = await continueNodeConversation(section.nodeId, userInput.trim())
      const sessionId = apiResponse.session_id

      // 입력 로그 추가
      addLog(section.nodeId, 'input', `📝 추가 프롬프트: ${userInput.trim()}`)
      setUserInput('') // 입력 초기화

      // SSE 연결 시작 (fetch + ReadableStream 패턴)
      setContinueSessionId(sessionId)

      const sseResponse = await fetch(`${API_BASE}/workflows/sessions/${sessionId}/stream`, {
        method: 'GET',
        headers: {
          'Accept': 'text/event-stream',
        },
      })

      if (!sseResponse.ok) {
        throw new Error(`SSE 연결 실패: ${sseResponse.status}`)
      }

      const reader = sseResponse.body?.getReader()
      if (!reader) {
        throw new Error('SSE 스트림을 읽을 수 없습니다')
      }

      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      // 백그라운드에서 SSE 읽기
      ;(async () => {
        try {
          while (true) {
            const { done, value } = await reader.read()

            if (done) {
              setIsSending(false)
              setContinueSessionId(null)
              break
            }

            // 청크를 문자열로 변환
            const chunk = decoder.decode(value, { stream: true })
            buffer += chunk

            // SSE 메시지 파싱 (빈 줄로 구분)
            const messages = buffer.split(/\r\n\r\n|\n\n/)
            buffer = messages.pop() || ''

            for (const message of messages) {
              if (!message.trim()) continue

              const lines = message.split(/\r\n|\n/)
              let dataContent = ''

              for (const line of lines) {
                const trimmedLine = line.trim()
                if (trimmedLine.startsWith('data:')) {
                  const lineData = trimmedLine.substring(5).trim()
                  if (lineData !== '[DONE]') {
                    dataContent += lineData
                  }
                }
              }

              if (!dataContent) continue

              try {
                const event = JSON.parse(dataContent)
                const { event_type, node_id, data } = event

                // 청크 타입에 따라 로그 타입 결정
                let logType: 'input' | 'execution' | 'output' | 'error' | 'complete' | 'start' = 'execution'
                if (data?.chunk_type === 'text') {
                  logType = 'output'
                } else if (data?.chunk_type === 'thinking' || data?.chunk_type === 'tool') {
                  logType = 'execution'
                }

                switch (event_type) {
                  case 'node_start':
                    addLog(node_id, 'start', '🚀 노드 추가 대화 시작')
                    break
                  case 'node_output':
                    if (data?.chunk) {
                      addLog(node_id, logType, data.chunk)
                    }
                    break
                  case 'node_complete':
                    addLog(node_id, 'complete', '✅ 노드 추가 대화 완료')
                    break
                  case 'node_error':
                    addLog(node_id, 'error', `❌ 에러: ${data?.error || '알 수 없는 오류'}`)
                    break
                }
              } catch (parseError) {
                console.error('SSE 메시지 파싱 에러:', parseError)
              }
            }
          }
        } catch (streamError) {
          console.error('SSE 스트림 에러:', streamError)
          setIsSending(false)
          setContinueSessionId(null)
        }
      })()

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다'
      setSendError(errorMessage)
      setIsSending(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* 노드 제목 */}
      <div className="p-3 bg-gray-100 border-b border-gray-200">
        <h3 className="font-semibold text-gray-900">{section.nodeName}</h3>
        <p className="text-xs text-gray-600 mt-1">Node ID: {section.nodeId}</p>
      </div>

      {/* 로그 내용 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-white">
        {section.logs.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            로그가 없습니다
          </div>
        ) : (
          <>
            {/* 입력 섹션 */}
            {inputLogs.length > 0 && (
              <div className="border rounded-md overflow-hidden">
                <div className="bg-blue-50 px-3 py-2 border-b border-blue-200">
                  <h4 className="text-sm font-semibold text-blue-900">📥 입력</h4>
                </div>
                <AutoScrollContainer
                  className="p-3"
                  maxHeight="200px"
                  dependency={inputLogs.length}
                >
                  <div className="space-y-2">
                    {inputLogs.map((log, idx) => (
                      <LogItemComponent key={idx} log={log} />
                    ))}
                  </div>
                </AutoScrollContainer>
              </div>
            )}

            {/* 실행 과정 섹션 */}
            {executionLogs.length > 0 && (
              <div className="border rounded-md overflow-hidden">
                <div className="bg-purple-50 px-3 py-2 border-b border-purple-200">
                  <h4 className="text-sm font-semibold text-purple-900">🔧 실행 과정</h4>
                </div>
                <AutoScrollContainer
                  className="p-3"
                  maxHeight="300px"
                  dependency={executionLogs.length}
                >
                  <div className="space-y-2">
                    {executionLogs.map((log, idx) => (
                      <LogItemComponent key={idx} log={log} />
                    ))}
                  </div>
                </AutoScrollContainer>
              </div>
            )}

            {/* 출력 섹션 */}
            {outputLogs.length > 0 && (
              <div className="border rounded-md overflow-hidden">
                <div className="bg-green-50 px-3 py-2 border-b border-green-200">
                  <h4 className="text-sm font-semibold text-green-900">📤 출력</h4>
                </div>
                <AutoScrollContainer
                  className="p-3"
                  maxHeight="300px"
                  dependency={outputLogs.length}
                >
                  <div className="space-y-2">
                    {outputLogs.map((log, idx) => (
                      <LogItemComponent key={idx} log={log} />
                    ))}
                  </div>
                </AutoScrollContainer>
              </div>
            )}

            {/* 에러 섹션 */}
            {errorLogs.length > 0 && (
              <div className="border rounded-md overflow-hidden">
                <div className="bg-red-50 px-3 py-2 border-b border-red-200">
                  <h4 className="text-sm font-semibold text-red-900">❌ 에러</h4>
                </div>
                <AutoScrollContainer
                  className="p-3"
                  maxHeight="250px"
                  dependency={errorLogs.length}
                >
                  <div className="space-y-2">
                    {errorLogs.map((log, idx) => (
                      <LogItemComponent key={idx} log={log} />
                    ))}
                  </div>
                </AutoScrollContainer>
              </div>
            )}

            {/* 기타 로그 */}
            {otherLogs.length > 0 && (
              <div className="border rounded-md overflow-hidden">
                <div className="bg-gray-50 px-3 py-2 border-b border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-900">📝 기타</h4>
                </div>
                <AutoScrollContainer
                  className="p-3"
                  maxHeight="200px"
                  dependency={otherLogs.length}
                >
                  <div className="space-y-2">
                    {otherLogs.map((log, idx) => (
                      <LogItemComponent key={idx} log={log} />
                    ))}
                  </div>
                </AutoScrollContainer>
              </div>
            )}
          </>
        )}
      </div>

      {/* 추가 프롬프트 입력 UI */}
      <div className="p-3 border-t border-gray-200 bg-blue-50">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSendPrompt()
                }
              }}
              placeholder="이 노드에 추가 프롬프트 입력..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isSending}
            />
            <Button
              onClick={handleSendPrompt}
              disabled={!userInput.trim() || isSending}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>전송 중...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>전송</span>
                </>
              )}
            </Button>
          </div>
          {sendError && (
            <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-md border border-red-200">
              ❌ {sendError}
            </div>
          )}
          <p className="text-xs text-gray-600">
            💡 이 노드의 이전 대화 컨텍스트를 유지하며 추가 작업을 요청할 수 있습니다
          </p>
        </div>
      </div>
    </div>
  )
}

function LogItemComponent({ log }: { log: LogItem }) {
  return (
    <div className="bg-white rounded p-2 border border-gray-200 shadow-sm">
      <div className="text-xs text-gray-500 mb-1">
        {new Date(log.timestamp).toLocaleString()}
      </div>
      <ParsedContent content={log.message} />
    </div>
  )
}
