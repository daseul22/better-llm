/**
 * Condition 노드 설정 컴포넌트
 *
 * 조건 분기 노드의 설정을 관리합니다.
 */

import React, { useState } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { FileText, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { WorkflowNode } from '@/lib/api'
import { useNodeConfig } from './hooks/useNodeConfig'
import { useAutoSave } from './hooks/useAutoSave'
import { useWorkflowStore } from '@/stores/workflowStore'
import { ParsedContent } from '@/components/ParsedContent'
import { AutoScrollContainer } from '@/components/AutoScrollContainer'
import { FieldHint } from '@/components/ui/field-hint'

interface ConditionNodeConfigProps {
  node: WorkflowNode
}

interface ConditionNodeData {
  condition_type: string
  condition_value: string
  true_branch_id?: string
  false_branch_id?: string
  max_iterations?: number | null  // 반복 제한 (null이면 반복 안함)
}

export const ConditionNodeConfig: React.FC<ConditionNodeConfigProps> = ({ node }) => {
  const [activeTab, setActiveTab] = useState('settings')
  const [isExamplesOpen, setIsExamplesOpen] = useState(false)
  const nodeInputs = useWorkflowStore((state) => state.execution.nodeInputs)
  const nodeOutputs = useWorkflowStore((state) => state.execution.nodeOutputs)

  // 초기 데이터 설정
  const initialData: ConditionNodeData = {
    condition_type: node.data.condition_type || 'contains',
    condition_value: node.data.condition_value || '',
    true_branch_id: node.data.true_branch_id,
    false_branch_id: node.data.false_branch_id,
    max_iterations: node.data.max_iterations ?? null,
  }

  // 노드 설정 Hook
  const { data, setData, hasChanges, saveMessage, save, reset } = useNodeConfig<ConditionNodeData>({
    nodeId: node.id,
    initialData,
    onValidate: (data) => {
      const errors: Record<string, string> = {}

      if (!data.condition_value.trim()) {
        errors.condition_value = '조건 값을 입력하세요'
      }

      // 정규표현식 검증
      if (data.condition_type === 'regex') {
        try {
          new RegExp(data.condition_value)
        } catch (e) {
          errors.condition_value = '올바른 정규표현식을 입력하세요'
        }
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

  return (
    <div className="h-full flex flex-col">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="flex w-auto mx-3 mt-3 gap-1">
          <TabsTrigger value="settings" className="text-sm flex-1">
            설정
          </TabsTrigger>
          <TabsTrigger value="logs" className="text-sm flex-1">
            <FileText className="h-3 w-3 mr-1" />
            로그
          </TabsTrigger>
        </TabsList>

        {/* 설정 탭 */}
        <TabsContent value="settings" className="flex-1 overflow-y-auto px-3 pb-3 space-y-3 mt-3">
        {/* 조건 타입 선택 */}
        <div>
          <label className="block text-sm font-medium mb-2">
            조건 타입 <span className="text-red-500">*</span>
          </label>
          <select
            value={data.condition_type}
            onChange={(e) => setData({ ...data, condition_type: e.target.value })}
            onKeyDown={handleInputKeyDown}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <option value="contains">텍스트 포함</option>
            <option value="regex">정규표현식</option>
            <option value="length">길이 비교</option>
            <option value="custom">커스텀 조건</option>
            <option value="llm">LLM 판단 (Haiku)</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            {data.condition_type === 'contains' && '입력 텍스트에 특정 문자열이 포함되어 있는지 확인'}
            {data.condition_type === 'regex' && '정규표현식 패턴 매칭'}
            {data.condition_type === 'length' && '텍스트 길이 비교 (예: >100, <=500)'}
            {data.condition_type === 'custom' && 'Python 표현식 평가 (예: len(output) > 0)'}
            {data.condition_type === 'llm' && 'LLM(Haiku)이 출력을 분석하여 조건 만족 여부 판단'}
          </p>
        </div>

        {/* 조건 값 입력 */}
        <div>
          <label className="block text-sm font-medium mb-2">
            {data.condition_type === 'llm' ? 'LLM 판단 프롬프트' : '조건 값'} <span className="text-red-500">*</span>
          </label>
          {data.condition_type === 'llm' ? (
            <textarea
              value={data.condition_value}
              onChange={(e) => setData({ ...data, condition_value: e.target.value })}
              onKeyDown={handleInputKeyDown}
              placeholder="예: 테스트가 모두 통과했는지 확인"
              rows={3}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 text-sm resize-none"
            />
          ) : (
            <input
              type="text"
              value={data.condition_value}
              onChange={(e) => setData({ ...data, condition_value: e.target.value })}
              onKeyDown={handleInputKeyDown}
              placeholder={
                data.condition_type === 'contains' ? '예: success' :
                data.condition_type === 'regex' ? '예: \\d{3}' :
                data.condition_type === 'length' ? '예: >20' :
                '예: len(output) > 0'
              }
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 font-mono text-sm"
            />
          )}
          {data.condition_type === 'length' && (
            <p className="text-xs text-gray-500 mt-1">
              연산자 사용 가능: &gt;, &lt;, &gt;=, &lt;=, ==
            </p>
          )}
          {data.condition_type === 'llm' && (
            <p className="text-xs text-gray-500 mt-1">
              LLM이 이전 노드의 출력을 분석하여 YES/NO로 판단합니다
            </p>
          )}
        </div>

        {/* 반복 제한 설정 */}
        <div className="border-t pt-4">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium">
              반복 제한 (피드백 루프 방지)
            </label>
            <input
              type="checkbox"
              checked={data.max_iterations !== null}
              onChange={(e) => {
                setData({ ...data, max_iterations: e.target.checked ? 3 : null })
              }}
              className="h-4 w-4 text-amber-600 focus:ring-amber-500 border-gray-300 rounded"
            />
          </div>
          {data.max_iterations !== null && (
            <div>
              <input
                type="number"
                min={1}
                max={20}
                value={data.max_iterations || 3}
                onChange={(e) => setData({ ...data, max_iterations: parseInt(e.target.value) || 3 })}
                onKeyDown={handleInputKeyDown}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                이 Condition 노드가 순환 경로에 있을 때 최대 {data.max_iterations}회까지 반복합니다.
                반복 횟수 초과 시 자동으로 true 경로로 이동합니다.
              </p>
            </div>
          )}
          {data.max_iterations === null && (
            <p className="text-xs text-gray-500">
              체크박스를 활성화하면 피드백 루프에서 최대 반복 횟수를 제한할 수 있습니다.
            </p>
          )}
        </div>

        <FieldHint
          hint="💡 True(왼쪽 초록) / False(오른쪽 빨강) 핸들로 연결"
          tooltip="True 경로: 왼쪽 초록색 핸들 | False 경로: 오른쪽 빨간색 핸들"
        />

        {/* 예시 (Collapsible) */}
        <Collapsible open={isExamplesOpen} onOpenChange={setIsExamplesOpen}>
          <CollapsibleTrigger className="text-xs text-blue-600 hover:underline flex items-center gap-1">
            📝 예시 보기
            <ChevronDown className={cn("h-3 w-3 transition-transform", isExamplesOpen && "rotate-180")} />
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 text-xs space-y-1 bg-gray-50 border rounded p-2">
            <div><strong>텍스트 포함:</strong> <code>"success"</code> → 출력에 "success" 포함 시 True</div>
            <div><strong>길이 비교:</strong> <code>"&gt;20"</code> → 출력 길이 20자 이상 시 True</div>
          </CollapsibleContent>
        </Collapsible>
        </TabsContent>

        {/* 로그 탭 */}
        <TabsContent value="logs" className="flex-1 overflow-y-auto px-3 pb-3 space-y-3 mt-3">
          <div className="space-y-3">

            {/* 노드 입력 */}
            <div className="border rounded-md overflow-hidden">
              <div className="bg-muted px-3 py-2 border-b">
                <div className="text-sm font-medium">노드 입력</div>
                <div className="text-xs text-muted-foreground">이 노드가 받은 입력 데이터 (부모 노드 출력)</div>
              </div>
              <div className="p-3">
                <AutoScrollContainer maxHeight="400px" dependency={nodeInputs[node.id]}>
                  <ParsedContent content={nodeInputs[node.id] || ''} />
                </AutoScrollContainer>
              </div>
            </div>

            {/* 노드 출력 */}
            <div className="border rounded-md overflow-hidden">
              <div className="bg-muted px-3 py-2 border-b">
                <div className="text-sm font-medium">노드 출력</div>
                <div className="text-xs text-muted-foreground">조건 평가 결과 (True/False 분기 정보)</div>
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
    </div>
  )
}
