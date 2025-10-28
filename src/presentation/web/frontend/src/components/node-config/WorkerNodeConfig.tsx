/**
 * Worker 노드 설정 컴포넌트
 *
 * 특정 작업을 수행하는 Worker 노드의 설정을 관리합니다.
 */

import React, { useState, useEffect, useRef } from 'react'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { useWorkflowStore } from '@/stores/workflowStore'
import { ListChecks, HelpCircle, CheckCircle2, Save, Search } from 'lucide-react'
import { WorkflowNode, getAgents, Agent, getTools, Tool } from '@/lib/api'
import { useNodeConfig } from './hooks/useNodeConfig'
import { useAutoSave } from './hooks/useAutoSave'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import { generateTemplatePreview } from '@/lib/templateRenderer'

interface WorkerNodeConfigProps {
  node: WorkflowNode
}

interface WorkerNodeData {
  task_template: string
  allowed_tools?: string[]
  thinking?: boolean
  system_prompt?: string  // 커스텀 워커용 시스템 프롬프트
  config?: {
    output_format?: string
    custom_prompt?: string
  }
}

export const WorkerNodeConfig: React.FC<WorkerNodeConfigProps> = ({ node }) => {
  const [activeTab, setActiveTab] = useState('basic')
  const [agents, setAgents] = useState<Agent[]>([])
  const [tools, setTools] = useState<Tool[]>([])
  const [toolSearchQuery, setToolSearchQuery] = useState('')
  const [useDefaultTools, setUseDefaultTools] = useState(true)
  const [canModifyTools, setCanModifyTools] = useState(true)
  const [systemPrompt, setSystemPrompt] = useState('')
  const searchInputRef = useRef<HTMLInputElement>(null)
  const nodes = useWorkflowStore((state) => state.nodes)

  // Agent 및 Tool 목록 로드
  useEffect(() => {
    const loadData = async () => {
      try {
        const [agentList, toolList] = await Promise.all([getAgents(), getTools()])
        setAgents(agentList)
        setTools(toolList)
      } catch (error) {
        console.error('❌ 데이터 로드 실패:', error)
      }
    }
    loadData()
  }, [])

  // 초기 데이터 설정
  const initialData: WorkerNodeData = {
    task_template: node.data.task_template || '',
    allowed_tools: node.data.allowed_tools || [],
    thinking: node.data.thinking,
    system_prompt: node.data.system_prompt || '',  // 커스텀 워커용
    config: {
      output_format: node.data.config?.output_format || 'plain_text',
      custom_prompt: node.data.config?.custom_prompt || '',
    },
  }

  // allowed_tools 여부로 기본 설정 사용 여부 판단
  useEffect(() => {
    if (node.data.allowed_tools && node.data.allowed_tools.length > 0) {
      setUseDefaultTools(false)
    } else {
      setUseDefaultTools(true)
    }
  }, [node.data.allowed_tools])

  // 시스템 프롬프트 및 도구 수정 가능 여부 설정
  useEffect(() => {
    if (agents.length === 0) return

    const agent = agents.find((a) => a.name === node.data.agent_name)
    if (agent) {
      // 커스텀 워커인 경우 노드 데이터의 system_prompt 사용, 없으면 agent의 것 사용
      const promptToUse = agent.is_custom && node.data.system_prompt
        ? node.data.system_prompt
        : agent.system_prompt || ''
      setSystemPrompt(promptToUse)

      // 커스텀 워커는 항상 도구 수정 가능, 기본 워커는 쓰기 도구가 있어야 수정 가능
      if (agent.is_custom) {
        setCanModifyTools(true)
      } else {
        const hasWriteTools = agent.allowed_tools.some((tool) => ['write', 'edit', 'bash'].includes(tool))
        setCanModifyTools(hasWriteTools)
      }
    } else {
      setSystemPrompt(`❌ Agent '${node.data.agent_name}'의 시스템 프롬프트를 찾을 수 없습니다.`)
    }
  }, [agents, node.data.agent_name, node.data.system_prompt])

  // 노드 설정 Hook
  const { data, setData, hasChanges, saveMessage, save, reset } = useNodeConfig<WorkerNodeData>({
    nodeId: node.id,
    initialData,
    onValidate: (data) => {
      const errors: Record<string, string> = {}

      if (!data.task_template.trim()) {
        errors.task_template = '작업 템플릿을 입력하세요'
      }

      // 변수 구문 검증
      const openBraces = (data.task_template.match(/\{\{/g) || []).length
      const closeBraces = (data.task_template.match(/\}\}/g) || []).length
      if (openBraces !== closeBraces) {
        errors.task_template = '변수 구문이 올바르지 않습니다 ({{ }})'
      }

      // 도구 선택 검증
      if (!useDefaultTools && (!data.allowed_tools || data.allowed_tools.length === 0)) {
        errors.tools = '최소 1개의 도구를 선택하거나 기본 설정을 사용하세요'
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

  // 도구 토글
  const handleToggleTool = (toolName: string) => {
    const currentTools = data.allowed_tools || []
    const newTools = currentTools.includes(toolName)
      ? currentTools.filter((t) => t !== toolName)
      : [...currentTools, toolName]

    setData({ ...data, allowed_tools: newTools })
  }

  // 필터링된 도구
  const filteredTools = tools.filter(
    (tool) =>
      tool.name.toLowerCase().includes(toolSearchQuery.toLowerCase()) ||
      tool.description.toLowerCase().includes(toolSearchQuery.toLowerCase())
  )

  // 현재 Agent 정보
  const currentAgent = agents.find((a) => a.name === node.data.agent_name)

  return (
    <Card className="h-full overflow-hidden flex flex-col border-0 shadow-none">
      <CardHeader className="pb-3 bg-gradient-to-r from-blue-50 to-cyan-50 border-b">
        <CardTitle className="text-lg flex items-center gap-2">
          <ListChecks className="h-5 w-5 text-blue-600" />
          Worker 노드 설정
        </CardTitle>
        <div className="text-sm text-muted-foreground flex items-center gap-2">
          <span className="font-medium">{node.data.agent_name}</span>
          <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
            {currentAgent?.role || '워커'}
          </span>
        </div>
      </CardHeader>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="flex w-auto mx-4 mt-4 gap-1">
          <TabsTrigger value="basic" className="text-xs flex-1 min-w-0">
            기본
          </TabsTrigger>
          <TabsTrigger value="tools" className="text-xs flex-1 min-w-0">
            도구
          </TabsTrigger>
          <TabsTrigger value="advanced" className="text-xs flex-1 min-w-0">
            고급
          </TabsTrigger>
          <TabsTrigger value="info" className="text-xs flex-1 min-w-0">
            정보
          </TabsTrigger>
        </TabsList>

        {/* 기본 설정 탭 */}
        <TabsContent value="basic" className="flex-1 overflow-y-auto px-4 pb-4 space-y-4 mt-4">
          {/* 작업 템플릿 */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">작업 템플릿</label>
              <span title="{{input}}을 사용하여 이전 노드의 출력을 참조할 수 있습니다">
                <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
              </span>
            </div>
            <textarea
              className="w-full p-2 border rounded-md text-sm font-mono"
              rows={5}
              value={data.task_template}
              onChange={(e) => setData({ ...data, task_template: e.target.value })}
              onKeyDown={handleInputKeyDown}
              placeholder="예: {{input}}을(를) 분석해주세요."
            />

            {/* 실시간 미리보기 */}
            {data.task_template.includes('{{') && (
              <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                <div className="text-xs font-medium text-blue-900 mb-2 flex items-center gap-1">
                  <span>미리보기 (예시 입력 적용)</span>
                </div>
                <div className="text-sm text-gray-700 font-mono bg-white p-2 rounded border">
                  {generateTemplatePreview(data.task_template, nodes, node.id)}
                </div>
              </div>
            )}

            <div className="text-xs text-muted-foreground">
              사용 가능한 변수: <code className="px-1.5 py-0.5 bg-gray-100 rounded font-mono">{'{{input}}'}</code>{' '}
              (이전 노드 출력)
            </div>
          </div>

          {/* Output 형식 */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">출력 형식</label>
              <span title="Worker Agent가 생성할 출력의 형식을 지정합니다">
                <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
              </span>
            </div>
            <select
              className="w-full p-2 border rounded-md text-sm"
              value={data.config?.output_format || 'plain_text'}
              onChange={(e) => setData({ ...data, config: { ...data.config, output_format: e.target.value } })}
            >
              <option value="plain_text">Plain Text (일반 텍스트)</option>
              <option value="markdown">Markdown</option>
              <option value="json">JSON</option>
              <option value="code">Code Block</option>
            </select>
          </div>
        </TabsContent>

        {/* 도구 탭 */}
        <TabsContent value="tools" className="flex-1 overflow-y-auto px-4 pb-4 space-y-4 mt-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">사용 가능한 도구</label>
                <span
                  title={
                    canModifyTools
                      ? 'Worker가 사용할 수 있는 도구를 선택하세요'
                      : '이 워커는 기본 도구만 사용합니다'
                  }
                >
                  <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
                </span>
              </div>
              {canModifyTools && (
                <label className="flex items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    checked={useDefaultTools}
                    onChange={(e) => {
                      setUseDefaultTools(e.target.checked)
                      if (e.target.checked) {
                        setData({ ...data, allowed_tools: [] })
                      }
                    }}
                    className="w-3 h-3"
                  />
                  기본 설정 사용
                </label>
              )}
            </div>

            {canModifyTools && !useDefaultTools ? (
              <>
                {/* 검색 바 */}
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    placeholder="도구 검색... (이름 또는 설명)"
                    className="w-full pl-8 p-2 border rounded-md text-sm"
                    value={toolSearchQuery}
                    onChange={(e) => setToolSearchQuery(e.target.value)}
                    onKeyDown={handleInputKeyDown}
                  />
                </div>

                {/* 도구 목록 */}
                <div className="border rounded-md p-3 space-y-2 max-h-96 overflow-y-auto">
                  {tools.length === 0 ? (
                    <div className="text-sm text-muted-foreground">도구 로딩 중...</div>
                  ) : filteredTools.length === 0 ? (
                    <div className="text-sm text-muted-foreground">검색 결과가 없습니다</div>
                  ) : (
                    filteredTools.map((tool) => (
                      <label
                        key={tool.name}
                        className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={(data.allowed_tools || []).includes(tool.name)}
                          onChange={() => handleToggleTool(tool.name)}
                          className="w-4 h-4"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{tool.name}</span>
                            {tool.readonly && (
                              <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded">
                                읽기 전용
                              </span>
                            )}
                            <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded">
                              {tool.category}
                            </span>
                          </div>
                          <div className="text-xs text-muted-foreground">{tool.description}</div>
                        </div>
                      </label>
                    ))
                  )}
                </div>

                <p className="text-xs text-muted-foreground">선택된 도구: {(data.allowed_tools || []).length}개</p>
              </>
            ) : (
              <div className="border rounded-md p-3 bg-gray-50">
                <p className="text-sm text-muted-foreground mb-3">
                  {canModifyTools
                    ? 'agent_config.json의 기본 도구 설정을 사용합니다.'
                    : '이 워커는 agent_config.json에 정의된 기본 도구만 사용합니다. (변경 불가)'}
                </p>
                <div className="flex flex-wrap gap-2">
                  {currentAgent?.allowed_tools.map((toolName) => {
                    const tool = tools.find((t) => t.name === toolName)
                    return (
                      <div
                        key={toolName}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-white border rounded-md text-sm"
                      >
                        <span className="font-medium">{toolName}</span>
                        {tool?.readonly && (
                          <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded">읽기 전용</span>
                        )}
                      </div>
                    )
                  }) || <span className="text-xs text-muted-foreground">도구 없음</span>}
                </div>
              </div>
            )}

            {/* Thinking 모드 */}
            <div className="space-y-2 border-t pt-4 mt-4">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">Thinking 모드</label>
                <span title="Thinking 모드를 활성화하면 Worker의 시스템 프롬프트에 ultrathink가 추가되어 복잡한 작업 시 사고 과정을 더 상세히 출력합니다. 토큰 사용량이 증가할 수 있습니다.">
                  <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
                </span>
              </div>

              <label className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={data.thinking ?? currentAgent?.thinking ?? false}
                  onChange={(e) => {
                    setData({ ...data, thinking: e.target.checked })
                  }}
                  className="w-4 h-4"
                />
                <span>
                  Thinking 모드 활성화
                  {data.thinking === undefined && (
                    <span className="ml-2 text-muted-foreground">
                      (기본값: {currentAgent?.thinking ? 'ON' : 'OFF'})
                    </span>
                  )}
                </span>
              </label>

              <p className="text-xs text-muted-foreground">
                {data.thinking
                  ? '✅ Worker의 시스템 프롬프트에 ultrathink가 추가되어 사고 과정을 상세히 출력합니다'
                  : '⚪ 기본 시스템 프롬프트만 사용합니다'}
              </p>
            </div>
          </div>
        </TabsContent>

        {/* 고급 탭 */}
        <TabsContent value="advanced" className="flex-1 overflow-y-auto px-4 pb-4 space-y-4 mt-4">
          {/* 커스텀 프롬프트 */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">추가 지시사항 (선택)</label>
              <span title="이 지시사항은 Worker의 시스템 프롬프트에 추가됩니다">
                <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
              </span>
            </div>
            <textarea
              className="w-full p-2 border rounded-md text-sm"
              rows={6}
              value={data.config?.custom_prompt || ''}
              onChange={(e) => setData({ ...data, config: { ...data.config, custom_prompt: e.target.value } })}
              onKeyDown={handleInputKeyDown}
              placeholder="예: 코드 작성 시 주석을 포함해주세요."
            />
            <p className="text-xs text-muted-foreground">
              워커의 기본 시스템 프롬프트에 이 지시사항이 추가됩니다.
            </p>
          </div>

          {/* 시스템 프롬프트 */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">
                시스템 프롬프트 {currentAgent?.is_custom ? '' : '(읽기 전용)'}
              </label>
              <span title={currentAgent?.is_custom
                ? "커스텀 워커의 시스템 프롬프트를 수정할 수 있습니다"
                : "기본 워커의 시스템 프롬프트는 수정할 수 없습니다"
              }>
                <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
              </span>
            </div>
            <textarea
              className={`w-full p-2 border rounded-md text-sm font-mono ${
                currentAgent?.is_custom ? 'bg-white' : 'bg-gray-50'
              }`}
              rows={15}
              value={currentAgent?.is_custom ? (data.system_prompt || systemPrompt) : systemPrompt}
              onChange={currentAgent?.is_custom ? (e) => setData({ ...data, system_prompt: e.target.value }) : undefined}
              onKeyDown={handleInputKeyDown}
              readOnly={!currentAgent?.is_custom}
            />
            <p className="text-xs text-muted-foreground">
              {currentAgent?.is_custom
                ? '커스텀 워커의 시스템 프롬프트를 자유롭게 수정할 수 있습니다.'
                : '기본 워커의 시스템 프롬프트는 수정할 수 없습니다.'}
            </p>
          </div>
        </TabsContent>

        {/* 정보 탭 */}
        <TabsContent value="info" className="flex-1 overflow-y-auto px-4 pb-20 space-y-4 mt-4">
          <div className="space-y-4">
            {/* 노드 정보 */}
            <div className="border rounded-md p-3 bg-gray-50">
              <div className="text-sm font-medium mb-2">노드 정보</div>
              <div className="space-y-2 text-xs text-muted-foreground">
                <div>
                  <span className="font-medium">ID:</span>
                  <div className="font-mono text-gray-600 mt-0.5 break-all">{node.id}</div>
                </div>
                <div>
                  <span className="font-medium">타입:</span>
                  <div className="text-gray-600 mt-0.5">Worker</div>
                </div>
                <div>
                  <span className="font-medium">Agent:</span>
                  <div className="text-gray-600 mt-0.5">{node.data.agent_name}</div>
                </div>
                <div>
                  <span className="font-medium">위치:</span>
                  <div className="font-mono text-gray-600 mt-0.5">
                    ({Math.round(node.position.x)}, {Math.round(node.position.y)})
                  </div>
                </div>
              </div>
            </div>

            {/* Agent 정보 */}
            {currentAgent && (
              <div className="border rounded-md p-3 bg-blue-50 border-blue-200">
                <div className="text-sm font-medium mb-2 text-blue-900">Agent 정보</div>
                <div className="space-y-2 text-xs text-blue-800">
                  <div>
                    <span className="font-medium">역할:</span>
                    <div className="mt-0.5">{currentAgent.role}</div>
                  </div>
                  <div>
                    <span className="font-medium">모델:</span>
                    <div className="mt-0.5 break-all">{currentAgent.model || 'claude-sonnet-4-5-20250929'}</div>
                  </div>
                  <div>
                    <span className="font-medium">기본 도구:</span>
                    <div className="mt-0.5 break-words">
                      {currentAgent.allowed_tools?.length > 0 ? currentAgent.allowed_tools.join(', ') : '없음'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 사용법 안내 */}
            <div className="border rounded-md p-3 bg-green-50 border-green-200">
              <div className="text-sm font-medium mb-2 text-green-900">사용법</div>
              <ul className="list-disc list-inside space-y-1 text-xs text-green-800">
                <li>작업 템플릿에서 {'{{input}}'} 변수로 이전 노드 출력 참조</li>
                <li>도구 탭에서 커스텀 도구 선택 가능 (일부 워커만)</li>
                <li>고급 탭에서 추가 지시사항 작성 가능</li>
                <li>변경사항은 3초 후 자동 저장됩니다</li>
              </ul>
            </div>
          </div>
        </TabsContent>
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
          <Button className="flex-1" onClick={save} disabled={!hasChanges}>
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
