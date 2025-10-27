/**
 * 실행 패널 컴포넌트
 *
 * 워크플로우 실행 및 결과 표시를 담당합니다.
 */

import React, { useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useWorkflowStore } from '@/stores/workflowStore'
import { executeWorkflow } from '@/lib/api'
import { Play, Square, Loader2 } from 'lucide-react'

export const ExecutionPanel: React.FC = () => {
  const {
    getWorkflow,
    execution,
    startExecution,
    stopExecution,
    setCurrentNode,
    addNodeOutput,
    addLog,
    clearExecution,
  } = useWorkflowStore()

  const [initialInput, setInitialInput] = useState('웹 UI 추가')
  const [isRunning, setIsRunning] = useState(false)

  // 워크플로우 실행
  const handleExecute = async () => {
    if (isRunning) return

    try {
      setIsRunning(true)
      startExecution()

      const workflow = getWorkflow()

      await executeWorkflow(
        workflow,
        initialInput,
        // onEvent
        (event) => {
          const { event_type, node_id, data } = event

          switch (event_type) {
            case 'node_start':
              setCurrentNode(node_id)
              addLog(node_id, 'start', `${data.agent_name} 실행 시작`)
              break

            case 'node_output':
              addNodeOutput(node_id, data.chunk)
              addLog(node_id, 'output', data.chunk)
              break

            case 'node_complete':
              addLog(
                node_id,
                'complete',
                `${data.agent_name} 완료 (출력: ${data.output_length}자)`
              )
              break

            case 'node_error':
              addLog(node_id, 'error', data.error)
              break

            case 'workflow_complete':
              addLog('', 'complete', '워크플로우 실행 완료')
              setCurrentNode(null)
              break
          }
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
          <div className="text-sm font-medium mb-2">실행 로그</div>
          <div className="flex-1 overflow-y-auto bg-gray-50 border rounded-md p-3 space-y-1">
            {execution.logs.length === 0 ? (
              <div className="text-xs text-muted-foreground">
                실행 로그가 표시됩니다...
              </div>
            ) : (
              execution.logs.map((log, index) => {
                let colorClass = 'text-gray-700'
                if (log.type === 'error') colorClass = 'text-red-600'
                if (log.type === 'complete') colorClass = 'text-green-600'

                return (
                  <div key={index} className={`text-xs ${colorClass} font-mono`}>
                    {log.nodeId && `[${log.nodeId}] `}
                    {log.message}
                  </div>
                )
              })
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
