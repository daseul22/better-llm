/**
 * Better-LLM 워크플로우 캔버스 앱
 *
 * 메인 레이아웃 및 컴포넌트 조합
 */

import React, { useState, useEffect, useCallback } from 'react'
import { ReactFlowProvider } from 'reactflow'
import { WorkflowCanvas } from './components/WorkflowCanvas'
import { NodePanel } from './components/NodePanel'
import { ExecutionPanel } from './components/ExecutionPanel'
import { Button } from './components/ui/button'
import { useWorkflowStore } from './stores/workflowStore'
import {
  saveWorkflow,
  getWorkflows,
  getWorkflow,
  deleteWorkflow,
  selectProject,
  getCurrentProject,
  saveProjectWorkflow,
  loadProjectWorkflow,
} from './lib/api'
import { Save, FolderOpen, Trash2, Folder } from 'lucide-react'
import { DirectoryBrowser } from './components/DirectoryBrowser'

const STORAGE_KEY_PROJECT_PATH = 'better-llm-last-project-path'

function App() {
  const { getWorkflow: getCurrentWorkflow, loadWorkflow, workflowName, setWorkflowName, nodes, edges } = useWorkflowStore()
  const [savedWorkflows, setSavedWorkflows] = useState<any[]>([])
  const [showLoadDialog, setShowLoadDialog] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  // 프로젝트 관련 상태
  const [currentProjectPath, setCurrentProjectPath] = useState<string | null>(null)
  const [showProjectDialog, setShowProjectDialog] = useState(false)
  const [projectPathInput, setProjectPathInput] = useState('')
  const [useBrowser, setUseBrowser] = useState(true) // 브라우저 vs 텍스트 입력

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

  // 노드/엣지 변경 시 자동 저장 (debounce)
  useEffect(() => {
    if (!currentProjectPath || nodes.length === 0) return

    const timer = setTimeout(() => {
      const workflow = getCurrentWorkflow()
      saveProjectWorkflow(workflow)
        .then(() => console.log('✅ 자동 저장 완료'))
        .catch((err) => console.warn('자동 저장 실패:', err))
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

  // 워크플로우 저장 (기존 방식 - ~/.better-llm/workflows/)
  const handleSave = async () => {
    try {
      setIsSaving(true)
      const workflow = getCurrentWorkflow()

      // 프로젝트가 선택되어 있으면 프로젝트에 저장
      if (currentProjectPath) {
        await saveProjectWorkflow(workflow)
        alert('프로젝트에 워크플로우가 저장되었습니다!')
      } else {
        // 프로젝트 미선택 시 기존 방식
        const workflowId = await saveWorkflow(workflow)
        alert(`워크플로우가 저장되었습니다! (ID: ${workflowId})`)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      alert(`저장 실패: ${errorMsg}`)
    } finally {
      setIsSaving(false)
    }
  }

  // 워크플로우 목록 불러오기
  const handleLoadList = async () => {
    try {
      const workflows = await getWorkflows()
      setSavedWorkflows(workflows)
      setShowLoadDialog(true)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      alert(`목록 불러오기 실패: ${errorMsg}`)
    }
  }

  // 워크플로우 불러오기
  const handleLoad = async (workflowId: string) => {
    try {
      const workflow = await getWorkflow(workflowId)
      loadWorkflow(workflow)
      setShowLoadDialog(false)
      alert(`워크플로우를 불러왔습니다: ${workflow.name}`)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      alert(`불러오기 실패: ${errorMsg}`)
    }
  }

  // 워크플로우 삭제
  const handleDelete = async (workflowId: string) => {
    if (!confirm('정말 삭제하시겠습니까?')) return

    try {
      await deleteWorkflow(workflowId)
      setSavedWorkflows((prev) => prev.filter((w) => w.id !== workflowId))
      alert('워크플로우가 삭제되었습니다')
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      alert(`삭제 실패: ${errorMsg}`)
    }
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
                placeholder="워크플로우 이름"
              />
              {currentProjectPath && (
                <div className="text-sm text-muted-foreground flex items-center gap-2">
                  <Folder className="h-4 w-4" />
                  <span className="max-w-[200px] truncate" title={currentProjectPath}>
                    {currentProjectPath.split('/').pop()}
                  </span>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <Button onClick={() => setShowProjectDialog(true)} variant="outline">
                <Folder className="mr-2 h-4 w-4" />
                프로젝트 선택
              </Button>
              <Button onClick={handleSave} disabled={isSaving}>
                <Save className="mr-2 h-4 w-4" />
                {isSaving ? '저장 중...' : '저장'}
              </Button>
              <Button onClick={handleLoadList} variant="outline">
                <FolderOpen className="mr-2 h-4 w-4" />
                불러오기
              </Button>
            </div>
          </div>
        </header>

        {/* 메인 레이아웃 */}
        <div className="flex-1 flex overflow-hidden">
          {/* 왼쪽: 노드 패널 */}
          <aside className="w-64 border-r bg-white p-4 overflow-y-auto">
            <NodePanel />
          </aside>

          {/* 중앙: 캔버스 */}
          <main className="flex-1 relative">
            <WorkflowCanvas />
          </main>

          {/* 오른쪽: 실행 패널 */}
          <aside className="w-96 border-l bg-white p-4 overflow-y-auto">
            <ExecutionPanel />
          </aside>
        </div>

        {/* 불러오기 다이얼로그 (간단 구현) */}
        {showLoadDialog && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full max-h-[80vh] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4">워크플로우 불러오기</h2>

              {savedWorkflows.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  저장된 워크플로우가 없습니다.
                </div>
              ) : (
                <div className="space-y-2">
                  {savedWorkflows.map((workflow) => (
                    <div
                      key={workflow.id}
                      className="border rounded-lg p-3 flex items-center justify-between hover:bg-gray-50"
                    >
                      <div className="flex-1">
                        <div className="font-medium">{workflow.name}</div>
                        <div className="text-xs text-muted-foreground">
                          노드: {workflow.node_count}, 엣지: {workflow.edge_count}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => handleLoad(workflow.id)}
                        >
                          불러오기
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDelete(workflow.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-4 flex justify-end">
                <Button variant="outline" onClick={() => setShowLoadDialog(false)}>
                  닫기
                </Button>
              </div>
            </div>
          </div>
        )}

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
