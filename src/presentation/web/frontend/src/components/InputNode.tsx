/**
 * Input 노드 컴포넌트 (React Flow 커스텀 노드)
 *
 * 워크플로우의 시작점이 되는 입력 노드입니다.
 * - 초기 입력 텍스트 저장
 * - 독립적인 실행 제어 (각 Input 노드별로 실행 가능)
 * - 실행 상태 표시
 */

import { memo, useState } from 'react'
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

  const {
    getWorkflow,
    startExecution,
    stopExecution,
    setCurrentNode,
    addNodeOutput,
    addLog,
    updateNode,
    setNodeStartTime,
    setNodeCompleted,
    setNodeError,
  } = useWorkflowStore()

  // 상태별 스타일 (WorkerNode 패턴과 동일)
  let statusClass = 'border-emerald-400 bg-emerald-50'
  let statusText = ''
  let statusColor = ''

  if (isExecuting || localIsRunning) {
    statusClass = 'border-yellow-500 bg-yellow-50'
    statusText = '실행 중...'
    statusColor = 'text-yellow-700'
  } else if (hasError) {
    statusClass = 'border-red-500 bg-red-50'
    statusText = '에러 발생'
    statusColor = 'text-red-700'
  } else if (isCompleted) {
    statusClass = 'border-green-500 bg-green-50'
    statusText = '완료'
    statusColor = 'text-green-700'
  }

  // 워크플로우 실행 (이 Input 노드에서 시작)
  const handleExecute = async () => {
    if (localIsRunning || !initial_input?.trim()) return

    try {
      setLocalIsRunning(true)
      updateNode(id, { isExecuting: true, isCompleted: false, hasError: false })
      startExecution()

      const workflow = getWorkflow()

      await executeWorkflow(
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
              if (elapsed_time !== undefined) {
                setNodeCompleted(node_id, elapsed_time, token_usage)
              }

              let completeMsg = `✅ ${eventData.agent_name} 완료`
              if (elapsed_time !== undefined) {
                completeMsg += ` (${elapsed_time.toFixed(1)}초)`
              }
              if (token_usage) {
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
              updateNode(id, { isCompleted: true })
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
        }
      )
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
    setLocalIsRunning(false)
    updateNode(id, { isExecuting: false })
    stopExecution()
    addLog('', 'error', '사용자가 실행을 중단했습니다')
  }

  return (
    <div className={cn('min-w-[300px] relative', !isExecuting && !isCompleted && 'node-appear')}>
      <Card
        className={cn(
          'border-2 transition-all',
          statusClass,
          selected && 'ring-2 ring-emerald-500',
          isExecuting && 'pulse-border'
        )}
      >
        <CardHeader className="pb-3 bg-gradient-to-r from-emerald-500 to-teal-500">
          <CardTitle className="text-base flex items-center justify-between text-white">
            <span className="flex items-center gap-2">
              {isExecuting && <Loader2 className="h-4 w-4 animate-spin" />}
              {isCompleted && !hasError && <CheckCircle2 className="h-4 w-4" />}
              {hasError && <XCircle className="h-4 w-4" />}
              {!isExecuting && !isCompleted && !hasError && <Zap className="h-4 w-4" />}
              START
            </span>
            {statusText && (
              <span className={cn('text-xs font-normal', statusColor, 'bg-white/20 px-2 py-1 rounded')}>
                {statusText}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4 space-y-2">
          {/* 입력 텍스트 미리보기 */}
          <div className="text-xs text-muted-foreground bg-white border border-emerald-200 rounded-md p-2.5 max-h-16 overflow-hidden">
            {initial_input?.substring(0, 80) || '초기 입력을 설정하세요...'}
            {(initial_input?.length || 0) > 80 && '...'}
          </div>

          {/* 진행 바 */}
          {isExecuting && (
            <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
              <div className="h-full bg-emerald-500 progress-bar rounded-full" />
            </div>
          )}

          {/* 실행 버튼 */}
          <div className="flex gap-2 pt-1">
            {!localIsRunning ? (
              <Button
                onClick={handleExecute}
                disabled={!initial_input?.trim()}
                size="sm"
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
              >
                <Play className="mr-2 h-4 w-4" />
                워크플로우 시작
              </Button>
            ) : (
              <Button
                onClick={handleStop}
                size="sm"
                variant="destructive"
                className="flex-1 font-semibold"
              >
                <Square className="mr-2 h-4 w-4" />
                중단
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 출력 핸들 (아래쪽 가운데) - WorkerNode와 동일한 패턴 */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="output"
        style={{
          position: 'absolute',
          bottom: '-6px',
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: '#10b981',
          width: '16px',
          height: '16px',
          borderRadius: '50%',
          border: '2px solid white',
          zIndex: 1
        }}
      />
    </div>
  )
})

InputNode.displayName = 'InputNode'
