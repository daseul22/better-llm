/**
 * Loop 노드 컴포넌트 (반복 실행)
 *
 * 지정된 조건이 만족될 때까지 연결된 노드를 반복 실행합니다.
 */

import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { RotateCw, Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { useWorkflowStore } from '@/stores/workflowStore'

interface LoopNodeData {
  max_iterations: number
  loop_condition: string
  loop_condition_type: string
  // 실행 상태
  isExecuting?: boolean
  isCompleted?: boolean
  hasError?: boolean
  currentIteration?: number
}

export const LoopNode = memo(({ id, data, selected }: NodeProps<LoopNodeData>) => {
  const { max_iterations, loop_condition, loop_condition_type, currentIteration } = data

  // Store에서 노드 실행 메타데이터 가져오기
  const nodeMeta = useWorkflowStore((state) => state.execution.nodeMeta[id])

  const status = nodeMeta?.status || 'idle'
  const isExecuting = status === 'running' || data.isExecuting
  const isCompleted = status === 'completed' || data.isCompleted
  const hasError = status === 'error' || data.hasError
  const elapsedTime = nodeMeta?.elapsedTime

  // 상태별 스타일
  let statusClass = 'border-teal-400 bg-teal-50'
  let statusText = ''
  let statusColor = ''

  if (isExecuting) {
    statusClass = 'border-yellow-500 bg-yellow-50'
    statusText = currentIteration
      ? `반복 중 (${currentIteration}/${max_iterations})`
      : '실행 중...'
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

  // 조건 타입 표시 텍스트
  const conditionTypeText: Record<string, string> = {
    contains: '포함 검사',
    regex: '정규표현식',
    custom: '커스텀 조건',
  }

  return (
    <div style={{ width: '260px', display: 'block', boxSizing: 'border-box' }}>
      {/* 입력 핸들 (위쪽 가운데) */}
      <Handle
        type="target"
        position={Position.Top}
        style={{
          background: '#555',
          width: '12px',
          height: '12px',
          border: '2px solid white',
          top: '-6px',
        }}
      />

      <Card
        className={cn(
          'cursor-pointer transition-all hover:shadow-md',
          statusClass,
          selected && 'ring-2 ring-blue-500'
        )}
      >
        <CardHeader className="p-3 pb-2">
          <CardTitle className="text-base flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <RotateCw className="h-4 w-4" />
              <span>반복 노드</span>
            </div>
            {isExecuting && <Loader2 className="h-4 w-4 animate-spin" />}
            {isCompleted && <CheckCircle2 className="h-4 w-4 text-green-600" />}
            {hasError && <XCircle className="h-4 w-4 text-red-600" />}
          </CardTitle>
        </CardHeader>

        <CardContent className="p-3 pt-0 space-y-2">
          {/* 최대 반복 횟수 */}
          <div className="text-xs text-gray-600">
            <span className="font-medium">최대 반복:</span> {max_iterations}회
          </div>

          {/* 종료 조건 타입 */}
          <div className="text-xs text-gray-600">
            <span className="font-medium">조건 타입:</span>{' '}
            {conditionTypeText[loop_condition_type] || loop_condition_type}
          </div>

          {/* 종료 조건 */}
          <div className="text-xs text-gray-600">
            <span className="font-medium">종료 조건:</span>{' '}
            <span className="font-mono bg-gray-100 px-1 rounded">
              {loop_condition.length > 25
                ? `${loop_condition.substring(0, 25)}...`
                : loop_condition}
            </span>
          </div>

          {/* 상태 표시 */}
          {statusText && (
            <div className={cn('text-xs font-medium', statusColor)}>{statusText}</div>
          )}

          {/* 실행 시간 표시 */}
          {elapsedTime !== undefined && (
            <div className="text-xs text-gray-500">⏱️ {elapsedTime.toFixed(2)}s</div>
          )}
        </CardContent>
      </Card>

      {/* 출력 핸들 (아래쪽 가운데) */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: '#555',
          width: '12px',
          height: '12px',
          border: '2px solid white',
          bottom: '-6px',
        }}
      />
    </div>
  )
})

LoopNode.displayName = 'LoopNode'
