/**
 * Manager 노드 설정 컴포넌트
 *
 * 워커들을 병렬로 실행하는 오케스트레이터 노드의 설정을 관리합니다.
 */

import React, { useState, useEffect, useRef } from 'react'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Settings, HelpCircle, CheckCircle2, Save, Search } from 'lucide-react'
import { WorkflowNode, getAgents, Agent } from '@/lib/api'
import { useNodeConfig } from './hooks/useNodeConfig'
import { useAutoSave } from './hooks/useAutoSave'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'

interface ManagerNodeConfigProps {
  node: WorkflowNode
}

interface ManagerNodeData {
  task_description: string
  available_workers: string[]
}

export const ManagerNodeConfig: React.FC<ManagerNodeConfigProps> = ({ node }) => {
  const [activeTab, setActiveTab] = useState('basic')
  const [agents, setAgents] = useState<Agent[]>([])
  const [workerSearchQuery, setWorkerSearchQuery] = useState('')
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Agent 목록 로드
  useEffect(() => {
    const loadAgents = async () => {
      try {
        const agentList = await getAgents()
        setAgents(agentList)
      } catch (error) {
        console.error('❌ Agent 목록 로드 실패:', error)
      }
    }
    loadAgents()
  }, [])

  // 노드 설정 Hook
  const { data, setData, hasChanges, saveMessage, save, reset } = useNodeConfig<ManagerNodeData>({
    nodeId: node.id,
    initialData: {
      task_description: node.data.task_description || '',
      available_workers: node.data.available_workers || [],
    },
    onValidate: (data) => {
      const errors: Record<string, string> = {}
      if (!data.task_description.trim()) {
        errors.task_description = '작업 설명을 입력하세요'
      }
      if (data.available_workers.length === 0) {
        errors.workers = '최소 1개의 워커를 선택하세요'
      }
      return errors
    },
  })

  // 자동 저장
  useAutoSave({
    hasChanges,
    onSave: save,
    delay: 3000,
  })

  // 키보드 단축키
  useKeyboardShortcuts({
    handlers: {
      onSave: hasChanges ? save : undefined,
      onReset: hasChanges ? reset : undefined,
      onSearch: () => searchInputRef.current?.focus(),
    },
  })

  // 입력 필드에서 키 이벤트 전파 방지
  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    e.stopPropagation()
  }

  // 워커 토글
  const handleToggleWorker = (workerName: string) => {
    const newWorkers = data.available_workers.includes(workerName)
      ? data.available_workers.filter((w) => w !== workerName)
      : [...data.available_workers, workerName]

    setData({ ...data, available_workers: newWorkers })
  }

  // 워커 선택 헬퍼
  const selectAllWorkers = () => {
    setData({ ...data, available_workers: agents.map((a) => a.name) })
  }

  const selectNoWorkers = () => {
    setData({ ...data, available_workers: [] })
  }

  const selectWorkerPreset = (preset: string) => {
    let workers: string[] = []
    switch (preset) {
      case 'full-dev':
        workers = ['planner', 'coder', 'reviewer', 'tester']
        break
      case 'quick-code':
        workers = ['coder', 'reviewer']
        break
      case 'planning':
        workers = ['planner', 'product_manager']
        break
      case 'creative':
        workers = ['ideator', 'planner']
        break
    }
    setData({ ...data, available_workers: workers })
  }

  // 필터링된 워커
  const filteredAgents = agents.filter(
    (agent) =>
      agent.name.toLowerCase().includes(workerSearchQuery.toLowerCase()) ||
      agent.role.toLowerCase().includes(workerSearchQuery.toLowerCase())
  )

  return (
    <Card className="h-full overflow-hidden flex flex-col border-0 shadow-none">
      <CardHeader className="pb-3 bg-gradient-to-r from-purple-50 to-pink-50 border-b">
        <CardTitle className="text-lg flex items-center gap-2">
          <Settings className="h-5 w-5 text-purple-600" />
          Manager 노드 설정
        </CardTitle>
        <div className="text-sm text-muted-foreground">워커를 조율하는 오케스트레이터</div>
      </CardHeader>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="flex w-auto mx-4 mt-4 gap-1">
          <TabsTrigger value="basic" className="text-xs flex-1 min-w-0">
            기본
          </TabsTrigger>
          <TabsTrigger value="workers" className="text-xs flex-1 min-w-0">
            워커
          </TabsTrigger>
          <TabsTrigger value="info" className="text-xs flex-1 min-w-0">
            정보
          </TabsTrigger>
        </TabsList>

        <div className="flex-1 overflow-hidden">
          {/* 기본 설정 탭 */}
          <TabsContent value="basic" className="h-full overflow-y-auto px-4 pb-20 mt-4 space-y-4">
            {/* 작업 설명 */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">작업 설명</label>
                <span title="이 작업 설명이 등록된 모든 워커에게 동일하게 전달됩니다">
                  <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
                </span>
              </div>
              <textarea
                className="w-full p-3 border rounded-md text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                rows={8}
                value={data.task_description}
                onChange={(e) => setData({ ...data, task_description: e.target.value })}
                onKeyDown={handleInputKeyDown}
                placeholder="Manager가 수행할 작업을 설명하세요...&#10;예시:&#10;- 웹 애플리케이션의 로그인 기능 구현&#10;- API 문서화 및 테스트 작성&#10;- 코드 리뷰 및 리팩토링"
              />
            </div>

            {/* 미리보기 */}
            {data.task_description.trim() && (
              <div className="bg-purple-50 border border-purple-200 rounded-md p-3">
                <div className="text-xs font-medium text-purple-900 mb-2">작업 설명 미리보기</div>
                <div className="text-sm text-gray-700 whitespace-pre-wrap bg-white p-3 rounded border">
                  {data.task_description}
                </div>
              </div>
            )}

            {/* 선택된 워커 요약 */}
            <div className="bg-gray-50 border rounded-md p-3">
              <div className="text-xs font-medium mb-2">등록된 워커 ({data.available_workers.length}개)</div>
              {data.available_workers.length === 0 ? (
                <div className="text-xs text-muted-foreground">워커 탭에서 워커를 선택하세요 (최소 1개 필수)</div>
              ) : (
                <div className="flex flex-wrap gap-1">
                  {data.available_workers.map((workerName) => {
                    const agent = agents.find((a) => a.name === workerName)
                    return (
                      <span key={workerName} className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded">
                        {workerName}
                        {agent && ` (${agent.role})`}
                      </span>
                    )
                  })}
                </div>
              )}
            </div>
          </TabsContent>

          {/* 워커 선택 탭 */}
          <TabsContent value="workers" className="h-full overflow-y-auto px-4 pb-20 mt-4 space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium">사용 가능한 워커</label>
                  <span title="Manager가 병렬로 실행할 워커들을 선택하세요">
                    <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">{data.available_workers.length}개 선택됨</span>
              </div>

              {/* 검색 바 */}
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  ref={searchInputRef}
                  type="text"
                  placeholder="워커 검색... (이름 또는 역할)"
                  className="w-full pl-8 p-2 border rounded-md text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  value={workerSearchQuery}
                  onChange={(e) => setWorkerSearchQuery(e.target.value)}
                  onKeyDown={handleInputKeyDown}
                />
              </div>

              {/* 빠른 선택 버튼 */}
              <div className="flex gap-2 flex-wrap">
                <Button size="sm" variant="outline" onClick={selectAllWorkers}>
                  모두 선택
                </Button>
                <Button size="sm" variant="outline" onClick={selectNoWorkers}>
                  모두 해제
                </Button>
                <Button size="sm" variant="outline" onClick={() => selectWorkerPreset('full-dev')}>
                  풀스택 개발
                </Button>
                <Button size="sm" variant="outline" onClick={() => selectWorkerPreset('quick-code')}>
                  빠른 코드
                </Button>
                <Button size="sm" variant="outline" onClick={() => selectWorkerPreset('planning')}>
                  기획
                </Button>
                <Button size="sm" variant="outline" onClick={() => selectWorkerPreset('creative')}>
                  창의적
                </Button>
              </div>

              {/* 워커 목록 */}
              <div className="border rounded-md p-3 space-y-2 max-h-80 overflow-y-auto">
                {agents.length === 0 ? (
                  <div className="text-sm text-muted-foreground">워커 로딩 중...</div>
                ) : filteredAgents.length === 0 ? (
                  <div className="text-sm text-muted-foreground">검색 결과가 없습니다</div>
                ) : (
                  filteredAgents.map((agent) => (
                    <label
                      key={agent.name}
                      className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={data.available_workers.includes(agent.name)}
                        onChange={() => handleToggleWorker(agent.name)}
                        className="w-4 h-4"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{agent.name}</span>
                          <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
                            {agent.allowed_tools.length}개 도구
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">{agent.role}</div>
                      </div>
                    </label>
                  ))
                )}
              </div>
            </div>
          </TabsContent>

          {/* 정보 탭 */}
          <TabsContent value="info" className="h-full overflow-y-auto px-4 pb-20 mt-4 space-y-4">
            {/* 노드 정보 */}
            <div className="space-y-3">
              <div className="text-sm font-semibold border-b pb-2">노드 정보</div>

              <div>
                <span className="font-medium">노드 ID:</span>
                <div className="mt-0.5 break-all text-sm text-muted-foreground">{node.id}</div>
              </div>

              <div>
                <span className="font-medium">타입:</span>
                <div className="mt-0.5 text-sm text-muted-foreground">Manager (오케스트레이터)</div>
              </div>

              <div>
                <span className="font-medium">위치:</span>
                <div className="mt-0.5 text-sm text-muted-foreground">
                  ({Math.round(node.position.x)}, {Math.round(node.position.y)})
                </div>
              </div>

              <div>
                <span className="font-medium">등록된 워커:</span>
                <div className="mt-1 text-sm text-muted-foreground">
                  {data.available_workers.length === 0 ? (
                    <span className="text-red-600">없음 (최소 1개 선택 필요)</span>
                  ) : (
                    <div className="space-y-1">
                      {data.available_workers.map((workerName) => {
                        const agent = agents.find((a) => a.name === workerName)
                        return (
                          <div key={workerName} className="flex items-center gap-2">
                            <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                            <span>{workerName}</span>
                            {agent && <span className="text-xs text-gray-500">({agent.role})</span>}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* 사용 가이드 */}
            <div className="space-y-3">
              <div className="text-sm font-semibold border-b pb-2">사용 가이드</div>

              <div className="text-xs text-muted-foreground space-y-2">
                <div>
                  <div className="font-medium text-purple-700 mb-1">Manager 노드란?</div>
                  <div>등록된 워커들을 병렬로 실행하여 복잡한 작업을 처리하는 오케스트레이터입니다.</div>
                </div>

                <div>
                  <div className="font-medium text-purple-700 mb-1">실행 방식</div>
                  <div>모든 워커에게 동일한 작업 설명이 전달되며, 각 워커는 독립적으로 작업을 수행합니다.</div>
                </div>

                <div>
                  <div className="font-medium text-purple-700 mb-1">결과 통합</div>
                  <div>모든 워커의 결과가 Markdown 형식으로 통합되어 다음 노드로 전달됩니다.</div>
                </div>

                <div>
                  <div className="font-medium text-purple-700 mb-1">권장 사용법</div>
                  <ul className="list-disc list-inside space-y-1 mt-1">
                    <li>플래닝 단계: planner만 선택</li>
                    <li>빠른 코딩: coder만 선택</li>
                    <li>풀스택 개발: planner + coder + reviewer + tester 선택</li>
                    <li>아이디어 생성: ideator + product_manager 선택</li>
                  </ul>
                </div>
              </div>
            </div>
          </TabsContent>
        </div>
      </Tabs>

      {/* 저장/초기화 버튼 */}
      <div className="border-t p-4 space-y-2">
        {saveMessage && (
          <div className="text-xs text-center py-1 px-2 rounded bg-green-100 text-green-700">
            <CheckCircle2 className="inline h-3 w-3 mr-1" />
            {saveMessage}
          </div>
        )}

        <div className="flex gap-2">
          <Button className="flex-1" onClick={save} disabled={!hasChanges || data.available_workers.length === 0}>
            <Save className="mr-2 h-4 w-4" />
            저장
          </Button>
          <Button variant="outline" onClick={reset} disabled={!hasChanges}>
            초기화
          </Button>
        </div>

        {hasChanges && !saveMessage && (
          <div className="text-xs text-yellow-600 text-center">변경사항이 있습니다. 3초 후 자동 저장됩니다.</div>
        )}

        <div className="text-xs text-muted-foreground text-center border-t pt-2">
          <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">Cmd+S</kbd> 저장 ·{' '}
          <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">Cmd+K</kbd> 검색 ·{' '}
          <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">Esc</kbd> 초기화
        </div>
      </div>
    </Card>
  )
}
