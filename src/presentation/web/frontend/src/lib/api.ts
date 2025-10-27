/**
 * Better-LLM API 클라이언트
 *
 * 백엔드 API와 통신하는 함수들을 제공합니다.
 */

const API_BASE = '/api'

/**
 * Agent 정보
 */
export interface Agent {
  name: string
  role: string
  description: string
  system_prompt: string  // 시스템 프롬프트 원본
  allowed_tools: string[]  // 기본 도구 목록
}

/**
 * 워크플로우 노드
 */
export interface WorkflowNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: {
    agent_name: string
    task_template: string
    config?: Record<string, any>
  }
}

/**
 * 워크플로우 엣지
 */
export interface WorkflowEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
}

/**
 * 워크플로우
 */
export interface Workflow {
  id?: string
  name: string
  description?: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  metadata?: Record<string, any>
}

/**
 * 워크플로우 실행 이벤트
 */
export interface WorkflowExecutionEvent {
  event_type: 'node_start' | 'node_output' | 'node_complete' | 'node_error' | 'workflow_complete'
  node_id: string
  data: Record<string, any>
}

/**
 * Agent 목록 조회
 */
export async function getAgents(): Promise<Agent[]> {
  const response = await fetch(`${API_BASE}/agents`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  const data = await response.json()
  return data.agents
}

/**
 * 워크플로우 실행 (SSE 스트리밍)
 */
export async function executeWorkflow(
  workflow: Workflow,
  initialInput: string,
  onEvent: (event: WorkflowExecutionEvent) => void,
  onComplete: () => void,
  onError: (error: string) => void
): Promise<void> {
  const response = await fetch(`${API_BASE}/workflows/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify({
      workflow,
      initial_input: initialInput,
    }),
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('응답 본문을 읽을 수 없습니다')
  }

  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()

      if (done) {
        console.log('[SSE] 스트림 종료 (done=true)')
        onComplete()
        break
      }

      // 청크를 문자열로 변환
      const chunk = decoder.decode(value, { stream: true })
      buffer += chunk

      console.log('[SSE] 원본 청크 수신:', chunk.length, '바이트')
      console.log('[SSE] 원본 데이터:', JSON.stringify(chunk.substring(0, 200)))

      // ✅ CRLF (\r\n\r\n) 또는 LF (\n\n) 모두 처리
      // SSE 표준: 메시지는 빈 줄(\n\n 또는 \r\n\r\n)로 구분
      const messages = buffer.split(/\r\n\r\n|\n\n/)
      buffer = messages.pop() || ''

      console.log('[SSE] 파싱된 메시지 개수:', messages.length)

      for (const message of messages) {
        if (!message.trim()) {
          console.log('[SSE] 빈 메시지 건너뜀')
          continue
        }

        console.log('[SSE] 메시지 처리:', JSON.stringify(message.substring(0, 100)))

        // ✅ CRLF (\r\n) 또는 LF (\n) 모두 처리
        const lines = message.split(/\r\n|\n/)
        let dataContent = ''

        for (const line of lines) {
          const trimmedLine = line.trim()
          if (trimmedLine.startsWith('data:')) {
            const lineData = trimmedLine.substring(5).trim()
            if (dataContent) {
              dataContent += '\n' + lineData
            } else {
              dataContent = lineData
            }
          }
        }

        if (!dataContent) {
          console.warn('[SSE] data: 필드 없음, 메시지 무시:', message)
          continue
        }

        console.log('[SSE] data 추출 완료:', dataContent.substring(0, 100))

        // [DONE] 시그널
        if (dataContent === '[DONE]') {
          console.log('[SSE] [DONE] 시그널 수신')
          onComplete()
          return
        }

        // ERROR 시그널
        if (dataContent.startsWith('ERROR:')) {
          const errorMsg = dataContent.substring(7)
          console.error('[SSE] ERROR 시그널:', errorMsg)
          onError(errorMsg)
          return
        }

        // 이벤트 파싱 (JSON)
        try {
          const event: WorkflowExecutionEvent = JSON.parse(dataContent)
          console.log('[SSE] ✅ 이벤트 파싱 성공:', event.event_type, event.node_id, event.data)
          onEvent(event)
        } catch (e) {
          console.error('[SSE] ❌ JSON 파싱 실패:', dataContent, e)
        }
      }
    }
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error)
    onError(errorMsg)
  } finally {
    reader.releaseLock()
  }
}

/**
 * 워크플로우 저장
 */
export async function saveWorkflow(workflow: Workflow): Promise<string> {
  const response = await fetch(`${API_BASE}/workflows`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ workflow }),
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const data = await response.json()
  return data.workflow_id
}

/**
 * 워크플로우 목록 조회
 */
export async function getWorkflows(): Promise<any[]> {
  const response = await fetch(`${API_BASE}/workflows`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  const data = await response.json()
  return data.workflows
}

/**
 * 워크플로우 조회 (단일)
 */
export async function getWorkflow(workflowId: string): Promise<Workflow> {
  const response = await fetch(`${API_BASE}/workflows/${workflowId}`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  return await response.json()
}

/**
 * 워크플로우 삭제
 */
export async function deleteWorkflow(workflowId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/workflows/${workflowId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
}

// ==================== 프로젝트 API ====================

/**
 * 프로젝트 정보
 */
export interface ProjectInfo {
  project_path: string | null
  has_existing_config: boolean
}

/**
 * 프로젝트 선택
 */
export async function selectProject(projectPath: string): Promise<{
  project_path: string
  message: string
  has_existing_config: boolean
}> {
  const response = await fetch(`${API_BASE}/projects/select`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ project_path: projectPath }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
  }

  return await response.json()
}

/**
 * 현재 프로젝트 정보 조회
 */
export async function getCurrentProject(): Promise<ProjectInfo> {
  const response = await fetch(`${API_BASE}/projects/current`)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  return await response.json()
}

/**
 * 프로젝트에 워크플로우 저장
 */
export async function saveProjectWorkflow(
  workflow: Workflow,
  projectPath?: string
): Promise<{ message: string; config_path: string }> {
  const response = await fetch(`${API_BASE}/projects/workflow`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      project_path: projectPath,
      workflow,
    }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
  }

  return await response.json()
}

/**
 * 프로젝트에서 워크플로우 로드
 */
export async function loadProjectWorkflow(
  projectPath?: string
): Promise<{
  project_path: string
  workflow: Workflow
  last_modified: string | null
}> {
  const url = projectPath
    ? `${API_BASE}/projects/workflow?project_path=${encodeURIComponent(projectPath)}`
    : `${API_BASE}/projects/workflow`

  const response = await fetch(url)

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
  }

  return await response.json()
}

// ==================== 파일 시스템 API ====================

/**
 * 디렉토리 엔트리
 */
export interface DirectoryEntry {
  name: string
  path: string
  is_directory: boolean
  is_readable: boolean
}

/**
 * 디렉토리 브라우징 응답
 */
export interface DirectoryBrowseResponse {
  current_path: string
  parent_path: string | null
  entries: DirectoryEntry[]
}

/**
 * 홈 디렉토리 조회
 */
export async function getHomeDirectory(): Promise<{ home_path: string }> {
  const response = await fetch(`${API_BASE}/filesystem/home`)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  return await response.json()
}

/**
 * 디렉토리 브라우징
 */
export async function browseDirectory(
  path?: string
): Promise<DirectoryBrowseResponse> {
  const url = path
    ? `${API_BASE}/filesystem/browse?path=${encodeURIComponent(path)}`
    : `${API_BASE}/filesystem/browse`

  const response = await fetch(url)

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
  }

  return await response.json()
}

// ==================== Tool API ====================

/**
 * Tool (도구) 정보
 */
export interface Tool {
  name: string
  description: string
  category: string
  readonly: boolean
}

/**
 * 사용 가능한 도구 목록 조회
 */
export async function getTools(): Promise<Tool[]> {
  const response = await fetch(`${API_BASE}/tools`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  const data = await response.json()
  return data.tools
}
