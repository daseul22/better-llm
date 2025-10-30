/**
 * Merge 노드 설정 컴포넌트
 *
 * 병합 노드의 설정을 관리합니다.
 */

import React, { useState } from 'react'
import { CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Merge, Save, RotateCcw, FileText, Maximize2 } from 'lucide-react'
import { WorkflowNode } from '@/lib/api'
import { useNodeConfig } from './hooks/useNodeConfig'
import { useAutoSave } from './hooks/useAutoSave'
import { useWorkflowStore } from '@/stores/workflowStore'
import { ParsedContent } from '@/components/ParsedContent'
import { AutoScrollContainer } from '@/components/AutoScrollContainer'
import { LogDetailModal } from '@/components/LogDetailModal'

interface MergeNodeConfigProps {
  node: WorkflowNode
}

interface MergeNodeData {
  merge_strategy: string
  separator: string
  custom_template?: string
}

export const MergeNodeConfig: React.FC<MergeNodeConfigProps> = ({ node }) => {
  const [activeTab, setActiveTab] = useState('basic')
  const [isLogDetailOpen, setIsLogDetailOpen] = useState(false)
  const nodeInputs = useWorkflowStore((state) => state.execution.nodeInputs)
  const nodeOutputs = useWorkflowStore((state) => state.execution.nodeOutputs)

  // 초기 데이터 설정
  const initialData: MergeNodeData = {
    merge_strategy: node.data.merge_strategy || 'concatenate',
    separator: node.data.separator || '\n\n---\n\n',
    custom_template: node.data.custom_template || '',
  }

  // 노드 설정 Hook
  const { data, setData, hasChanges, saveMessage, save, reset } = useNodeConfig<MergeNodeData>({
    nodeId: node.id,
    initialData,
    onValidate: (data) => {
      const errors: Record<string, string> = {}

      if (!data.separator && data.merge_strategy === 'concatenate') {
        errors.separator = '구분자를 입력하세요'
      }

      if (data.merge_strategy === 'custom' && !data.custom_template?.trim()) {
        errors.custom_template = '커스텀 템플릿을 입력하세요'
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

  // 입력 필드에서 키 이벤트 전파 방지
  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    e.stopPropagation()
  }

  // 로그 상세 모달용 sections 생성 (Merge 노드 + 부모 노드들)
  const edges = useWorkflowStore((state) => state.edges)
  const nodes = useWorkflowStore((state) => state.nodes)
  const logs = useWorkflowStore((state) => state.execution.logs)

  const logSections = React.useMemo(() => {
    const sections = []

    // Merge 노드 자체 로그
    const mergeLogs = logs.filter(log => log.nodeId === node.id)
    if (mergeLogs.length > 0) {
      sections.push({
        nodeId: node.id,
        nodeName: `Merge (${node.id.substring(0, 8)})`,
        logs: mergeLogs
      })
    }

    // 부모 노드들의 로그
    const parentEdges = edges.filter(e => e.target === node.id)
    parentEdges.forEach(edge => {
      const parentNode = nodes.find(n => n.id === edge.source)
      const parentLogs = logs.filter(log => log.nodeId === edge.source)

      if (parentLogs.length > 0) {
        const nodeName = parentNode?.type === 'worker'
          ? (parentNode.data.agent_name || 'Worker')
          : (parentNode?.type === 'input' ? 'Input' : parentNode?.type || 'Unknown')

        sections.push({
          nodeId: edge.source,
          nodeName: `${nodeName} (${edge.source.substring(0, 8)})`,
          logs: parentLogs
        })
      }
    })

    return sections
  }, [logs, node.id, edges, nodes])

  return (
    <div className="h-full flex flex-col">
      <CardHeader className="pb-4 border-b">
        <CardTitle className="text-lg flex items-center gap-2">
          <Merge className="h-5 w-5 text-indigo-600" />
          병합 노드 설정
        </CardTitle>
      </CardHeader>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center gap-2 mx-4 mt-4">
          <TabsList className="flex w-auto gap-1 flex-1">
            <TabsTrigger value="basic" className="text-xs flex-1 min-w-0">
              기본
            </TabsTrigger>
            <TabsTrigger value="logs" className="text-xs flex-1 min-w-0">
              <FileText className="h-3 w-3 mr-1" />
              로그
            </TabsTrigger>
          </TabsList>
          {activeTab === 'logs' && (
            <button
              onClick={() => setIsLogDetailOpen(true)}
              className="flex items-center gap-1 px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
              title="로그 상세 보기"
            >
              <Maximize2 className="w-3 h-3" />
              상세
            </button>
          )}
        </div>

        {/* 기본 설정 탭 */}
        <TabsContent value="basic" className="flex-1 overflow-y-auto px-4 pb-4 space-y-4 mt-4">
        {/* 병합 전략 선택 */}
        <div>
          <label className="block text-sm font-medium mb-2">
            병합 전략 <span className="text-red-500">*</span>
          </label>
          <select
            value={data.merge_strategy}
            onChange={(e) => setData({ ...data, merge_strategy: e.target.value })}
            onKeyDown={handleInputKeyDown}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="concatenate">연결 (Concatenate)</option>
            <option value="first">첫 번째만</option>
            <option value="last">마지막만</option>
            <option value="custom">커스텀 템플릿</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            {data.merge_strategy === 'concatenate' && '모든 입력을 구분자로 연결합니다'}
            {data.merge_strategy === 'first' && '첫 번째 입력만 사용합니다'}
            {data.merge_strategy === 'last' && '마지막 입력만 사용합니다'}
            {data.merge_strategy === 'custom' && '커스텀 템플릿으로 입력을 결합합니다'}
          </p>
        </div>

        {/* 구분자 (concatenate 전략일 때만) */}
        {data.merge_strategy === 'concatenate' && (
          <div>
            <label className="block text-sm font-medium mb-2">
              구분자 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={data.separator}
              onChange={(e) => setData({ ...data, separator: e.target.value })}
              onKeyDown={handleInputKeyDown}
              placeholder="예: \n\n---\n\n"
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              입력들을 구분할 문자열 (\n은 줄바꿈)
            </p>
          </div>
        )}

        {/* 커스텀 템플릿 (custom 전략일 때만) */}
        {data.merge_strategy === 'custom' && (
          <div>
            <label className="block text-sm font-medium mb-2">
              커스텀 템플릿 <span className="text-red-500">*</span>
            </label>
            <textarea
              value={data.custom_template}
              onChange={(e) => setData({ ...data, custom_template: e.target.value })}
              onKeyDown={handleInputKeyDown}
              placeholder="예: 입력1: {input1}\n입력2: {input2}"
              rows={4}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm resize-none"
            />
            <p className="text-xs text-gray-500 mt-1">
              {'{input1}'}, {'{input2}'} 등의 변수로 입력을 참조
            </p>
          </div>
        )}

        {/* 병합 대상 안내 */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-blue-700 font-medium mb-2">💡 병합 동작</p>
          <ul className="text-xs text-blue-600 space-y-1">
            <li>• Merge 노드는 <strong>여러 부모 노드</strong>의 출력을 하나로 합칩니다</li>
            <li>• 조건 분기(Condition)나 병렬 실행 후 결과를 통합할 때 사용</li>
            <li>• 병합된 결과는 다음 노드로 전달됩니다</li>
          </ul>
        </div>

        {/* 예시 */}
        <div className="bg-gray-50 border rounded-lg p-3">
          <p className="text-sm font-medium mb-2">📝 예시</p>
          <div className="space-y-2 text-xs">
            <div>
              <p className="font-medium">연결 (Concatenate):</p>
              <code className="bg-white px-2 py-1 rounded block mt-1">
                입력1의 결과
                <br />
                ---
                <br />
                입력2의 결과
              </code>
            </div>
            <div>
              <p className="font-medium">커스텀 템플릿:</p>
              <code className="bg-white px-2 py-1 rounded block mt-1">
                ## True 경로
                <br />
                {'{input1}'}
                <br />
                <br />
                ## False 경로
                <br />
                {'{input2}'}
              </code>
            </div>
          </div>
        </div>

        {/* 사용 시나리오 */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <p className="text-sm text-green-700 font-medium mb-2">✅ 사용 시나리오</p>
          <ul className="text-xs text-green-600 space-y-1">
            <li>• <strong>조건 분기 통합:</strong> Condition 노드의 True/False 경로 결과 합치기</li>
            <li>• <strong>병렬 작업 통합:</strong> 여러 Worker가 독립적으로 작업한 결과 결합</li>
            <li>• <strong>반복 결과 수집:</strong> Loop 노드의 각 반복 결과를 모으기</li>
          </ul>
        </div>
        </TabsContent>

        {/* 로그 탭 */}
        <TabsContent value="logs" className="flex-1 overflow-y-auto px-4 pb-4 space-y-4 mt-4">
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
              이 노드의 입력과 출력을 확인할 수 있습니다 (디버깅용)
            </div>

            {/* 노드 입력 */}
            <div className="border rounded-md overflow-hidden">
              <div className="bg-blue-50 px-3 py-2 border-b">
                <div className="text-sm font-medium text-blue-900">노드 입력</div>
                <div className="text-xs text-blue-700">이 노드가 받은 입력 데이터 (모든 부모 노드 출력)</div>
              </div>
              <div className="p-3">
                <AutoScrollContainer maxHeight="400px" dependency={nodeInputs[node.id]}>
                  <ParsedContent content={nodeInputs[node.id] || ''} />
                </AutoScrollContainer>
              </div>
            </div>

            {/* 노드 출력 */}
            <div className="border rounded-md overflow-hidden">
              <div className="bg-green-50 px-3 py-2 border-b">
                <div className="text-sm font-medium text-green-900">노드 출력</div>
                <div className="text-xs text-green-700">병합된 결과 (전략에 따라 처리됨)</div>
              </div>
              <div className="p-3">
                <AutoScrollContainer maxHeight="400px" dependency={nodeOutputs[node.id]}>
                  <ParsedContent content={nodeOutputs[node.id] || ''} />
                </AutoScrollContainer>
              </div>
            </div>

            {/* 통계 정보 */}
            <div className="border rounded-md p-3 bg-purple-50 border-purple-200">
              <div className="text-sm font-medium mb-2 text-purple-900">통계</div>
              <div className="space-y-1 text-xs text-purple-800">
                <div>
                  <span className="font-medium">입력 길이:</span>{' '}
                  {nodeInputs[node.id] ? `${nodeInputs[node.id].length.toLocaleString()}자` : '0자'}
                </div>
                <div>
                  <span className="font-medium">출력 길이:</span>{' '}
                  {nodeOutputs[node.id] ? `${nodeOutputs[node.id].length.toLocaleString()}자` : '0자'}
                </div>
                <div>
                  <span className="font-medium">상태:</span>{' '}
                  {nodeOutputs[node.id] ? (
                    <span className="text-green-600 font-medium">✓ 완료</span>
                  ) : nodeInputs[node.id] ? (
                    <span className="text-yellow-600 font-medium">⏳ 진행중</span>
                  ) : (
                    <span className="text-gray-500">⏸ 대기중</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* 저장 버튼 */}
      <div className="border-t p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {saveMessage && (
            <span className="text-sm text-green-600 flex items-center gap-1">
              <Save className="h-4 w-4" />
              {saveMessage}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={reset}
            disabled={!hasChanges}
          >
            <RotateCcw className="h-4 w-4 mr-1" />
            초기화
          </Button>
          <Button
            size="sm"
            onClick={save}
            disabled={!hasChanges}
            className="bg-indigo-600 hover:bg-indigo-700"
          >
            <Save className="h-4 w-4 mr-1" />
            저장
          </Button>
        </div>
      </div>

      {/* 로그 상세 모달 */}
      <LogDetailModal
        isOpen={isLogDetailOpen}
        onClose={() => setIsLogDetailOpen(false)}
        sections={logSections}
        title="Merge 노드 실행 로그 상세"
      />
    </div>
  )
}
