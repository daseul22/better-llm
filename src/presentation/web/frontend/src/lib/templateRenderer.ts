/**
 * 템플릿 렌더링 유틸리티
 *
 * {{input}}, {{node_X}} 등의 템플릿 변수를 실제 값으로 치환합니다.
 */

import { WorkflowNode } from './api'

export interface TemplateContext {
  input?: string
  nodes?: Record<string, string> // node_id => output
}

/**
 * 템플릿 문자열을 렌더링합니다.
 *
 * @param template 템플릿 문자열 (예: "{{input}}을 분석하고 {{node_1}}을 참고하세요")
 * @param context 컨텍스트 (input, nodes)
 * @returns 렌더링된 문자열
 */
export function renderTemplate(template: string, context: TemplateContext): string {
  if (!template) return ''

  let rendered = template

  // {{input}} 치환
  if (context.input !== undefined) {
    rendered = rendered.replace(/\{\{input\}\}/g, context.input)
  }

  // {{node_X}} 치환
  if (context.nodes) {
    Object.keys(context.nodes).forEach((nodeId) => {
      const output = context.nodes![nodeId]
      // node_X 형식 또는 직접 nodeId
      const patterns = [
        new RegExp(`\\{\\{${nodeId}\\}\\}`, 'g'),
        new RegExp(`\\{\\{node_${nodeId}\\}\\}`, 'g'),
      ]
      patterns.forEach((pattern) => {
        rendered = rendered.replace(pattern, output)
      })
    })
  }

  return rendered
}

/**
 * 템플릿에서 사용된 변수 목록을 추출합니다.
 *
 * @param template 템플릿 문자열
 * @returns 변수 이름 배열 (예: ['input', 'node_1', 'node_2'])
 */
export function extractTemplateVariables(template: string): string[] {
  if (!template) return []

  const pattern = /\{\{(\w+)\}\}/g
  const matches: string[] = []
  let match

  while ((match = pattern.exec(template)) !== null) {
    matches.push(match[1])
  }

  // 중복 제거
  return Array.from(new Set(matches))
}

/**
 * 템플릿이 유효한지 검증합니다.
 *
 * @param template 템플릿 문자열
 * @param availableNodeIds 사용 가능한 노드 ID 목록
 * @returns 유효하면 null, 아니면 에러 메시지
 */
export function validateTemplate(
  template: string,
  availableNodeIds: string[]
): string | null {
  if (!template) return '템플릿이 비어있습니다'

  const variables = extractTemplateVariables(template)

  for (const variable of variables) {
    // 'input'은 항상 유효
    if (variable === 'input') continue

    // 'node_'로 시작하거나 노드 ID 직접 참조
    const isNodeReference =
      variable.startsWith('node_') || availableNodeIds.includes(variable)

    if (!isNodeReference) {
      return `유효하지 않은 변수입니다: {{${variable}}}`
    }

    // 노드 ID 참조인데 존재하지 않는 경우
    if (availableNodeIds.length > 0) {
      const referencedNodeId = variable.startsWith('node_')
        ? variable.substring(5)
        : variable

      if (
        referencedNodeId !== variable &&
        !availableNodeIds.includes(referencedNodeId)
      ) {
        return `존재하지 않는 노드를 참조합니다: {{${variable}}}`
      }
    }
  }

  return null
}

/**
 * 템플릿 프리뷰를 생성합니다 (예시 값으로 렌더링).
 *
 * @param template 템플릿 문자열
 * @param workflowNodes 워크플로우의 모든 노드
 * @param currentNodeId 현재 노드 ID (제외용)
 * @returns 프리뷰 문자열
 */
export function generateTemplatePreview(
  template: string,
  workflowNodes: WorkflowNode[],
  currentNodeId?: string
): string {
  const context: TemplateContext = {
    input: '[초기 입력 예시]',
    nodes: {},
  }

  // 다른 노드들의 출력 예시 생성
  workflowNodes.forEach((node) => {
    if (node.id === currentNodeId) return // 현재 노드 제외

    let exampleOutput = '[노드 출력 예시]'

    // 노드 타입별로 예시 텍스트 커스터마이징
    if (node.type === 'worker' && typeof node.data === 'object' && 'agent_name' in node.data) {
      const agentName = node.data.agent_name
      switch (agentName) {
        case 'planner':
          exampleOutput = '[계획 수립 결과]'
          break
        case 'coder':
          exampleOutput = '[생성된 코드]'
          break
        case 'reviewer':
          exampleOutput = '[리뷰 의견]'
          break
        case 'tester':
          exampleOutput = '[테스트 결과]'
          break
        default:
          exampleOutput = `[${agentName} 출력]`
      }
    } else if (node.type === 'manager') {
      exampleOutput = '[Manager 통합 결과]'
    } else if (node.type === 'input') {
      exampleOutput = '[초기 입력]'
    }

    context.nodes![node.id] = exampleOutput
  })

  return renderTemplate(template, context)
}
