/**
 * 노드 설정 패널 (라우터)
 *
 * 선택된 노드 타입에 따라 적절한 설정 컴포넌트를 렌더링합니다.
 *
 * 이 파일은 리팩토링 후 라우터 역할만 수행합니다 (기존 1500줄 → 100줄).
 * 각 노드 타입별 설정은 node-config/ 디렉토리의 컴포넌트에서 관리합니다:
 * - InputNodeConfig.tsx (Input 노드)
 * - WorkerNodeConfig.tsx (Worker 노드)
 */

import React from 'react'
import { useWorkflowStore } from '@/stores/workflowStore'
import { Settings } from 'lucide-react'
import { InputNodeConfig } from './node-config/InputNodeConfig'
import { WorkerNodeConfig } from './node-config/WorkerNodeConfig'
import { ConditionNodeConfig } from './node-config/ConditionNodeConfig'
import { MergeNodeConfig } from './node-config/MergeNodeConfig'

export const NodeConfigPanel: React.FC = () => {
  const getSelectedNode = useWorkflowStore((state) => state.getSelectedNode)
  const selectedNode = getSelectedNode()

  // 노드가 선택되지 않은 경우 - 빈 상태 표시
  if (!selectedNode) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center space-y-3">
          <Settings className="h-12 w-12 text-muted-foreground mx-auto opacity-50" />
          <div className="text-sm text-muted-foreground">
            노드를 선택하면
            <br />
            상세 설정을 편집할 수 있습니다
          </div>
        </div>
      </div>
    )
  }

  // 노드 타입에 따라 적절한 설정 컴포넌트 렌더링
  switch (selectedNode.type) {
    case 'input':
      return <InputNodeConfig node={selectedNode} />

    case 'worker':
      return <WorkerNodeConfig node={selectedNode} />

    case 'condition':
      return <ConditionNodeConfig node={selectedNode} />

    case 'merge':
      return <MergeNodeConfig node={selectedNode} />

    default:
      return (
        <div className="h-full flex items-center justify-center p-6">
          <div className="text-center space-y-3">
            <Settings className="h-12 w-12 text-red-500 mx-auto opacity-50" />
            <div className="text-sm text-red-600">
              알 수 없는 노드 타입: {selectedNode.type}
              <br />
              설정을 표시할 수 없습니다
            </div>
          </div>
        </div>
      )
  }
}
