/**
 * 커스텀 워커 생성 모달 컴포넌트
 *
 * worker_prompt_engineer를 실행하여 커스텀 워커 프롬프트를 생성하고,
 * 사용자와 상호작용하며 최종 저장까지 수행합니다.
 */

import React, { useState, useRef, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { generateCustomWorker, saveCustomWorker, getTools, Tool, getCurrentProject } from '@/lib/api'
import { Loader2, Send, Save, X, Sparkles, ArrowDown } from 'lucide-react'
import { ParsedContent } from './ParsedContent'

interface CustomWorkerCreateModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  onGeneratingStateChange?: (isGenerating: boolean) => void
}

export const CustomWorkerCreateModal: React.FC<CustomWorkerCreateModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  onGeneratingStateChange,
}) => {
  // 단계: 'input' | 'generating' | 'review' | 'saving'
  const [step, setStep] = useState<'input' | 'generating' | 'review' | 'saving'>('input')

  // 입력 필드
  const [workerRequirements, setWorkerRequirements] = useState('')
  const [workerName, setWorkerName] = useState('')
  const [workerRole, setWorkerRole] = useState('')

  // 생성된 프롬프트
  const [generatedOutput, setGeneratedOutput] = useState('')
  const [outputChunks, setOutputChunks] = useState<string[]>([])
  const [generatedPrompt, setGeneratedPrompt] = useState('')

  // 도구 선택
  const [availableTools, setAvailableTools] = useState<Tool[]>([])
  const [selectedTools, setSelectedTools] = useState<string[]>(['read', 'glob'])

  // 모델 선택
  const [selectedModel, setSelectedModel] = useState('claude-sonnet-4-5-20250929')

  // Thinking 모드
  const [thinking, setThinking] = useState(false)

  // 에러 및 로딩
  const [error, setError] = useState<string | null>(null)
  const [abortController, setAbortController] = useState<AbortController | null>(null)

  // 프로젝트 경로
  const [projectPath, setProjectPath] = useState<string | null>(null)

  // 스크롤 참조 및 자동 스크롤
  const outputContainerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // 세션 ID
  const [sessionId, setSessionId] = useState<string | null>(null)

  // localStorage 키
  const STORAGE_KEY = 'custom_worker_session'

  // step 변경 시 generating 상태 알림
  useEffect(() => {
    if (onGeneratingStateChange) {
      const isGenerating = step === 'generating' || step === 'review'
      onGeneratingStateChange(isGenerating)
    }
  }, [step, onGeneratingStateChange])

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
    // 모달이 열리지 않았거나 이미 실행 중이면 스킵
    if (!isOpen || step === 'generating' || step === 'review') {
      return
    }

    const session = loadSession()
    if (!session || session.status !== 'generating') {
      return
    }

    console.log('🔄 진행 중인 세션 발견:', session)

    // 세션 복원
    const sid = session.session_id
    const requirements = session.worker_requirements || ''

    setSessionId(sid)
    setWorkerRequirements(requirements)
    setStep('generating')

    // 재접속 시작
    console.log('🔌 세션 재접속:', sid)
    const controller = new AbortController()
    setAbortController(controller)

    const reconnect = async () => {
      try {
        await generateCustomWorker(
          requirements,
          (chunk) => {
            setGeneratedOutput((prev) => prev + chunk)
            setOutputChunks((prev) => [...prev, chunk])
          },
          (finalOutput) => {
            console.log('워커 프롬프트 생성 완료 (재접속)')
            setStep('review')
            setAbortController(null)
            clearSession()  // 완료되면 세션 정리
            extractPromptFromOutput(finalOutput)
          },
          (error) => {
            setError(error)
            setStep('input')
            setAbortController(null)
            clearSession()  // 에러 시 세션 정리
          },
          controller.signal,
          sid  // 세션 ID 전달
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

    // cleanup: 컴포넌트 언마운트 시 abort
    return () => {
      if (controller) {
        controller.abort()
      }
    }
  }, [isOpen])  // isOpen 변경 시마다 체크

  // 도구 목록 로드
  useEffect(() => {
    const loadTools = async () => {
      try {
        const tools = await getTools()
        setAvailableTools(tools)
      } catch (err) {
        console.error('도구 목록 로드 실패:', err)
      }
    }
    loadTools()
  }, [])

  // 프로젝트 경로 로드
  useEffect(() => {
    const loadProject = async () => {
      try {
        const project = await getCurrentProject()
        setProjectPath(project.project_path)
      } catch (err) {
        console.error('프로젝트 경로 로드 실패:', err)
      }
    }
    loadProject()
  }, [])

  // 자동 스크롤 (스트리밍 중)
  useEffect(() => {
    if (autoScroll && outputContainerRef.current && step === 'generating') {
      outputContainerRef.current.scrollTop = outputContainerRef.current.scrollHeight
    }
  }, [generatedOutput, autoScroll, step])

  // 스크롤 이벤트 핸들러 (수동 스크롤 감지)
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
        behavior: 'smooth'
      })
      setAutoScroll(true)
    }
  }

  // 모달 닫기
  const handleClose = () => {
    // generating이나 review 단계에서는 abort하지 않음 (백그라운드 실행 계속)
    // input 단계일 때만 초기화 (아직 작업 시작 안 함)
    if (step === 'input') {
      resetModal()
    }
    onClose()
  }

  // 워커 실행 중단 (명시적으로 호출)
  const handleAbort = () => {
    if (abortController) {
      abortController.abort()
    }
    setStep('input')
    setError('사용자가 작업을 중단했습니다')
    clearSession()  // 세션 정리
  }

  // 모달 리셋
  const resetModal = () => {
    setStep('input')
    setWorkerRequirements('')
    setWorkerName('')
    setWorkerRole('')
    setGeneratedOutput('')
    setOutputChunks([])
    setGeneratedPrompt('')
    setSelectedTools(['read', 'glob'])
    setSelectedModel('claude-sonnet-4-5-20250929')
    setThinking(false)
    setError(null)
    setAbortController(null)
    setSessionId(null)
    clearSession()  // 세션 정리
  }

  // 워커 프롬프트 생성 시작
  const handleGenerate = async () => {
    if (!workerRequirements.trim()) {
      setError('워커 요구사항을 입력해주세요')
      return
    }

    setStep('generating')
    setGeneratedOutput('')
    setOutputChunks([])
    setGeneratedPrompt('')
    setError(null)

    // 세션 ID 생성 및 저장
    const newSessionId = sessionId || `cw-${Date.now()}`
    setSessionId(newSessionId)
    saveSession({
      session_id: newSessionId,
      status: 'generating',
      worker_requirements: workerRequirements,
    })

    const controller = new AbortController()
    setAbortController(controller)

    try {
      await generateCustomWorker(
        workerRequirements,
        (chunk) => {
          setGeneratedOutput((prev) => prev + chunk)
          setOutputChunks((prev) => [...prev, chunk])
        },
        (finalOutput) => {
          console.log('워커 프롬프트 생성 완료')
          setStep('review')
          setAbortController(null)
          clearSession()  // 완료되면 세션 정리

          // 최종 출력에서 프롬프트 추출
          extractPromptFromOutput(finalOutput)
        },
        (error) => {
          setError(error)
          setStep('input')
          setAbortController(null)
          clearSession()  // 에러 시 세션 정리
        },
        controller.signal,
        newSessionId  // 세션 ID 전달
      )
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setError(errorMsg)
      setStep('input')
      setAbortController(null)
      clearSession()
    }
  }

  // 생성된 출력에서 JSON 파싱 및 필드 추출
  const extractPromptFromOutput = (output: string) => {
    console.log('📥 extractPromptFromOutput 호출됨')
    console.log('📊 출력 길이:', output.length)
    console.log('📄 출력 내용 미리보기:', output.substring(0, 500))

    let jsonText = ''

    try {
      // 방법 1 (우선): Balanced brace matching으로 JSON 직접 추출
      // worker_name을 찾고 그 근처의 { 부터 시작
      const workerNameIdx = output.indexOf('"worker_name"')
      if (workerNameIdx !== -1) {
        // worker_name 앞의 { 찾기 (최대 500자 이전까지)
        let startIdx = -1
        for (let i = workerNameIdx; i >= Math.max(0, workerNameIdx - 500); i--) {
          if (output[i] === '{') {
            startIdx = i
            break
          }
        }

        if (startIdx !== -1) {
          console.log('🔍 JSON 시작 위치 발견:', startIdx)
          // Balanced bracket matching으로 끝나는 } 찾기
          let depth = 0
          let endIdx = -1
          let inString = false
          let escapeNext = false

          for (let i = startIdx; i < output.length; i++) {
            const char = output[i]

            // 이스케이프 처리
            if (escapeNext) {
              escapeNext = false
              continue
            }

            if (char === '\\') {
              escapeNext = true
              continue
            }

            // 문자열 내부 처리
            if (char === '"') {
              inString = !inString
              continue
            }

            // 문자열 외부에서만 브레이스 카운트
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
            console.log('📦 JSON 시작:', jsonText.substring(0, 200))
            console.log('📦 JSON 끝:', jsonText.substring(Math.max(0, jsonText.length - 200)))
          } else {
            console.log('⚠️ JSON 끝을 찾지 못함 (불완전한 출력)')
          }
        }
      }

      // 방법 2 (폴백): ```json ... ``` 블록에서 추출
      if (!jsonText) {
        console.log('🔄 Balanced matching 실패, JSON 블록 추출 시도')

        // ```json 찾기
        const jsonBlockRegex = /```json\s*\n([\s\S]+?)```/
        const match = output.match(jsonBlockRegex)

        if (match && match[1]) {
          jsonText = match[1].trim()
          console.log('✅ JSON 블록 추출 성공 (길이):', jsonText.length)
        }
      }

      if (!jsonText) {
        console.log('❌ JSON 형태를 찾을 수 없음')
        console.log('📄 전체 출력:', output)
      }

      if (jsonText) {
        // JSON 파싱
        const parsed = JSON.parse(jsonText)
        console.log('✅ JSON 파싱 성공:', parsed)

        // 필드 추출 및 설정
        if (parsed.worker_name) {
          console.log('✅ worker_name 설정:', parsed.worker_name)
          setWorkerName(parsed.worker_name)
        }

        if (parsed.role) {
          console.log('✅ role 설정:', parsed.role)
          setWorkerRole(parsed.role)
        }

        if (parsed.prompt) {
          console.log('✅ prompt 설정 (길이):', parsed.prompt.length)
          setGeneratedPrompt(parsed.prompt)
        }

        if (parsed.allowed_tools && Array.isArray(parsed.allowed_tools)) {
          console.log('✅ allowed_tools 설정:', parsed.allowed_tools)
          setSelectedTools(parsed.allowed_tools)
        }

        if (parsed.model) {
          console.log('✅ model 설정:', parsed.model)
          setSelectedModel(parsed.model)
        }

        return
      }
    } catch (e) {
      console.error('⚠️ JSON 파싱 실패:', e)
      console.error('⚠️ 파싱 시도한 텍스트:', jsonText.substring(0, 500))
    }

    console.log('🔄 폴백 로직 사용')
    // JSON 파싱 실패 시 폴백: 기존 텍스트 파싱 로직
    fallbackTextParsing(output)
  }

  // JSON 파싱 실패 시 사용하는 폴백 함수
  const fallbackTextParsing = (output: string) => {
    // 코드 블록에서 프롬프트 추출
    const codeBlockRegex = /```(?:txt|text|md|markdown)?\n([\s\S]*?)```/g
    const matches = [...output.matchAll(codeBlockRegex)]

    if (matches.length > 0) {
      const longestMatch = matches.reduce((longest, current) =>
        current[1].length > longest[1].length ? current : longest
      )
      setGeneratedPrompt(longestMatch[1].trim())
    }

    // 워커 이름 추출
    const namePatterns = [
      /워커\s*이름[:\s]*`?([a-z0-9_-]+)`?/i,
      /"worker_name"\s*:\s*"([^"]+)"/i,
      /name[:\s]*`?([a-z0-9_-]+)`?/i,
    ]

    for (const pattern of namePatterns) {
      const nameMatch = output.match(pattern)
      if (nameMatch) {
        setWorkerName(nameMatch[1])
        break
      }
    }

    // 역할 추출
    const rolePatterns = [
      /"role"\s*:\s*"([^"]+)"/i,
      /역할[:\s]*"?([^"\n]+)"?/i,
      /role[:\s]*"?([^"\n]+)"?/i,
    ]

    for (const pattern of rolePatterns) {
      const roleMatch = output.match(pattern)
      if (roleMatch) {
        setWorkerRole(roleMatch[1].trim())
        break
      }
    }

    // 기본값 설정
    if (!workerName) {
      const keywords = workerRequirements.toLowerCase()
      if (keywords.includes('리뷰') || keywords.includes('review')) {
        setWorkerName('custom_reviewer')
      } else if (keywords.includes('테스트') || keywords.includes('test')) {
        setWorkerName('custom_tester')
      } else if (keywords.includes('분석') || keywords.includes('analy')) {
        setWorkerName('custom_analyzer')
      } else {
        setWorkerName('custom_worker')
      }
    }

    if (!workerRole) {
      const firstSentence = workerRequirements.split(/[.!?]/)[0].trim()
      if (firstSentence) {
        setWorkerRole(firstSentence.substring(0, 50))
      }
    }
  }

  // 재생성 (피드백 포함)
  const handleRegenerate = () => {
    setStep('input')
    // 기존 요구사항에 피드백 추가 가능하도록 유지
  }

  // 저장
  const handleSave = async () => {
    if (!projectPath) {
      setError('프로젝트가 선택되지 않았습니다. 먼저 프로젝트를 선택해주세요.')
      return
    }

    if (!workerName.trim()) {
      setError('워커 이름을 입력해주세요')
      return
    }

    if (!workerRole.trim()) {
      setError('워커 역할을 입력해주세요')
      return
    }

    if (!generatedPrompt.trim()) {
      setError('프롬프트 내용이 비어있습니다')
      return
    }

    if (selectedTools.length === 0) {
      setError('최소 1개의 도구를 선택해주세요')
      return
    }

    setStep('saving')
    setError(null)

    try {
      await saveCustomWorker({
        project_path: projectPath,
        worker_name: workerName,
        role: workerRole,
        prompt_content: generatedPrompt,
        allowed_tools: selectedTools,
        model: selectedModel,
        thinking,
      })

      // 성공 알림 및 초기화
      alert(`커스텀 워커 '${workerName}' 저장 완료!`)
      onSuccess()
      resetModal()  // 저장 완료 후 상태 초기화
      onClose()
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setError(errorMsg)
      setStep('review')
    }
  }

  // 도구 토글
  const toggleTool = (toolName: string) => {
    setSelectedTools((prev) =>
      prev.includes(toolName)
        ? prev.filter((t) => t !== toolName)
        : [...prev, toolName]
    )
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            커스텀 워커 생성
          </DialogTitle>
        </DialogHeader>

        {/* 단계: 입력 */}
        {step === 'input' && (
          <div className="space-y-4">
            <div>
              <Label htmlFor="requirements">원하는 워커의 요구사항</Label>
              <Textarea
                id="requirements"
                value={workerRequirements}
                onChange={(e) => setWorkerRequirements(e.target.value)}
                placeholder="예: 데이터를 분석하고 시각화하는 워커를 만들고 싶습니다. Python 스크립트를 실행하고 결과를 요약해주세요."
                rows={6}
                className="mt-2"
              />
              <p className="text-sm text-muted-foreground mt-1">
                워커가 수행할 역할과 필요한 기능을 자세히 설명해주세요.
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
            {/* 상태 표시 */}
            <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                <span className="text-sm font-medium text-blue-900">워커 프롬프트 생성 중...</span>
              </div>
              <div className="text-xs text-blue-700 mt-1">
                AI가 요구사항을 분석하고 프롬프트를 작성하고 있습니다
              </div>
            </div>

            {/* 출력 로그 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-xs font-medium">생성 로그</div>
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
                {/* 자동 스크롤 비활성화 알림 */}
                {!autoScroll && (
                  <div className="sticky top-0 z-10 flex justify-center mb-2">
                    <div className="bg-gray-800 text-white text-xs px-3 py-1.5 rounded-full shadow-lg">
                      자동 스크롤 일시 중지됨
                    </div>
                  </div>
                )}

                {/* 파싱된 출력 */}
                {generatedOutput.trim() ? (
                  <ParsedContent content={generatedOutput} />
                ) : (
                  <div className="text-gray-500 italic text-sm">
                    워커 프롬프트 엔지니어가 작업 중입니다...
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

        {/* 단계: 검토 및 설정 */}
        {step === 'review' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="workerName">워커 이름 *</Label>
                <Input
                  id="workerName"
                  value={workerName}
                  onChange={(e) => setWorkerName(e.target.value)}
                  placeholder="data_analyzer"
                  className="mt-1"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  영문, 숫자, _ 만 사용
                </p>
              </div>

              <div>
                <Label htmlFor="workerRole">워커 역할 *</Label>
                <Input
                  id="workerRole"
                  value={workerRole}
                  onChange={(e) => setWorkerRole(e.target.value)}
                  placeholder="데이터 분석 및 시각화"
                  className="mt-1"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="prompt">생성된 프롬프트 (수정 가능)</Label>
              <Textarea
                id="prompt"
                value={generatedPrompt}
                onChange={(e) => setGeneratedPrompt(e.target.value)}
                rows={10}
                className="mt-2 font-mono text-sm"
              />
            </div>

            <div>
              <Label>허용 도구 선택 *</Label>
              <div className="grid grid-cols-3 gap-2 mt-2">
                {availableTools.map((tool) => (
                  <div key={tool.name} className="flex items-center space-x-2">
                    <Checkbox
                      id={`tool-${tool.name}`}
                      checked={selectedTools.includes(tool.name)}
                      onCheckedChange={() => toggleTool(tool.name)}
                    />
                    <label
                      htmlFor={`tool-${tool.name}`}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      {tool.name}
                    </label>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                워커가 사용할 수 있는 도구를 선택하세요 (최소 1개)
              </p>
            </div>

            <div>
              <Label htmlFor="model">모델</Label>
              <select
                id="model"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="mt-1 w-full px-3 py-2 border rounded-md"
              >
                <option value="claude-sonnet-4-5-20250929">Claude Sonnet 4.5</option>
                <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="thinking"
                checked={thinking}
                onCheckedChange={(checked) => setThinking(checked as boolean)}
              />
              <label htmlFor="thinking" className="text-sm font-medium">
                Thinking 모드 활성화
              </label>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}
          </div>
        )}

        {/* 단계: 저장 중 */}
        {step === 'saving' && (
          <div className="flex items-center justify-center py-8">
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">커스텀 워커 저장 중...</p>
            </div>
          </div>
        )}

        <DialogFooter>
          {step === 'input' && (
            <>
              <Button variant="outline" onClick={handleClose}>
                <X className="mr-2 h-4 w-4" />
                취소
              </Button>
              <Button onClick={handleGenerate} disabled={!workerRequirements.trim()}>
                <Send className="mr-2 h-4 w-4" />
                생성 시작
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

          {step === 'review' && (
            <>
              <Button variant="outline" onClick={handleRegenerate}>
                재생성
              </Button>
              <Button variant="outline" onClick={handleClose}>
                <X className="mr-2 h-4 w-4" />
                취소
              </Button>
              <Button onClick={handleSave}>
                <Save className="mr-2 h-4 w-4" />
                저장
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
