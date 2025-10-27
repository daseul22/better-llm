/**
 * 실행 패널 컴포넌트
 *
 * 워크플로우 실행 및 결과 표시를 담당합니다.
 */

import React, { useState, useEffect, useRef } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useWorkflowStore } from '@/stores/workflowStore'
import { executeWorkflow } from '@/lib/api'
import { parseClaudeMessage } from '@/lib/messageParser'
import { Play, Square, Loader2 } from 'lucide-react'

export const ExecutionPanel: React.FC = () => {
  // ✅ Zustand selector로 개별 필드 구독 (리렌더링 최적화)
  const getWorkflow = useWorkflowStore((state) => state.getWorkflow)
  const startExecution = useWorkflowStore((state) => state.startExecution)
  const stopExecution = useWorkflowStore((state) => state.stopExecution)
  const setCurrentNode = useWorkflowStore((state) => state.setCurrentNode)
  const addNodeOutput = useWorkflowStore((state) => state.addNodeOutput)
  const addLog = useWorkflowStore((state) => state.addLog)
  const clearExecution = useWorkflowStore((state) => state.clearExecution)

  // ✅ 로그 배열 구독
  const logs = useWorkflowStore((state) => state.execution.logs)

  const [initialInput, setInitialInput] = useState('웹 UI 추가')
  const [isRunning, setIsRunning] = useState(false)

  // ✅ 로그 자동 스크롤 (최신 로그로 이동)
  const logEndRef = useRef<HTMLDivElement>(null)

  // ✅ 접을 수 있는 로그의 펼침 상태 관리 (로그 인덱스 → 펼침 여부)
  const [expandedLogs, setExpandedLogs] = useState<Set<number>>(new Set())

  // 디버깅: logs 배열 변경 추적
  useEffect(() => {
    console.log('[ExecutionPanel] logs 변경됨:', logs.length, logs)
  }, [logs])

  // 로그 펼침/접기 토글
  const toggleLogExpand = (index: number) => {
    setExpandedLogs((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  // 로그가 추가될 때마다 자동 스크롤
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // 워크플로우 실행
  const handleExecute = async () => {
    if (isRunning) return

    try {
      setIsRunning(true)
      startExecution()  // 초기 로그 포함 (store에서 자동 추가)

      const workflow = getWorkflow()

      await executeWorkflow(
        workflow,
        initialInput,
        // onEvent
        (event) => {
          console.log('='.repeat(60))
          console.log('[ExecutionPanel] 🎯 onEvent 콜백 호출됨!')
          console.log('[ExecutionPanel] 전체 이벤트:', JSON.stringify(event, null, 2))

          const { event_type, node_id, data } = event
          console.log('[ExecutionPanel] event_type:', event_type)
          console.log('[ExecutionPanel] node_id:', node_id)
          console.log('[ExecutionPanel] data:', data)
          console.log('[ExecutionPanel] addLog 함수 존재:', typeof addLog === 'function')

          switch (event_type) {
            case 'node_start':
              console.log('[ExecutionPanel] 🟢 node_start 분기 진입')
              console.log('[ExecutionPanel] agent_name:', data.agent_name)

              setCurrentNode(node_id)
              console.log('[ExecutionPanel] setCurrentNode 호출 완료')

              const startMsg = `▶️  ${data.agent_name} 실행 시작`
              console.log('[ExecutionPanel] addLog 호출 직전:', { node_id, type: 'start', message: startMsg })
              addLog(node_id, 'start', startMsg)
              console.log('[ExecutionPanel] addLog 호출 완료')
              break

            case 'node_output':
              console.log('[ExecutionPanel] 📝 node_output 분기 진입')
              console.log('[ExecutionPanel] chunk 길이:', data.chunk?.length)

              // nodeOutputs에 청크 저장 (전체 출력 누적)
              addNodeOutput(node_id, data.chunk)

              // ✅ 로그에도 청크 추가 (Worker의 실시간 사고 과정 표시)
              if (data.chunk && data.chunk.trim().length > 0) {
                // 원본 텍스트를 그대로 저장 (렌더링 시 파싱)
                addLog(node_id, 'output', data.chunk)
              }
              break

            case 'node_complete':
              console.log('[ExecutionPanel] 🟢 node_complete 분기 진입')
              console.log('[ExecutionPanel] agent_name:', data.agent_name)
              console.log('[ExecutionPanel] output_length:', data.output_length)

              const completeMsg = `✅ ${data.agent_name} 완료 (출력: ${data.output_length}자)`
              console.log('[ExecutionPanel] addLog 호출 직전:', { node_id, type: 'complete', message: completeMsg })
              addLog(node_id, 'complete', completeMsg)
              console.log('[ExecutionPanel] addLog 호출 완료')
              break

            case 'node_error':
              console.log('[ExecutionPanel] 🔴 node_error 분기 진입')
              console.log('[ExecutionPanel] error:', data.error)
              addLog(node_id, 'error', `❌ ${data.error}`)
              break

            case 'workflow_complete':
              console.log('[ExecutionPanel] 🎉 workflow_complete 분기 진입')
              addLog('', 'complete', '🎉 워크플로우 실행 완료')
              setCurrentNode(null)
              break

            default:
              console.error('[ExecutionPanel] ❌ 알 수 없는 이벤트 타입:', event_type)
          }

          console.log('='.repeat(60))
        },
        // onComplete
        () => {
          setIsRunning(false)
          stopExecution()
        },
        // onError
        (error) => {
          setIsRunning(false)
          stopExecution()
          addLog('', 'error', `실행 실패: ${error}`)
        }
      )
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setIsRunning(false)
      stopExecution()
      addLog('', 'error', `실행 실패: ${errorMsg}`)
    }
  }

  // 실행 중단 (현재는 중단 기능 미지원, UI만 제공)
  const handleStop = () => {
    setIsRunning(false)
    stopExecution()
    addLog('', 'error', '사용자가 실행을 중단했습니다')
  }

  // 로그 초기화
  const handleClear = () => {
    clearExecution()
    setInitialInput('')
  }

  return (
    <Card className="h-full overflow-hidden flex flex-col">
      <CardHeader>
        <CardTitle className="text-lg">실행 제어</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden flex flex-col space-y-4">
        {/* 입력 섹션 */}
        <div className="space-y-2">
          <label className="text-sm font-medium">초기 입력</label>
          <textarea
            className="w-full p-2 border rounded-md text-sm"
            rows={3}
            value={initialInput}
            onChange={(e) => setInitialInput(e.target.value)}
            placeholder="워크플로우 초기 입력을 입력하세요..."
            disabled={isRunning}
          />
        </div>

        {/* 실행 버튼 */}
        <div className="flex gap-2">
          <Button
            onClick={handleExecute}
            disabled={isRunning}
            className="flex-1"
          >
            {isRunning ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                실행 중...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                실행
              </>
            )}
          </Button>

          {isRunning && (
            <Button onClick={handleStop} variant="destructive" className="flex-1">
              <Square className="mr-2 h-4 w-4" />
              중단
            </Button>
          )}

          <Button onClick={handleClear} variant="outline" disabled={isRunning}>
            초기화
          </Button>
        </div>

        {/* 로그 섹션 */}
        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="text-sm font-medium mb-2">실행 로그 ({logs.length})</div>
          <div className="flex-1 overflow-y-auto bg-gray-50 border rounded-md p-3 space-y-1">
            {logs.length === 0 ? (
              <div className="text-xs text-muted-foreground">
                실행 로그가 표시됩니다...
              </div>
            ) : (
              <>
                {logs.map((log, index) => {
                  // output 타입만 파싱 시도
                  const parsed = log.type === 'output'
                    ? parseClaudeMessage(log.message)
                    : { type: 'raw' as const, content: log.message, isCollapsible: false }

                  const isExpanded = expandedLogs.has(index)

                  let colorClass = 'text-gray-700'
                  let fontWeight = ''

                  // 로그 타입별 색상 및 스타일
                  if (log.type === 'error') {
                    colorClass = 'text-red-600'
                    fontWeight = 'font-semibold'
                  } else if (log.type === 'complete') {
                    colorClass = 'text-green-600'
                    fontWeight = 'font-semibold'
                  } else if (log.type === 'start') {
                    colorClass = 'text-blue-600'
                    fontWeight = 'font-semibold'
                  } else if (log.type === 'output') {
                    colorClass = 'text-gray-600'
                    fontWeight = 'font-normal'
                  }

                  // 접을 수 있는 로그 (UserMessage, ToolResult)
                  if (parsed.isCollapsible) {
                    const lines = parsed.content.split('\n')
                    const firstLine = lines[0] || parsed.content.substring(0, 80)
                    const hasMore = lines.length > 1 || parsed.content.length > 80

                    return (
                      <div key={index} className="border-l-2 border-gray-300 pl-2 my-1">
                        <div
                          className={`text-xs ${colorClass} font-mono cursor-pointer hover:bg-gray-100 rounded px-1`}
                          onClick={() => toggleLogExpand(index)}
                        >
                          <span className="select-none">{isExpanded ? '▼' : '▶'}</span> {firstLine}
                          {hasMore && !isExpanded && ' ...'}
                        </div>
                        {isExpanded && (
                          <div className="text-xs text-gray-600 font-mono whitespace-pre-wrap mt-1 pl-3 max-h-24 overflow-y-auto bg-gray-50 rounded p-2 border border-gray-200">
                            {parsed.content}
                          </div>
                        )}
                      </div>
                    )
                  }

                  // 일반 로그
                  return (
                    <div key={index} className={`text-xs ${colorClass} ${fontWeight} font-mono whitespace-pre-wrap`}>
                      {log.nodeId && log.type !== 'output' && `[${log.nodeId}] `}
                      {parsed.content}
                    </div>
                  )
                })}
                {/* 자동 스크롤 앵커 */}
                <div ref={logEndRef} />
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
