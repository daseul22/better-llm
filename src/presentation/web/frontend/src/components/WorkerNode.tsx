/**
 * Worker 노드 컴포넌트 (React Flow 커스텀 노드)
 *
 * Worker Agent를 나타내는 노드입니다.
 * - Agent 선택
 * - 작업 템플릿 입력
 * - 실행 상태 표시
 */

import React, { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface WorkerNodeData {
  agent_name: string
  task_template: string
  config?: Record<string, any>
  // 실행 상태 (옵션)
  isExecuting?: boolean
  isCompleted?: boolean
  hasError?: boolean
}

export const WorkerNode = memo(({ data, selected }: NodeProps<WorkerNodeData>) => {
  const { agent_name, isExecuting, isCompleted, hasError } = data

  // 상태별 스타일
  let statusClass = 'border-gray-300'
  let statusText = ''
  let statusColor = ''

  if (isExecuting) {
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

  return (
    <div className="min-w-[250px]">
      {/* 입력 핸들 (위쪽) */}
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-blue-500 !w-3 !h-3"
      />

      <Card
        className={cn(
          'border-2 transition-all',
          statusClass,
          selected && 'ring-2 ring-blue-500'
        )}
      >
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center justify-between">
            <span>{agent_name || '워커 선택'}</span>
            {statusText && (
              <span className={cn('text-xs font-normal', statusColor)}>
                {statusText}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4">
          <div className="text-xs text-muted-foreground">
            {data.task_template?.substring(0, 60) || '작업 템플릿을 입력하세요...'}
            {(data.task_template?.length || 0) > 60 && '...'}
          </div>
        </CardContent>
      </Card>

      {/* 출력 핸들 (아래쪽) */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-blue-500 !w-3 !h-3"
      />
    </div>
  )
})

WorkerNode.displayName = 'WorkerNode'
