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
import { Play, Square, Loader2, Zap } from 'lucide-react'
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
    updateNode
  } = useWorkflowStore()

  // 상태별 스타일
  let statusClass = 'border-emerald-400'
  let bodyBgClass = 'bg-gradient-to-br from-emerald-50 to-teal-50'
  let statusText = ''
  let statusColor = ''
  let borderGlow = ''

  if (isExecuting || localIsRunning) {
    statusClass = 'border-yellow-500'
    bodyBgClass = 'bg-yellow-50'
    statusText = '실행 중...'
    statusColor = 'text-yellow-700'
    borderGlow = 'shadow-lg shadow-yellow-200'
  } else if (hasError) {
    statusClass = 'border-red-500'
    bodyBgClass = 'bg-red-50'
    statusText = '에러 발생'
    statusColor = 'text-red-700'
  } else if (isCompleted) {
    statusClass = 'border-green-500'
    bodyBgClass = 'bg-green-50'
    statusText = '완료'
    statusColor = 'text-green-700'
  } else {
    borderGlow = 'shadow-md shadow-emerald-100'
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
          const { event_type, node_id, data: eventData } = event

          switch (event_type) {
            case 'node_start':
              setCurrentNode(node_id)
              addLog(node_id, 'start', `▶️  ${eventData.agent_name} 실행 시작`)
              break

            case 'node_output':
              addNodeOutput(node_id, eventData.chunk)
              if (eventData.chunk && eventData.chunk.trim().length > 0) {
                addLog(node_id, 'output', eventData.chunk)
              }
              break

            case 'node_complete':
              addLog(node_id, 'complete', `✅ ${eventData.agent_name} 완료 (출력: ${eventData.output_length}자)`)
              break

            case 'node_error':
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
    <div className="min-w-[300px]">
      <Card
        className={cn(
          'border-2 transition-all duration-200',
          statusClass,
          borderGlow,
          selected && 'ring-2 ring-emerald-500 ring-offset-2'
        )}
      >
        <CardHeader className="pb-2 bg-gradient-to-r from-emerald-500 to-teal-500">
          <CardTitle className="text-base flex items-center justify-between text-white">
            <span className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              <span className="font-bold">START</span>
            </span>
            {statusText && (
              <span className={cn('text-xs font-semibold px-2 py-1 rounded bg-white/20')}>
                {statusText}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className={cn("pt-3 pb-4 space-y-3", bodyBgClass)}>
          {/* 입력 텍스트 미리보기 */}
          <div className="text-xs text-gray-600 bg-white border border-emerald-200 rounded-md p-2.5 max-h-16 overflow-hidden font-medium">
            {initial_input || '초기 입력을 설정하세요...'}
          </div>

          {/* 실행 버튼 */}
          <div className="flex gap-2">
            {!localIsRunning ? (
              <Button
                onClick={handleExecute}
                disabled={!initial_input?.trim()}
                size="sm"
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-md"
              >
                <Play className="mr-2 h-4 w-4" />
                워크플로우 시작
              </Button>
            ) : (
              <Button
                onClick={handleStop}
                size="sm"
                variant="destructive"
                className="flex-1 font-semibold shadow-md"
              >
                <Square className="mr-2 h-4 w-4" />
                중단
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 출력 핸들 (아래쪽만) */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-emerald-500 !w-4 !h-4 !border-2 !border-white !left-1/2 !-translate-x-1/2"
      />
    </div>
  )
})

InputNode.displayName = 'InputNode'
