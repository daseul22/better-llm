/**
 * 워크플로우 상태 관리 (Zustand)
 *
 * React Flow의 노드 및 엣지 상태를 관리합니다.
 */

import { create } from 'zustand'
import { WorkflowNode, WorkflowEdge, Workflow, WorkflowValidationError } from '@/lib/api'

export type NodeExecutionStatus = 'idle' | 'running' | 'completed' | 'error'

export interface NodeExecutionMeta {
  status: NodeExecutionStatus
  startTime?: number
  endTime?: number
  elapsedTime?: number
  tokenUsage?: {
    input_tokens: number
    output_tokens: number
    total_tokens: number
  }
  error?: string
}

interface WorkflowExecutionState {
  isExecuting: boolean
  currentNodeId: string | null
  nodeOutputs: Record<string, string>
  nodeMeta: Record<string, NodeExecutionMeta>
  logs: Array<{
    nodeId: string
    type: 'start' | 'output' | 'complete' | 'error'
    message: string
    timestamp: number
  }>
  totalTokenUsage: {
    input_tokens: number
    output_tokens: number
    total_tokens: number
  }
}

interface WorkflowStore {
  // 워크플로우 정의
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  workflowName: string
  workflowDescription: string

  // 선택된 노드
  selectedNodeId: string | null

  // 실행 상태
  execution: WorkflowExecutionState

  // 검증 상태
  validationErrors: WorkflowValidationError[]
  isValidating: boolean

  // 노드/엣지 조작
  setNodes: (nodes: WorkflowNode[]) => void
  setEdges: (edges: WorkflowEdge[]) => void
  addNode: (node: WorkflowNode) => void
  updateNode: (nodeId: string, data: Partial<WorkflowNode['data']>) => void
  deleteNode: (nodeId: string) => void
  addEdge: (edge: WorkflowEdge) => void
  deleteEdge: (edgeId: string) => void

  // 노드 선택
  setSelectedNodeId: (nodeId: string | null) => void
  getSelectedNode: () => WorkflowNode | null

  // 워크플로우 메타데이터
  setWorkflowName: (name: string) => void
  setWorkflowDescription: (description: string) => void

  // 워크플로우 전체 로드/저장
  loadWorkflow: (workflow: Workflow) => void
  getWorkflow: () => Workflow
  clearWorkflow: () => void

  // 실행 상태 관리
  startExecution: () => void
  stopExecution: () => void
  setCurrentNode: (nodeId: string | null) => void
  addNodeOutput: (nodeId: string, output: string) => void
  addLog: (nodeId: string, type: WorkflowExecutionState['logs'][0]['type'], message: string) => void
  clearExecution: () => void

  // 노드별 실행 상태 관리
  setNodeStatus: (nodeId: string, status: NodeExecutionStatus) => void
  setNodeStartTime: (nodeId: string, timestamp: number) => void
  setNodeCompleted: (nodeId: string, elapsedTime: number, tokenUsage?: NodeExecutionMeta['tokenUsage']) => void
  setNodeError: (nodeId: string, error: string) => void
  getNodeMeta: (nodeId: string) => NodeExecutionMeta | null

  // 검증 상태 관리
  setValidationErrors: (errors: WorkflowValidationError[]) => void
  setIsValidating: (isValidating: boolean) => void
  clearValidationErrors: () => void
  getValidationErrorsForNode: (nodeId: string) => WorkflowValidationError[]
}

const initialExecutionState: WorkflowExecutionState = {
  isExecuting: false,
  currentNodeId: null,
  nodeOutputs: {},
  nodeMeta: {},
  logs: [],
  totalTokenUsage: {
    input_tokens: 0,
    output_tokens: 0,
    total_tokens: 0,
  },
}

