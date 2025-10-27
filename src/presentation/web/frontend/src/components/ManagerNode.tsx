/**
 * Manager 노드 컴포넌트 (React Flow 커스텀 노드)
 *
 * Manager Agent를 나타내는 노드입니다.
 * - 등록된 워커 목록 표시
 * - 작업 설명 입력
 * - 실행 상태 표시
 * - 병렬 워커 호출 지원
 */

import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { Loader2, CheckCircle2, XCircle, Target } from 'lucide-react'

interface ManagerNodeData {
  task_description: string
  available_workers: string[]
  config?: Record<string, any>
  // 실행 상태 (옵션)
  isExecuting?: boolean
  isCompleted?: boolean
  hasError?: boolean
}

export const ManagerNode = memo(({ data, selected }: NodeProps<ManagerNodeData>) => {
  const { task_description, available_workers, isExecuting, isCompleted, hasError } = data

  // 상태별 스타일
  let statusClass = 'border-purple-400 bg-purple-50'
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
    <div className={cn('min-w-[280px]', !isExecuting && !isCompleted && 'node-appear')}>
      {/* 입력 핸들 (위쪽) */}
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-purple-500 !w-3 !h-3"
      />

      <Card
        className={cn(
          'border-2 transition-all',
          statusClass,
          selected && 'ring-2 ring-purple-500',
          isExecuting && 'pulse-border'
        )}
      >
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center justify-between">
            <span className="flex items-center gap-2">
              {isExecuting && <Loader2 className="h-4 w-4 animate-spin text-yellow-600" />}
              {isCompleted && !hasError && <CheckCircle2 className="h-4 w-4 text-green-600" />}
              {hasError && <XCircle className="h-4 w-4 text-red-600" />}
              {!isExecuting && !isCompleted && !hasError && <Target className="h-4 w-4 text-purple-600" />}
              Manager
            </span>
            {statusText && (
              <span className={cn('text-xs font-normal', statusColor)}>
                {statusText}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4 space-y-2">
          {/* 작업 설명 미리보기 */}
          <div className="text-xs text-muted-foreground">
            {task_description?.substring(0, 60) || '작업 설명을 입력하세요...'}
            {(task_description?.length || 0) > 60 && '...'}
          </div>

          {/* 진행 바 */}
          {isExecuting && (
            <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
              <div className="h-full bg-purple-500 progress-bar rounded-full" />
            </div>
          )}

          {/* 등록된 워커 표시 */}
          {available_workers && available_workers.length > 0 && (
            <div className="mt-2 pt-2 border-t border-purple-200">
              <div className="text-xs font-semibold text-purple-700 mb-1">
                등록된 워커 ({available_workers.length}개)
              </div>
              <div className="flex flex-wrap gap-1">
                {available_workers.map((worker) => (
                  <span
                    key={worker}
                    className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded"
                  >
                    {worker}
                  </span>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 출력 핸들 (아래쪽) */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-purple-500 !w-3 !h-3"
      />
    </div>
  )
})

ManagerNode.displayName = 'ManagerNode'
