/**
 * WorkerButton 컴포넌트
 *
 * NodePanel에서 워커 버튼을 렌더링하는 공통 컴포넌트
 * 드래그 앤 드롭 및 클릭으로 노드 추가 지원
 */

import React from 'react'
import { Button } from '@/components/ui/button'
import { LucideIcon } from 'lucide-react'

interface WorkerButtonProps {
  /** 워커 이름 */
  name: string
  /** 워커 역할/설명 */
  role: string
  /** 아이콘 */
  icon: LucideIcon
  /** 아이콘 색상 클래스 */
  iconColor?: string
  /** 제목 색상 클래스 (선택적) */
  titleColor?: string
  /** 배경색 클래스 (선택적) */
  bgColor?: string
  /** hover 배경색 클래스 */
  hoverBgColor: string
  /** 테두리 색상 클래스 */
  borderColor?: string
  /** 클릭 핸들러 */
  onClick: () => void
  /** 드래그 시작 핸들러 */
  onDragStart: (e: React.DragEvent) => void
  /** 비활성화 여부 */
  disabled?: boolean
}

export const WorkerButton: React.FC<WorkerButtonProps> = ({
  name,
  role,
  icon: Icon,
  iconColor,
  titleColor,
  bgColor = 'bg-white',
  hoverBgColor,
  borderColor,
  onClick,
  onDragStart,
  disabled = false,
}) => {
  return (
    <Button
      variant="outline"
      className={`w-full justify-start text-left ${borderColor ?? ''} ${hoverBgColor} ${bgColor} cursor-grab active:cursor-grabbing disabled:cursor-not-allowed`}
      onClick={onClick}
      draggable={!disabled}
      onDragStart={onDragStart}
      disabled={disabled}
      aria-label={`${name} 워커 추가`}
    >
      <Icon className={`mr-2 h-4 w-4 ${iconColor ?? ''}`} aria-hidden="true" />
      <div className="flex flex-col items-start flex-1">
        <span className={`font-medium ${titleColor ?? ''}`}>{name}</span>
        <span className="text-xs text-muted-foreground line-clamp-2">
          {role}
        </span>
      </div>
    </Button>
  )
}
