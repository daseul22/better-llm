/**
 * Better-LLM 워크플로우 캔버스 앱
 *
 * 메인 레이아웃 및 컴포넌트 조합
 */

import React, { useState } from 'react'
import { ReactFlowProvider } from 'reactflow'
import { WorkflowCanvas } from './components/WorkflowCanvas'
import { NodePanel } from './components/NodePanel'
import { ExecutionPanel } from './components/ExecutionPanel'
import { Button } from './components/ui/button'
import { useWorkflowStore } from './stores/workflowStore'
import { saveWorkflow, getWorkflows, getWorkflow, deleteWorkflow } from './lib/api'
import { Save, FolderOpen, Trash2 } from 'lucide-react'

function App() {
  const { getWorkflow: getCurrentWorkflow, loadWorkflow, workflowName, setWorkflowName } = useWorkflowStore()
  const [savedWorkflows, setSavedWorkflows] = useState<any[]>([])
  const [showLoadDialog, setShowLoadDialog] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  // 워크플로우 저장
  const handleSave = async () => {
    try {
      setIsSaving(true)
      const workflow = getCurrentWorkflow()
      const workflowId = await saveWorkflow(workflow)
      alert(`워크플로우가 저장되었습니다! (ID: ${workflowId})`)
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
            </div>

            <div className="flex gap-2">
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
      </div>
    </ReactFlowProvider>
  )
}

export default App
