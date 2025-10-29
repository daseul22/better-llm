/**
 * 자동 레이아웃 유틸리티
 *
 * Dagre 라이브러리를 사용하여 워크플로우 노드를 계층적으로 배치합니다.
 */

import dagre from 'dagre'
import type { WorkflowNode, WorkflowEdge } from './api'

/**
 * 노드와 엣지를 계층적으로 자동 배치합니다.
 *
 * @param nodes - 워크플로우 노드 배열
 * @param edges - 워크플로우 엣지 배열
 * @param direction - 레이아웃 방향 ('TB' = 위→아래, 'LR' = 왼쪽→오른쪽)
 * @returns 위치가 업데이트된 노드 배열
 */
export function getLayoutedNodes(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  direction: 'TB' | 'LR' = 'LR'
): WorkflowNode[] {
  // dagre 그래프 생성
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))

  // 그래프 설정
  dagreGraph.setGraph({
    rankdir: direction,      // 레이아웃 방향
    nodesep: 100,            // 노드 간 수평 간격
    ranksep: 200,            // 레벨 간 수직 간격
    marginx: 50,             // 좌우 여백
    marginy: 50,             // 상하 여백
  })

  // 노드별 기본 크기 (노드 타입에 따라 다를 수 있음)
  const getNodeDimensions = (node: WorkflowNode) => {
    switch (node.type) {
      case 'input':
        return { width: 300, height: 150 }
      case 'worker':
        return { width: 300, height: 200 }
      case 'condition':
        return { width: 250, height: 180 }
      case 'loop':
        return { width: 250, height: 150 }
      case 'merge':
        return { width: 250, height: 150 }
      default:
        return { width: 250, height: 150 }
    }
  }

  // 노드 추가
  nodes.forEach((node) => {
    const dimensions = getNodeDimensions(node)
    dagreGraph.setNode(node.id, dimensions)
  })

  // 엣지 추가
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  // 레이아웃 계산
  dagre.layout(dagreGraph)

  // 계산된 위치를 노드에 적용
  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    const dimensions = getNodeDimensions(node)

    // dagre는 노드 중심점을 반환하므로, 좌상단 좌표로 변환
    const x = nodeWithPosition.x - dimensions.width / 2
    const y = nodeWithPosition.y - dimensions.height / 2

    return {
      ...node,
      position: {
        x: Math.round(x),
        y: Math.round(y),
      },
    }
  })

  return layoutedNodes
}

/**
 * 워크플로우 전체를 자동 배치합니다.
 *
 * @param workflow - 노드와 엣지를 포함한 워크플로우 객체
 * @param direction - 레이아웃 방향
 * @returns 위치가 업데이트된 워크플로우 객체
 */
export function layoutWorkflow(
  workflow: { nodes: WorkflowNode[]; edges: WorkflowEdge[] },
  direction: 'TB' | 'LR' = 'LR'
): { nodes: WorkflowNode[]; edges: WorkflowEdge[] } {
  const layoutedNodes = getLayoutedNodes(workflow.nodes, workflow.edges, direction)

  return {
    nodes: layoutedNodes,
    edges: workflow.edges,
  }
}
