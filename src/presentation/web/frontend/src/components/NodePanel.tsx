/**
 * 노드 패널 컴포넌트
 *
 * Agent 목록을 표시하고, 드래그 앤 드롭으로 캔버스에 추가합니다.
 * Manager 노드도 추가할 수 있습니다.
 */

import React, { useEffect, useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Agent, getAgents } from '@/lib/api'
import { useWorkflowStore } from '@/stores/workflowStore'
import { WorkflowNode } from '@/lib/api'
import { Plus, Target, Zap, Search, ChevronDown, ChevronUp, Sparkles, GitBranch, RotateCw, Merge } from 'lucide-react'

export const NodePanel: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['input', 'manager', 'advanced', 'general', 'specialized']))

  const { addNode, nodes } = useWorkflowStore()

  // 섹션 토글 함수
  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  // 워커 분류
  const generalWorkers = ['planner', 'coder', 'reviewer', 'tester', 'committer', 'ideator', 'product_manager', 'documenter']
  const specializedWorkers = ['style_reviewer', 'security_reviewer', 'architecture_reviewer', 'bug_fixer', 'log_analyzer', 'summarizer']

  // 검색 필터
  const filteredAgents = agents.filter((agent) =>
    agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    agent.role.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // 범용/특화 워커 분리
  const filteredGeneralWorkers = filteredAgents.filter((agent) => generalWorkers.includes(agent.name))
  const filteredSpecializedWorkers = filteredAgents.filter((agent) => specializedWorkers.includes(agent.name))

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

  // 드래그 시작 핸들러
  const onDragStart = (event: React.DragEvent, nodeType: string, nodeData: any) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({ type: nodeType, data: nodeData }))
    event.dataTransfer.effectAllowed = 'move'
  }

  // Agent를 캔버스에 추가 (클릭)
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

  // Manager 노드를 캔버스에 추가
  const handleAddManager = () => {
    // 노드 위치 계산
    const x = 100 + (nodes.length % 3) * 300
    const y = 100 + Math.floor(nodes.length / 3) * 150

    const newNode: WorkflowNode = {
      id: `manager-${Date.now()}`,
      type: 'manager',
      position: { x, y },
      data: {
        task_description: '작업 설명을 입력하세요',
        available_workers: [],
      },
    }

    addNode(newNode)
  }

  // Input 노드를 캔버스에 추가
  const handleAddInput = () => {
    // 노드 위치 계산
    const x = 100 + (nodes.length % 3) * 300
    const y = 100 + Math.floor(nodes.length / 3) * 150

    const newNode: WorkflowNode = {
      id: `input-${Date.now()}`,
      type: 'input',
      position: { x, y },
      data: {
        initial_input: '초기 입력을 입력하세요',
      },
    }

    addNode(newNode)
  }

  // Condition 노드를 캔버스에 추가
  const handleAddCondition = () => {
    const x = 100 + (nodes.length % 3) * 300
    const y = 100 + Math.floor(nodes.length / 3) * 150

    const newNode: WorkflowNode = {
      id: `condition-${Date.now()}`,
      type: 'condition',
      position: { x, y },
      data: {
        condition_type: 'contains',
        condition_value: 'success',
      },
    }

    addNode(newNode)
  }

  // Loop 노드를 캔버스에 추가
  const handleAddLoop = () => {
    const x = 100 + (nodes.length % 3) * 300
    const y = 100 + Math.floor(nodes.length / 3) * 150

    const newNode: WorkflowNode = {
      id: `loop-${Date.now()}`,
      type: 'loop',
      position: { x, y },
      data: {
        max_iterations: 5,
        loop_condition: '완료',
        loop_condition_type: 'contains',
      },
    }

    addNode(newNode)
  }

  // Merge 노드를 캔버스에 추가
  const handleAddMerge = () => {
    const x = 100 + (nodes.length % 3) * 300
    const y = 100 + Math.floor(nodes.length / 3) * 150

    const newNode: WorkflowNode = {
      id: `merge-${Date.now()}`,
      type: 'merge',
      position: { x, y },
      data: {
        merge_strategy: 'concatenate',
        separator: '\n\n---\n\n',
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
    <Card className="h-full overflow-hidden flex flex-col border-0 shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          노드 추가
        </CardTitle>
        {/* 검색 바 */}
        <div className="relative mt-3">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="노드 검색..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-3">
        {/* Input 노드 섹션 */}
        <div className="border rounded-lg overflow-hidden bg-emerald-50/50">
          <button
            onClick={() => toggleSection('input')}
            className="w-full flex items-center justify-between p-3 hover:bg-emerald-100/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-emerald-600" />
              <span className="font-semibold text-sm text-emerald-700">Input 노드</span>
              <span className="text-xs px-2 py-0.5 bg-emerald-200 text-emerald-700 rounded-full">1</span>
            </div>
            {expandedSections.has('input') ? (
              <ChevronUp className="h-4 w-4 text-emerald-600" />
            ) : (
              <ChevronDown className="h-4 w-4 text-emerald-600" />
            )}
          </button>
          {expandedSections.has('input') && (
            <div className="p-3 pt-0 space-y-2">
              <Button
                variant="outline"
                className="w-full justify-start text-left border-emerald-300 hover:bg-emerald-50 bg-white cursor-grab active:cursor-grabbing"
                onClick={handleAddInput}
                draggable
                onDragStart={(e) => onDragStart(e, 'input', { initial_input: '초기 입력을 입력하세요' })}
              >
                <Zap className="mr-2 h-4 w-4 text-emerald-600" />
                <div className="flex flex-col items-start">
                  <span className="font-medium text-emerald-700">Input</span>
                  <span className="text-xs text-muted-foreground">
                    워크플로우 시작점
                  </span>
                </div>
              </Button>
            </div>
          )}
        </div>

        {/* Manager 노드 섹션 */}
        <div className="border rounded-lg overflow-hidden bg-purple-50/50">
          <button
            onClick={() => toggleSection('manager')}
            className="w-full flex items-center justify-between p-3 hover:bg-purple-100/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-purple-600" />
              <span className="font-semibold text-sm text-purple-700">Manager 노드</span>
              <span className="text-xs px-2 py-0.5 bg-purple-200 text-purple-700 rounded-full">1</span>
            </div>
            {expandedSections.has('manager') ? (
              <ChevronUp className="h-4 w-4 text-purple-600" />
            ) : (
              <ChevronDown className="h-4 w-4 text-purple-600" />
            )}
          </button>
          {expandedSections.has('manager') && (
            <div className="p-3 pt-0 space-y-2">
              <Button
                variant="outline"
                className="w-full justify-start text-left border-purple-300 hover:bg-purple-50 bg-white cursor-grab active:cursor-grabbing"
                onClick={handleAddManager}
                draggable
                onDragStart={(e) => onDragStart(e, 'manager', { task_description: '작업 설명을 입력하세요', available_workers: [] })}
              >
                <Plus className="mr-2 h-4 w-4 text-purple-600" />
                <div className="flex flex-col items-start">
                  <span className="font-medium text-purple-700">Manager</span>
                  <span className="text-xs text-muted-foreground">
                    워커 오케스트레이터
                  </span>
                </div>
              </Button>
            </div>
          )}
        </div>

        {/* 고급 노드 섹션 (Condition, Loop, Merge) */}
        <div className="border rounded-lg overflow-hidden bg-blue-50/50">
          <button
            onClick={() => toggleSection('advanced')}
            className="w-full flex items-center justify-between p-3 hover:bg-blue-100/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-blue-600" />
              <span className="font-semibold text-sm text-blue-700">고급 노드</span>
              <span className="text-xs px-2 py-0.5 bg-blue-200 text-blue-700 rounded-full">3</span>
            </div>
            {expandedSections.has('advanced') ? (
              <ChevronUp className="h-4 w-4 text-blue-600" />
            ) : (
              <ChevronDown className="h-4 w-4 text-blue-600" />
            )}
          </button>
          {expandedSections.has('advanced') && (
            <div className="p-3 pt-0 space-y-2">
              {/* Condition 노드 */}
              <Button
                variant="outline"
                className="w-full justify-start text-left border-amber-300 hover:bg-amber-50 bg-white cursor-grab active:cursor-grabbing"
                onClick={handleAddCondition}
                draggable
                onDragStart={(e) => onDragStart(e, 'condition', { condition_type: 'contains', condition_value: 'success' })}
              >
                <GitBranch className="mr-2 h-4 w-4 text-amber-600" />
                <div className="flex flex-col items-start">
                  <span className="font-medium text-amber-700">조건 분기</span>
                  <span className="text-xs text-muted-foreground">
                    조건에 따라 True/False 분기
                  </span>
                </div>
              </Button>

              {/* Loop 노드 */}
              <Button
                variant="outline"
                className="w-full justify-start text-left border-teal-300 hover:bg-teal-50 bg-white cursor-grab active:cursor-grabbing"
                onClick={handleAddLoop}
                draggable
                onDragStart={(e) => onDragStart(e, 'loop', { max_iterations: 5, loop_condition: '완료', loop_condition_type: 'contains' })}
              >
                <RotateCw className="mr-2 h-4 w-4 text-teal-600" />
                <div className="flex flex-col items-start">
                  <span className="font-medium text-teal-700">반복</span>
                  <span className="text-xs text-muted-foreground">
                    조건 만족 시까지 반복 실행
                  </span>
                </div>
              </Button>

              {/* Merge 노드 */}
              <Button
                variant="outline"
                className="w-full justify-start text-left border-sky-300 hover:bg-sky-50 bg-white cursor-grab active:cursor-grabbing"
                onClick={handleAddMerge}
                draggable
                onDragStart={(e) => onDragStart(e, 'merge', { merge_strategy: 'concatenate', separator: '\n\n---\n\n' })}
              >
                <Merge className="mr-2 h-4 w-4 text-sky-600" />
                <div className="flex flex-col items-start">
                  <span className="font-medium text-sky-700">병합</span>
                  <span className="text-xs text-muted-foreground">
                    여러 분기 결과를 통합
                  </span>
                </div>
              </Button>
            </div>
          )}
        </div>

        {/* 범용 Worker 노드 섹션 */}
        <div className="border rounded-lg overflow-hidden bg-slate-50/50">
          <button
            onClick={() => toggleSection('general')}
            className="w-full flex items-center justify-between p-3 hover:bg-slate-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Plus className="h-4 w-4 text-slate-600" />
              <span className="font-semibold text-sm text-slate-700">범용 워커</span>
              <span className="text-xs px-2 py-0.5 bg-slate-200 text-slate-700 rounded-full">
                {filteredGeneralWorkers.length}
              </span>
            </div>
            {expandedSections.has('general') ? (
              <ChevronUp className="h-4 w-4 text-slate-600" />
            ) : (
              <ChevronDown className="h-4 w-4 text-slate-600" />
            )}
          </button>
          {expandedSections.has('general') && (
            <div className="p-3 pt-0 space-y-2">
              {filteredGeneralWorkers.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-4">
                  검색 결과가 없습니다
                </div>
              ) : (
                filteredGeneralWorkers.map((agent) => (
                  <Button
                    key={agent.name}
                    variant="outline"
                    className="w-full justify-start text-left hover:bg-slate-50 bg-white cursor-grab active:cursor-grabbing"
                    onClick={() => handleAddAgent(agent)}
                    draggable
                    onDragStart={(e) => onDragStart(e, 'worker', { agent_name: agent.name, task_template: `{{input}}을(를) ${agent.role} 해주세요.` })}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    <div className="flex flex-col items-start flex-1">
                      <span className="font-medium">{agent.name}</span>
                      <span className="text-xs text-muted-foreground line-clamp-1">
                        {agent.role}
                      </span>
                    </div>
                  </Button>
                ))
              )}
            </div>
          )}
        </div>

        {/* 특화 Worker 노드 섹션 */}
        <div className="border rounded-lg overflow-hidden bg-orange-50/50">
          <button
            onClick={() => toggleSection('specialized')}
            className="w-full flex items-center justify-between p-3 hover:bg-orange-100/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-orange-600" />
              <span className="font-semibold text-sm text-orange-700">특화 워커</span>
              <span className="text-xs px-2 py-0.5 bg-orange-200 text-orange-700 rounded-full">
                {filteredSpecializedWorkers.length}
              </span>
            </div>
            {expandedSections.has('specialized') ? (
              <ChevronUp className="h-4 w-4 text-orange-600" />
            ) : (
              <ChevronDown className="h-4 w-4 text-orange-600" />
            )}
          </button>
          {expandedSections.has('specialized') && (
            <div className="p-3 pt-0 space-y-2">
              {filteredSpecializedWorkers.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-4">
                  검색 결과가 없습니다
                </div>
              ) : (
                filteredSpecializedWorkers.map((agent) => (
                  <Button
                    key={agent.name}
                    variant="outline"
                    className="w-full justify-start text-left hover:bg-orange-50 bg-white cursor-grab active:cursor-grabbing"
                    onClick={() => handleAddAgent(agent)}
                    draggable
                    onDragStart={(e) => onDragStart(e, 'worker', { agent_name: agent.name, task_template: `{{input}}을(를) ${agent.role} 해주세요.` })}
                  >
                    <Target className="mr-2 h-4 w-4 text-orange-600" />
                    <div className="flex flex-col items-start flex-1">
                      <span className="font-medium">{agent.name}</span>
                      <span className="text-xs text-muted-foreground line-clamp-1">
                        {agent.role}
                      </span>
                    </div>
                  </Button>
                ))
              )}
            </div>
          )}
        </div>

        {/* 드래그 힌트 */}
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-700">
            <strong>💡 팁:</strong> 노드를 드래그하여 캔버스에 배치하거나 클릭하여 추가하세요
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
