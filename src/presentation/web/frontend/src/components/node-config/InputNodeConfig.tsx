/**
 * Input 노드 설정 컴포넌트
 *
 * 워크플로우 시작점인 Input 노드의 설정을 관리합니다.
 */

import React, { useState, useMemo, useRef, useEffect } from 'react'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { useWorkflowStore } from '@/stores/workflowStore'
import { Terminal, HelpCircle, CheckCircle2, Save, ScrollText, ChevronDown, ChevronRight, Brain, ArrowDown } from 'lucide-react'
import { WorkflowNode } from '@/lib/api'
import { useNodeConfig } from './hooks/useNodeConfig'
import { useAutoSave } from './hooks/useAutoSave'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import { parseLogMessage } from '@/lib/logParser'

interface InputNodeConfigProps {
  node: WorkflowNode
}

interface InputNodeData {
  initial_input: string
  parallel_execution?: boolean
}

/**
 * 메시지에서 tool_use_id 추출
 */
function extractToolUseId(message: string): string | null {
  const match = message.match(/tool_use_id='([^']+)'/)
  return match ? match[1] : null
}

/**
 * 메시지에서 도구 이름 추출 (AssistantMessage의 ToolUseBlock)
 */
function extractToolName(message: string): { id: string; name: string } | null {
  // JSON 형식
  try {
    const data = JSON.parse(message)
    if (data.role === 'assistant' && Array.isArray(data.content)) {
      for (const block of data.content) {
        if (block.type === 'tool_use' && block.id && block.name) {
          return { id: block.id, name: block.name }
        }
      }
    }
  } catch (e) {
    // JSON이 아니면 무시
  }

  // Python repr 형식 1: ToolUseBlock(id='...', name='...', type='tool_use')
  const match1 = message.match(/ToolUseBlock\(id='([^']+)',\s*name='([^']+)'/)
  if (match1) {
    return { id: match1[1], name: match1[2] }
  }

  // Python repr 형식 2: 순서가 다른 경우
  const match2 = message.match(/ToolUseBlock\(.*?id='([^']+)'.*?name='([^']+)'/)
  if (match2) {
    return { id: match2[1], name: match2[2] }
  }

  return null
}

/**
 * 로그 목록에서 tool_use_id -> tool_name 매핑 테이블 생성
 */
function buildToolNameMap(logs: any[]): Map<string, string> {
  const map = new Map<string, string>()

  for (const log of logs) {
    const toolInfo = extractToolName(log.message)
    if (toolInfo) {
      map.set(toolInfo.id, toolInfo.name)
    }
  }

  return map
}

/**
 * 단일 로그 항목 컴포넌트
 */
const LogItem: React.FC<{ log: any; index: number; toolNameMap: Map<string, string> }> = ({ log, index, toolNameMap }) => {
  const [isToolExpanded, setIsToolExpanded] = useState(false)
  const parsed = parseLogMessage(log.message)

  // tool_result 타입인 경우 매핑 테이블에서 도구 이름 찾기
  if (parsed.type === 'tool_result' && parsed.toolUse) {
    const toolUseId = extractToolUseId(log.message)
    if (toolUseId && toolNameMap.has(toolUseId)) {
      parsed.toolUse.toolName = toolNameMap.get(toolUseId)!
    }
  }

  // 로그 타입별 스타일
  const getLogStyle = () => {
    if (log.type === 'error') return 'bg-red-50 border-red-200 text-red-900'
    if (log.type === 'complete') return 'bg-green-50 border-green-200 text-green-900'
    if (log.type === 'start') return 'bg-blue-50 border-blue-200 text-blue-900'
    return 'bg-gray-50 border-gray-200 text-gray-900'
  }

  // 파싱된 메시지 타입별 렌더링
  const renderParsedContent = () => {
    switch (parsed.type) {
      case 'user_message':
        return (
          <div className="space-y-1">
            <div className="text-xs font-semibold text-blue-700">👤 사용자 메시지</div>
            <div className="text-sm whitespace-pre-wrap bg-white p-2 rounded border">{parsed.content}</div>
          </div>
        )

      case 'assistant_message':
        return (
          <div className="space-y-1">
            <div className="text-xs font-semibold text-purple-700">🤖 어시스턴트 응답</div>
            <div className="text-sm whitespace-pre-wrap bg-white p-2 rounded border">{parsed.content}</div>
          </div>
        )

      case 'tool_use':
        return (
          <div className="space-y-1">
            <div
              className="flex items-center gap-2 cursor-pointer hover:bg-gray-100 p-1 rounded"
              onClick={() => setIsToolExpanded(!isToolExpanded)}
            >
              {isToolExpanded ? (
                <ChevronDown className="h-3 w-3 text-gray-600 flex-shrink-0" />
              ) : (
                <ChevronRight className="h-3 w-3 text-gray-600 flex-shrink-0" />
              )}
              <div className="text-xs font-semibold text-orange-700 overflow-hidden text-ellipsis whitespace-nowrap">
                🔧 도구 호출: {parsed.toolUse?.toolName}
              </div>
            </div>

            {/* 도구 사용 정보 (토글 가능) */}
            {isToolExpanded && parsed.toolUse && (
              <div className="ml-5 bg-white border rounded p-2 space-y-2 max-h-[300px] overflow-y-auto">
                {/* 도구 입력 */}
                {Object.keys(parsed.toolUse.input).length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-gray-700 mb-1">입력 파라미터:</div>
                    <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto break-words whitespace-pre-wrap">
                      {JSON.stringify(parsed.toolUse.input, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* 접혀있을 때는 간단한 미리보기 */}
            {!isToolExpanded && (
              <div className="ml-5 text-xs text-gray-600 overflow-hidden text-ellipsis whitespace-nowrap">
                {Object.keys(parsed.toolUse?.input || {}).length}개 파라미터
              </div>
            )}
          </div>
        )

      case 'tool_result':
        return (
          <div className="space-y-1">
            <div
              className="flex items-center gap-2 cursor-pointer hover:bg-gray-100 p-1 rounded"
              onClick={() => setIsToolExpanded(!isToolExpanded)}
            >
              {isToolExpanded ? (
                <ChevronDown className="h-3 w-3 text-gray-600 flex-shrink-0" />
              ) : (
                <ChevronRight className="h-3 w-3 text-gray-600 flex-shrink-0" />
              )}
              <div className="text-xs font-semibold text-green-700 overflow-hidden text-ellipsis whitespace-nowrap">
                ✅ 도구 결과: {parsed.toolUse?.toolName}
              </div>
            </div>

            {/* 도구 결과 (토글 가능) */}
            {isToolExpanded && (
              <div className="ml-5 bg-white border rounded p-2 space-y-2 max-h-[300px] overflow-y-auto">
                <div>
                  <div className="text-xs font-medium text-gray-700 mb-1">결과:</div>
                  <div className="text-xs whitespace-pre-wrap bg-gray-50 p-2 rounded break-words">{parsed.content}</div>
                </div>
              </div>
            )}

            {/* 접혀있을 때는 간단한 미리보기 */}
            {!isToolExpanded && (
              <div className="ml-5 text-xs text-gray-600 overflow-hidden text-ellipsis whitespace-nowrap">
                {parsed.content.substring(0, 100)}...
              </div>
            )}
          </div>
        )

      case 'thinking':
        return (
          <div className="space-y-1">
            <div
              className="flex items-center gap-2 cursor-pointer hover:bg-purple-50 p-1 rounded transition-colors"
              onClick={() => setIsToolExpanded(!isToolExpanded)}
            >
              {isToolExpanded ? (
                <ChevronDown className="h-3 w-3 text-purple-600 flex-shrink-0" />
              ) : (
                <ChevronRight className="h-3 w-3 text-purple-600 flex-shrink-0" />
              )}
              <Brain className="h-3.5 w-3.5 text-purple-600 flex-shrink-0" />
              <div className="text-xs font-semibold text-purple-700 overflow-hidden text-ellipsis whitespace-nowrap">
                사고 과정 (Extended Thinking)
              </div>
            </div>

            {/* 사고 과정 (토글 가능) */}
            {isToolExpanded && (
              <div className="ml-5 bg-purple-50 border border-purple-200 rounded p-3 max-h-[300px] overflow-y-auto">
                <div className="text-xs whitespace-pre-wrap break-words text-purple-900">{parsed.content}</div>
              </div>
            )}

            {/* 접혀있을 때는 간단한 미리보기 */}
            {!isToolExpanded && (
              <div className="ml-5 text-xs text-purple-600 italic overflow-hidden text-ellipsis whitespace-nowrap">
                {parsed.content.substring(0, 80)}...
              </div>
            )}
          </div>
        )

      case 'text':
      default:
        return <div className="text-sm font-mono whitespace-pre-wrap break-words">{parsed.content}</div>
    }
  }

  return (
    <div key={index} className={`p-2 rounded border text-xs ${getLogStyle()}`}>
      <div className="flex flex-col gap-1">
        <div className="text-xs text-muted-foreground">
          {new Date(log.timestamp).toLocaleTimeString()}
        </div>
        <div>{renderParsedContent()}</div>
      </div>
    </div>
  )
}

/**
 * 실행 로그 패널 컴포넌트 (자동 스크롤 기능 포함)
 */
const ExecutionLogsPanel: React.FC = () => {
  const execution = useWorkflowStore((state) => state.execution)
  const { logs, isExecuting, totalTokenUsage } = execution

  // tool_use_id -> tool_name 매핑 테이블 생성
  const toolNameMap = useMemo(() => buildToolNameMap(logs), [logs])

  // 자동 스크롤 관련 상태 및 ref
  const logsContainerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // 자동 스크롤 (로그가 업데이트될 때만)
  useEffect(() => {
    if (autoScroll && logsContainerRef.current) {
      // scrollIntoView 대신 scrollTop 직접 조작 (부모 스크롤 방지)
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  // 스크롤 이벤트 핸들러 (수동 스크롤 감지)
  const handleScroll = () => {
    if (!logsContainerRef.current) return

    const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50 // 50px 여유

    // 맨 아래에 있으면 자동 스크롤 활성화, 아니면 비활성화
    setAutoScroll(isAtBottom)
  }

  // 맨 아래로 스크롤 버튼
  const scrollToBottom = () => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTo({
        top: logsContainerRef.current.scrollHeight,
        behavior: 'smooth'
      })
      setAutoScroll(true)
    }
  }

  return (
    <div className="space-y-3">
      {/* 실행 상태 */}
      <div className="bg-gray-50 border rounded-md p-2">
        <div className="flex items-center justify-between">
          <div className="text-xs font-medium">실행 상태</div>
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
          <div className="text-xs text-muted-foreground space-y-0.5 mt-1.5">
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

      {/* 로그 목록 */}
      <div className="space-y-2 relative pt-1">
        <div className="flex items-center justify-between">
          <div className="text-xs font-medium">실행 로그</div>
          <div className="flex items-center gap-2">
            <div className="text-xs text-muted-foreground">{logs.length}개</div>
            {!autoScroll && logs.length > 0 && (
              <Button
                size="sm"
                variant="outline"
                onClick={scrollToBottom}
                className="h-6 px-2 text-xs"
              >
                <ArrowDown className="h-3 w-3 mr-1" />
                맨 아래로
              </Button>
            )}
          </div>
        </div>

        {logs.length === 0 ? (
          <div className="bg-gray-50 border rounded-md p-6 text-center">
            <ScrollText className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
            <div className="text-sm text-muted-foreground">워크플로우를 실행하면 로그가 표시됩니다</div>
          </div>
        ) : (
          <div
            ref={logsContainerRef}
            onScroll={handleScroll}
            className="space-y-2 max-h-[500px] overflow-y-auto scroll-smooth relative"
          >
            {/* 자동 스크롤 비활성화 알림 (스크롤 컨테이너 내부 상단에 sticky) */}
            {!autoScroll && (
              <div className="sticky top-0 z-10 flex justify-center mb-2">
                <div className="bg-gray-800 text-white text-xs px-3 py-1.5 rounded-full shadow-lg">
                  자동 스크롤 일시 중지됨
                </div>
              </div>
            )}

            {logs.map((log, index) => (
              <LogItem key={index} log={log} index={index} toolNameMap={toolNameMap} />
            ))}
          </div>
        )}
      </div>
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
            <ExecutionLogsPanel />
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
