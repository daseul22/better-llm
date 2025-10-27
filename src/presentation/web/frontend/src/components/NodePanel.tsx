/**
 * 노드 패널 컴포넌트
 *
 * Agent 목록을 표시하고, 드래그 앤 드롭으로 캔버스에 추가합니다.
 */

import React, { useEffect, useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Agent, getAgents } from '@/lib/api'
import { useWorkflowStore } from '@/stores/workflowStore'
import { WorkflowNode } from '@/lib/api'
import { Plus } from 'lucide-react'

export const NodePanel: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const { addNode, nodes } = useWorkflowStore()

  // Agent 목록 로드
  useEffect(() => {
    const loadAgents = async () => {
      try {
        setLoading(true)
        const data = await getAgents()
        setAgents(data)
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err)
        setError(errorMsg)
      } finally {
        setLoading(false)
      }
    }

    loadAgents()
  }, [])

  // Agent를 캔버스에 추가
  const handleAddAgent = (agent: Agent) => {
    // 노드 위치 계산 (기존 노드 개수에 따라 오프셋)
    const x = 100 + (nodes.length % 3) * 300
    const y = 100 + Math.floor(nodes.length / 3) * 150

    const newNode: WorkflowNode = {
      id: `node-${Date.now()}`,
      type: 'worker',
      position: { x, y },
      data: {
        agent_name: agent.name,
        task_template: `{{input}}을(를) ${agent.role} 해주세요.`,
      },
    }

    addNode(newNode)
  }

  if (loading) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="text-lg">Worker 노드</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">로딩 중...</div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="text-lg">Worker 노드</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-red-500">에러: {error}</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="h-full overflow-hidden flex flex-col">
      <CardHeader>
        <CardTitle className="text-lg">Worker 노드</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto">
        <div className="space-y-2">
          {agents.map((agent) => (
            <Button
              key={agent.name}
              variant="outline"
              className="w-full justify-start text-left"
              onClick={() => handleAddAgent(agent)}
            >
              <Plus className="mr-2 h-4 w-4" />
              <div className="flex flex-col items-start">
                <span className="font-medium">{agent.name}</span>
                <span className="text-xs text-muted-foreground">
                  {agent.role}
                </span>
              </div>
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
