/**
 * 워크플로우 상태 관리 (Zustand)
 *
 * React Flow의 노드 및 엣지 상태를 관리합니다.
 */

import { create } from 'zustand'
import { WorkflowNode, WorkflowEdge, Workflow } from '@/lib/api'

interface WorkflowExecutionState {
  isExecuting: boolean
  currentNodeId: string | null
  nodeOutputs: Record<string, string>
  logs: Array<{
    nodeId: string
    type: 'start' | 'output' | 'complete' | 'error'
    message: string
    timestamp: number
  }>
}

interface WorkflowStore {
  // 워크플로우 정의
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  workflowName: string
  workflowDescription: string

  // 실행 상태
  execution: WorkflowExecutionState

  // 노드/엣지 조작
  setNodes: (nodes: WorkflowNode[]) => void
  setEdges: (edges: WorkflowEdge[]) => void
  addNode: (node: WorkflowNode) => void
  updateNode: (nodeId: string, data: Partial<WorkflowNode['data']>) => void
  deleteNode: (nodeId: string) => void
  addEdge: (edge: WorkflowEdge) => void
  deleteEdge: (edgeId: string) => void

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
}

const initialExecutionState: WorkflowExecutionState = {
  isExecuting: false,
  currentNodeId: null,
  nodeOutputs: {},
  logs: [],
}

export const useWorkflowStore = create<WorkflowStore>((set, get) => ({
  // 초기 상태
  nodes: [],
  edges: [],
  workflowName: '새 워크플로우',
  workflowDescription: '',
  execution: initialExecutionState,

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
    })),

  addEdge: (edge) =>
    set((state) => ({ edges: [...state.edges, edge] })),

  deleteEdge: (edgeId) =>
    set((state) => ({
      edges: state.edges.filter((edge) => edge.id !== edgeId),
    })),

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
      workflowName: '새 워크플로우',
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
    set((state) => ({
      execution: initialExecutionState,
    })),
}))
