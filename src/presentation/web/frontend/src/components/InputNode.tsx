/**
 * Input 노드 컴포넌트 (React Flow 커스텀 노드)
 *
 * 워크플로우의 시작점이 되는 입력 노드입니다.
 * - 초기 입력 텍스트 저장
 * - 독립적인 실행 제어 (각 Input 노드별로 실행 가능)
 * - 실행 상태 표시
 */

import { memo, useState, useRef } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { Play, Square, Zap, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { useWorkflowStore } from '@/stores/workflowStore'
import { executeWorkflow } from '@/lib/api'

interface InputNodeData {
  initial_input: string
  // 실행 상태 (옵션)
  isExecuting?: boolean
  isCompleted?: boolean
  hasError?: boolean
}

export const InputNode = memo(({ id, data, selected }: NodeProps<InputNodeData>) => {
  const { initial_input, isExecuting, isCompleted, hasError } = data
  const [localIsRunning, setLocalIsRunning] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  const {
    getWorkflow,
    startExecution,
    stopExecution,
    setCurrentNode,
    addNodeOutput,
    setNodeInput,
    addLog,
    updateNode,
    setNodeStartTime,
    setNodeCompleted,
    setNodeError,
  } = useWorkflowStore()

  // 상태별 스타일 (WorkerNode 패턴과 동일)
  let statusClass = 'border-emerald-400 bg-emerald-50'
  let statusText = ''

  if (isExecuting || localIsRunning) {
    statusClass = 'border-yellow-500 bg-yellow-50'
    statusText = '실행 중...'
  } else if (hasError) {
    statusClass = 'border-red-500 bg-red-50'
    statusText = '에러 발생'
  } else if (isCompleted) {
    statusClass = 'border-green-500 bg-green-50'
    statusText = '완료'
  }

  // 워크플로우 실행 (이 Input 노드에서 시작)
  const handleExecute = async () => {
    if (localIsRunning || !initial_input?.trim()) return

    try {
      setLocalIsRunning(true)
      updateNode(id, { isExecuting: true, isCompleted: false, hasError: false })
      startExecution()

      const workflow = getWorkflow()

      // AbortController 생성
      const abortController = new AbortController()
      abortControllerRef.current = abortController

      // 재접속 로직: localStorage에서 세션 ID 확인
      const STORAGE_KEY_SESSION_ID = 'claude-flow-workflow-session-id'
      const savedSessionId = localStorage.getItem(STORAGE_KEY_SESSION_ID)

      // Zustand store에서 현재 로그 개수 확인 (중복 방지용)
      const currentLogs = useWorkflowStore.getState().execution.logs
      const lastEventIndex = currentLogs.length > 0 ? currentLogs.length - 1 : undefined

      console.log('[InputNode] 재접속 체크:', {
        savedSessionId,
        lastEventIndex,
        isReconnect: !!savedSessionId && lastEventIndex !== undefined
      })

      const sessionId = await executeWorkflow(
        workflow,
        initial_input,
        // onEvent
        (event) => {
          const { event_type, node_id, data: eventData, timestamp, elapsed_time, token_usage } = event

          switch (event_type) {
            case 'node_start':
              setCurrentNode(node_id)
              if (timestamp) {
                setNodeStartTime(node_id, new Date(timestamp).getTime())
              }
              if (eventData.input) {
                setNodeInput(node_id, eventData.input)
              }
              addLog(node_id, 'start', `▶️  ${eventData.agent_name} 실행 시작`)
              break

            case 'node_output':
              addNodeOutput(node_id, eventData.chunk)
              if (eventData.chunk && eventData.chunk.trim().length > 0) {
                addLog(node_id, 'output', eventData.chunk)
              }
              break

            case 'node_complete':
              // 노드 완료: 실행 시간 및 토큰 사용량 업데이트
              console.log('[InputNode] node_complete 이벤트:', {
                node_id,
                elapsed_time,
                token_usage,
              })

              if (elapsed_time !== undefined) {
                setNodeCompleted(node_id, elapsed_time, token_usage)
              }

              let completeMsg = `✅ ${eventData.agent_name} 완료`
              if (elapsed_time !== undefined) {
                completeMsg += ` (${elapsed_time.toFixed(1)}초)`
              }
              if (token_usage && token_usage.total_tokens > 0) {
                completeMsg += ` [${token_usage.total_tokens.toLocaleString()} tokens]`
              }
              addLog(node_id, 'complete', completeMsg)
              break

            case 'node_error':
              // 노드 에러: elapsed_time 및 에러 메시지 저장
              if (eventData.error) {
                setNodeError(node_id, eventData.error)
              }
              addLog(node_id, 'error', `❌ ${eventData.error}`)
              updateNode(id, { hasError: true })
              break

            case 'workflow_complete':
              addLog('', 'complete', '🎉 워크플로우 실행 완료')
              setCurrentNode(null)
              updateNode(id, { isCompleted: true, isExecuting: false })
              break
          }
        },
        // onComplete
        () => {
          setLocalIsRunning(false)
          updateNode(id, { isExecuting: false })
          stopExecution()
        },
        // onError
        (error) => {
          setLocalIsRunning(false)
          updateNode(id, { isExecuting: false, hasError: true })
          stopExecution()
          addLog('', 'error', `실행 실패: ${error}`)
        },
        // signal
        abortController.signal,
        // sessionId (재접속용)
        savedSessionId || undefined,
        // lastEventIndex (중복 방지용)
        lastEventIndex,
        // startNodeId (이 Input 노드에서만 시작)
        id
      )

      // 세션 ID를 localStorage에 저장 (새로고침 후 복원용)
      if (sessionId) {
        localStorage.setItem('claude-flow-workflow-session-id', sessionId)
        console.log('[InputNode] 세션 ID 저장:', sessionId)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setLocalIsRunning(false)
      updateNode(id, { isExecuting: false, hasError: true })
      stopExecution()
      addLog('', 'error', `실행 실패: ${errorMsg}`)
    }
  }

  // 실행 중단
  const handleStop = () => {
    // AbortController로 실행 중단
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }

    setLocalIsRunning(false)
    updateNode(id, { isExecuting: false })
    stopExecution()
    addLog('', 'error', '⏹️ 사용자가 실행을 중단했습니다')
  }

  return (
    <div style={{ width: '260px', display: 'block', boxSizing: 'border-box' }}>
      <Card
        style={{ width: '260px', boxSizing: 'border-box' }}
        className={cn(
          'border-2 transition-all',
          statusClass,
          selected && 'ring-2 ring-emerald-500',
          isExecuting && 'pulse-border',
          !isExecuting && !isCompleted && 'node-appear'
        )}
      >
        <CardHeader className="py-2 px-3 bg-gradient-to-r from-emerald-500 to-teal-500">
          <CardTitle className="text-sm flex items-center justify-between text-white">
            <span className="flex items-center gap-1.5">
              {isExecuting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {isCompleted && !hasError && <CheckCircle2 className="h-3.5 w-3.5" />}
              {hasError && <XCircle className="h-3.5 w-3.5" />}
              {!isExecuting && !isCompleted && !hasError && <Zap className="h-3.5 w-3.5" />}
              START
            </span>
            {statusText && (
              <span className="text-[10px] font-normal bg-white/20 px-1.5 py-0.5 rounded">
                {statusText}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="py-1.5 px-3 space-y-1">
          {/* 입력 텍스트 미리보기 */}
          <div className="text-[11px] text-muted-foreground bg-white border border-emerald-200 rounded p-1.5 max-h-12 overflow-hidden line-clamp-2">
            {initial_input?.substring(0, 60) || '아키텍처 패턴 리뷰 해주세요'}
            {(initial_input?.length || 0) > 60 && '...'}
          </div>

          {/* 실행 버튼 */}
          {!localIsRunning ? (
            <Button
              onClick={handleExecute}
              disabled={!initial_input?.trim()}
              size="sm"
              className="w-full h-7 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold"
            >
              <Play className="mr-1 h-3 w-3" />
              시작
            </Button>
          ) : (
            <Button
              onClick={handleStop}
              size="sm"
              variant="destructive"
              className="w-full h-7 text-xs font-semibold"
            >
              <Square className="mr-1 h-3 w-3" />
              중단
            </Button>
          )}
        </CardContent>
      </Card>

      {/* 출력 핸들 (아래쪽 가운데) - WorkerNode와 동일한 패턴 */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="output"
        style={{
          position: 'absolute',
          bottom: 0,
          left: '50%',
          transform: 'translate(-50%, 50%)',
          backgroundColor: '#10b981',
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          zIndex: 1
        }}
      />
    </div>
  )
})

InputNode.displayName = 'InputNode'
