/**
 * 노드 설정 패널 컴포넌트
 *
 * 선택된 노드의 상세 설정을 표시하고 편집합니다.
 * - 기본 프롬프트 (task_template)
 * - Output 형식
 * - 추가 설정 (config)
 */

import React, { useEffect, useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useWorkflowStore } from '@/stores/workflowStore'
import { getAgents, Agent } from '@/lib/api'
import { Save } from 'lucide-react'

export const NodeConfigPanel: React.FC = () => {
  const selectedNodeId = useWorkflowStore((state) => state.selectedNodeId)
  const getSelectedNode = useWorkflowStore((state) => state.getSelectedNode)
  const updateNode = useWorkflowStore((state) => state.updateNode)

  const selectedNode = getSelectedNode()

  // 로컬 상태 (편집 중인 값)
  const [taskTemplate, setTaskTemplate] = useState('')
  const [outputFormat, setOutputFormat] = useState('plain_text')
  const [customPrompt, setCustomPrompt] = useState('')
  const [hasChanges, setHasChanges] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  // Agent 목록 및 시스템 프롬프트
  const [agents, setAgents] = useState<Agent[]>([])
  const [systemPrompt, setSystemPrompt] = useState('')

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

  // 선택된 노드가 변경되면 로컬 상태 초기화
  useEffect(() => {
    if (selectedNode) {
      console.log('[NodeConfigPanel] 노드 선택:', selectedNode.data.agent_name)
      console.log('[NodeConfigPanel] agents 배열 길이:', agents.length)

      setTaskTemplate(selectedNode.data.task_template || '')
      setOutputFormat(selectedNode.data.config?.output_format || 'plain_text')
      setCustomPrompt(selectedNode.data.config?.custom_prompt || '')
      setHasChanges(false)

      // 시스템 프롬프트 가져오기
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
    }
  }, [selectedNode, agents])

  // 변경사항 추적
  useEffect(() => {
    if (!selectedNode) return

    const changed =
      taskTemplate !== (selectedNode.data.task_template || '') ||
      outputFormat !== (selectedNode.data.config?.output_format || 'plain_text') ||
      customPrompt !== (selectedNode.data.config?.custom_prompt || '')

    setHasChanges(changed)
  }, [taskTemplate, outputFormat, customPrompt, selectedNode])

  // 저장
  const handleSave = () => {
    if (!selectedNodeId) return

    try {
      updateNode(selectedNodeId, {
        task_template: taskTemplate,
        config: {
          ...selectedNode?.data.config,
          output_format: outputFormat,
          custom_prompt: customPrompt,
        },
      })

      setHasChanges(false)
      setSaveMessage('✅ 저장됨 (자동 저장 대기 중...)')

      console.log('💾 노드 설정 저장:', {
        nodeId: selectedNodeId,
        agent: selectedNode?.data.agent_name,
        taskTemplate: taskTemplate.substring(0, 50),
        outputFormat,
        hasCustomPrompt: !!customPrompt,
      })

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

    setTaskTemplate(selectedNode.data.task_template || '')
    setOutputFormat(selectedNode.data.config?.output_format || 'plain_text')
    setCustomPrompt(selectedNode.data.config?.custom_prompt || '')
    setHasChanges(false)
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

  return (
    <Card className="h-full overflow-hidden flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">노드 설정</CardTitle>
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
