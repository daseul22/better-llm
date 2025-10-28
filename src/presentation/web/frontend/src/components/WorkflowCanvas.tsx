/**
 * 워크플로우 캔버스 컴포넌트 (React Flow)
 *
 * 워커 노드를 드래그 앤 드롭으로 배치하고 연결합니다.
 */

import React, { useCallback, useRef } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
  NodeTypes,
  useReactFlow,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { WorkerNode } from './WorkerNode'
import { ManagerNode } from './ManagerNode'
import { InputNode } from './InputNode'
import { useWorkflowStore } from '@/stores/workflowStore'
import { WorkflowNode, WorkflowEdge } from '@/lib/api'

// 커스텀 노드 타입 등록
const nodeTypes: NodeTypes = {
  worker: WorkerNode,
  manager: ManagerNode,
  input: InputNode,
}

export const WorkflowCanvas: React.FC = () => {
  const {
    nodes: storeNodes,
    edges: storeEdges,
    setNodes,
    setEdges,
    addNode,
    addEdge: addStoreEdge,
    deleteNode,
    deleteEdge,
    execution,
    setSelectedNodeId,
  } = useWorkflowStore()

  // React Flow의 노드/엣지 상태 (로컬)
  const [nodes, setLocalNodes, onNodesChange] = useNodesState(storeNodes)
  const [edges, setLocalEdges, onEdgesChange] = useEdgesState(storeEdges)

  // React Flow 인스턴스 (좌표 변환에 필요)
  const { project } = useReactFlow()
  const reactFlowWrapper = useRef<HTMLDivElement>(null)

  // Zustand 상태와 로컬 상태 동기화
  React.useEffect(() => {
    setLocalNodes(storeNodes)
  }, [storeNodes, setLocalNodes])

  React.useEffect(() => {
    // Zustand에서 로드된 엣지에도 화살표 및 스타일 적용
    const edgesWithMarkers = storeEdges.map((edge) => ({
      ...edge,
      type: 'default',
      animated: true,
      style: { stroke: '#3b82f6', strokeWidth: 2 },
      markerEnd: {
        type: 'arrowclosed' as const,
        color: '#3b82f6',
      },
    }))
    setLocalEdges(edgesWithMarkers as any)
  }, [storeEdges, setLocalEdges])

  // 실행 상태 표시 (노드 데이터 및 엣지 스타일 업데이트)
  React.useEffect(() => {
    // 노드 상태 업데이트
    setLocalNodes((nds) =>
      nds.map((node) => {
        const isExecuting = execution.currentNodeId === node.id
        const isCompleted = execution.nodeOutputs[node.id] !== undefined
        const hasError = execution.logs.some(
          (log) => log.nodeId === node.id && log.type === 'error'
        )

        return {
          ...node,
          data: {
            ...node.data,
            isExecuting,
            isCompleted,
            hasError,
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
  }, [execution.currentNodeId, execution.nodeOutputs, execution.logs, setLocalNodes, setLocalEdges])

  // 노드 변경 핸들러 (삭제 포함)
  const handleNodesChange: OnNodesChange = useCallback(
    (changes) => {
      onNodesChange(changes)

      // 삭제된 노드를 Zustand에 반영
      changes.forEach((change) => {
        if (change.type === 'remove') {
          deleteNode(change.id)
        }
      })

      // 위치 변경을 Zustand에 반영
      setLocalNodes((nds) => {
        setNodes(nds as WorkflowNode[])
        return nds
      })
    },
    [onNodesChange, deleteNode, setNodes, setLocalNodes]
  )

  // 엣지 변경 핸들러 (삭제 포함)
  const handleEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      onEdgesChange(changes)

      // 삭제된 엣지를 Zustand에 반영
      changes.forEach((change) => {
        if (change.type === 'remove') {
          deleteEdge(change.id)
        }
      })

      // Zustand에 반영
      setLocalEdges((eds) => {
        setEdges(eds as WorkflowEdge[])
        return eds
      })
    },
    [onEdgesChange, deleteEdge, setEdges, setLocalEdges]
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

  // 노드 클릭 핸들러 (선택)
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      setSelectedNodeId(node.id)
    },
    [setSelectedNodeId]
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
        onPaneClick={handlePaneClick}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={nodeTypes}
        fitView
        className="bg-gray-50"
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  )
}