export const useWorkflowStore = create<WorkflowStore>((set, get) => ({
  // 초기 상태
  nodes: [],
  edges: [],
  workflowName: '새 프로젝트',
  workflowDescription: '',
  selectedNodeId: null,
  execution: initialExecutionState,
  validationErrors: [],
  isValidating: false,

  // 노드/엣지 조작
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),

  addNode: (node) =>
    set((state) => ({ nodes: [...state.nodes, node] })),

  updateNode: (nodeId, data) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      ),
    })),

  deleteNode: (nodeId) =>
    set((state) => ({
      nodes: state.nodes.filter((node) => node.id !== nodeId),
      edges: state.edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      ),
      // 삭제된 노드가 선택되어 있었다면 선택 해제
      selectedNodeId: state.selectedNodeId === nodeId ? null : state.selectedNodeId,
    })),

  addEdge: (edge) =>
    set((state) => ({ edges: [...state.edges, edge] })),

  deleteEdge: (edgeId) =>
    set((state) => ({
      edges: state.edges.filter((edge) => edge.id !== edgeId),
    })),

  // 노드 선택
  setSelectedNodeId: (nodeId) => set({ selectedNodeId: nodeId }),

  getSelectedNode: () => {
    const state = get()
    if (!state.selectedNodeId) return null
    return state.nodes.find((node) => node.id === state.selectedNodeId) || null
  },

  // 워크플로우 메타데이터
  setWorkflowName: (name) => set({ workflowName: name }),
  setWorkflowDescription: (description) => set({ workflowDescription: description }),

  // 워크플로우 전체 로드/저장
  loadWorkflow: (workflow) =>
    set({
      nodes: workflow.nodes,
      edges: workflow.edges,
      workflowName: workflow.name,
      workflowDescription: workflow.description || '',
    }),

  getWorkflow: () => {
    const state = get()
    return {
      name: state.workflowName,
      description: state.workflowDescription,
      nodes: state.nodes,
      edges: state.edges,
    }
  },

  clearWorkflow: () =>
    set({
      nodes: [],
      edges: [],
      workflowName: '새 프로젝트',
      workflowDescription: '',
      execution: initialExecutionState,
    }),

  // 실행 상태 관리
  startExecution: () =>
    set((state) => ({
      execution: {
        ...state.execution,
        isExecuting: true,
        currentNodeId: null,
        nodeOutputs: {},
        logs: [
          {
            nodeId: '',
            type: 'start',
            message: '🚀 워크플로우 실행 시작...',
            timestamp: Date.now(),
          }
        ],
      },
    })),

  stopExecution: () =>
    set((state) => ({
      execution: {
        ...state.execution,
        isExecuting: false,
        currentNodeId: null,
      },
    })),

  setCurrentNode: (nodeId) =>
    set((state) => ({
      execution: {
        ...state.execution,
        currentNodeId: nodeId,
      },
    })),

  addNodeOutput: (nodeId, output) =>
    set((state) => ({
      execution: {
        ...state.execution,
        nodeOutputs: {
          ...state.execution.nodeOutputs,
          [nodeId]: (state.execution.nodeOutputs[nodeId] || '') + output,
        },
      },
    })),

  addLog: (nodeId, type, message) => {
    console.log('[workflowStore] addLog 호출:', { nodeId, type, message })

    set((state) => {
      const newLog = {
        nodeId,
        type,
        message,
        timestamp: Date.now(),
      }
      const newLogs = [...state.execution.logs, newLog]

      console.log('[workflowStore] logs 업데이트:', {
        이전: state.execution.logs.length,
        이후: newLogs.length,
        마지막_로그: newLog
      })

      return {
        execution: {
          ...state.execution,
          logs: newLogs,
        },
      }
    })
  },

  clearExecution: () =>
    set({
      execution: initialExecutionState,
    }),

  // 노드별 실행 상태 관리 구현
  setNodeStatus: (nodeId, status) =>
    set((state) => ({
      execution: {
        ...state.execution,
        nodeMeta: {
          ...state.execution.nodeMeta,
          [nodeId]: {
            ...(state.execution.nodeMeta[nodeId] || { status: 'idle' }),
            status,
          },
        },
      },
    })),

  setNodeStartTime: (nodeId, timestamp) =>
    set((state) => ({
      execution: {
        ...state.execution,
        nodeMeta: {
          ...state.execution.nodeMeta,
          [nodeId]: {
            ...(state.execution.nodeMeta[nodeId] || { status: 'idle' }),
            status: 'running',
            startTime: timestamp,
          },
        },
      },
    })),

  setNodeCompleted: (nodeId, elapsedTime, tokenUsage) =>
    set((state) => {
      const updatedMeta = {
        ...state.execution.nodeMeta,
        [nodeId]: {
          ...(state.execution.nodeMeta[nodeId] || { status: 'idle' }),
          status: 'completed' as NodeExecutionStatus,
          endTime: Date.now(),
          elapsedTime,
          tokenUsage,
        },
      }

      // 전체 토큰 사용량 업데이트
      const newTotalTokenUsage = { ...state.execution.totalTokenUsage }
      if (tokenUsage) {
        newTotalTokenUsage.input_tokens += tokenUsage.input_tokens
        newTotalTokenUsage.output_tokens += tokenUsage.output_tokens
        newTotalTokenUsage.total_tokens += tokenUsage.total_tokens
      }

      return {
        execution: {
          ...state.execution,
          nodeMeta: updatedMeta,
          totalTokenUsage: newTotalTokenUsage,
        },
      }
    }),

  setNodeError: (nodeId, error) =>
    set((state) => ({
      execution: {
        ...state.execution,
        nodeMeta: {
          ...state.execution.nodeMeta,
          [nodeId]: {
            ...(state.execution.nodeMeta[nodeId] || { status: 'idle' }),
            status: 'error',
            endTime: Date.now(),
            error,
          },
        },
      },
    })),

  getNodeMeta: (nodeId) => {
    const state = get()
    return state.execution.nodeMeta[nodeId] || null
  },

  // 검증 상태 관리
  setValidationErrors: (errors) => set({ validationErrors: errors }),

  setIsValidating: (isValidating) => set({ isValidating }),

  clearValidationErrors: () => set({ validationErrors: [] }),

  getValidationErrorsForNode: (nodeId) => {
    const state = get()
    return state.validationErrors.filter((error) => error.node_id === nodeId)
  },
}))
