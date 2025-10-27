/**
 * 워크플로우 캔버스 컴포넌트 (React Flow)
 *
 * 워커 노드를 드래그 앤 드롭으로 배치하고 연결합니다.
 */

import React, { useCallback } from 'react'
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
} from 'reactflow'
import 'reactflow/dist/style.css'

import { WorkerNode } from './WorkerNode'
import { ManagerNode } from './ManagerNode'
import { useWorkflowStore } from '@/stores/workflowStore'
import { WorkflowNode, WorkflowEdge } from '@/lib/api'

// 커스텀 노드 타입 등록
const nodeTypes: NodeTypes = {
  worker: WorkerNode,
  manager: ManagerNode,
}

export const WorkflowCanvas: React.FC = () => {
  const {
    nodes: storeNodes,
    edges: storeEdges,
    setNodes,
    setEdges,
    addEdge: addStoreEdge,
    deleteNode,
    deleteEdge,
    execution,
    setSelectedNodeId,
    setRightPanelMode,
  } = useWorkflowStore()

  // React Flow의 노드/엣지 상태 (로컬)
  const [nodes, setLocalNodes, onNodesChange] = useNodesState(storeNodes)
  const [edges, setLocalEdges, onEdgesChange] = useEdgesState(storeEdges)

  // Zustand 상태와 로컬 상태 동기화
  React.useEffect(() => {
    setLocalNodes(storeNodes)
  }, [storeNodes, setLocalNodes])

  React.useEffect(() => {
    setLocalEdges(storeEdges)
  }, [storeEdges, setLocalEdges])

  // 실행 상태 표시 (노드 데이터 업데이트)
  React.useEffect(() => {
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
  }, [execution.currentNodeId, execution.nodeOutputs, execution.logs, setLocalNodes])

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

      setLocalEdges((eds) => addEdge(connection, eds))
      addStoreEdge(newEdge)
    },
    [setLocalEdges, addStoreEdge]
  )

  // 노드 클릭 핸들러 (선택 + 패널 전환)
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      setSelectedNodeId(node.id)
      setRightPanelMode('node-config')
    },
    [setSelectedNodeId, setRightPanelMode]
  )

  // 캔버스 클릭 핸들러 (선택 해제 + 패널 전환)
  const handlePaneClick = useCallback(() => {
    setSelectedNodeId(null)
    setRightPanelMode('execution')
  }, [setSelectedNodeId, setRightPanelMode])

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={handleConnect}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
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
