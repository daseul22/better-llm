/**
 * Better-LLM 워크플로우 캔버스 앱
 *
 * 메인 레이아웃 및 컴포넌트 조합
 */

import { useState, useEffect } from 'react'
import { ReactFlowProvider } from 'reactflow'
import { WorkflowCanvas } from './components/WorkflowCanvas'
import { NodePanel } from './components/NodePanel'
import { NodeConfigPanel } from './components/NodeConfigPanel'
import { Button } from './components/ui/button'
import { useWorkflowStore } from './stores/workflowStore'
import {
  selectProject,
  saveProjectWorkflow,
  loadProjectWorkflow,
} from './lib/api'
import { Folder, ChevronLeft, ChevronRight, PanelLeftClose, PanelRightClose } from 'lucide-react'
import { DirectoryBrowser } from './components/DirectoryBrowser'

const STORAGE_KEY_PROJECT_PATH = 'better-llm-last-project-path'

function App() {
  const { getWorkflow: getCurrentWorkflow, loadWorkflow, workflowName, setWorkflowName, nodes, edges } = useWorkflowStore()

  // 프로젝트 관련 상태
  const [currentProjectPath, setCurrentProjectPath] = useState<string | null>(null)
  const [showProjectDialog, setShowProjectDialog] = useState(false)
  const [projectPathInput, setProjectPathInput] = useState('')
  const [useBrowser, setUseBrowser] = useState(true) // 브라우저 vs 텍스트 입력

  // 사이드바 토글 상태
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true)

  // 저장 상태 표시
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')

  // 앱 시작 시 프로젝트 자동 로드
  useEffect(() => {
    const loadLastProject = async () => {
      // localStorage에서 마지막 프로젝트 경로 가져오기
      const lastProjectPath = localStorage.getItem(STORAGE_KEY_PROJECT_PATH)

      if (lastProjectPath) {
        try {
          // 백엔드에 프로젝트 선택
          const result = await selectProject(lastProjectPath)
          setCurrentProjectPath(result.project_path)

          // 기존 설정이 있으면 자동 로드
          if (result.has_existing_config) {
            const data = await loadProjectWorkflow()
            loadWorkflow(data.workflow)
            console.log(`✅ 프로젝트 자동 로드: ${lastProjectPath}`)
          }
        } catch (err) {
          console.warn('프로젝트 자동 로드 실패:', err)
          // 실패 시 localStorage 정리
          localStorage.removeItem(STORAGE_KEY_PROJECT_PATH)
        }
      }
    }

    loadLastProject()
  }, [loadWorkflow])

  // ESC 키 핸들링: 프로젝트 선택 다이얼로그
  useEffect(() => {
    if (!showProjectDialog) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowProjectDialog(false)
        setProjectPathInput('')
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [showProjectDialog])

  // 노드/엣지 변경 시 자동 저장 (debounce)
  useEffect(() => {
    if (!currentProjectPath || nodes.length === 0) return

    // 저장 대기 상태
    setSaveStatus('saving')

    const timer = setTimeout(() => {
      const workflow = getCurrentWorkflow()
      console.log('💾 워크플로우 자동 저장 중...', {
        nodes: workflow.nodes.length,
        edges: workflow.edges.length,
        name: workflow.name,
      })

      saveProjectWorkflow(workflow)
        .then(() => {
          console.log('✅ 자동 저장 완료')
          setSaveStatus('saved')
          // 2초 후 상태 초기화
          setTimeout(() => setSaveStatus('idle'), 2000)
        })
        .catch((err) => {
          console.error('❌ 자동 저장 실패:', err)
          setSaveStatus('idle')
        })
    }, 2000) // 2초 debounce

    return () => clearTimeout(timer)
  }, [nodes, edges, workflowName, currentProjectPath, getCurrentWorkflow])

  // 프로젝트 선택 핸들러 (브라우저 또는 텍스트 입력)
  const handleSelectProjectPath = async (path: string) => {
    try {
      const result = await selectProject(path)
      setCurrentProjectPath(result.project_path)
      localStorage.setItem(STORAGE_KEY_PROJECT_PATH, result.project_path)

      // 기존 설정이 있으면 로드
      if (result.has_existing_config) {
        const data = await loadProjectWorkflow()
        loadWorkflow(data.workflow)
        alert(`프로젝트 로드 완료: ${data.workflow.name}`)
      } else {
        alert('새 프로젝트가 선택되었습니다. 워크플로우를 구성하세요.')
      }

      setShowProjectDialog(false)
      setProjectPathInput('')
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      alert(`프로젝트 선택 실패: ${errorMsg}`)
    }
  }

  // 텍스트 입력으로 프로젝트 선택
  const handleSelectProjectManual = async () => {
    if (!projectPathInput.trim()) {
      alert('프로젝트 경로를 입력하세요')
      return
    }

    await handleSelectProjectPath(projectPathInput.trim())
  }

  return (
    <ReactFlowProvider>
      <div className="h-screen flex flex-col bg-background">
        {/* 헤더 */}
        <header className="border-b bg-white px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-primary">Better-LLM</h1>
              <input
                type="text"
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                className="text-lg font-medium border-b border-transparent hover:border-gray-300 focus:border-primary outline-none px-2"
                placeholder="프로젝트 이름"
              />
              {currentProjectPath && (
                <div className="text-sm text-muted-foreground flex items-center gap-2">
                  <Folder className="h-4 w-4" />
                  <span className="max-w-[200px] truncate" title={currentProjectPath}>
                    {currentProjectPath.split('/').pop()}
                  </span>
                </div>
              )}

              {/* 저장 상태 표시 */}
              {currentProjectPath && (
                <div className="text-xs text-muted-foreground flex items-center gap-1">
                  {saveStatus === 'saving' && (
                    <>
                      <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
                      <span>저장 중...</span>
                    </>
                  )}
                  {saveStatus === 'saved' && (
                    <>
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                      <span>저장됨</span>
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <Button onClick={() => setShowProjectDialog(true)} variant="outline">
                <Folder className="mr-2 h-4 w-4" />
                프로젝트 선택
              </Button>
            </div>
          </div>
        </header>

        {/* 메인 레이아웃 */}
        <div className="flex-1 flex overflow-hidden">
          {/* 왼쪽: 노드 패널 */}
          {leftSidebarOpen && (
            <aside className="w-64 border-r bg-white p-4 overflow-y-auto">
              <NodePanel />
            </aside>
          )}

          {/* 중앙: 캔버스 */}
          <main className="flex-1 relative">
            <WorkflowCanvas />

            {/* 사이드바 토글 버튼 */}
            <div className="absolute top-4 left-4 flex gap-2 z-10">
              <Button
                size="sm"
                variant="outline"
                className="bg-white shadow-md"
                onClick={() => setLeftSidebarOpen(!leftSidebarOpen)}
                title={leftSidebarOpen ? "왼쪽 패널 닫기" : "왼쪽 패널 열기"}
              >
                {leftSidebarOpen ? (
                  <PanelLeftClose className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </Button>
            </div>

            <div className="absolute top-4 right-4 flex gap-2 z-10">
              <Button
                size="sm"
                variant="outline"
                className="bg-white shadow-md"
                onClick={() => setRightSidebarOpen(!rightSidebarOpen)}
                title={rightSidebarOpen ? "오른쪽 패널 닫기" : "오른쪽 패널 열기"}
              >
                {rightSidebarOpen ? (
                  <PanelRightClose className="h-4 w-4" />
                ) : (
                  <ChevronLeft className="h-4 w-4" />
                )}
              </Button>
            </div>
          </main>

          {/* 오른쪽: 노드 설정 패널 */}
          {rightSidebarOpen && (
            <aside className="w-96 border-l bg-white flex flex-col overflow-hidden">
              {/* 패널 내용 */}
              <div className="flex-1 overflow-hidden p-4">
                <NodeConfigPanel />
              </div>
            </aside>
          )}
        </div>

        {/* 프로젝트 선택 다이얼로그 */}
        {showProjectDialog && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full h-[80vh] flex flex-col">
              <div className="border-b p-4 flex items-center justify-between">
                <h2 className="text-xl font-bold">프로젝트 디렉토리 선택</h2>

                {/* 브라우저/텍스트 입력 토글 */}
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant={useBrowser ? 'default' : 'outline'}
                    onClick={() => setUseBrowser(true)}
                  >
                    <Folder className="h-4 w-4 mr-2" />
                    브라우저
                  </Button>
                  <Button
                    size="sm"
                    variant={!useBrowser ? 'default' : 'outline'}
                    onClick={() => setUseBrowser(false)}
                  >
                    텍스트 입력
                  </Button>
                </div>
              </div>

              <div className="flex-1 overflow-hidden">
                {useBrowser ? (
                  /* 디렉토리 브라우저 */
                  <DirectoryBrowser
                    onSelectDirectory={handleSelectProjectPath}
                    onCancel={() => {
                      setShowProjectDialog(false)
                      setProjectPathInput('')
                    }}
                  />
                ) : (
                  /* 텍스트 입력 방식 */
                  <div className="p-6 space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        프로젝트 경로
                      </label>
                      <input
                        type="text"
                        value={projectPathInput}
                        onChange={(e) => setProjectPathInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            handleSelectProjectManual()
                          }
                        }}
                        className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                        placeholder="/Users/username/my-project"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        설정은 <code className="bg-gray-100 px-1 py-0.5 rounded">.better-llm/workflow-config.json</code>에 저장됩니다.
                      </p>
                    </div>

                    {currentProjectPath && (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <div className="text-sm font-medium text-blue-900">
                          현재 선택된 프로젝트:
                        </div>
                        <div className="text-sm text-blue-700 mt-1 font-mono">
                          {currentProjectPath}
                        </div>
                      </div>
                    )}

                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                      <div className="text-sm text-yellow-900">
                        <strong>안내:</strong>
                        <ul className="list-disc list-inside mt-1 space-y-1">
                          <li>로컬 파일 시스템 경로를 입력하세요</li>
                          <li>기존 설정이 있으면 자동으로 로드됩니다</li>
                          <li>워크플로우 변경 시 자동으로 저장됩니다</li>
                        </ul>
                      </div>
                    </div>

                    <div className="mt-6 flex justify-end gap-2">
                      <Button
                        variant="outline"
                        onClick={() => {
                          setShowProjectDialog(false)
                          setProjectPathInput('')
                        }}
                      >
                        취소
                      </Button>
                      <Button onClick={handleSelectProjectManual}>
                        선택
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </ReactFlowProvider>
  )
}

export default App
