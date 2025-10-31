/**
 * 노드 요약 패널
 *
 * 선택된 노드의 간단한 정보를 표시하고, 더블클릭으로 전체 설정을 열 수 있습니다.
 */

import React from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useWorkflowStore } from '@/stores/workflowStore'
import { Settings, MousePointerClick, Zap, Target, GitBranch, Merge as MergeIcon } from 'lucide-react'

interface NodeSummaryPanelProps {
  onOpenFullConfig: () => void
}

export const NodeSummaryPanel: React.FC<NodeSummaryPanelProps> = ({ onOpenFullConfig }) => {
  const getSelectedNode = useWorkflowStore((state) => state.getSelectedNode)
  const selectedNode = getSelectedNode()

  if (!selectedNode) {
    return (
      <Card>
        <CardContent className="pt-6 text-center">
          <Settings className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
          <p className="text-sm text-muted-foreground">노드를 선택하세요</p>
          <p className="text-xs text-muted-foreground mt-1">
            더블클릭으로 상세 설정 열기
          </p>
        </CardContent>
      </Card>
    )
  }

  // 노드 타입별 아이콘
  const getNodeIcon = () => {
    switch (selectedNode.type) {
      case 'input':
        return <Target className="h-5 w-5 text-blue-600" />
      case 'worker':
        return <Zap className="h-5 w-5 text-purple-600" />
      case 'condition':
        return <GitBranch className="h-5 w-5 text-orange-600" />
      case 'merge':
        return <MergeIcon className="h-5 w-5 text-green-600" />
      default:
        return <Settings className="h-5 w-5 text-gray-600" />
    }
  }

  // 노드 타입별 색상
  const getNodeColor = () => {
    switch (selectedNode.type) {
      case 'input':
        return 'bg-blue-100 text-blue-800'
      case 'worker':
        return 'bg-purple-100 text-purple-800'
      case 'condition':
        return 'bg-orange-100 text-orange-800'
      case 'merge':
        return 'bg-green-100 text-green-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  // 간단한 정보 표시
  const renderSummary = () => {
    switch (selectedNode.type) {
      case 'input':
        return (
          <div className="space-y-2">
            <div className="text-sm">
              <span className="font-medium">입력 프롬프트:</span>
              <p className="text-muted-foreground mt-1 line-clamp-3">
                {selectedNode.data.prompt || '(설정되지 않음)'}
              </p>
            </div>
          </div>
        )
      case 'worker':
        return (
          <div className="space-y-2">
            <div className="text-sm">
              <span className="font-medium">에이전트:</span>
              <p className="text-muted-foreground mt-1">
                {selectedNode.data.agent_name || '(알 수 없음)'}
              </p>
            </div>
            <div className="text-sm">
              <span className="font-medium">작업:</span>
              <p className="text-muted-foreground mt-1 line-clamp-2">
                {selectedNode.data.task_template || '(설정되지 않음)'}
              </p>
            </div>
            {selectedNode.data.allowed_tools && selectedNode.data.allowed_tools.length > 0 && (
              <div className="text-sm">
                <span className="font-medium">도구:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {selectedNode.data.allowed_tools.slice(0, 3).map((tool: string) => (
                    <Badge key={tool} variant="outline" className="text-xs">
                      {tool}
                    </Badge>
                  ))}
                  {selectedNode.data.allowed_tools.length > 3 && (
                    <Badge variant="outline" className="text-xs">
                      +{selectedNode.data.allowed_tools.length - 3}
                    </Badge>
                  )}
                </div>
              </div>
            )}
          </div>
        )
      case 'condition':
        return (
          <div className="space-y-2">
            <div className="text-sm">
              <span className="font-medium">조건:</span>
              <p className="text-muted-foreground mt-1 line-clamp-2">
                {selectedNode.data.condition || '(설정되지 않음)'}
              </p>
            </div>
          </div>
        )
      case 'merge':
        return (
          <div className="space-y-2">
            <div className="text-sm">
              <span className="font-medium">병합 전략:</span>
              <p className="text-muted-foreground mt-1">
                {selectedNode.data.merge_strategy || 'concatenate'}
              </p>
            </div>
          </div>
        )
      default:
        return <p className="text-sm text-muted-foreground">정보 없음</p>
    }
  }

  return (
    <Card className="border-2 border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {getNodeIcon()}
            <CardTitle className="text-base">{selectedNode.data.agent_name || selectedNode.type}</CardTitle>
          </div>
          <Badge className={getNodeColor()}>{selectedNode.type}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {renderSummary()}

        <Button
          onClick={onOpenFullConfig}
          className="w-full"
          variant="outline"
          size="sm"
        >
          <MousePointerClick className="mr-2 h-4 w-4" />
          전체 설정 열기 (더블클릭)
        </Button>
      </CardContent>
    </Card>
  )
}
