/**
 * 워크플로우 캔버스 컴포넌트 (React Flow)
 *
 * 워커 노드를 드래그 앤 드롭으로 배치하고 연결합니다.
 */

import React, { useCallback, useRef, useEffect, useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Panel,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
  NodeTypes,
  useReactFlow,
  NodeDragHandler,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { WorkerNode } from './WorkerNode'
import { InputNode } from './InputNode'
import { ConditionNode } from './ConditionNode'
import { MergeNode } from './MergeNode'
import { useWorkflowStore } from '@/stores/workflowStore'
import { WorkflowNode, WorkflowEdge, validateWorkflow } from '@/lib/api'
import { useAutoLayout } from '@/hooks/useAutoLayout'

// 커스텀 노드 타입 등록
const nodeTypes: NodeTypes = {
  worker: WorkerNode,
  input: InputNode,
  condition: ConditionNode,
  merge: MergeNode,
}

interface WorkflowCanvasProps {
  onNodeDoubleClick?: () => void
}

export const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({ onNodeDoubleClick }) => {
  const {
    nodes: storeNodes,
    edges: storeEdges,
    setEdges,
    addNode,
    addEdge: addStoreEdge,
    updateNodePosition,
    deleteNode,
    deleteEdge,
    execution,
    setSelectedNodeId,
    validationErrors,
    setValidationErrors,
    setIsValidating,
    getWorkflow,
    getValidationErrorsForNode,
  } = useWorkflowStore()

  // React Flow의 노드/엣지 상태 (로컬)
  const [nodes, setLocalNodes, onNodesChange] = useNodesState(storeNodes)
  const [edges, setLocalEdges, onEdgesChange] = useEdgesState(storeEdges)

  // React Flow 인스턴스 (좌표 변환에 필요)
  const { project } = useReactFlow()
  const reactFlowWrapper = useRef<HTMLDivElement>(null)

  // Zustand 상태와 로컬 상태 동기화 (메모이제이션으로 불필요한 재렌더링 방지)
  const nodesWithDeletable = useMemo(() => {
    return storeNodes.map(node => ({
      ...node,
      deletable: false,
    }))
  }, [storeNodes])

  // 메모이제이션된 노드를 로컬 상태에 동기화
  React.useEffect(() => {
    setLocalNodes(nodesWithDeletable)
  }, [nodesWithDeletable, setLocalNodes])

  // 실시간 워크플로우 검증 (debounce 1초)
  useEffect(() => {
    // 노드/엣지가 비어있으면 검증 스킵
    if (storeNodes.length === 0) {
      setValidationErrors([])
      return
    }

    // Debounce: 1초 후 검증 API 호출
    const timer = setTimeout(async () => {
      try {
        setIsValidating(true)

        const workflow = getWorkflow()
        const result = await validateWorkflow(workflow)

        setValidationErrors(result.errors)
      } catch (error) {
        console.error('워크플로우 검증 실패:', error)
        // 에러 발생 시 검증 에러 초기화
        setValidationErrors([])
      } finally {
        setIsValidating(false)
      }
    }, 1000) // 1초 debounce

    // 클린업: 타이머 취소
    return () => clearTimeout(timer)
  }, [storeNodes, storeEdges, getWorkflow, setValidationErrors, setIsValidating])

  React.useEffect(() => {
    // Zustand에서 로드된 엣지에도 화살표 및 스타일 적용
    const edgesWithMarkers = storeEdges.map((edge) => ({
      ...edge,
      type: 'default' as const,
      animated: true,
      style: { stroke: '#3b82f6', strokeWidth: 2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#3b82f6',
      },
    }))
    setLocalEdges(edgesWithMarkers)
  }, [storeEdges, setLocalEdges])

  // 실행 상태 및 검증 에러 표시 (노드 데이터 업데이트)
  React.useEffect(() => {
    // 노드 상태 업데이트
    setLocalNodes((nds) =>
      nds.map((node) => {
        const isExecuting = execution.currentNodeId === node.id
        const isCompleted = execution.nodeOutputs[node.id] !== undefined
        const hasError = execution.logs.some(
          (log) => log.nodeId === node.id && log.type === 'error'
        )

        // 검증 에러 가져오기
        const nodeValidationErrors = getValidationErrorsForNode(node.id)
        const hasValidationError = nodeValidationErrors.some(e => e.severity === 'error')
        const hasValidationWarning = nodeValidationErrors.some(e => e.severity === 'warning')

        return {
          ...node,
          data: {
            ...node.data,
            isExecuting,
            isCompleted,
            hasError,
            validationErrors: nodeValidationErrors,
            hasValidationError,
            hasValidationWarning,
          },
        }
      })
    )

    // 엣지 스타일 업데이트 (현재 실행 중인 노드로 연결된 엣지 강조)
    setLocalEdges((eds) =>
      eds.map((edge) => {
        const isActiveEdge =
          execution.currentNodeId &&
          (edge.source === execution.currentNodeId || edge.target === execution.currentNodeId)

        return {
          ...edge,
          animated: isActiveEdge || edge.animated,
          style: {
            ...edge.style,
            stroke: isActiveEdge ? '#facc15' : '#3b82f6', // 실행 중: 노란색, 기본: 파란색
            strokeWidth: isActiveEdge ? 3 : 2,
          },
          markerEnd: {
            ...(edge.markerEnd as any),
            color: isActiveEdge ? '#facc15' : '#3b82f6',
          },
        }
      })
    )
  }, [
    execution.currentNodeId,
    execution.nodeOutputs,
    execution.logs,
    validationErrors,
    setLocalNodes,
    setLocalEdges,
    getValidationErrorsForNode,
  ])

  // 자동 레이아웃 커스텀 훅 사용
  const { autoLayout } = useAutoLayout({
    nodes: storeNodes,
    edges: storeEdges,
    updateNodePosition,
    setLocalNodes,
  })


  // 노드 변경 핸들러
  const handleNodesChange: OnNodesChange = useCallback(
    (changes) => {
      onNodesChange(changes)

      // 노드 변경 처리
      changes.forEach((change) => {
        if (change.type === 'position' && change.position) {
          // 디버그 로그
          console.log('[WorkflowCanvas] position change:', {
            id: change.id,
            dragging: change.dragging,
            position: change.position,
          })

          // 드래그 완료 시에만 position을 Zustand에 반영
          // dragging이 false이거나 undefined일 때 (드래그 완료 시점)
          if (change.dragging === false || change.dragging === undefined) {
            console.log('[WorkflowCanvas] updateNodePosition 호출:', change.id, change.position)
            updateNodePosition(change.id, change.position)
          }
        }
      })
    },
    [onNodesChange, updateNodePosition]
  )

  // 엣지 변경 핸들러
  const handleEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      onEdgesChange(changes)

      // 선택된 엣지 처리
      changes.forEach((change) => {
        if (change.type === 'select') {
          // 선택된 엣지 강조
          setLocalEdges((eds) =>
            eds.map((edge) => {
              if (edge.id === change.id) {
                return {
                  ...edge,
                  style: {
                    ...edge.style,
                    stroke: change.selected ? '#10b981' : '#3b82f6', // 선택: 초록색, 기본: 파란색
                    strokeWidth: change.selected ? 4 : 2,
                  },
                  markerEnd: {
                    ...(edge.markerEnd as any),
                    color: change.selected ? '#10b981' : '#3b82f6',
                  },
                }
              }
              return edge
            })
          )
        }
      })

      // Zustand에 반영
      setLocalEdges((eds) => {
        setEdges(eds as WorkflowEdge[])
        return eds
      })
    },
    [onEdgesChange, setEdges, setLocalEdges]
  )

  // 엣지 연결 핸들러
  const handleConnect: OnConnect = useCallback(
    (connection: Connection) => {
      const newEdge: WorkflowEdge = {
        id: `edge-${connection.source}-${connection.target}`,
        source: connection.source!,
        target: connection.target!,
        sourceHandle: connection.sourceHandle ?? undefined,
        targetHandle: connection.targetHandle ?? undefined,
      }

      // React Flow 엣지에 화살표 추가
      const reactFlowEdge = {
        ...connection,
        id: newEdge.id,
        type: 'default',
        animated: true,  // 애니메이션 효과
        style: { stroke: '#3b82f6', strokeWidth: 2 },  // 파란색, 두께 2
        markerEnd: {
          type: 'arrowclosed' as const,
          color: '#3b82f6',
        },
      }

      setLocalEdges((eds) => addEdge(reactFlowEdge, eds))
      addStoreEdge(newEdge)
    },
    [setLocalEdges, addStoreEdge]
  )

  // 노드 드래그 완료 핸들러 (위치 저장)
  const handleNodeDragStop: NodeDragHandler = useCallback(
    (_event, node) => {
      console.log('[WorkflowCanvas] onNodeDragStop:', node.id, node.position)
      updateNodePosition(node.id, node.position)
    },
    [updateNodePosition]
  )

  // 노드 클릭 핸들러 (선택)
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      setSelectedNodeId(node.id)
    },
    [setSelectedNodeId]
  )

  // 노드 더블클릭 핸들러 (Dialog 열기)
  const handleNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      setSelectedNodeId(node.id)
      if (onNodeDoubleClick) {
        onNodeDoubleClick()
      }
    },
    [setSelectedNodeId, onNodeDoubleClick]
  )

  // 캔버스 클릭 핸들러 (선택 해제)
  const handlePaneClick = useCallback(() => {
    setSelectedNodeId(null)
  }, [setSelectedNodeId])

  // 드래그 오버 핸들러 (드롭 허용)
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  // 드롭 핸들러 (노드 추가)
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()

      const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect()
      if (!reactFlowBounds) return

      const data = event.dataTransfer.getData('application/reactflow')
      if (!data) return

      const { type, data: nodeData } = JSON.parse(data)

      // 화면 좌표를 React Flow 좌표로 변환
      const position = project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      })

      const newNode: WorkflowNode = {
        id: `${type}-${Date.now()}`,
        type,
        position,
        data: nodeData,
      }

      addNode(newNode)
    },
    [project, addNode]
  )


  return (
    <div ref={reactFlowWrapper} className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={handleConnect}
        onNodeClick={handleNodeClick}
        onNodeDoubleClick={handleNodeDoubleClick}
        onNodeDragStop={handleNodeDragStop}
        onPaneClick={handlePaneClick}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={nodeTypes}
        className="bg-gray-50"
        elevateEdgesOnSelect={false}
        elevateNodesOnSelect={false}
        fitView={false}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
      >
        <Background />
        <Controls />
        <MiniMap />

        {/* 자동 레이아웃 버튼 */}
        <Panel position="bottom-right" className="flex gap-2">
          <button
            onClick={() => autoLayout('COMPACT')}
            disabled={storeNodes.length === 0}
            className="px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 disabled:bg-gray-300 disabled:cursor-not-allowed shadow-md transition-colors text-sm font-medium"
            title="작은 화면에 최적화 (컴팩트 배치)"
          >
            📱 컴팩트
          </button>
        </Panel>
      </ReactFlow>
    </div>
  )
}
