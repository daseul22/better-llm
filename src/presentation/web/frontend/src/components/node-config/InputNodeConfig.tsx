/**
 * Input 노드 설정 컴포넌트
 *
 * 워크플로우 시작점인 Input 노드의 설정을 관리합니다.
 */

import React, { useState } from 'react'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { useWorkflowStore } from '@/stores/workflowStore'
import { Terminal, HelpCircle, CheckCircle2, Save } from 'lucide-react'
import { WorkflowNode } from '@/lib/api'
import { useNodeConfig } from './hooks/useNodeConfig'
import { useAutoSave } from './hooks/useAutoSave'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import { ParsedContent } from '@/components/ParsedContent'
import { AutoScrollContainer } from '@/components/AutoScrollContainer'

interface InputNodeConfigProps {
  node: WorkflowNode
}

interface InputNodeData {
  initial_input: string
  parallel_execution?: boolean
}

/**
 * 노드별 실행 로그 컴포넌트 (WorkerNodeConfig 스타일)
 */
const NodeExecutionLogs: React.FC = () => {
  const nodes = useWorkflowStore((state) => state.nodes)
  const nodeInputs = useWorkflowStore((state) => state.execution.nodeInputs)
  const nodeOutputs = useWorkflowStore((state) => state.execution.nodeOutputs)
  const { isExecuting, totalTokenUsage } = useWorkflowStore((state) => state.execution)

  // 실행된 노드들만 필터링
  const executedNodes = nodes.filter(
    (node) => nodeInputs[node.id] || nodeOutputs[node.id]
  )

  return (
    <div className="space-y-4">
      {/* 실행 상태 및 토큰 사용량 */}
      <div className="bg-gray-50 border rounded-md p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-medium">실행 상태</div>
          {isExecuting ? (
            <div className="flex items-center gap-1.5 text-yellow-600">
              <span className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></span>
              <span className="text-xs">실행 중...</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-gray-600">
              <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
              <span className="text-xs">대기 중</span>
            </div>
          )}
        </div>

        {/* 토큰 사용량 */}
        {totalTokenUsage.total_tokens > 0 && (
          <div className="text-xs text-muted-foreground space-y-0.5 border-t pt-2">
            <div className="flex items-center justify-between">
              <span>입력 토큰:</span>
              <span className="font-mono">{totalTokenUsage.input_tokens.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>출력 토큰:</span>
              <span className="font-mono">{totalTokenUsage.output_tokens.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between font-medium text-gray-900 border-t pt-0.5 mt-0.5">
              <span>총합:</span>
              <span className="font-mono">{totalTokenUsage.total_tokens.toLocaleString()}</span>
            </div>
          </div>
        )}
      </div>

      {/* 노드별 입출력 표시 */}
      {executedNodes.length === 0 ? (
        <div className="bg-gray-50 border rounded-md p-6 text-center">
          <Terminal className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
          <div className="text-sm text-muted-foreground">워크플로우를 실행하면 노드별 입출력이 표시됩니다</div>
        </div>
      ) : (
        <div className="space-y-4">
          {executedNodes.map((execNode) => (
            <div key={execNode.id} className="space-y-3 border rounded-lg p-3 bg-white">
              {/* 노드 헤더 */}
              <div className="flex items-center justify-between border-b pb-2">
                <div className="font-medium text-sm">
                  {execNode.type === 'input' && '📥 Input'}
                  {execNode.type === 'worker' && `🤖 ${execNode.data.agent_name || 'Worker'}`}
                  {execNode.type === 'manager' && '👔 Manager'}
                  {execNode.type === 'condition' && '🔀 Condition'}
                  {execNode.type === 'loop' && '🔁 Loop'}
                  {execNode.type === 'merge' && '🔗 Merge'}
                </div>
                <div className="text-xs text-muted-foreground font-mono">
                  {execNode.id.substring(0, 8)}
                </div>
              </div>

              {/* 노드 입력 */}
              {nodeInputs[execNode.id] && (
                <div className="border rounded-md overflow-hidden">
                  <div className="bg-blue-50 px-3 py-2 border-b">
                    <div className="text-sm font-medium text-blue-900">노드 입력</div>
                    <div className="text-xs text-blue-700">이 노드가 받은 입력 데이터</div>
                  </div>
                  <div className="p-3">
                    <AutoScrollContainer maxHeight="300px" dependency={nodeInputs[execNode.id]}>
                      <ParsedContent content={nodeInputs[execNode.id]} />
                    </AutoScrollContainer>
                  </div>
                </div>
              )}

              {/* 노드 출력 */}
              {nodeOutputs[execNode.id] && (
                <div className="border rounded-md overflow-hidden">
                  <div className="bg-green-50 px-3 py-2 border-b">
                    <div className="text-sm font-medium text-green-900">노드 출력</div>
                    <div className="text-xs text-green-700">이 노드가 생성한 출력 데이터</div>
                  </div>
                  <div className="p-3">
                    <AutoScrollContainer maxHeight="300px" dependency={nodeOutputs[execNode.id]}>
                      <ParsedContent content={nodeOutputs[execNode.id]} />
                    </AutoScrollContainer>
                  </div>
                </div>
              )}

              {/* 통계 정보 */}
              <div className="border rounded-md p-3 bg-purple-50 border-purple-200">
                <div className="text-sm font-medium mb-2 text-purple-900">통계</div>
                <div className="space-y-1 text-xs text-purple-800">
                  <div>
                    <span className="font-medium">입력 길이:</span>{' '}
                    {nodeInputs[execNode.id] ? `${nodeInputs[execNode.id].length.toLocaleString()}자` : '0자'}
                  </div>
                  <div>
                    <span className="font-medium">출력 길이:</span>{' '}
                    {nodeOutputs[execNode.id] ? `${nodeOutputs[execNode.id].length.toLocaleString()}자` : '0자'}
                  </div>
                  <div>
                    <span className="font-medium">상태:</span>{' '}
                    {nodeOutputs[execNode.id] ? (
                      <span className="text-green-600 font-medium">✓ 완료</span>
                    ) : nodeInputs[execNode.id] ? (
                      <span className="text-yellow-600 font-medium">⏳ 진행중</span>
                    ) : (
                      <span className="text-gray-500">⏸ 대기중</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export const InputNodeConfig: React.FC<InputNodeConfigProps> = ({ node }) => {
  const [activeTab, setActiveTab] = useState('basic')

  // 노드 설정 Hook 사용
  const { data, setData, hasChanges, saveMessage, save, reset } = useNodeConfig<InputNodeData>({
    nodeId: node.id,
    initialData: {
      initial_input: node.data.initial_input || '',
      parallel_execution: node.data.parallel_execution ?? false,
    },
    onValidate: (_data) => {
      const errors: Record<string, string> = {}
      // 빈 입력도 허용 (빈 문자열 전달 가능)
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
    },
  })

  // 입력 필드에서 키 이벤트 전파 방지 (노드 삭제 등 React Flow 기본 동작 방지)
  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    e.stopPropagation()
  }

  // 연결 상태 확인
  const edges = useWorkflowStore((state) => state.edges)
  const connectedEdges = edges.filter((e) => e.source === node.id)

  return (
    <Card className="h-full overflow-hidden flex flex-col border-0 shadow-none">
      <CardHeader className="pb-3 bg-gradient-to-r from-emerald-50 to-teal-50 border-b">
        <CardTitle className="text-lg flex items-center gap-2">
          <Terminal className="h-5 w-5 text-emerald-600" />
          Input 노드 설정
        </CardTitle>
        <div className="text-sm text-muted-foreground">워크플로우 시작점</div>
      </CardHeader>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
        {/* 탭 헤더 */}
        <TabsList className="flex w-auto mx-4 mt-4 gap-1">
          <TabsTrigger value="basic" className="text-xs flex-1 min-w-0">
            기본
          </TabsTrigger>
          <TabsTrigger value="logs" className="text-xs flex-1 min-w-0">
            실행 로그
          </TabsTrigger>
          <TabsTrigger value="info" className="text-xs flex-1 min-w-0">
            정보
          </TabsTrigger>
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
                value={data.initial_input}
                onChange={(e) => setData({ ...data, initial_input: e.target.value })}
                onKeyDown={handleInputKeyDown}
                placeholder="아키텍처 패턴 리뷰 해주세요"
              />
              <p className="text-xs text-muted-foreground">이 입력이 연결된 첫 번째 노드로 전달됩니다.</p>
            </div>

            {/* 미리보기 */}
            {data.initial_input.trim() && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-md p-3">
                <div className="text-xs font-medium text-emerald-900 mb-2">초기 입력 미리보기</div>
                <div className="text-sm text-gray-700 whitespace-pre-wrap bg-white p-3 rounded border">
                  {data.initial_input}
                </div>
                <div className="text-xs text-emerald-700 mt-2">글자 수: {data.initial_input.length}자</div>
              </div>
            )}

            {/* 연결 상태 */}
            <div className="bg-gray-50 border rounded-md p-3">
              <div className="text-xs font-medium mb-2">연결 상태</div>
              <div className="text-xs text-muted-foreground">
                {connectedEdges.length > 0 ? (
                  <div className="flex items-center gap-2 text-green-600">
                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                    <span>{connectedEdges.length}개 노드에 연결됨</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-yellow-600">
                    <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
                    <span>연결된 노드 없음 (실행 불가)</span>
                  </div>
                )}
              </div>
            </div>

            {/* 병렬 실행 옵션 */}
            <div className="space-y-2 border-t pt-4">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">병렬 실행</label>
                <span title="이 노드에서 여러 자식 노드로 연결된 경우, 자식 노드들을 병렬로 실행할지 순차적으로 실행할지 선택합니다">
                  <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
                </span>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={data.parallel_execution ?? false}
                  onChange={(e) => setData({ ...data, parallel_execution: e.target.checked })}
                  className="w-4 h-4"
                />
                <span>자식 노드들을 병렬로 실행</span>
              </label>
              <p className="text-xs text-muted-foreground">
                {data.parallel_execution
                  ? '✅ 이 노드의 자식 노드들이 동시에 실행되어 전체 실행 시간이 단축됩니다'
                  : '⚪ 자식 노드들이 순차적으로 실행됩니다'}
              </p>
            </div>
          </TabsContent>

          {/* 실행 로그 탭 */}
          <TabsContent value="logs" className="h-full overflow-y-auto px-4 pb-20 mt-4">
            <NodeExecutionLogs />
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
                <div className="mt-0.5 text-sm text-muted-foreground">Input (시작점)</div>
              </div>

              <div>
                <span className="font-medium">위치:</span>
                <div className="mt-0.5 text-sm text-muted-foreground">
                  ({Math.round(node.position.x)}, {Math.round(node.position.y)})
                </div>
              </div>

              <div>
                <span className="font-medium">입력 크기:</span>
                <div className="mt-0.5 text-sm text-muted-foreground">{data.initial_input.length}자</div>
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

        {/* 키보드 단축키 안내 */}
        <div className="text-xs text-muted-foreground text-center border-t pt-2">
          <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">⌘S</kbd> 저장 ·{' '}
          <kbd className="px-1.5 py-0.5 bg-gray-100 border rounded text-xs">Esc</kbd> 초기화
        </div>
      </div>
    </Card>
  )
}
