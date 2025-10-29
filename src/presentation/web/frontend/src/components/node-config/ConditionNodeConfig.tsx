/**
 * Condition 노드 설정 컴포넌트
 *
 * 조건 분기 노드의 설정을 관리합니다.
 */

import React, { useState } from 'react'
import { CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { GitBranch, Save, RotateCcw, FileText } from 'lucide-react'
import { WorkflowNode } from '@/lib/api'
import { useNodeConfig } from './hooks/useNodeConfig'
import { useAutoSave } from './hooks/useAutoSave'
import { useWorkflowStore } from '@/stores/workflowStore'
import { ParsedContent } from '@/components/ParsedContent'
import { AutoScrollContainer } from '@/components/AutoScrollContainer'

interface ConditionNodeConfigProps {
  node: WorkflowNode
}

interface ConditionNodeData {
  condition_type: string
  condition_value: string
  true_branch_id?: string
  false_branch_id?: string
}

export const ConditionNodeConfig: React.FC<ConditionNodeConfigProps> = ({ node }) => {
  const [activeTab, setActiveTab] = useState('basic')
  const nodeInputs = useWorkflowStore((state) => state.execution.nodeInputs)
  const nodeOutputs = useWorkflowStore((state) => state.execution.nodeOutputs)

  // 초기 데이터 설정
  const initialData: ConditionNodeData = {
    condition_type: node.data.condition_type || 'contains',
    condition_value: node.data.condition_value || '',
    true_branch_id: node.data.true_branch_id,
    false_branch_id: node.data.false_branch_id,
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
      <CardHeader className="pb-4 border-b">
        <CardTitle className="text-lg flex items-center gap-2">
          <GitBranch className="h-5 w-5 text-amber-600" />
          조건 분기 노드 설정
        </CardTitle>
      </CardHeader>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="flex w-auto mx-4 mt-4 gap-1">
          <TabsTrigger value="basic" className="text-xs flex-1 min-w-0">
            기본
          </TabsTrigger>
          <TabsTrigger value="logs" className="text-xs flex-1 min-w-0">
            <FileText className="h-3 w-3 mr-1" />
            로그
          </TabsTrigger>
        </TabsList>

        {/* 기본 설정 탭 */}
        <TabsContent value="basic" className="flex-1 overflow-y-auto px-4 pb-4 space-y-4 mt-4">
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
          </select>
          <p className="text-xs text-gray-500 mt-1">
            {data.condition_type === 'contains' && '입력 텍스트에 특정 문자열이 포함되어 있는지 확인'}
            {data.condition_type === 'regex' && '정규표현식 패턴 매칭'}
            {data.condition_type === 'length' && '텍스트 길이 비교 (예: >100, <=500)'}
            {data.condition_type === 'custom' && 'Python 표현식 평가 (예: len(output) > 0)'}
          </p>
        </div>

        {/* 조건 값 입력 */}
        <div>
          <label className="block text-sm font-medium mb-2">
            조건 값 <span className="text-red-500">*</span>
          </label>
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
          {data.condition_type === 'length' && (
            <p className="text-xs text-gray-500 mt-1">
              연산자 사용 가능: &gt;, &lt;, &gt;=, &lt;=, ==
            </p>
          )}
        </div>

        {/* 분기 경로 안내 */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-blue-700 font-medium mb-2">💡 분기 경로 설정</p>
          <ul className="text-xs text-blue-600 space-y-1">
            <li>• <strong>True 경로:</strong> 왼쪽 초록색 핸들에서 드래그하여 연결</li>
            <li>• <strong>False 경로:</strong> 오른쪽 빨간색 핸들에서 드래그하여 연결</li>
            <li>• 각 경로는 엣지의 sourceHandle로 자동 구분됩니다</li>
          </ul>
        </div>

        {/* 예시 */}
        <div className="bg-gray-50 border rounded-lg p-3">
          <p className="text-sm font-medium mb-2">📝 예시</p>
          <div className="space-y-2 text-xs">
            <div>
              <p className="font-medium">텍스트 포함:</p>
              <code className="bg-white px-2 py-1 rounded">condition_value = "success"</code>
              <p className="text-gray-600">→ 출력에 "success"가 포함되면 True</p>
            </div>
            <div>
              <p className="font-medium">길이 비교:</p>
              <code className="bg-white px-2 py-1 rounded">condition_value = "&gt;20"</code>
              <p className="text-gray-600">→ 출력 길이가 20자 이상이면 True</p>
            </div>
          </div>
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
                <div className="text-xs text-blue-700">이 노드가 받은 입력 데이터 (부모 노드 출력)</div>
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
                <div className="text-xs text-green-700">조건 평가 결과 (True/False 분기 정보)</div>
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
            className="bg-amber-600 hover:bg-amber-700"
          >
            <Save className="h-4 w-4 mr-1" />
            저장
          </Button>
        </div>
      </div>
    </div>
  )
}
