/**
 * Claude Flow 워크플로우 캔버스 앱
 *
 * 메인 레이아웃 및 컴포넌트 조합
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { ReactFlowProvider } from 'reactflow'
import { WorkflowCanvas } from './components/WorkflowCanvas'
import { NodePanel } from './components/NodePanel'
import { NodeConfigPanel } from './components/NodeConfigPanel'
import { NodeSummaryPanel } from './components/NodeSummaryPanel'
import { ExecutionLogsPanel } from './components/ExecutionLogsPanel'
import { ValidationErrorsPanel } from './components/ValidationErrorsPanel'
import { WorkflowSelector } from './components/WorkflowSelector'
import { Button } from './components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './components/ui/dialog'
import { useWorkflowStore } from './stores/workflowStore'
import {
  selectProject,
  saveProjectWorkflowByName,
  loadProjectWorkflowByName,
  listProjectWorkflows,
  getWorkflowSession,
  clearProjectSessions,
  clearProjectLogs,
  clearNodeSessions,
  loadDisplayConfig,
  saveDisplayConfig,
} from './lib/api'
import { Folder, ChevronLeft, ChevronRight, PanelLeftClose, PanelRightClose, BookTemplate, Settings, Trash2, FileText, Save, Eye, Zap, Target, GitBranch, Merge as MergeIcon, RotateCcw } from 'lucide-react'
import { Badge } from './components/ui/badge'
import { DialogFooter } from './components/ui/dialog'
import { DirectoryBrowser } from './components/DirectoryBrowser'
import { ToastContainer, ToastType } from './components/Toast'
import { TemplateGallery } from './components/TemplateGallery'
import { LogsAndSessionsViewer } from './components/LogsAndSessionsViewer'

const STORAGE_KEY_PROJECT_PATH = 'claude-flow-last-project-path'
const STORAGE_KEY_SESSION_ID = 'claude-flow-workflow-session-id'

function App() {
  const {
    getWorkflow: getCurrentWorkflow,
    loadWorkflow,
    workflowName,
    setWorkflowName,
    currentWorkflowFileName,
    setCurrentWorkflowFileName,
    nodes,
    edges,
    restoreFromSession,
    execution,
    getSelectedNode,
    setSelectedNodeId,
  } = useWorkflowStore()

  // 프로젝트 관련 상태
  const [currentProjectPath, setCurrentProjectPath] = useState<string | null>(null)
  const [showProjectDialog, setShowProjectDialog] = useState(false)
  const [projectPathInput, setProjectPathInput] = useState('')
  const [useBrowser, setUseBrowser] = useState(true) // 브라우저 vs 텍스트 입력

  // 템플릿 갤러리 상태
  const [showTemplateGallery, setShowTemplateGallery] = useState(false)

  // 프로젝트 관리 메뉴 상태
  const [showProjectMenu, setShowProjectMenu] = useState(false)

  // 로그/세션 뷰어 상태
  const [showLogsViewer, setShowLogsViewer] = useState(false)

  // 사이드바 토글 상태
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true)

  // 노드 설정 Dialog 상태
  const [isNodeConfigDialogOpen, setIsNodeConfigDialogOpen] = useState(false)

  // 저장 상태 표시
  const [saveStatus, setSaveStatus] = useState<'idle' | 'pending' | 'saving' | 'saved'>('idle')

  // 자동 저장 타이머 추적
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 노드 데이터 변경 추적 (unsaved changes detection)
  const nodeDataSnapshotRef = useRef<any>(null)
  const [hasUnsavedNodeChanges, setHasUnsavedNodeChanges] = useState(false)

  // 토스트 알림 상태
  const [toasts, setToasts] = useState<Array<{
    id: string
    type: ToastType
    message: string
    duration?: number
  }>>([])


  // 토스트 추가 함수 (useCallback으로 메모이제이션)
  const addToast = useCallback((type: ToastType, message: string, duration = 3000) => {
    const id = `toast-${Date.now()}`
    setToasts((prev) => [...prev, { id, type, message, duration }])
  }, [])

  // 토스트 제거 함수
  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  // 초기 로드 완료 플래그
  const initialLoadDone = useRef(false)

  // Display 설정 로드
  const loadDisplaySettings = async () => {
    try {
      const config = await loadDisplayConfig()
      setLeftSidebarOpen(config.left_sidebar_open)
      setRightSidebarOpen(config.right_sidebar_open)
      console.log('✅ Display 설정 로드:', config)
    } catch (err) {
      console.warn('Display 설정 로드 실패 (기본값 사용):', err)
    }
  }

  // Display 설정 로드 (앱 시작 시 항상 실행)
  useEffect(() => {
    loadDisplaySettings()
  }, [])

  // 앱 시작 시 프로젝트 자동 로드 및 세션 복원 (한 번만 실행)
  useEffect(() => {
    // 이미 로드되었으면 스킵
    if (initialLoadDone.current) return
    initialLoadDone.current = true

    const loadLastProject = async () => {
      // 1. 세션 복원 시도 (우선순위 높음 - 세션에 프로젝트 경로 포함)
      const lastSessionId = localStorage.getItem(STORAGE_KEY_SESSION_ID)
      if (lastSessionId) {
        try {
          console.log('🔄 세션 복원 시도:', lastSessionId)
          const session = await getWorkflowSession(lastSessionId)

          // 1️⃣ 세션에서 프로젝트 경로 복원 (세션에 저장된 project_path 사용)
          if (session.project_path) {
            try {
              const result = await selectProject(session.project_path)
              setCurrentProjectPath(result.project_path)
              console.log(`✅ 세션에서 프로젝트 경로 복원: ${session.project_path}`)
            } catch (err) {
              console.warn('세션 프로젝트 경로 복원 실패:', err)
            }
          } else {
            console.warn('⚠️  세션에 프로젝트 경로 정보 없음')
          }

          // 2️⃣ 워크플로우 세션 복원 (기존 로그 복원 - 모든 세션)
          restoreFromSession(session)
          console.log('✅ 세션 복원 완료:', session.session_id)

          // 3️⃣ 실행 중인 세션만 스트림 재접속
          if (session.status === 'running') {
            console.log('🔌 실행 중인 세션 감지 - 스트림 자동 재접속 시작')

              // 현재 로그 개수 확인 (중복 방지용)
              const lastEventIndex = session.logs.length > 0 ? session.logs.length - 1 : undefined

              // 동적으로 executeWorkflow import 및 호출
              import('./lib/api').then(({ executeWorkflow }) => {
                const abortController = new AbortController()

                executeWorkflow(
                  session.workflow,
                  session.initial_input,
                  // onEvent
                  (event) => {
                    // Zustand store에 이벤트 전달 (restoreFromSession과 동일한 로직)
                    const { event_type, node_id, data: eventData, timestamp, elapsed_time, token_usage } = event
                    const store = useWorkflowStore.getState()

                    switch (event_type) {
                      case 'node_start':
                        store.setCurrentNode(node_id)
                        if (timestamp) {
                          store.setNodeStartTime(node_id, new Date(timestamp).getTime())
                        }
                        if (eventData.input) {
                          store.setNodeInput(node_id, eventData.input)
                        }
                        store.addLog(node_id, 'start', `▶️  ${eventData.agent_name || eventData.node_type || 'Unknown'} 실행 시작`)
                        break

                      case 'node_output':
                        store.addNodeOutput(node_id, eventData.chunk)
                        if (eventData.chunk && eventData.chunk.trim().length > 0) {
                          store.addLog(node_id, 'output', eventData.chunk)
                        }
                        break

                      case 'node_complete':
                        console.log('[App] 스트림 재접속 - node_complete 이벤트:', {
                          node_id,
                          elapsed_time,
                          token_usage,
                        })

                        if (elapsed_time !== undefined) {
                          store.setNodeCompleted(node_id, elapsed_time, token_usage)
                        }
                        let completeMsg = `✅ ${eventData.agent_name || eventData.node_type || 'Unknown'} 완료`
                        if (elapsed_time !== undefined) {
                          completeMsg += ` (${elapsed_time.toFixed(1)}초)`
                        }
                        if (token_usage && token_usage.total_tokens > 0) {
                          completeMsg += ` [${token_usage.total_tokens.toLocaleString()} tokens]`
                        }
                        store.addLog(node_id, 'complete', completeMsg)
                        break

                      case 'node_error':
                        if (eventData.error) {
                          store.setNodeError(node_id, eventData.error)
                        }
                        store.addLog(node_id, 'error', `❌ ${eventData.error || 'Unknown error'}`)
                        break

                      case 'workflow_complete':
                        store.addLog('', 'complete', eventData.message || '🎉 워크플로우 실행 완료')
                        store.setCurrentNode(null)
                        store.stopExecution()
                        break
                    }
                  },
                  // onComplete
                  () => {
                    console.log('✅ 스트림 재접속 완료 - 워크플로우 실행 완료')
                    useWorkflowStore.getState().stopExecution()
                  },
                  // onError
                  (error) => {
                    console.error('❌ 스트림 재접속 실패:', error)
                    useWorkflowStore.getState().stopExecution()
                    addToast('error', `스트림 재접속 실패: ${error}`)
                  },
                  // signal
                  abortController.signal,
                  // sessionId (재접속용)
                  lastSessionId,
                  // lastEventIndex (중복 방지용)
                  lastEventIndex
                ).then((returnedSessionId) => {
                  console.log('✅ 스트림 재접속 성공:', returnedSessionId)
                  addToast('success', '실시간 스트림이 재개되었습니다')
                }).catch((err) => {
                  console.error('❌ 스트림 재접속 중 에러:', err)
                  addToast('error', `스트림 재접속 실패: ${err.message}`)
                })
              })
          }

          // 세션 복원 성공 시 워크플로우 로드 스킵
          return
        } catch (err) {
          console.warn('세션 복원 실패 (세션 삭제됨 또는 만료):', err)
          localStorage.removeItem(STORAGE_KEY_SESSION_ID)
        }
      }

      // 2. 세션 복원 실패 시 localStorage에서 프로젝트 경로 복원
      const lastProjectPath = localStorage.getItem(STORAGE_KEY_PROJECT_PATH)
      if (lastProjectPath) {
        try {
          // 백엔드에 프로젝트 선택
          const result = await selectProject(lastProjectPath)
          setCurrentProjectPath(result.project_path)
          console.log(`✅ localStorage에서 프로젝트 경로 복원: ${lastProjectPath}`)

          // 워크플로우 목록 로드
          try {
            const workflowsResult = await listProjectWorkflows()

            if (workflowsResult.workflows.length > 0) {
              // 첫 번째 워크플로우 로드
              const firstWorkflow = workflowsResult.workflows[0]
              const workflowData = await loadProjectWorkflowByName(firstWorkflow.name)
              loadWorkflow(workflowData.workflow)
              setCurrentWorkflowFileName(firstWorkflow.name)
              console.log(`✅ 워크플로우 자동 로드: ${firstWorkflow.name}`)
            }
          } catch (err) {
            console.warn('워크플로우 자동 로드 실패:', err)
          }
        } catch (err) {
          console.warn('프로젝트 자동 로드 실패:', err)
          // 실패 시 localStorage 정리
          localStorage.removeItem(STORAGE_KEY_PROJECT_PATH)
        }
      }
    }

    loadLastProject()
  }, [loadWorkflow, restoreFromSession, addToast])

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

  // 프로젝트 관리 메뉴 외부 클릭 감지
  useEffect(() => {
    if (!showProjectMenu) return

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      // 메뉴 버튼이나 메뉴 내부를 클릭한 경우 무시
      if (target.closest('.project-menu-container')) {
        return
      }
      setShowProjectMenu(false)
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showProjectMenu])

  // 수동 저장 핸들러
  const handleManualSave = useCallback(() => {
    // 실행 중일 때는 저장 금지
    if (execution.isExecuting) {
      addToast('warning', '워크플로우 실행 중에는 저장할 수 없습니다')
      return
    }

    if (currentProjectPath && nodes.length > 0) {
      // 자동 저장 타이머가 있으면 취소
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current)
        autoSaveTimerRef.current = null
        console.log('🚫 자동 저장 타이머 취소됨 (수동 저장 시작)')
      }

      setSaveStatus('saving')
      const workflow = getCurrentWorkflow()
      saveProjectWorkflowByName(currentWorkflowFileName, workflow)
        .then(() => {
          setSaveStatus('saved')
          addToast('success', '워크플로우가 저장되었습니다')
          setTimeout(() => setSaveStatus('idle'), 2000)
        })
        .catch((err) => {
          setSaveStatus('idle')
          addToast('error', `저장 실패: ${err}`)
        })
    } else {
      addToast('warning', '저장할 프로젝트 또는 노드가 없습니다')
    }
  }, [execution.isExecuting, currentProjectPath, nodes, getCurrentWorkflow, addToast, currentWorkflowFileName])

  // 노드 더블클릭 핸들러 (Dialog 열기)
  const handleNodeDoubleClick = useCallback(() => {
    const selectedNode = getSelectedNode()
    if (selectedNode) {
      // 노드 데이터 스냅샷 저장 (unsaved changes 감지용)
      nodeDataSnapshotRef.current = JSON.parse(JSON.stringify(selectedNode.data))
      setHasUnsavedNodeChanges(false)
      setIsNodeConfigDialogOpen(true)
    }
  }, [getSelectedNode])

  // Dialog 닫기 핸들러 (unsaved changes 확인)
  const handleCloseNodeConfigDialog = useCallback((open: boolean) => {
    if (!open) {
      // Dialog를 닫으려고 할 때
      const selectedNode = getSelectedNode()

      // 변경사항이 있는지 확인
      if (selectedNode && nodeDataSnapshotRef.current) {
        const hasChanges = JSON.stringify(selectedNode.data) !== JSON.stringify(nodeDataSnapshotRef.current)

        if (hasChanges) {
          // 변경사항이 있으면 확인 창 표시
          if (confirm('저장하지 않은 변경사항이 있습니다. 정말 닫으시겠습니까?')) {
            setIsNodeConfigDialogOpen(false)
            setHasUnsavedNodeChanges(false)
            nodeDataSnapshotRef.current = null
          }
          // 취소하면 Dialog를 닫지 않음
        } else {
          // 변경사항이 없으면 그냥 닫기
          setIsNodeConfigDialogOpen(false)
          setHasUnsavedNodeChanges(false)
          nodeDataSnapshotRef.current = null
        }
      } else {
        // 스냅샷이 없으면 그냥 닫기
        setIsNodeConfigDialogOpen(false)
        setHasUnsavedNodeChanges(false)
        nodeDataSnapshotRef.current = null
      }
    } else {
      setIsNodeConfigDialogOpen(true)
    }
  }, [getSelectedNode])

  // 전역 키보드 단축키 핸들링
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
      const cmdOrCtrl = isMac ? e.metaKey : e.ctrlKey

      // Cmd/Ctrl + S: 수동 저장
      if (cmdOrCtrl && e.key === 's') {
        e.preventDefault()
        handleManualSave()
      }

      // Esc: Dialog 닫기 또는 선택 해제
      if (e.key === 'Escape' && !showProjectDialog) {
        if (isNodeConfigDialogOpen) {
          setIsNodeConfigDialogOpen(false)
        } else {
          setSelectedNodeId(null)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [showProjectDialog, isNodeConfigDialogOpen, handleManualSave, setSelectedNodeId])

  // 노드/엣지 변경 시 자동 저장 (debounce)
  useEffect(() => {
    // 프로젝트 선택되지 않았거나 노드가 없으면 스킵
    if (!currentProjectPath || nodes.length === 0) {
      // 노드가 있는데 프로젝트가 선택되지 않았으면 경고
      if (nodes.length > 0 && !currentProjectPath) {
        console.warn('⚠️  프로젝트가 선택되지 않았습니다. 자동 저장을 건너뜁니다.')
      }
      return
    }

    // 실행 중일 때는 자동 저장 스킵
    if (execution.isExecuting) {
      console.log('⏸️  워크플로우 실행 중이므로 자동 저장을 건너뜁니다.')
      return
    }

    // 자동 저장 대기 상태 (5초 타이머 시작)
    setSaveStatus('pending')

    const timer = setTimeout(() => {
      // 실제 저장 시작 - 상태를 'saving'으로 변경
      setSaveStatus('saving')
      const workflow = getCurrentWorkflow()

      saveProjectWorkflowByName(currentWorkflowFileName, workflow)
        .then(() => {
          console.log('✅ 자동 저장 완료')
          setSaveStatus('saved')
          addToast('success', '워크플로우가 자동 저장되었습니다')
          autoSaveTimerRef.current = null
          // 2초 후 상태 초기화
          setTimeout(() => setSaveStatus('idle'), 2000)
        })
        .catch((err) => {
          console.error('❌ 자동 저장 실패:', err)
          setSaveStatus('idle')
          autoSaveTimerRef.current = null
          const errorMsg = err instanceof Error ? err.message : String(err)
          addToast('error', `자동 저장 실패: ${errorMsg}`)
        })
    }, 5000) // 5초 debounce

    // 타이머를 ref에 저장 (수동 저장 시 취소 가능하도록)
    autoSaveTimerRef.current = timer

    return () => {
      clearTimeout(timer)
      if (autoSaveTimerRef.current === timer) {
        autoSaveTimerRef.current = null
      }
    }
  }, [nodes, edges, workflowName, currentProjectPath, execution.isExecuting, getCurrentWorkflow, addToast, currentWorkflowFileName])

  // Display 설정 변경 시 자동 저장 (debounce)
  useEffect(() => {
    // 프로젝트 선택되지 않았으면 스킵
    if (!currentProjectPath) {
      return
    }

    // 초기 로드 중이면 스킵 (무한 루프 방지)
    if (!initialLoadDone.current) {
      return
    }

    const timer = setTimeout(async () => {
      try {
        // 기존 설정 로드 (expanded_sections 보존)
        const existingConfig = await loadDisplayConfig()

        const displayConfig = {
          left_sidebar_open: leftSidebarOpen,
          right_sidebar_open: rightSidebarOpen,
          expanded_sections: existingConfig.expanded_sections, // 기존 값 유지
        }

        console.log('💾 Display 설정 자동 저장 중 (사이드바)...', displayConfig)

        await saveDisplayConfig(displayConfig)
        console.log('✅ Display 설정 자동 저장 완료')
      } catch (err) {
        console.error('❌ Display 설정 저장 실패:', err)
      }
    }, 1000) // 1초 debounce

    return () => clearTimeout(timer)
  }, [leftSidebarOpen, rightSidebarOpen, currentProjectPath])

  // 프로젝트 선택 핸들러 (브라우저 또는 텍스트 입력)
  const handleSelectProjectPath = async (path: string) => {
    try {
      const result = await selectProject(path)
      setCurrentProjectPath(result.project_path)
      localStorage.setItem(STORAGE_KEY_PROJECT_PATH, result.project_path)

      // 워크플로우 목록 로드
      try {
        const workflowsResult = await listProjectWorkflows()

        if (workflowsResult.workflows.length > 0) {
          // 첫 번째 워크플로우 로드
          const firstWorkflow = workflowsResult.workflows[0]
          const workflowData = await loadProjectWorkflowByName(firstWorkflow.name)
          loadWorkflow(workflowData.workflow)
          setCurrentWorkflowFileName(firstWorkflow.name)
          addToast('success', `프로젝트 및 워크플로우 로드 완료: ${workflowData.workflow.name}`)
        } else {
          // 워크플로우가 없으면 기본 워크플로우 생성 (빈 워크플로우)
          addToast('info', '새 프로젝트가 선택되었습니다. 워크플로우를 구성하세요.')
        }
      } catch (err) {
        console.warn('워크플로우 로드 실패:', err)
        addToast('warning', '워크플로우를 로드할 수 없습니다. 새로운 워크플로우를 생성하세요.')
      }

      setShowProjectDialog(false)
      setProjectPathInput('')
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      addToast('error', `프로젝트 선택 실패: ${errorMsg}`)
    }
  }

  // 텍스트 입력으로 프로젝트 선택
  const handleSelectProjectManual = async () => {
    if (!projectPathInput.trim()) {
      addToast('warning', '프로젝트 경로를 입력하세요')
      return
    }

    await handleSelectProjectPath(projectPathInput.trim())
  }

  // 세션 비우기 핸들러
  const handleClearSessions = async () => {
    if (!currentProjectPath) {
      addToast('warning', '프로젝트가 선택되지 않았습니다')
      return
    }

    if (!confirm('모든 세션 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
      return
    }

    try {
      const result = await clearProjectSessions()
      addToast(
        'success',
        `${result.message} (${result.deleted_files}개 파일, ${result.freed_space_mb} MB 확보)`
      )
      setShowProjectMenu(false)

      // localStorage의 세션 ID도 삭제
      localStorage.removeItem(STORAGE_KEY_SESSION_ID)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      addToast('error', `세션 삭제 실패: ${errorMsg}`)
    }
  }

  // 로그 비우기 핸들러
  const handleClearLogs = async () => {
    if (!currentProjectPath) {
      addToast('warning', '프로젝트가 선택되지 않았습니다')
      return
    }

    if (!confirm('모든 로그 파일을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
      return
    }

    try {
      const result = await clearProjectLogs()
      addToast(
        'success',
        `${result.message} (${result.deleted_files}개 파일, ${result.freed_space_mb} MB 확보)`
      )
      setShowProjectMenu(false)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      addToast('error', `로그 삭제 실패: ${errorMsg}`)
    }
  }

  // 모든 노드 세션 초기화 핸들러
  const handleClearNodeSessions = async () => {
    if (!currentProjectPath) {
      addToast('warning', '프로젝트가 선택되지 않았습니다')
      return
    }

    if (!confirm('모든 노드의 세션을 초기화하시겠습니까?\n각 노드의 대화 기록이 모두 삭제됩니다.')) {
      return
    }

    try {
      const result = await clearNodeSessions()
      addToast('success', `세션 초기화 완료! ${result.deleted_sessions}개의 세션이 삭제되었습니다.`)
      setShowProjectMenu(false)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      addToast('error', `세션 초기화 실패: ${errorMsg}`)
    }
  }

  return (
    <ReactFlowProvider>
      <div className="h-screen flex flex-col bg-background transition-colors duration-300">
        {/* 헤더 */}
        <header className="border-b bg-white px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-primary">Claude Flow</h1>

              {/* 워크플로우 선택 */}
              {currentProjectPath && (
                <WorkflowSelector
                  currentProjectPath={currentProjectPath}
                  currentWorkflow={getCurrentWorkflow()}
                  currentWorkflowName={currentWorkflowFileName}
                  onWorkflowChange={(workflow, workflowName) => {
                    loadWorkflow(workflow)
                    setCurrentWorkflowFileName(workflowName)
                  }}
                  onWorkflowNameChange={(name) => setWorkflowName(name)}
                />
              )}

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

              {/* 저장 상태 표시 */}
              {currentProjectPath && (
                <div className="text-xs text-muted-foreground flex items-center gap-1">
                  {saveStatus === 'pending' && (
                    <>
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                      <span>자동 저장 대기 중...</span>
                    </>
                  )}
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
              <Button
                onClick={handleManualSave}
                variant="outline"
                disabled={!currentProjectPath || nodes.length === 0 || execution.isExecuting}
                title={execution.isExecuting ? '워크플로우 실행 중에는 저장할 수 없습니다' : '워크플로우 저장 (Cmd+S)'}
              >
                <Save className="mr-2 h-4 w-4" />
                저장
              </Button>
              <Button onClick={() => setShowTemplateGallery(true)} variant="outline">
                <BookTemplate className="mr-2 h-4 w-4" />
                템플릿
              </Button>
              <Button onClick={() => setShowProjectDialog(true)} variant="outline">
                <Folder className="mr-2 h-4 w-4" />
                프로젝트 선택
              </Button>

              {/* 프로젝트 관리 메뉴 */}
              <div className="relative project-menu-container">
                <Button
                  onClick={() => setShowProjectMenu(!showProjectMenu)}
                  variant="outline"
                  disabled={!currentProjectPath}
                  title="프로젝트 관리"
                >
                  <Settings className="h-4 w-4" />
                </Button>

                {/* 드롭다운 메뉴 */}
                {showProjectMenu && currentProjectPath && (
                  <div className="absolute right-0 top-full mt-2 w-56 bg-white border rounded-lg shadow-lg z-50">
                    <div className="py-1">
                      <button
                        onClick={() => {
                          setShowLogsViewer(true)
                          setShowProjectMenu(false)
                        }}
                        className="w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center gap-2 transition-colors"
                      >
                        <Eye className="h-4 w-4 text-green-600" />
                        <span>로그 & 세션 보기</span>
                      </button>
                      <button
                        onClick={handleClearNodeSessions}
                        className="w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center gap-2 transition-colors"
                      >
                        <Trash2 className="h-4 w-4 text-red-600" />
                        <span>모든 노드 세션 초기화</span>
                      </button>
                      <button
                        onClick={handleClearSessions}
                        className="w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center gap-2 transition-colors"
                      >
                        <Trash2 className="h-4 w-4 text-orange-600" />
                        <span>프로젝트 세션 비우기</span>
                      </button>
                      <button
                        onClick={handleClearLogs}
                        className="w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center gap-2 transition-colors"
                      >
                        <FileText className="h-4 w-4 text-blue-600" />
                        <span>로그 비우기</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* 프로젝트 미선택 경고 배너 */}
        {!currentProjectPath && (
          <div className="bg-yellow-100 border-b border-yellow-300 px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="text-yellow-800 font-medium">
                ⚠️ 프로젝트가 선택되지 않았습니다
              </div>
              <div className="text-yellow-700 text-sm">
                워크플로우를 저장하려면 먼저 프로젝트를 선택하세요.
              </div>
            </div>
            <Button
              size="sm"
              onClick={() => setShowProjectDialog(true)}
              className="bg-yellow-600 hover:bg-yellow-700 text-white"
            >
              <Folder className="mr-2 h-4 w-4" />
              프로젝트 선택
            </Button>
          </div>
        )}

        {/* 메인 레이아웃 */}
        <div className="flex-1 flex overflow-hidden">
          {/* 왼쪽: 노드 패널 */}
          {leftSidebarOpen && (
            <aside className="w-80 border-r bg-white p-4 overflow-y-auto transition-transform duration-300 ease-out">
              <NodePanel />
            </aside>
          )}

          {/* 중앙: 캔버스 */}
          <main className="flex-1 relative">
            <WorkflowCanvas onNodeDoubleClick={handleNodeDoubleClick} />

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

          {/* 오른쪽: 노드 정보 & 실행 로그 패널 */}
          {rightSidebarOpen && (
            <aside className="w-[28rem] border-l bg-white flex flex-col overflow-hidden transition-transform duration-300 ease-out">
              {/* 패널 내용 */}
              <div className="flex-1 overflow-y-auto px-2 py-4 space-y-4">
                <NodeSummaryPanel onOpenFullConfig={() => setIsNodeConfigDialogOpen(true)} />
                <ValidationErrorsPanel />
                <ExecutionLogsPanel />
              </div>
            </aside>
          )}
        </div>

        {/* 토스트 알림 */}
        <ToastContainer toasts={toasts} onRemoveToast={removeToast} />

        {/* 노드 설정 Dialog */}
        <Dialog open={isNodeConfigDialogOpen} onOpenChange={handleCloseNodeConfigDialog}>
          <DialogContent className="w-[95vw] max-w-6xl h-[95vh] flex flex-col p-0">
            {/* Enhanced Header */}
            <DialogHeader className="flex-shrink-0 px-6 py-4 border-b">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {/* 노드 아이콘 */}
                  <div className="w-10 h-10 rounded-full flex items-center justify-center bg-gradient-to-br from-blue-100 to-purple-100">
                    {(() => {
                      const node = getSelectedNode()
                      if (!node) return <Settings className="h-5 w-5 text-gray-600" />

                      switch (node.type) {
                        case 'input':
                          return <Target className="h-5 w-5 text-blue-600" />
                        case 'worker':
                          return <Zap className="h-5 w-5 text-purple-600" />
                        case 'condition':
                          return <GitBranch className="h-5 w-5 text-orange-600" />
                        case 'merge':
                          return <MergeIcon className="h-5 w-5 text-green-600" />
                        default:
                          return <Settings className="h-5 w-5 text-gray-600" />
                      }
                    })()}
                  </div>

                  {/* 노드 제목 및 타입 */}
                  <div>
                    <DialogTitle className="text-lg">
                      {getSelectedNode()
                        ? `${getSelectedNode()!.data.agent_name || getSelectedNode()!.type} 설정`
                        : '노드 설정'}
                    </DialogTitle>
                    {getSelectedNode() && (
                      <p className="text-sm text-muted-foreground mt-0.5">
                        {getSelectedNode()!.type === 'input' && 'Input Node'}
                        {getSelectedNode()!.type === 'worker' && `Worker Node - ${getSelectedNode()!.data.agent_name || 'Unknown'}`}
                        {getSelectedNode()!.type === 'condition' && 'Condition Node'}
                        {getSelectedNode()!.type === 'merge' && 'Merge Node'}
                      </p>
                    )}
                  </div>
                </div>

                {/* 상태 badges */}
                <div className="flex items-center gap-2">
                  {/* 노드 타입 badge */}
                  {getSelectedNode() && (
                    <Badge
                      className={
                        getSelectedNode()!.type === 'input'
                          ? 'bg-blue-100 text-blue-800'
                          : getSelectedNode()!.type === 'worker'
                          ? 'bg-purple-100 text-purple-800'
                          : getSelectedNode()!.type === 'condition'
                          ? 'bg-orange-100 text-orange-800'
                          : getSelectedNode()!.type === 'merge'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }
                    >
                      {getSelectedNode()!.type}
                    </Badge>
                  )}

                  {/* Auto-save indicator */}
                  {saveStatus === 'pending' && (
                    <Badge variant="outline" className="text-blue-600 border-blue-300">
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse mr-2" />
                      저장 대기 중
                    </Badge>
                  )}
                  {saveStatus === 'saving' && (
                    <Badge variant="outline" className="text-yellow-600 border-yellow-300">
                      <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse mr-2" />
                      저장 중
                    </Badge>
                  )}
                  {saveStatus === 'saved' && (
                    <Badge variant="outline" className="text-green-600 border-green-300">
                      <div className="w-2 h-2 bg-green-500 rounded-full mr-2" />
                      저장됨
                    </Badge>
                  )}
                </div>
              </div>
            </DialogHeader>

            {/* 노드 설정 내용 */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <NodeConfigPanel />
            </div>

            {/* Enhanced Footer */}
            <DialogFooter className="flex-shrink-0 px-6 py-4 border-t bg-gray-50">
              <div className="flex items-center justify-between w-full">
                {/* 키보드 단축키 힌트 */}
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <kbd className="px-2 py-1 bg-white border rounded text-xs font-mono">⌘S</kbd>
                    <span>워크플로우 저장</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <kbd className="px-2 py-1 bg-white border rounded text-xs font-mono">Esc</kbd>
                    <span>닫기</span>
                  </div>
                </div>

                {/* 액션 버튼 */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const selectedNode = getSelectedNode()
                      if (selectedNode && nodeDataSnapshotRef.current) {
                        // 스냅샷으로 복원
                        useWorkflowStore.getState().updateNodeData(selectedNode.id, nodeDataSnapshotRef.current)
                        addToast('success', '변경사항이 취소되었습니다')
                      }
                    }}
                    disabled={!getSelectedNode()}
                  >
                    <RotateCcw className="mr-2 h-4 w-4" />
                    초기화
                  </Button>
                  <Button
                    onClick={() => {
                      setIsNodeConfigDialogOpen(false)
                      setHasUnsavedNodeChanges(false)
                      nodeDataSnapshotRef.current = null
                    }}
                  >
                    닫기
                  </Button>
                </div>
              </div>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 템플릿 갤러리 */}
        {showTemplateGallery && (
          <TemplateGallery
            onClose={() => setShowTemplateGallery(false)}
            onSelectTemplate={(workflow) => {
              loadWorkflow(workflow)
              addToast('success', `템플릿 "${workflow.name}"이(가) 로드되었습니다`)
            }}
            onImportTemplate={(workflow) => {
              loadWorkflow(workflow)
              addToast('success', `워크플로우 "${workflow.name}"이(가) 가져오기 되었습니다`)
            }}
          />
        )}

        {/* 로그 & 세션 뷰어 */}
        <LogsAndSessionsViewer
          isOpen={showLogsViewer}
          onClose={() => setShowLogsViewer(false)}
          projectPath={currentProjectPath}
        />

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
                        설정은 <code className="bg-gray-100 px-1 py-0.5 rounded">.claude-flow/workflow-config.json</code>에 저장됩니다.
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
