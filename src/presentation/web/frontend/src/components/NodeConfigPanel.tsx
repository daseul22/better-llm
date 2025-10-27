/**
 * 노드 설정 패널 컴포넌트
 *
 * 선택된 노드의 상세 설정을 표시하고 편집합니다.
 * - 기본 프롬프트 (task_template)
 * - Output 형식
 * - 추가 설정 (config)
 */

import React, { useEffect, useState, useRef } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useWorkflowStore } from '@/stores/workflowStore'
import { getAgents, Agent, getTools, Tool } from '@/lib/api'
import { Save } from 'lucide-react'
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

  // 실행 로그 관련
  const logs = useWorkflowStore((state) => state.execution.logs)
  const logEndRef = useRef<HTMLDivElement>(null)
  const [expandedLogs, setExpandedLogs] = useState<Set<number>>(new Set())

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

  if (!selectedNode) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-sm text-muted-foreground text-center">
          노드를 선택하면 상세 설정을 편집할 수 있습니다.
        </div>
      </div>
    )
  }

  // Input 노드 설정 UI
  if (selectedNode.type === 'input') {
    return (
      <Card className="h-full overflow-hidden flex flex-col">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Input 노드 설정</CardTitle>
          <div className="text-sm text-muted-foreground">
            워크플로우 시작점
          </div>
        </CardHeader>

        <CardContent className="flex-1 overflow-y-auto space-y-4">
          {/* 초기 입력 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">초기 입력</label>
            <textarea
              className="w-full p-2 border rounded-md text-sm"
              rows={8}
              value={inputInitialInput}
              onChange={(e) => setInputInitialInput(e.target.value)}
              placeholder="워크플로우 초기 입력을 입력하세요..."
            />
            <p className="text-xs text-muted-foreground">
              이 입력이 연결된 첫 번째 노드로 전달됩니다.
            </p>
          </div>

          {/* 노드 정보 */}
          <div className="border-t pt-4 space-y-2">
            <div className="text-xs text-muted-foreground">
              <div className="font-medium mb-1">노드 정보</div>
              <div>ID: {selectedNode.id}</div>
              <div>타입: Input (시작점)</div>
              <div>
                위치: ({Math.round(selectedNode.position.x)},{' '}
                {Math.round(selectedNode.position.y)})
              </div>
            </div>
          </div>

          {/* 사용법 안내 */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="text-sm text-blue-900">
              <strong>💡 사용법:</strong>
              <ul className="list-disc list-inside mt-1 space-y-1 text-xs">
                <li>노드 내부의 "실행" 버튼으로 독립적으로 실행 가능</li>
                <li>여러 Input 노드를 만들어 여러 플로우 실행 가능</li>
                <li>연결된 노드가 없으면 실행되지 않습니다</li>
              </ul>
            </div>
          </div>

          {/* 실행 로그 섹션 */}
          <div className="border-t pt-4 space-y-2">
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
            <div className="overflow-y-auto bg-gray-50 border rounded-md p-3 space-y-1 max-h-64">
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
        </CardContent>

        {/* 저장/초기화 버튼 */}
        <div className="border-t p-4 space-y-2">
          {/* 저장 메시지 */}
          {saveMessage && (
            <div className="text-xs text-center py-1 px-2 rounded bg-gray-100">
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

          {hasChanges && (
            <div className="text-xs text-yellow-600 text-center">
              변경사항이 있습니다. 저장 버튼을 클릭하세요.
            </div>
          )}
        </div>
      </Card>
    )
  }

  // Manager 노드 설정 UI
  if (selectedNode.type === 'manager') {
    return (
      <Card className="h-full overflow-hidden flex flex-col">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Manager 노드 설정</CardTitle>
          <div className="text-sm text-muted-foreground">
            워커를 조율하는 오케스트레이터
          </div>
        </CardHeader>

        <CardContent className="flex-1 overflow-y-auto space-y-4">
          {/* 작업 설명 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">작업 설명</label>
            <textarea
              className="w-full p-2 border rounded-md text-sm"
              rows={6}
              value={managerTaskDescription}
              onChange={(e) => setManagerTaskDescription(e.target.value)}
              placeholder="Manager가 수행할 작업을 설명하세요..."
            />
            <p className="text-xs text-muted-foreground">
              이 작업 설명이 등록된 워커들에게 전달됩니다.
            </p>
          </div>

          {/* 사용 가능한 워커 선택 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">사용 가능한 워커</label>
            <div className="border rounded-md p-3 space-y-2">
              {agents.length === 0 ? (
                <div className="text-sm text-muted-foreground">워커 로딩 중...</div>
              ) : (
                agents.map((agent) => (
                  <label
                    key={agent.name}
                    className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={managerAvailableWorkers.includes(agent.name)}
                      onChange={() => handleToggleWorker(agent.name)}
                      className="w-4 h-4"
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium">{agent.name}</div>
                      <div className="text-xs text-muted-foreground">{agent.role}</div>
                    </div>
                  </label>
                ))
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              선택된 워커: {managerAvailableWorkers.length}개
            </p>
            {managerAvailableWorkers.length === 0 && (
              <p className="text-xs text-yellow-600">
                ⚠️ 최소 1개의 워커를 선택해야 합니다.
              </p>
            )}
          </div>

          {/* 노드 정보 */}
          <div className="border-t pt-4 space-y-2">
            <div className="text-xs text-muted-foreground">
              <div className="font-medium mb-1">노드 정보</div>
              <div>ID: {selectedNode.id}</div>
              <div>타입: Manager (오케스트레이터)</div>
              <div>
                위치: ({Math.round(selectedNode.position.x)},{' '}
                {Math.round(selectedNode.position.y)})
              </div>
            </div>
          </div>
        </CardContent>

        {/* 저장/초기화 버튼 */}
        <div className="border-t p-4 space-y-2">
          {/* 저장 메시지 */}
          {saveMessage && (
            <div className="text-xs text-center py-1 px-2 rounded bg-gray-100">
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

          {hasChanges && (
            <div className="text-xs text-yellow-600 text-center">
              변경사항이 있습니다. 저장 버튼을 클릭하세요.
            </div>
          )}
        </div>
      </Card>
    )
  }

  // Worker 노드 설정 UI
  return (
    <Card className="h-full overflow-hidden flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Worker 노드 설정</CardTitle>
        <div className="text-sm text-muted-foreground">
          {selectedNode.data.agent_name}
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto space-y-4">
        {/* 시스템 프롬프트 (읽기 전용) */}
        <div className="space-y-2">
          <label className="text-sm font-medium">시스템 프롬프트 (읽기 전용)</label>
          <textarea
            className="w-full p-2 border rounded-md text-sm font-mono bg-gray-50"
            rows={12}
            value={systemPrompt}
            readOnly
          />
          <p className="text-xs text-muted-foreground">
            기본 워커의 시스템 프롬프트는 수정할 수 없습니다.
          </p>
        </div>

        {/* 작업 템플릿 */}
        <div className="space-y-2">
          <label className="text-sm font-medium">작업 템플릿</label>
          <textarea
            className="w-full p-2 border rounded-md text-sm"
            rows={4}
            value={taskTemplate}
            onChange={(e) => setTaskTemplate(e.target.value)}
            placeholder="예: {{input}}을(를) 분석해주세요."
          />
          <p className="text-xs text-muted-foreground">
            {'{{input}}'}은 이전 노드의 출력으로 대체됩니다.
          </p>
        </div>

        {/* Output 형식 */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Output 형식</label>
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
          <p className="text-xs text-muted-foreground">
            Worker Agent의 출력 형식을 지정합니다.
          </p>
        </div>

        {/* 커스텀 프롬프트 (추가 지시사항) */}
        <div className="space-y-2">
          <label className="text-sm font-medium">추가 지시사항 (선택)</label>
          <textarea
            className="w-full p-2 border rounded-md text-sm"
            rows={6}
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder="예: 코드 작성 시 주석을 포함해주세요."
          />
          <p className="text-xs text-muted-foreground">
            이 지시사항은 Worker의 시스템 프롬프트에 추가됩니다.
          </p>
        </div>

        {/* 사용 가능한 도구 선택 */}
        {canModifyTools ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">사용 가능한 도구</label>
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
            </div>

            {!useDefaultTools && (
              <div className="border rounded-md p-3 space-y-2">
                {tools.length === 0 ? (
                  <div className="text-sm text-muted-foreground">도구 로딩 중...</div>
                ) : (
                  tools.map((tool) => (
                    <label
                      key={tool.name}
                      className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
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
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {tool.description} · {tool.category}
                        </div>
                      </div>
                    </label>
                  ))
                )}
              </div>
            )}

            <p className="text-xs text-muted-foreground">
              {useDefaultTools
                ? 'agent_config.json의 기본 도구 설정을 사용합니다.'
                : `선택된 도구: ${allowedTools.length}개`}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <label className="text-sm font-medium">사용 가능한 도구</label>
            <div className="border rounded-md p-3 bg-gray-50">
              <p className="text-sm text-muted-foreground mb-3">
                이 워커는 agent_config.json에 정의된 기본 도구만 사용합니다. (변경 불가)
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
          </div>
        )}

        {/* 노드 정보 */}
        <div className="border-t pt-4 space-y-2">
          <div className="text-xs text-muted-foreground">
            <div className="font-medium mb-1">노드 정보</div>
            <div>ID: {selectedNode.id}</div>
            <div>Agent: {selectedNode.data.agent_name}</div>
            <div>
              위치: ({Math.round(selectedNode.position.x)},{' '}
              {Math.round(selectedNode.position.y)})
            </div>
          </div>
        </div>
      </CardContent>

      {/* 저장/초기화 버튼 */}
      <div className="border-t p-4 space-y-2">
        {/* 저장 메시지 */}
        {saveMessage && (
          <div className="text-xs text-center py-1 px-2 rounded bg-gray-100">
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

        {hasChanges && (
          <div className="text-xs text-yellow-600 text-center">
            변경사항이 있습니다. 저장 버튼을 클릭하세요.
          </div>
        )}
      </div>
    </Card>
  )
}
