/**
 * useAutoLayout 커스텀 훅
 *
 * WorkflowCanvas의 자동 레이아웃 로직을 분리한 커스텀 훅
 * Dagre 라이브러리를 사용하여 노드를 자동으로 배치합니다.
 */

import { useCallback } from 'react'
import dagre from 'dagre'
import { WorkflowNode, WorkflowEdge } from '@/lib/api'

type LayoutDirection = 'TB' | 'LR' | 'COMPACT'

interface LayoutConfig {
  rankdir: 'TB' | 'LR'
  nodesep: number
  ranksep: number
  align?: undefined
  ranker: 'network-simplex'
}

interface UseAutoLayoutProps {
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  updateNodePosition: (nodeId: string, position: { x: number; y: number }) => void
  setLocalNodes: (nodes: WorkflowNode[]) => void
}

export const useAutoLayout = ({
  nodes,
  edges,
  updateNodePosition,
  setLocalNodes,
}: UseAutoLayoutProps) => {
  /**
   * 레이아웃 설정 가져오기
   */
  const getLayoutConfig = useCallback((direction: LayoutDirection): {
    config: LayoutConfig
    nodeWidth: number
    nodeHeight: number
  } => {
    if (direction === 'COMPACT') {
      return {
        config: {
          rankdir: 'TB',
          nodesep: 120,
          ranksep: 80,
          align: undefined,
          ranker: 'network-simplex',
        },
        nodeWidth: 200,
        nodeHeight: 80,
      }
    } else if (direction === 'TB') {
      return {
        config: {
          rankdir: 'TB',
          nodesep: 200,
          ranksep: 120,
          align: undefined,
          ranker: 'network-simplex',
        },
        nodeWidth: 220,
        nodeHeight: 100,
      }
    } else {
      // LR (가로 정렬)
      return {
        config: {
          rankdir: 'LR',
          nodesep: 150,
          ranksep: 250,
          align: undefined,
          ranker: 'network-simplex',
        },
        nodeWidth: 220,
        nodeHeight: 100,
      }
    }
  }, [])

  /**
   * 조건 분기 후처리: true/false 브랜치를 좌우로 벌림
   */
  const adjustConditionBranches = useCallback((
    layoutedNodes: WorkflowNode[],
    direction: LayoutDirection,
    conditionNodes: Set<string>
  ): WorkflowNode[] => {
    return layoutedNodes.map((node) => {
      const parentEdge = edges.find((e) => e.target === node.id)
      if (!parentEdge || !conditionNodes.has(parentEdge.source)) {
        return node
      }

      const isTrueBranch = parentEdge.sourceHandle === 'true'
      const isFalseBranch = parentEdge.sourceHandle === 'false'

      if (direction === 'TB' || direction === 'COMPACT') {
        // 세로 배치: true는 왼쪽, false는 오른쪽으로 이동
        const offset = direction === 'COMPACT' ? 150 : 200
        if (isTrueBranch) {
          return { ...node, position: { ...node.position, x: node.position.x - offset } }
        } else if (isFalseBranch) {
          return { ...node, position: { ...node.position, x: node.position.x + offset } }
        }
      } else {
        // 가로 배치: true는 위, false는 아래로 이동
        const offset = 150
        if (isTrueBranch) {
          return { ...node, position: { ...node.position, y: node.position.y - offset } }
        } else if (isFalseBranch) {
          return { ...node, position: { ...node.position, y: node.position.y + offset } }
        }
      }

      return node
    })
  }, [edges])

  /**
   * 자동 레이아웃 실행
   */
  const autoLayout = useCallback((direction: LayoutDirection = 'TB') => {
    const dagreGraph = new dagre.graphlib.Graph()
    dagreGraph.setDefaultEdgeLabel(() => ({}))

    // 레이아웃 설정
    const { config, nodeWidth, nodeHeight } = getLayoutConfig(direction)
    dagreGraph.setGraph(config)

    // 조건 분기 및 병합 노드 식별
    const conditionNodes = new Set(
      nodes.filter((n) => n.type === 'condition' || n.type === 'loop').map((n) => n.id)
    )
    const mergeNodes = new Set(nodes.filter((n) => n.type === 'merge').map((n) => n.id))

    // 노드 추가 (조건/병합 노드는 크기 조정)
    nodes.forEach((node) => {
      const isSpecialNode = conditionNodes.has(node.id) || mergeNodes.has(node.id)
      dagreGraph.setNode(node.id, {
        width: isSpecialNode ? nodeWidth * 1.2 : nodeWidth,
        height: isSpecialNode ? nodeHeight * 1.2 : nodeHeight,
      })
    })

    // 엣지 추가 (조건 분기는 가중치 부여)
    edges.forEach((edge) => {
      const isFromCondition = conditionNodes.has(edge.source)
      const isTrueEdge = edge.sourceHandle === 'true'
      const isFalseEdge = edge.sourceHandle === 'false'

      let weight = 1
      if (isFromCondition) {
        // true는 왼쪽, false는 오른쪽으로 배치하도록 가중치 조정
        weight = isTrueEdge ? 2 : isFalseEdge ? 2 : 1
      }

      dagreGraph.setEdge(edge.source, edge.target, { weight })
    })

    // 레이아웃 계산
    dagre.layout(dagreGraph)

    // 계산된 위치로 노드 업데이트
    const layoutedNodes = nodes.map((node) => {
      const nodeWithPosition = dagreGraph.node(node.id)
      const isSpecialNode = conditionNodes.has(node.id) || mergeNodes.has(node.id)
      const width = isSpecialNode ? nodeWidth * 1.2 : nodeWidth
      const height = isSpecialNode ? nodeHeight * 1.2 : nodeHeight

      return {
        ...node,
        position: {
          x: nodeWithPosition.x - width / 2,
          y: nodeWithPosition.y - height / 2,
        },
      }
    })

    // 조건 분기 후처리
    const adjustedNodes = adjustConditionBranches(layoutedNodes, direction, conditionNodes)

    // 위치 업데이트
    adjustedNodes.forEach((node) => {
      updateNodePosition(node.id, node.position)
    })

    // 로컬 상태 업데이트
    setLocalNodes(adjustedNodes)

    const layoutName =
      direction === 'COMPACT' ? '컴팩트' : direction === 'TB' ? '세로' : '가로'
    console.log(`자동 레이아웃 적용 완료 (${layoutName}):`, adjustedNodes.length, '개 노드')
  }, [nodes, edges, getLayoutConfig, adjustConditionBranches, updateNodePosition, setLocalNodes])

  return { autoLayout }
}
