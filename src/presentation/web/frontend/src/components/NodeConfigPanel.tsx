/**
 * 노드 설정 패널 컴포넌트
 *
 * 선택된 노드의 상세 설정을 표시하고 편집합니다.
 * - 탭 기반 구조 (기본 설정 / 도구 / 고급 / 정보)
 * - 검색 가능한 워커/도구 선택
 * - 실시간 미리보기 및 유효성 검증
 * - 키보드 단축키 지원 (Cmd+S, Cmd+K, Esc)
 * - 자동 저장 (3초 debounce)
 */

import React, { useEffect, useState, useRef } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { useWorkflowStore } from '@/stores/workflowStore'
import { getAgents, Agent, getTools, Tool } from '@/lib/api'
import { Save, Settings, ListChecks, Terminal, Search, HelpCircle, AlertCircle, CheckCircle2 } from 'lucide-react'
import { parseClaudeMessage } from '@/lib/messageParser'

export const NodeConfigPanel: React.FC = () => {
  const selectedNodeId = useWorkflowStore((state) => state.selectedNodeId)
  const getSelectedNode = useWorkflowStore((state) => state.getSelectedNode)
  const updateNode = useWorkflowStore((state) => state.updateNode)

  const selectedNode = getSelectedNode()

  // 로컬 상태 (편집 중인 값 - Worker 노드)
  const [taskTemplate, setTaskTemplate] = useState('')
  const [outputFormat, setOutputFormat] = useState('plain_text')
  const [customPrompt, setCustomPrompt] = useState('')
  const [hasChanges, setHasChanges] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  // Agent 목록 및 시스템 프롬프트
  const [agents, setAgents] = useState<Agent[]>([])
  const [systemPrompt, setSystemPrompt] = useState('')

  // Manager 노드 전용 로컬 상태
  const [managerTaskDescription, setManagerTaskDescription] = useState('')
  const [managerAvailableWorkers, setManagerAvailableWorkers] = useState<string[]>([])

  // Input 노드 전용 로컬 상태
  const [inputInitialInput, setInputInitialInput] = useState('')

  // Tool 관련 상태
  const [tools, setTools] = useState<Tool[]>([])
  const [allowedTools, setAllowedTools] = useState<string[]>([])
  const [useDefaultTools, setUseDefaultTools] = useState(true) // 기본 도구 사용 여부
  const [canModifyTools, setCanModifyTools] = useState(true) // 도구 수정 가능 여부

  // 검색 관련 상태
  const [workerSearchQuery, setWorkerSearchQuery] = useState('')
  const [toolSearchQuery, setToolSearchQuery] = useState('')
  const searchInputRef = useRef<HTMLInputElement>(null)

  // 유효성 검증 상태
  const [errors, setErrors] = useState<Record<string, string>>({})

  // 탭 상태 (Worker 노드용)
  const [activeTab, setActiveTab] = useState('basic')

  // 자동 저장 타이머
  const autoSaveTimerRef = useRef<number | null>(null)

  // 실행 로그 관련
  const logs = useWorkflowStore((state) => state.execution.logs)
  const logEndRef = useRef<HTMLDivElement>(null)
  const [expandedLogs, setExpandedLogs] = useState<Set<number>>(new Set())

  // 유효성 검증 함수
  const validateSettings = () => {
    const newErrors: Record<string, string> = {}

    if (!selectedNode) return true

    // Input 노드 검증
    if (selectedNode.type === 'input') {
      if (!inputInitialInput.trim()) {
        newErrors.initial_input = '초기 입력을 입력하세요'
      }
    }

    // Manager 노드 검증
    if (selectedNode.type === 'manager') {
      if (!managerTaskDescription.trim()) {
        newErrors.task_description = '작업 설명을 입력하세요'
      }
      if (managerAvailableWorkers.length === 0) {
        newErrors.workers = '최소 1개의 워커를 선택하세요'
      }
    }

    // Worker 노드 검증
    if (selectedNode.type === 'worker') {
      if (!taskTemplate.trim()) {
        newErrors.task_template = '작업 템플릿을 입력하세요'
      }
      // 변수 구문 검증
      const openBraces = (taskTemplate.match(/\{\{/g) || []).length
      const closeBraces = (taskTemplate.match(/\}\}/g) || []).length
      if (openBraces !== closeBraces) {
        newErrors.task_template = '변수 구문이 올바르지 않습니다 ({{ }})'
      }
      // 도구 선택 검증
      if (!useDefaultTools && allowedTools.length === 0) {
        newErrors.tools = '최소 1개의 도구를 선택하거나 기본 설정을 사용하세요'
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // 로그 자동 스크롤
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // 로그 펼침/접기 토글
  const toggleLogExpand = (index: number) => {
    setExpandedLogs((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  // Agent 목록 로드 (마운트 시 한 번만)
  useEffect(() => {
    const loadAgents = async () => {
      try {
        console.log('[NodeConfigPanel] Agent 목록 로드 시작...')
        const agentList = await getAgents()
        console.log('[NodeConfigPanel] Agent 목록 로드 완료:', agentList.length, '개')
        console.log('[NodeConfigPanel] Agent 목록:', agentList.map(a => ({
          name: a.name,
          promptLength: a.system_prompt?.length || 0
        })))
        setAgents(agentList)
      } catch (error) {
        console.error('❌ Agent 목록 로드 실패:', error)
        setSystemPrompt('❌ Agent 목록 로드 실패')
      }
    }
    loadAgents()
  }, [])

  // Tool 목록 로드 (마운트 시 한 번만)
  useEffect(() => {
    const loadTools = async () => {
      try {
        console.log('[NodeConfigPanel] Tool 목록 로드 시작...')
        const toolList = await getTools()
        console.log('[NodeConfigPanel] Tool 목록 로드 완료:', toolList.length, '개')
        setTools(toolList)
      } catch (error) {
        console.error('❌ Tool 목록 로드 실패:', error)
      }
    }
    loadTools()
  }, [])

  // 키보드 단축키
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+S / Ctrl+S: 저장
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        if (hasChanges && validateSettings()) {
          handleSave()
        }
      }

      // Cmd+K / Ctrl+K: 검색 포커스
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        searchInputRef.current?.focus()
      }

      // Esc: 변경사항 초기화
      if (e.key === 'Escape' && hasChanges) {
        handleReset()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [hasChanges])

  // 자동 저장 (3초 debounce)
  useEffect(() => {
    // 자동 저장 타이머 정리
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current)
    }

    // 변경사항이 있고 유효성 검증 통과 시 자동 저장
    if (hasChanges && validateSettings()) {
      autoSaveTimerRef.current = setTimeout(() => {
        handleSave()
        setSaveMessage('✅ 자동 저장됨')
        setTimeout(() => setSaveMessage(null), 2000)
      }, 3000)
    }

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current)
      }
    }
  }, [hasChanges, taskTemplate, outputFormat, customPrompt, allowedTools, useDefaultTools, managerTaskDescription, managerAvailableWorkers, inputInitialInput])

  // 실시간 유효성 검증
  useEffect(() => {
    if (selectedNode) {
      validateSettings()
    }
  }, [taskTemplate, managerTaskDescription, managerAvailableWorkers, inputInitialInput, allowedTools, useDefaultTools])

  // 선택된 노드가 변경되면 로컬 상태 초기화
  useEffect(() => {
    if (selectedNode) {
      // Input 노드인 경우
      if (selectedNode.type === 'input') {
        console.log('[NodeConfigPanel] Input 노드 선택:', selectedNode.id)
        setInputInitialInput(selectedNode.data.initial_input || '')
        setHasChanges(false)
        return
      }

      // Manager 노드인 경우
      if (selectedNode.type === 'manager') {
        console.log('[NodeConfigPanel] Manager 노드 선택:', selectedNode.id)
        setManagerTaskDescription(selectedNode.data.task_description || '')
        setManagerAvailableWorkers(selectedNode.data.available_workers || [])
        setHasChanges(false)
        return
      }

      // Worker 노드인 경우
      console.log('[NodeConfigPanel] Worker 노드 선택:', selectedNode.data.agent_name)
      console.log('[NodeConfigPanel] agents 배열 길이:', agents.length)

      setTaskTemplate(selectedNode.data.task_template || '')
      setOutputFormat(selectedNode.data.config?.output_format || 'plain_text')
      setCustomPrompt(selectedNode.data.config?.custom_prompt || '')

      // allowed_tools 초기화
      if (selectedNode.data.allowed_tools && selectedNode.data.allowed_tools.length > 0) {
        setAllowedTools(selectedNode.data.allowed_tools)
        setUseDefaultTools(false)
      } else {
        setAllowedTools([])
        setUseDefaultTools(true)
      }

      setHasChanges(false)

      // 시스템 프롬프트 가져오기 및 도구 수정 가능 여부 판단
      if (agents.length === 0) {
        console.log('[NodeConfigPanel] agents 배열이 비어있음, 로딩 중...')
        setSystemPrompt('시스템 프롬프트를 로드하는 중...')
        return
      }

      const agent = agents.find((a) => a.name === selectedNode.data.agent_name)
      console.log('[NodeConfigPanel] 매칭된 agent:', agent?.name, ', 프롬프트 길이:', agent?.system_prompt?.length || 0)

      if (agent?.system_prompt) {
        setSystemPrompt(agent.system_prompt)
      } else {
        setSystemPrompt(`❌ Agent '${selectedNode.data.agent_name}'의 시스템 프롬프트를 찾을 수 없습니다.`)
      }

      // 도구 수정 가능 여부 판단 (agent_config.json의 allowed_tools 기반)
      if (agent) {
        // 쓰기 도구가 하나라도 있으면 커스터마이즈 가능
        const hasWriteTools = agent.allowed_tools.some((tool) =>
          ['write', 'edit', 'bash'].includes(tool)
        )
        setCanModifyTools(hasWriteTools)
        console.log('[NodeConfigPanel] 도구 수정 가능:', hasWriteTools, ', 기본 도구:', agent.allowed_tools)
      } else {
        setCanModifyTools(true) // 기본값
      }
    }
  }, [selectedNode, agents])

  // 변경사항 추적
  useEffect(() => {
    if (!selectedNode) return

    // Input 노드인 경우
    if (selectedNode.type === 'input') {
      const changed = inputInitialInput !== (selectedNode.data.initial_input || '')
      setHasChanges(changed)
      return
    }

    // Manager 노드인 경우
    if (selectedNode.type === 'manager') {
      const changed =
        managerTaskDescription !== (selectedNode.data.task_description || '') ||
        JSON.stringify(managerAvailableWorkers) !== JSON.stringify(selectedNode.data.available_workers || [])
      setHasChanges(changed)
      return
    }

    // Worker 노드인 경우
    const originalAllowedTools = selectedNode.data.allowed_tools || []
    const toolsChanged = !useDefaultTools &&
      JSON.stringify(allowedTools.sort()) !== JSON.stringify(originalAllowedTools.sort())

    const changed =
      taskTemplate !== (selectedNode.data.task_template || '') ||
      outputFormat !== (selectedNode.data.config?.output_format || 'plain_text') ||
      customPrompt !== (selectedNode.data.config?.custom_prompt || '') ||
      toolsChanged

    setHasChanges(changed)
  }, [taskTemplate, outputFormat, customPrompt, allowedTools, useDefaultTools, managerTaskDescription, managerAvailableWorkers, inputInitialInput, selectedNode])

  // 저장
  const handleSave = () => {
    if (!selectedNodeId || !selectedNode) return

    try {
      // Input 노드인 경우
      if (selectedNode.type === 'input') {
        updateNode(selectedNodeId, {
          initial_input: inputInitialInput,
        })

        console.log('💾 Input 노드 설정 저장:', {
          nodeId: selectedNodeId,
          initialInput: inputInitialInput.substring(0, 50),
        })

        setHasChanges(false)
        setSaveMessage('✅ 저장됨 (자동 저장 대기 중...)')
        setTimeout(() => setSaveMessage(null), 3000)
        return
      }

      // Manager 노드인 경우
      if (selectedNode.type === 'manager') {
        updateNode(selectedNodeId, {
          task_description: managerTaskDescription,
          available_workers: managerAvailableWorkers,
        })

        console.log('💾 Manager 노드 설정 저장:', {
          nodeId: selectedNodeId,
          taskDescription: managerTaskDescription.substring(0, 50),
          availableWorkers: managerAvailableWorkers,
        })
      } else {
        // Worker 노드인 경우
        updateNode(selectedNodeId, {
          task_template: taskTemplate,
          allowed_tools: useDefaultTools ? undefined : allowedTools.length > 0 ? allowedTools : undefined,
          config: {
            ...selectedNode.data.config,
            output_format: outputFormat,
            custom_prompt: customPrompt,
          },
        })

        console.log('💾 Worker 노드 설정 저장:', {
          nodeId: selectedNodeId,
          agent: selectedNode.data.agent_name,
          taskTemplate: taskTemplate.substring(0, 50),
          outputFormat,
          hasCustomPrompt: !!customPrompt,
          allowedTools: useDefaultTools ? 'default' : allowedTools,
        })
      }

      setHasChanges(false)
      setSaveMessage('✅ 저장됨 (자동 저장 대기 중...)')

      // 3초 후 메시지 제거
      setTimeout(() => setSaveMessage(null), 3000)
    } catch (error) {
      console.error('❌ 노드 설정 저장 실패:', error)
      setSaveMessage('❌ 저장 실패')
      setTimeout(() => setSaveMessage(null), 3000)
    }
  }

  // 초기화
  const handleReset = () => {
    if (!selectedNode) return

    // Input 노드인 경우
    if (selectedNode.type === 'input') {
      setInputInitialInput(selectedNode.data.initial_input || '')
      setHasChanges(false)
      return
    }

    // Manager 노드인 경우
    if (selectedNode.type === 'manager') {
      setManagerTaskDescription(selectedNode.data.task_description || '')
      setManagerAvailableWorkers(selectedNode.data.available_workers || [])
      setHasChanges(false)
      return
    }

    // Worker 노드인 경우
    setTaskTemplate(selectedNode.data.task_template || '')
    setOutputFormat(selectedNode.data.config?.output_format || 'plain_text')
    setCustomPrompt(selectedNode.data.config?.custom_prompt || '')

    // allowed_tools 복원
    if (selectedNode.data.allowed_tools && selectedNode.data.allowed_tools.length > 0) {
      setAllowedTools(selectedNode.data.allowed_tools)
      setUseDefaultTools(false)
    } else {
      setAllowedTools([])
      setUseDefaultTools(true)
    }

    setHasChanges(false)
  }

  // Manager 노드 워커 토글
  const handleToggleWorker = (workerName: string) => {
    if (managerAvailableWorkers.includes(workerName)) {
      setManagerAvailableWorkers(managerAvailableWorkers.filter((w) => w !== workerName))
    } else {
      setManagerAvailableWorkers([...managerAvailableWorkers, workerName])
    }
  }

  // Worker 노드 도구 토글
  const handleToggleTool = (toolName: string) => {
    if (allowedTools.includes(toolName)) {
      setAllowedTools(allowedTools.filter((t) => t !== toolName))
    } else {
      setAllowedTools([...allowedTools, toolName])
    }
  }

  // 워커 선택 헬퍼
  const selectAllWorkers = () => {
    setManagerAvailableWorkers(agents.map((a) => a.name))
  }

  const selectNoWorkers = () => {
    setManagerAvailableWorkers([])
  }

  const selectWorkerPreset = (preset: string) => {
    switch (preset) {
      case 'full-dev':
        setManagerAvailableWorkers(['planner', 'coder', 'reviewer', 'tester'])
        break
      case 'quick-code':
        setManagerAvailableWorkers(['coder', 'reviewer'])
        break
      case 'planning':
        setManagerAvailableWorkers(['planner', 'product_manager'])
        break
      case 'creative':
        setManagerAvailableWorkers(['ideator', 'planner'])
        break
    }
  }

  // 필터링된 워커 및 도구
  const filteredAgents = agents.filter((agent) =>
    agent.name.toLowerCase().includes(workerSearchQuery.toLowerCase()) ||
    agent.role.toLowerCase().includes(workerSearchQuery.toLowerCase())
  )

  const filteredTools = tools.filter((tool) =>
    tool.name.toLowerCase().includes(toolSearchQuery.toLowerCase()) ||
    tool.description.toLowerCase().includes(toolSearchQuery.toLowerCase())
  )

  if (!selectedNode) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center space-y-3">
          <Settings className="h-12 w-12 text-muted-foreground mx-auto opacity-50" />
          <div className="text-sm text-muted-foreground">
            노드를 선택하면
            <br />
            상세 설정을 편집할 수 있습니다
          </div>
        </div>
      </div>
    )
  }

  // Input 노드 설정 UI (탭 기반)
  if (selectedNode.type === 'input') {
    return (
      <Card className="h-full overflow-hidden flex flex-col border-0 shadow-none">
        <CardHeader className="pb-3 bg-gradient-to-r from-emerald-50 to-teal-50 border-b">
          <CardTitle className="text-lg flex items-center gap-2">
            <Terminal className="h-5 w-5 text-emerald-600" />
            Input 노드 설정
          </CardTitle>
          <div className="text-sm text-muted-foreground">
            워크플로우 시작점
          </div>
        </CardHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
          {/* 탭 헤더 */}
          <TabsList className="flex w-full px-4 mt-4 gap-1">
            <TabsTrigger value="basic" className="text-xs flex-1 min-w-0">기본</TabsTrigger>
            <TabsTrigger value="logs" className="text-xs flex-1 min-w-0">로그</TabsTrigger>
            <TabsTrigger value="info" className="text-xs flex-1 min-w-0">정보</TabsTrigger>
          </TabsList>

          {/* 탭 컨텐츠 */}
          <div className="flex-1 overflow-hidden">
            {/* 기본 설정 탭 */}
            <TabsContent value="basic" className="h-full overflow-y-auto px-4 pb-20 mt-4 space-y-4">
              {/* 초기 입력 */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium">초기 입력</label>
                  <span title="워크플로우를 시작하는 초기 입력입니다">
                    <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
                  </span>
                </div>
                <textarea
                  className="w-full p-3 border rounded-md text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                  rows={10}
                  value={inputInitialInput}
                  onChange={(e) => setInputInitialInput(e.target.value)}
                  placeholder="워크플로우 초기 입력을 입력하세요...&#10;예시:&#10;- 새로운 기능 추가&#10;- 버그 수정&#10;- 코드 리뷰"
                />
                <p className="text-xs text-muted-foreground">
                  이 입력이 연결된 첫 번째 노드로 전달됩니다.
                </p>
                {errors.initial_input && (
                  <div className="text-xs text-red-600 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {errors.initial_input}
                  </div>
                )}
              </div>

              {/* 미리보기 */}
              {inputInitialInput.trim() && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-md p-3">
                  <div className="text-xs font-medium text-emerald-900 mb-2">
                    초기 입력 미리보기
                  </div>
                  <div className="text-sm text-gray-700 whitespace-pre-wrap bg-white p-3 rounded border">
                    {inputInitialInput}
                  </div>
                  <div className="text-xs text-emerald-700 mt-2">
                    글자 수: {inputInitialInput.length}자
                  </div>
                </div>
              )}

              {/* 연결 상태 */}
              <div className="bg-gray-50 border rounded-md p-3">
                <div className="text-xs font-medium mb-2">연결 상태</div>
                <div className="text-xs text-muted-foreground">
                  {/* 연결된 노드 체크 (edges에서 확인) */}
                  {(() => {
                    const edges = useWorkflowStore.getState().edges
                    const connectedEdges = edges.filter(e => e.source === selectedNode.id)
                    return connectedEdges.length > 0 ? (
                      <div className="flex items-center gap-2 text-green-600">
                        <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                        <span>{connectedEdges.length}개 노드에 연결됨</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-yellow-600">
                        <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
                        <span>연결된 노드 없음 (실행 불가)</span>
                      </div>
                    )
                  })()}
                </div>
              </div>
            </TabsContent>

            {/* 실행 로그 탭 */}
            <TabsContent value="logs" className="h-full overflow-y-auto px-4 pb-20 mt-4 space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">실행 로그 ({logs.length})</label>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      const clearExecution = useWorkflowStore.getState().clearExecution
                      clearExecution()
                    }}
                    disabled={logs.length === 0}
                  >
                    초기화
                  </Button>
                </div>
                <div className="overflow-y-auto bg-gray-50 border rounded-md p-3 space-y-1 max-h-96">
                  {logs.length === 0 ? (
                    <div className="text-xs text-muted-foreground">
                      실행 로그가 표시됩니다...
                    </div>
                  ) : (
                    <>
                      {logs.map((log, index) => {
                        // output 타입만 파싱 시도
                        const parsed = log.type === 'output'
                          ? parseClaudeMessage(log.message)
                          : { type: 'raw' as const, content: log.message, isCollapsible: false }

                        const isExpanded = expandedLogs.has(index)

                        let colorClass = 'text-gray-700'
                        let fontWeight = ''

                        // 로그 타입별 색상 및 스타일
                        if (log.type === 'error') {
                          colorClass = 'text-red-600'
                          fontWeight = 'font-semibold'
                        } else if (log.type === 'complete') {
                          colorClass = 'text-green-600'
                          fontWeight = 'font-semibold'
                        } else if (log.type === 'start') {
                          colorClass = 'text-blue-600'
                          fontWeight = 'font-semibold'
                        } else if (log.type === 'output') {
                          colorClass = 'text-gray-600'
                          fontWeight = 'font-normal'
                        }

                        // 접을 수 있는 로그 (UserMessage, ToolResult)
                        if (parsed.isCollapsible) {
                          const lines = parsed.content.split('\n')
                          const firstLine = lines[0] || parsed.content.substring(0, 80)
                          const hasMore = lines.length > 1 || parsed.content.length > 80

                          return (
                            <div key={index} className="border-l-2 border-gray-300 pl-2 my-1">
                              <div
                                className={`text-xs ${colorClass} font-mono cursor-pointer hover:bg-gray-100 rounded px-1`}
                                onClick={() => toggleLogExpand(index)}
                              >
                                <span className="select-none">{isExpanded ? '▼' : '▶'}</span> {firstLine}
                                {hasMore && !isExpanded && ' ...'}
                              </div>
                              {isExpanded && (
                                <div className="text-xs text-gray-600 font-mono whitespace-pre-wrap mt-1 pl-3 max-h-24 overflow-y-auto bg-gray-50 rounded p-2 border border-gray-200">
                                  {parsed.content}
                                </div>
                              )}
                            </div>
                          )
                        }

                        // 일반 로그
                        return (
                          <div key={index} className={`text-xs ${colorClass} ${fontWeight} font-mono whitespace-pre-wrap`}>
                            {log.nodeId && log.type !== 'output' && `[${log.nodeId}] `}
                            {parsed.content}
                          </div>
                        )
                      })}
                      {/* 자동 스크롤 앵커 */}
                      <div ref={logEndRef} />
                    </>
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
                  <div className="mt-0.5 break-all text-sm text-muted-foreground">
                    {selectedNode.id}
                  </div>
                </div>

                <div>
                  <span className="font-medium">타입:</span>
                  <div className="mt-0.5 text-sm text-muted-foreground">
                    Input (시작점)
                  </div>
                </div>

                <div>
                  <span className="font-medium">위치:</span>
                  <div className="mt-0.5 text-sm text-muted-foreground">
                    ({Math.round(selectedNode.position.x)}, {Math.round(selectedNode.position.y)})
                  </div>
                </div>

                <div>
                  <span className="font-medium">입력 크기:</span>
                  <div className="mt-0.5 text-sm text-muted-foreground">
                    {inputInitialInput.length}자
                  </div>
                </div>
              </div>

              {/* 사용 가이드 */}
              <div className="space-y-3">
                <div className="text-sm font-semibold border-b pb-2">사용 가이드</div>

                <div className="text-xs text-muted-foreground space-y-2">
                  <div>
                    <div className="font-medium text-emerald-700 mb-1">Input 노드란?</div>
                    <div>워크플로우의 시작점입니다. 연결된 노드들에게 초기 입력을 전달합니다.</div>
                  </div>

                  <div>
                    <div className="font-medium text-emerald-700 mb-1">실행 방법</div>
                    <ul className="list-disc list-inside space-y-1 mt-1">
                      <li>노드 내부의 "실행" 버튼 클릭</li>
                      <li>연결된 노드가 있어야 실행 가능</li>
                      <li>독립적으로 실행되며 다른 Input 노드에 영향 없음</li>
                    </ul>
                  </div>

                  <div>
                    <div className="font-medium text-emerald-700 mb-1">활용 팁</div>
                    <ul className="list-disc list-inside space-y-1 mt-1">
                      <li>여러 Input 노드를 만들어 다양한 시나리오 테스트</li>
                      <li>각 Input 노드는 별도의 워크플로우로 실행됨</li>
                      <li>Manager 노드에 연결하면 병렬 워커 실행 가능</li>
                      <li>Worker 노드에 직접 연결하면 단일 작업 실행</li>
                    </ul>
                  </div>

                  <div>
                    <div className="font-medium text-emerald-700 mb-1">주의사항</div>
                    <ul className="list-disc list-inside space-y-1 mt-1">
                      <li>연결된 노드가 없으면 실행되지 않습니다</li>
                      <li>입력이 비어있어도 실행 가능 (빈 문자열 전달)</li>
                      <li>로그는 실행 완료 시까지 누적됩니다</li>
                    </ul>
                  </div>
                </div>
              </div>
            </TabsContent>
          </div>
        </Tabs>

        {/* 저장/초기화 버튼 */}
        <div className="border-t p-4 space-y-2">
          {/* 저장 메시지 */}
          {saveMessage && (
            <div className="text-xs text-center py-1 px-2 rounded bg-green-100 text-green-700">
              <CheckCircle2 className="inline h-3 w-3 mr-1" />
              {saveMessage}
            </div>
          )}

          <div className="flex gap-2">
            <Button
              className="flex-1"
              onClick={handleSave}
              disabled={!hasChanges}
            >
              <Save className="mr-2 h-4 w-4" />
              저장
            </Button>
            <Button
              variant="outline"
              onClick={handleReset}
              disabled={!hasChanges}
            >
              초기화
            </Button>
          </div>

          {hasChanges && !saveMessage && (
            <div className="text-xs text-yellow-600 text-center">
              변경사항이 있습니다. 3초 후 자동 저장됩니다.
            </div>
          )}

          {/* 키보드 단축키 안내 */}
          <div className="text-xs text-muted-foreground text-center border-t pt-2">
            <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">⌘S</kbd> 저장 ·{' '}
            <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">Esc</kbd> 초기화
          </div>
        </div>
      </Card>
    )
  }

  // Manager 노드 설정 UI (탭 기반)
  if (selectedNode.type === 'manager') {
    return (
      <Card className="h-full overflow-hidden flex flex-col border-0 shadow-none">
        <CardHeader className="pb-3 bg-gradient-to-r from-purple-50 to-pink-50 border-b">
          <CardTitle className="text-lg flex items-center gap-2">
            <Settings className="h-5 w-5 text-purple-600" />
            Manager 노드 설정
          </CardTitle>
          <div className="text-sm text-muted-foreground">
            워커를 조율하는 오케스트레이터
          </div>
        </CardHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
          {/* 탭 헤더 */}
          <TabsList className="flex w-full px-4 mt-4 gap-1">
            <TabsTrigger value="basic" className="text-xs flex-1 min-w-0">기본</TabsTrigger>
            <TabsTrigger value="workers" className="text-xs flex-1 min-w-0">워커</TabsTrigger>
            <TabsTrigger value="info" className="text-xs flex-1 min-w-0">정보</TabsTrigger>
          </TabsList>

          {/* 탭 컨텐츠 */}
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
                  value={managerTaskDescription}
                  onChange={(e) => setManagerTaskDescription(e.target.value)}
                  placeholder="Manager가 수행할 작업을 설명하세요...&#10;예시:&#10;- 웹 애플리케이션의 로그인 기능 구현&#10;- API 문서화 및 테스트 작성&#10;- 코드 리뷰 및 리팩토링"
                />
                {errors.task_description && (
                  <div className="text-xs text-red-600 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {errors.task_description}
                  </div>
                )}
              </div>

              {/* 미리보기 */}
              {managerTaskDescription.trim() && (
                <div className="bg-purple-50 border border-purple-200 rounded-md p-3">
                  <div className="text-xs font-medium text-purple-900 mb-2">
                    작업 설명 미리보기
                  </div>
                  <div className="text-sm text-gray-700 whitespace-pre-wrap bg-white p-3 rounded border">
                    {managerTaskDescription}
                  </div>
                </div>
              )}

              {/* 선택된 워커 요약 */}
              <div className="bg-gray-50 border rounded-md p-3">
                <div className="text-xs font-medium mb-2">등록된 워커 ({managerAvailableWorkers.length}개)</div>
                {managerAvailableWorkers.length === 0 ? (
                  <div className="text-xs text-muted-foreground">워커 탭에서 워커를 선택하세요 (최소 1개 필수)</div>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {managerAvailableWorkers.map((workerName) => {
                      const agent = agents.find((a) => a.name === workerName)
                      return (
                        <span
                          key={workerName}
                          className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded"
                        >
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
                  <span className="text-xs text-muted-foreground">
                    {managerAvailableWorkers.length}개 선택됨
                  </span>
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
                          checked={managerAvailableWorkers.includes(agent.name)}
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

                {errors.workers && (
                  <div className="text-xs text-red-600 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {errors.workers}
                  </div>
                )}
              </div>
            </TabsContent>

            {/* 정보 탭 */}
            <TabsContent value="info" className="h-full overflow-y-auto px-4 pb-20 mt-4 space-y-4">
              {/* 노드 정보 */}
              <div className="space-y-3">
                <div className="text-sm font-semibold border-b pb-2">노드 정보</div>

                <div>
                  <span className="font-medium">노드 ID:</span>
                  <div className="mt-0.5 break-all text-sm text-muted-foreground">
                    {selectedNode.id}
                  </div>
                </div>

                <div>
                  <span className="font-medium">타입:</span>
                  <div className="mt-0.5 text-sm text-muted-foreground">
                    Manager (오케스트레이터)
                  </div>
                </div>

                <div>
                  <span className="font-medium">위치:</span>
                  <div className="mt-0.5 text-sm text-muted-foreground">
                    ({Math.round(selectedNode.position.x)}, {Math.round(selectedNode.position.y)})
                  </div>
                </div>

                <div>
                  <span className="font-medium">등록된 워커:</span>
                  <div className="mt-1 text-sm text-muted-foreground">
                    {managerAvailableWorkers.length === 0 ? (
                      <span className="text-red-600">없음 (최소 1개 선택 필요)</span>
                    ) : (
                      <div className="space-y-1">
                        {managerAvailableWorkers.map((workerName) => {
                          const agent = agents.find((a) => a.name === workerName)
                          return (
                            <div key={workerName} className="flex items-center gap-2">
                              <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                              <span>{workerName}</span>
                              {agent && (
                                <span className="text-xs text-gray-500">({agent.role})</span>
                              )}
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
          {/* 저장 메시지 */}
          {saveMessage && (
            <div className="text-xs text-center py-1 px-2 rounded bg-green-100 text-green-700">
              <CheckCircle2 className="inline h-3 w-3 mr-1" />
              {saveMessage}
            </div>
          )}

          <div className="flex gap-2">
            <Button
              className="flex-1"
              onClick={handleSave}
              disabled={!hasChanges || managerAvailableWorkers.length === 0}
            >
              <Save className="mr-2 h-4 w-4" />
              저장
            </Button>
            <Button
              variant="outline"
              onClick={handleReset}
              disabled={!hasChanges}
            >
              초기화
            </Button>
          </div>

          {hasChanges && !saveMessage && (
            <div className="text-xs text-yellow-600 text-center">
              변경사항이 있습니다. 3초 후 자동 저장됩니다.
            </div>
          )}

          {/* 키보드 단축키 안내 */}
          <div className="text-xs text-muted-foreground text-center border-t pt-2">
            <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">⌘S</kbd> 저장 ·{' '}
            <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">⌘K</kbd> 검색 ·{' '}
            <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">Esc</kbd> 초기화
          </div>
        </div>
      </Card>
    )
  }

  // Worker 노드 설정 UI (탭 기반)
  return (
    <Card className="h-full overflow-hidden flex flex-col border-0 shadow-none">
      <CardHeader className="pb-3 bg-gradient-to-r from-blue-50 to-cyan-50 border-b">
        <CardTitle className="text-lg flex items-center gap-2">
          <ListChecks className="h-5 w-5 text-blue-600" />
          Worker 노드 설정
        </CardTitle>
        <div className="text-sm text-muted-foreground flex items-center gap-2">
          <span className="font-medium">{selectedNode.data.agent_name}</span>
          <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
            {agents.find((a) => a.name === selectedNode.data.agent_name)?.role || '워커'}
          </span>
        </div>
      </CardHeader>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="flex w-full px-4 mt-4 gap-1">
          <TabsTrigger value="basic" className="text-xs flex-1 min-w-0">기본</TabsTrigger>
          <TabsTrigger value="tools" className="text-xs flex-1 min-w-0">도구</TabsTrigger>
          <TabsTrigger value="advanced" className="text-xs flex-1 min-w-0">고급</TabsTrigger>
          <TabsTrigger value="info" className="text-xs flex-1 min-w-0">정보</TabsTrigger>
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
              value={taskTemplate}
              onChange={(e) => setTaskTemplate(e.target.value)}
              placeholder="예: {{input}}을(를) 분석해주세요."
            />

            {/* 실시간 미리보기 */}
            {taskTemplate.includes('{{') && (
              <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                <div className="text-xs font-medium text-blue-900 mb-2 flex items-center gap-1">
                  <span>미리보기 (예시 입력 적용)</span>
                </div>
                <div className="text-sm text-gray-700 font-mono bg-white p-2 rounded border">
                  {taskTemplate.replace(/\{\{input\}\}/g, '이전 노드의 출력 예시...')}
                </div>
              </div>
            )}

            {/* 변수 가이드 */}
            <div className="text-xs text-muted-foreground">
              사용 가능한 변수:{' '}
              <code className="px-1.5 py-0.5 bg-gray-100 rounded font-mono">{'{{input}}'}</code>{' '}
              (이전 노드 출력)
            </div>

            {errors.task_template && (
              <div className="text-xs text-red-600 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                {errors.task_template}
              </div>
            )}
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
              value={outputFormat}
              onChange={(e) => setOutputFormat(e.target.value)}
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
                <span title={canModifyTools ? "Worker가 사용할 수 있는 도구를 선택하세요" : "이 워커는 기본 도구만 사용합니다"}>
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
                        setAllowedTools([])
                      }
                    }}
                    className="w-3 h-3"
                  />
                  기본 설정 사용
                </label>
              )}
            </div>

            {canModifyTools && !useDefaultTools && (
              <>
                {/* 검색 바 */}
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="도구 검색... (이름 또는 설명)"
                    className="w-full pl-8 p-2 border rounded-md text-sm"
                    value={toolSearchQuery}
                    onChange={(e) => setToolSearchQuery(e.target.value)}
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
                          checked={allowedTools.includes(tool.name)}
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

                <p className="text-xs text-muted-foreground">
                  선택된 도구: {allowedTools.length}개
                </p>

                {errors.tools && (
                  <div className="text-xs text-red-600 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {errors.tools}
                  </div>
                )}
              </>
            )}

            {/* 기본 설정 사용 시 또는 수정 불가 시 */}
            {(useDefaultTools || !canModifyTools) && (
              <div className="border rounded-md p-3 bg-gray-50">
                <p className="text-sm text-muted-foreground mb-3">
                  {canModifyTools
                    ? 'agent_config.json의 기본 도구 설정을 사용합니다.'
                    : '이 워커는 agent_config.json에 정의된 기본 도구만 사용합니다. (변경 불가)'}
                </p>
                <div className="flex flex-wrap gap-2">
                  {agents.find((a) => a.name === selectedNode.data.agent_name)?.allowed_tools.map((toolName) => {
                    const tool = tools.find((t) => t.name === toolName)
                    return (
                      <div
                        key={toolName}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-white border rounded-md text-sm"
                      >
                        <span className="font-medium">{toolName}</span>
                        {tool?.readonly && (
                          <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded">
                            읽기 전용
                          </span>
                        )}
                      </div>
                    )
                  }) || <span className="text-xs text-muted-foreground">도구 없음</span>}
                </div>
              </div>
            )}
          </div>
        </TabsContent>

        {/* 고급 탭 */}
        <TabsContent value="advanced" className="flex-1 overflow-y-auto px-4 pb-4 space-y-4 mt-4">
          {/* 커스텀 프롬프트 (추가 지시사항) */}
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
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="예: 코드 작성 시 주석을 포함해주세요."
            />
            <p className="text-xs text-muted-foreground">
              워커의 기본 시스템 프롬프트에 이 지시사항이 추가됩니다.
            </p>
          </div>

          {/* 시스템 프롬프트 (읽기 전용) */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">시스템 프롬프트 (읽기 전용)</label>
              <span title="워커의 기본 시스템 프롬프트입니다. 수정할 수 없습니다">
                <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
              </span>
            </div>
            <textarea
              className="w-full p-2 border rounded-md text-sm font-mono bg-gray-50"
              rows={15}
              value={systemPrompt}
              readOnly
            />
            <p className="text-xs text-muted-foreground">
              기본 워커의 시스템 프롬프트는 수정할 수 없습니다.
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
                  <div className="font-mono text-gray-600 mt-0.5 break-all">{selectedNode.id}</div>
                </div>
                <div>
                  <span className="font-medium">타입:</span>
                  <div className="text-gray-600 mt-0.5">Worker</div>
                </div>
                <div>
                  <span className="font-medium">Agent:</span>
                  <div className="text-gray-600 mt-0.5">{selectedNode.data.agent_name}</div>
                </div>
                <div>
                  <span className="font-medium">위치:</span>
                  <div className="font-mono text-gray-600 mt-0.5">
                    ({Math.round(selectedNode.position.x)}, {Math.round(selectedNode.position.y)})
                  </div>
                </div>
              </div>
            </div>

            {/* Agent 정보 */}
            {(() => {
              const currentAgent = agents.find((a) => a.name === selectedNode.data.agent_name)
              if (!currentAgent) return null

              return (
                <div className="border rounded-md p-3 bg-blue-50 border-blue-200">
                  <div className="text-sm font-medium mb-2 text-blue-900">Agent 정보</div>
                  <div className="space-y-2 text-xs text-blue-800">
                    <div>
                      <span className="font-medium">역할:</span>
                      <div className="mt-0.5">{currentAgent.role}</div>
                    </div>
                    <div>
                      <span className="font-medium">모델:</span>
                      <div className="mt-0.5 break-all">
                        {currentAgent.model || 'claude-sonnet-4-5-20250929'}
                      </div>
                    </div>
                    <div>
                      <span className="font-medium">기본 도구:</span>
                      <div className="mt-0.5 break-words">
                        {currentAgent.allowed_tools?.length > 0
                          ? currentAgent.allowed_tools.join(', ')
                          : '없음'}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })()}

            {/* 사용법 안내 */}
            <div className="border rounded-md p-3 bg-green-50 border-green-200">
              <div className="text-sm font-medium mb-2 text-green-900">💡 사용법</div>
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
        {/* 저장 메시지 */}
        {saveMessage && (
          <div className="text-xs text-center py-1 px-2 rounded bg-green-100 text-green-700">
            <CheckCircle2 className="inline h-3 w-3 mr-1" />
            {saveMessage}
          </div>
        )}

        <div className="flex gap-2">
          <Button
            className="flex-1"
            onClick={handleSave}
            disabled={!hasChanges}
          >
            <Save className="mr-2 h-4 w-4" />
            저장
          </Button>
          <Button
            variant="outline"
            onClick={handleReset}
            disabled={!hasChanges}
          >
            초기화
          </Button>
        </div>

        {hasChanges && !saveMessage && (
          <div className="text-xs text-yellow-600 text-center">
            변경사항이 있습니다. 3초 후 자동 저장됩니다.
          </div>
        )}

        {/* 키보드 단축키 안내 */}
        <div className="text-xs text-muted-foreground text-center border-t pt-2">
          <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">⌘S</kbd> 저장 ·{' '}
          <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">⌘K</kbd> 검색 ·{' '}
          <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">Esc</kbd> 초기화
        </div>
      </div>
    </Card>
  )
}
