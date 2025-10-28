/**
 * Worker 노드 컴포넌트 (React Flow 커스텀 노드)
 *
 * Worker Agent를 나타내는 노드입니다.
 * - Agent 선택
 * - 작업 템플릿 입력
 * - 실행 상태 표시
 */

import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'

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

  // Agent별 색상 매핑
  const agentColors: Record<string, { border: string; bg: string; text: string }> = {
    planner: { border: 'border-orange-400', bg: 'bg-orange-50', text: 'text-orange-700' },
    coder: { border: 'border-green-400', bg: 'bg-green-50', text: 'text-green-700' },
    reviewer: { border: 'border-red-400', bg: 'bg-red-50', text: 'text-red-700' },
    tester: { border: 'border-indigo-400', bg: 'bg-indigo-50', text: 'text-indigo-700' },
    committer: { border: 'border-cyan-400', bg: 'bg-cyan-50', text: 'text-cyan-700' },
    ideator: { border: 'border-pink-400', bg: 'bg-pink-50', text: 'text-pink-700' },
    product_manager: { border: 'border-violet-400', bg: 'bg-violet-50', text: 'text-violet-700' },
  }

  // 기본 색상 (agent_name이 매칭되지 않을 때)
  const defaultColors = { border: 'border-gray-400', bg: 'bg-gray-50', text: 'text-gray-700' }
  const colors = agentColors[agent_name] || defaultColors

  // 상태별 스타일
  let statusClass = `${colors.border} ${colors.bg}`
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
    <div className={cn('min-w-[250px] relative', !isExecuting && !isCompleted && 'node-appear')}>
      {/* 입력 핸들 (위쪽 가운데) */}
      <Handle
        type="target"
        position={Position.Top}
        id="input"
        style={{
          position: 'absolute',
          top: '-6px',
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: '#3b82f6',
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          zIndex: 10
        }}
      />

      <Card
        className={cn(
          'border-2 transition-all',
          statusClass,
          selected && 'ring-2 ring-blue-500',
          isExecuting && 'pulse-border'
        )}
      >
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center justify-between">
            <span className="flex items-center gap-2">
              {isExecuting && <Loader2 className="h-4 w-4 animate-spin text-yellow-600" />}
              {isCompleted && !hasError && <CheckCircle2 className="h-4 w-4 text-green-600" />}
              {hasError && <XCircle className="h-4 w-4 text-red-600" />}
              {agent_name || '워커 선택'}
            </span>
            {statusText && (
              <span className={cn('text-xs font-normal', statusColor)}>
                {statusText}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4 space-y-2">
          <div className="text-xs text-muted-foreground">
            {data.task_template?.substring(0, 60) || '작업 템플릿을 입력하세요...'}
            {(data.task_template?.length || 0) > 60 && '...'}
          </div>

          {/* 진행 바 */}
          {isExecuting && (
            <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
              <div className="h-full bg-yellow-500 progress-bar rounded-full" />
            </div>
          )}
        </CardContent>
      </Card>

      {/* 출력 핸들 (아래쪽 가운데) */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="output"
        style={{
          position: 'absolute',
          bottom: '-6px',
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: '#3b82f6',
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          zIndex: 10
        }}
      />
    </div>
  )
})

WorkerNode.displayName = 'WorkerNode'
