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

interface InputNodeConfigProps {
  node: WorkflowNode
}

interface InputNodeData {
  initial_input: string
}

export const InputNodeConfig: React.FC<InputNodeConfigProps> = ({ node }) => {
  const [activeTab, setActiveTab] = useState('basic')

  // 노드 설정 Hook 사용
  const { data, setData, hasChanges, saveMessage, save, reset } = useNodeConfig<InputNodeData>({
    nodeId: node.id,
    initialData: {
      initial_input: node.data.initial_input || '',
    },
    onValidate: (data) => {
      const errors: Record<string, string> = {}
      if (!data.initial_input.trim()) {
        errors.initial_input = '초기 입력을 입력하세요'
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
                placeholder="워크플로우 초기 입력을 입력하세요...&#10;예시:&#10;- 새로운 기능 추가&#10;- 버그 수정&#10;- 코드 리뷰"
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
