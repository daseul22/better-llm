/**
 * Loop 노드 설정 컴포넌트
 *
 * 반복 노드의 설정을 관리합니다.
 */

import React, { useState } from 'react'
import { CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { RotateCw, Save, RotateCcw, FileText } from 'lucide-react'
import { WorkflowNode } from '@/lib/api'
import { useNodeConfig } from './hooks/useNodeConfig'
import { useAutoSave } from './hooks/useAutoSave'
import { useWorkflowStore } from '@/stores/workflowStore'
import { ParsedContent } from '@/components/ParsedContent'
import { AutoScrollContainer } from '@/components/AutoScrollContainer'

interface LoopNodeConfigProps {
  node: WorkflowNode
}

interface LoopNodeData {
  max_iterations: number
  loop_condition: string
  loop_condition_type: string
}

export const LoopNodeConfig: React.FC<LoopNodeConfigProps> = ({ node }) => {
  const [activeTab, setActiveTab] = useState('basic')
  const nodeInputs = useWorkflowStore((state) => state.execution.nodeInputs)
  const nodeOutputs = useWorkflowStore((state) => state.execution.nodeOutputs)

  // 초기 데이터 설정
  const initialData: LoopNodeData = {
    max_iterations: node.data.max_iterations || 5,
    loop_condition: node.data.loop_condition || '',
    loop_condition_type: node.data.loop_condition_type || 'contains',
  }

  // 노드 설정 Hook
  const { data, setData, hasChanges, saveMessage, save, reset } = useNodeConfig<LoopNodeData>({
    nodeId: node.id,
    initialData,
    onValidate: (data) => {
      const errors: Record<string, string> = {}

      if (data.max_iterations < 1) {
        errors.max_iterations = '최대 반복 횟수는 1 이상이어야 합니다'
      }

      if (data.max_iterations > 100) {
        errors.max_iterations = '최대 반복 횟수는 100 이하여야 합니다'
      }

      if (!data.loop_condition.trim()) {
        errors.loop_condition = '종료 조건을 입력하세요'
      }

      // 정규표현식 검증
      if (data.loop_condition_type === 'regex') {
        try {
          new RegExp(data.loop_condition)
        } catch (e) {
          errors.loop_condition = '올바른 정규표현식을 입력하세요'
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
          <RotateCw className="h-5 w-5 text-teal-600" />
          반복 노드 설정
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
        {/* 최대 반복 횟수 */}
        <div>
          <label className="block text-sm font-medium mb-2">
            최대 반복 횟수 <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            min="1"
            max="100"
            value={data.max_iterations}
            onChange={(e) => setData({ ...data, max_iterations: parseInt(e.target.value) || 1 })}
            onKeyDown={handleInputKeyDown}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            무한 루프 방지를 위한 최대 반복 횟수 (1~100)
          </p>
        </div>

        {/* 종료 조건 타입 */}
        <div>
          <label className="block text-sm font-medium mb-2">
            종료 조건 타입 <span className="text-red-500">*</span>
          </label>
          <select
            value={data.loop_condition_type}
            onChange={(e) => setData({ ...data, loop_condition_type: e.target.value })}
            onKeyDown={handleInputKeyDown}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value="contains">텍스트 포함</option>
            <option value="regex">정규표현식</option>
            <option value="custom">커스텀 조건</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            {data.loop_condition_type === 'contains' && '출력에 특정 문자열이 포함되면 반복 종료'}
            {data.loop_condition_type === 'regex' && '정규표현식 패턴 매칭 시 반복 종료'}
            {data.loop_condition_type === 'custom' && 'Python 표현식이 True이면 반복 종료'}
          </p>
        </div>

        {/* 종료 조건 값 */}
        <div>
          <label className="block text-sm font-medium mb-2">
            종료 조건 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={data.loop_condition}
            onChange={(e) => setData({ ...data, loop_condition: e.target.value })}
            onKeyDown={handleInputKeyDown}
            placeholder={
              data.loop_condition_type === 'contains' ? '예: 완료' :
              data.loop_condition_type === 'regex' ? '예: .*완료.*' :
              '예: "완료" in output'
            }
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono text-sm"
          />
          <p className="text-xs text-gray-500 mt-1">
            이 조건이 만족되면 반복을 종료합니다
          </p>
        </div>

        {/* 반복 대상 안내 */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-blue-700 font-medium mb-2">💡 반복 실행</p>
          <ul className="text-xs text-blue-600 space-y-1">
            <li>• Loop 노드의 <strong>출력 핸들(아래)</strong>에 연결된 노드를 반복 실행</li>
            <li>• 현재는 <strong>Worker 노드만</strong> 반복 실행 가능</li>
            <li>• 각 반복마다 이전 결과가 다음 반복의 입력으로 전달됩니다</li>
          </ul>
        </div>

        {/* 예시 */}
        <div className="bg-gray-50 border rounded-lg p-3">
          <p className="text-sm font-medium mb-2">📝 예시</p>
          <div className="space-y-2 text-xs">
            <div>
              <p className="font-medium">텍스트 포함:</p>
              <code className="bg-white px-2 py-1 rounded">loop_condition = "완료"</code>
              <p className="text-gray-600">→ 출력에 "완료"가 나타날 때까지 반복</p>
            </div>
            <div>
              <p className="font-medium">정규표현식:</p>
              <code className="bg-white px-2 py-1 rounded">loop_condition = "테스트.*통과"</code>
              <p className="text-gray-600">→ "테스트...통과" 패턴이 나타날 때까지 반복</p>
            </div>
          </div>
        </div>

        {/* 경고 */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <p className="text-sm text-yellow-700 font-medium mb-1">⚠️ 주의사항</p>
          <ul className="text-xs text-yellow-600 space-y-1">
            <li>• 종료 조건이 만족되지 않으면 최대 반복 횟수까지 실행됩니다</li>
            <li>• 각 반복은 LLM API를 호출하므로 비용이 발생합니다</li>
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
                <div className="text-xs text-green-700">모든 반복 결과 통합</div>
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
            className="bg-teal-600 hover:bg-teal-700"
          >
            <Save className="h-4 w-4 mr-1" />
            저장
          </Button>
        </div>
      </div>
    </div>
  )
}
