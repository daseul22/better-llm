/**
 * 워크플로우 자동 설계 모달 컴포넌트
 *
 * workflow_designer를 실행하여 워크플로우를 자동 설계하고,
 * 사용자와 상호작용하며 최종 워크플로우를 캔버스에 적용합니다.
 */

import React, { useState, useRef, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { designWorkflow } from '@/lib/api'
import { Loader2, Send, Check, X, Wand2, ArrowDown, ChevronDown, ChevronRight, Brain } from 'lucide-react'
import { parseLogMessage } from '@/lib/logParser'
import { useWorkflowStore } from '@/stores/workflowStore'
import type { Workflow } from '@/lib/api'

interface WorkflowDesignerModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  onDesigningStateChange?: (isDesigning: boolean) => void
}

/**
 * 단일 출력 청크 렌더링 컴포넌트
 */
const OutputChunkItem: React.FC<{ chunk: string; index: number }> = ({ chunk }) => {
  const [isExpanded, setIsExpanded] = useState(false)
  const parsed = parseLogMessage(chunk)

  const renderParsedContent = () => {
    switch (parsed.type) {
      case 'assistant_message':
        return (
          <div className="space-y-1">
            <div className="text-xs font-semibold text-purple-700">🤖 워커 응답</div>
            <div className="text-sm whitespace-pre-wrap bg-white p-3 rounded border leading-relaxed">
              {parsed.content}
            </div>
          </div>
        )

      case 'tool_use':
        return (
          <div className="space-y-1">
            <div
              className="flex items-center gap-2 cursor-pointer hover:bg-gray-100 p-1 rounded"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <ChevronDown className="h-3 w-3 text-gray-600 flex-shrink-0" />
              ) : (
                <ChevronRight className="h-3 w-3 text-gray-600 flex-shrink-0" />
              )}
              <div className="text-xs font-semibold text-orange-700 overflow-hidden text-ellipsis whitespace-nowrap">
                🔧 도구 호출: {parsed.toolUse?.toolName}
              </div>
            </div>
            {isExpanded && parsed.toolUse && (
              <div className="ml-5 bg-white border rounded p-2 space-y-2 max-h-[300px] overflow-y-auto">
                {Object.keys(parsed.toolUse.input).length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-gray-700 mb-1">입력:</div>
                    <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto break-words whitespace-pre-wrap">
                      {JSON.stringify(parsed.toolUse.input, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )

      case 'thinking':
        return (
          <div className="space-y-1">
            <div
              className="flex items-center gap-2 cursor-pointer hover:bg-purple-50 p-1 rounded transition-colors"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <ChevronDown className="h-3 w-3 text-purple-600 flex-shrink-0" />
              ) : (
                <ChevronRight className="h-3 w-3 text-purple-600 flex-shrink-0" />
              )}
              <Brain className="h-3.5 w-3.5 text-purple-600 flex-shrink-0" />
              <div className="text-xs font-semibold text-purple-700 overflow-hidden text-ellipsis whitespace-nowrap">
                사고 과정 (Extended Thinking)
              </div>
            </div>
            {isExpanded && (
              <div className="ml-5 bg-purple-50 border border-purple-200 rounded p-3 max-h-[300px] overflow-y-auto">
                <div className="text-xs whitespace-pre-wrap break-words text-purple-900">
                  {parsed.content}
                </div>
              </div>
            )}
          </div>
        )

      case 'text':
      default:
        return (
          <div className="text-sm whitespace-pre-wrap break-words leading-relaxed text-gray-800 bg-white p-3 rounded border">
            {parsed.content}
          </div>
        )
    }
  }

  return <div className="space-y-1">{renderParsedContent()}</div>
}

export const WorkflowDesignerModal: React.FC<WorkflowDesignerModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  onDesigningStateChange,
}) => {
  // 단계: 'input' | 'generating' | 'preview'
  const [step, setStep] = useState<'input' | 'generating' | 'preview'>('input')

  // 입력 필드
  const [requirements, setRequirements] = useState('')

  // 생성된 출력
  const [generatedOutput, setGeneratedOutput] = useState('')
  const [outputChunks, setOutputChunks] = useState<string[]>([])

  // 파싱된 워크플로우
  const [parsedWorkflow, setParsedWorkflow] = useState<Workflow | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)

  // 에러 및 로딩
  const [error, setError] = useState<string | null>(null)
  const [abortController, setAbortController] = useState<AbortController | null>(null)

  // 스크롤 참조 및 자동 스크롤
  const outputContainerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // 세션 ID
  const [sessionId, setSessionId] = useState<string | null>(null)

  // localStorage 키
  const STORAGE_KEY = 'workflow_design_session'

  // Workflow Store
  const loadWorkflow = useWorkflowStore((state) => state.loadWorkflow)

  // step 변경 시 generating 상태 알림
  useEffect(() => {
    if (onDesigningStateChange) {
      const isDesigning = step === 'generating' || step === 'preview'
      onDesigningStateChange(isDesigning)
    }
  }, [step, onDesigningStateChange])

  // 세션 저장
  const saveSession = (session: any) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  }

  // 세션 로드
  const loadSession = () => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? JSON.parse(stored) : null
  }

  // 세션 제거
  const clearSession = () => {
    localStorage.removeItem(STORAGE_KEY)
  }

  // 모달이 열릴 때 진행 중인 세션 확인 및 재접속
  useEffect(() => {
    if (!isOpen) {
      return
    }

    // 이미 재접속 중이면 중복 실행 방지
    if (step === 'generating' || step === 'preview') {
      console.log('⏭️ 이미 실행 중이므로 세션 복구 스킵:', step)
      return
    }

    const session = loadSession()
    if (!session || session.status !== 'generating') {
      console.log('ℹ️ 복구할 세션 없음')
      return
    }

    console.log('🔄 진행 중인 설계 세션 발견:', session)

    const sid = session.session_id
    const reqs = session.requirements || ''

    setSessionId(sid)
    setRequirements(reqs)
    setStep('generating')

    // 재접속 시작
    console.log('🔌 세션 재접속:', sid)
    const controller = new AbortController()
    setAbortController(controller)

    const reconnect = async () => {
      try {
        await designWorkflow(
          reqs,
          (chunk) => {
            setGeneratedOutput((prev) => prev + chunk)
            setOutputChunks((prev) => [...prev, chunk])
          },
          (finalOutput) => {
            console.log('워크플로우 설계 완료 (재접속)')
            setStep('preview')
            setAbortController(null)
            clearSession()
            extractWorkflowFromOutput(finalOutput)
          },
          (error) => {
            setError(error)
            setStep('input')
            setAbortController(null)
            clearSession()
          },
          controller.signal,
          sid
        )
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err)
        setError(errorMsg)
        setStep('input')
        setAbortController(null)
        clearSession()
      }
    }

    reconnect()

    return () => {
      if (controller) {
        controller.abort()
      }
    }
  }, [isOpen])

  // 자동 스크롤
  useEffect(() => {
    if (autoScroll && outputContainerRef.current && step === 'generating') {
      outputContainerRef.current.scrollTop = outputContainerRef.current.scrollHeight
    }
  }, [generatedOutput, autoScroll, step])

  // 스크롤 이벤트 핸들러
  const handleScroll = () => {
    if (!outputContainerRef.current) return

    const { scrollTop, scrollHeight, clientHeight } = outputContainerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50

    setAutoScroll(isAtBottom)
  }

  // 맨 아래로 스크롤
  const scrollToBottom = () => {
    if (outputContainerRef.current) {
      outputContainerRef.current.scrollTo({
        top: outputContainerRef.current.scrollHeight,
        behavior: 'smooth',
      })
      setAutoScroll(true)
    }
  }

  // 모달 닫기
  const handleClose = () => {
    if (step === 'input') {
      resetModal()
    }
    onClose()
  }

  // 설계 중단
  const handleAbort = () => {
    if (abortController) {
      abortController.abort()
    }
    setStep('input')
    setError('사용자가 작업을 중단했습니다')
    clearSession()
  }

  // 모달 리셋
  const resetModal = () => {
    setStep('input')
    setRequirements('')
    setGeneratedOutput('')
    setOutputChunks([])
    setParsedWorkflow(null)
    setParseError(null)
    setError(null)
    setAbortController(null)
    setSessionId(null)
    clearSession()
  }

  // 워크플로우 설계 시작
  const handleGenerate = async () => {
    if (!requirements.trim()) {
      setError('워크플로우 요구사항을 입력해주세요')
      return
    }

    setStep('generating')
    setGeneratedOutput('')
    setOutputChunks([])
    setParsedWorkflow(null)
    setParseError(null)
    setError(null)

    const newSessionId = sessionId || `wf-${Date.now()}`
    setSessionId(newSessionId)
    saveSession({
      session_id: newSessionId,
      status: 'generating',
      requirements,
    })

    const controller = new AbortController()
    setAbortController(controller)

    try {
      await designWorkflow(
        requirements,
        (chunk) => {
          setGeneratedOutput((prev) => prev + chunk)
          setOutputChunks((prev) => [...prev, chunk])
        },
        (finalOutput) => {
          console.log('워크플로우 설계 완료')
          setStep('preview')
          setAbortController(null)
          clearSession()
          extractWorkflowFromOutput(finalOutput)
        },
        (error) => {
          setError(error)
          setStep('input')
          setAbortController(null)
          clearSession()
        },
        controller.signal,
        newSessionId
      )
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setError(errorMsg)
      setStep('input')
      setAbortController(null)
      clearSession()
    }
  }

  // 생성된 출력에서 워크플로우 JSON 추출
  const extractWorkflowFromOutput = (output: string) => {
    console.log('📥 extractWorkflowFromOutput 호출됨')
    console.log('📊 출력 길이:', output.length)

    let jsonText = ''

    try {
      // "workflow" 필드를 찾고 그 근처의 { 부터 시작
      const workflowIdx = output.indexOf('"workflow"')
      if (workflowIdx !== -1) {
        // workflow 앞의 { 찾기
        let startIdx = -1
        for (let i = workflowIdx; i >= Math.max(0, workflowIdx - 500); i--) {
          if (output[i] === '{') {
            startIdx = i
            break
          }
        }

        if (startIdx !== -1) {
          console.log('🔍 JSON 시작 위치 발견:', startIdx)
          // Balanced bracket matching
          let depth = 0
          let endIdx = -1
          let inString = false
          let escapeNext = false

          for (let i = startIdx; i < output.length; i++) {
            const char = output[i]

            if (escapeNext) {
              escapeNext = false
              continue
            }

            if (char === '\\') {
              escapeNext = true
              continue
            }

            if (char === '"') {
              inString = !inString
              continue
            }

            if (!inString) {
              if (char === '{') depth++
              if (char === '}') {
                depth--
                if (depth === 0) {
                  endIdx = i + 1
                  break
                }
              }
            }
          }

          if (endIdx !== -1) {
            jsonText = output.substring(startIdx, endIdx)
            console.log('✅ Balanced matching 성공 (길이):', jsonText.length)
          }
        }
      }

      // 폴백: ```json ... ``` 블록에서 추출
      if (!jsonText) {
        console.log('🔄 Balanced matching 실패, JSON 블록 추출 시도')
        const jsonBlockRegex = /```json\s*\n([\s\S]+?)```/
        const match = output.match(jsonBlockRegex)

        if (match && match[1]) {
          jsonText = match[1].trim()
          console.log('✅ JSON 블록 추출 성공 (길이):', jsonText.length)
        }
      }

      if (!jsonText) {
        throw new Error('워크플로우 JSON을 찾을 수 없습니다')
      }

      // JSON 파싱
      const parsed = JSON.parse(jsonText)
      console.log('✅ JSON 파싱 성공:', parsed)

      // workflow 필드 추출
      if (parsed.workflow) {
        setParsedWorkflow(parsed.workflow)
        setParseError(null)
        console.log('✅ 워크플로우 추출 성공:', parsed.workflow)
      } else {
        throw new Error('workflow 필드가 없습니다')
      }
    } catch (e) {
      console.error('⚠️ 워크플로우 파싱 실패:', e)
      const errorMsg = e instanceof Error ? e.message : String(e)
      setParseError(errorMsg)
      setParsedWorkflow(null)
    }
  }

  // 워크플로우 적용
  const handleApply = () => {
    if (!parsedWorkflow) {
      setError('워크플로우를 파싱할 수 없습니다')
      return
    }

    try {
      loadWorkflow(parsedWorkflow)
      alert('워크플로우가 캔버스에 적용되었습니다')
      onSuccess()
      resetModal()
      onClose()
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setError(errorMsg)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-primary" />
            워크플로우 자동 설계
          </DialogTitle>
        </DialogHeader>

        {/* 단계: 입력 */}
        {step === 'input' && (
          <div className="space-y-4">
            <div>
              <label htmlFor="requirements" className="text-sm font-medium">
                원하는 워크플로우 설명
              </label>
              <Textarea
                id="requirements"
                value={requirements}
                onChange={(e) => setRequirements(e.target.value)}
                placeholder="예: 코드 작성 후 리뷰하고 테스트 실행하는 워크플로우를 만들어주세요"
                rows={6}
                className="mt-2"
              />
              <p className="text-sm text-muted-foreground mt-1">
                AI가 요구사항을 분석하여 노드와 연결을 자동으로 설계합니다
              </p>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}
          </div>
        )}

        {/* 단계: 생성 중 */}
        {step === 'generating' && (
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                <span className="text-sm font-medium text-blue-900">워크플로우 설계 중...</span>
              </div>
              <div className="text-xs text-blue-700 mt-1">
                AI가 요구사항을 분석하고 워크플로우를 설계하고 있습니다
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-xs font-medium">설계 로그</div>
                {!autoScroll && (
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

              <div
                ref={outputContainerRef}
                onScroll={handleScroll}
                className="bg-slate-50 border rounded-lg p-4 max-h-96 overflow-y-auto scroll-smooth relative"
              >
                {!autoScroll && (
                  <div className="sticky top-0 z-10 flex justify-center mb-2">
                    <div className="bg-gray-800 text-white text-xs px-3 py-1.5 rounded-full shadow-lg">
                      자동 스크롤 일시 중지됨
                    </div>
                  </div>
                )}

                {outputChunks.length > 0 ? (
                  <div className="space-y-2">
                    {outputChunks.map((chunk, index) => (
                      <OutputChunkItem key={index} chunk={chunk} index={index} />
                    ))}
                  </div>
                ) : (
                  <div className="text-gray-500 italic text-sm">
                    워크플로우 디자이너가 작업 중입니다...
                  </div>
                )}
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                <div className="font-medium mb-1">에러 발생</div>
                <div>{error}</div>
              </div>
            )}
          </div>
        )}

        {/* 단계: 미리보기 */}
        {step === 'preview' && (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-md p-3">
              <div className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium text-green-900">워크플로우 설계 완료</span>
              </div>
            </div>

            {parsedWorkflow ? (
              <div>
                <div className="text-sm font-medium mb-2">설계된 워크플로우</div>
                <div className="bg-slate-50 border rounded-lg p-4 max-h-96 overflow-y-auto">
                  <div className="space-y-2">
                    <div>
                      <span className="text-xs font-semibold text-gray-700">이름:</span>
                      <span className="text-sm ml-2">{parsedWorkflow.name}</span>
                    </div>
                    {parsedWorkflow.description && (
                      <div>
                        <span className="text-xs font-semibold text-gray-700">설명:</span>
                        <span className="text-sm ml-2">{parsedWorkflow.description}</span>
                      </div>
                    )}
                    <div>
                      <span className="text-xs font-semibold text-gray-700">노드 수:</span>
                      <span className="text-sm ml-2">{parsedWorkflow.nodes.length}개</span>
                    </div>
                    <div>
                      <span className="text-xs font-semibold text-gray-700">연결 수:</span>
                      <span className="text-sm ml-2">{parsedWorkflow.edges.length}개</span>
                    </div>
                  </div>

                  <div className="mt-4">
                    <div className="text-xs font-semibold text-gray-700 mb-2">노드 상세:</div>
                    <div className="space-y-2">
                      {parsedWorkflow.nodes.map((node) => {
                        const typeColors: Record<string, string> = {
                          input: 'bg-blue-50 border-blue-300',
                          worker: 'bg-green-50 border-green-300',
                          manager: 'bg-purple-50 border-purple-300',
                          condition: 'bg-yellow-50 border-yellow-300',
                          loop: 'bg-orange-50 border-orange-300',
                          merge: 'bg-pink-50 border-pink-300',
                        }
                        const typeIcons: Record<string, string> = {
                          input: '📥',
                          worker: '⚙️',
                          manager: '👥',
                          condition: '🔀',
                          loop: '🔁',
                          merge: '🔗',
                        }
                        const bgColor = typeColors[node.type] || 'bg-white border-gray-300'
                        const icon = typeIcons[node.type] || '📦'

                        return (
                          <div key={node.id} className={`text-xs p-3 rounded border ${bgColor}`}>
                            <div className="font-semibold flex items-center gap-2 mb-1">
                              <span>{icon}</span>
                              <span>{node.id}</span>
                              <span className="text-gray-600 font-normal">({node.type})</span>
                            </div>
                            {node.data && (
                              <div className="ml-6 mt-1 space-y-1 text-gray-700">
                                {node.data.agent_name && (
                                  <div>• Agent: <span className="font-medium">{node.data.agent_name}</span></div>
                                )}
                                {node.data.task_template && (
                                  <div>• Task: <span className="italic">{node.data.task_template.substring(0, 80)}{node.data.task_template.length > 80 ? '...' : ''}</span></div>
                                )}
                                {node.data.task_description && (
                                  <div>• Task: <span className="italic">{node.data.task_description.substring(0, 80)}{node.data.task_description.length > 80 ? '...' : ''}</span></div>
                                )}
                                {node.data.available_workers && (
                                  <div>• Workers: <span className="font-medium">{node.data.available_workers.join(', ')}</span></div>
                                )}
                                {node.data.condition_type && (
                                  <div>• Condition: <span className="font-medium">{node.data.condition_type} "{node.data.condition_value}"</span></div>
                                )}
                                {node.data.max_iterations && (
                                  <div>• Max Iterations: <span className="font-medium">{node.data.max_iterations}</span></div>
                                )}
                                {node.data.merge_strategy && (
                                  <div>• Strategy: <span className="font-medium">{node.data.merge_strategy}</span></div>
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  <div className="mt-4">
                    <div className="text-xs font-semibold text-gray-700 mb-2">연결 관계:</div>
                    <div className="space-y-1">
                      {parsedWorkflow.edges.map((edge) => (
                        <div key={edge.id} className="text-xs bg-white p-2 rounded border flex items-center gap-2">
                          <span className="font-medium text-blue-600">{edge.source}</span>
                          <span className="text-gray-400">→</span>
                          <span className="font-medium text-green-600">{edge.target}</span>
                          {edge.sourceHandle && (
                            <span className="text-gray-500 text-[10px] ml-auto">({edge.sourceHandle})</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-3 text-sm text-muted-foreground">
                  ✅ 확인 버튼을 누르면 워크플로우가 캔버스에 적용됩니다
                </div>
              </div>
            ) : (
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="text-sm font-medium text-yellow-900 mb-1">파싱 실패</div>
                <div className="text-sm text-yellow-800">{parseError}</div>
                <div className="mt-2 text-xs text-yellow-700">
                  전체 출력을 확인하여 수동으로 JSON을 추출해주세요
                </div>
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          {step === 'input' && (
            <>
              <Button variant="outline" onClick={handleClose}>
                <X className="mr-2 h-4 w-4" />
                취소
              </Button>
              <Button onClick={handleGenerate} disabled={!requirements.trim()}>
                <Send className="mr-2 h-4 w-4" />
                설계 시작
              </Button>
            </>
          )}

          {step === 'generating' && (
            <>
              <Button variant="outline" onClick={handleClose}>
                백그라운드 실행
              </Button>
              <Button variant="destructive" onClick={handleAbort}>
                <X className="mr-2 h-4 w-4" />
                중단
              </Button>
            </>
          )}

          {step === 'preview' && (
            <>
              <Button variant="outline" onClick={() => setStep('input')}>
                다시 설계
              </Button>
              <Button variant="outline" onClick={handleClose}>
                <X className="mr-2 h-4 w-4" />
                취소
              </Button>
              <Button onClick={handleApply} disabled={!parsedWorkflow}>
                <Check className="mr-2 h-4 w-4" />
                확인 (캔버스에 적용)
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
