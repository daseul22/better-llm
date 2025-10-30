/**
 * WorkerSection 컴포넌트
 *
 * NodePanel에서 섹션(범용/특화/커스텀 워커)을 렌더링하는 공통 컴포넌트
 * 중복 제거 및 재사용성 향상
 */

import React, { ReactNode } from 'react'
import { ChevronDown, ChevronUp, LucideIcon } from 'lucide-react'

interface WorkerSectionProps {
  /** 섹션 ID (토글 상태 관리용) */
  sectionId: string
  /** 섹션 제목 */
  title: string
  /** 섹션 아이콘 */
  icon: LucideIcon
  /** 항목 개수 (배지 표시) */
  itemCount: number
  /** 확장 여부 */
  isExpanded: boolean
  /** 토글 핸들러 */
  onToggle: (sectionId: string) => void
  /** 섹션 배경색 클래스 */
  bgColor: string
  /** 섹션 hover 배경색 클래스 */
  hoverBgColor: string
  /** 아이콘 색상 클래스 */
  iconColor: string
  /** 제목 색상 클래스 */
  titleColor: string
  /** 배지 배경색 클래스 */
  badgeBgColor: string
  /** 배지 텍스트 색상 클래스 */
  badgeTextColor: string
  /** 자식 컴포넌트 */
  children: ReactNode
}

export const WorkerSection: React.FC<WorkerSectionProps> = ({
  sectionId,
  title,
  icon: Icon,
  itemCount,
  isExpanded,
  onToggle,
  bgColor,
  hoverBgColor,
  iconColor,
  titleColor,
  badgeBgColor,
  badgeTextColor,
  children,
}) => {
  return (
    <div className={`border rounded-lg overflow-hidden ${bgColor}`}>
      <button
        onClick={() => onToggle(sectionId)}
        className={`w-full flex items-center justify-between p-3 ${hoverBgColor} transition-colors`}
        aria-expanded={isExpanded}
        aria-controls={`${sectionId}-content`}
      >
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 ${iconColor}`} aria-hidden="true" />
          <span className={`font-semibold text-sm ${titleColor}`}>{title}</span>
          <span className={`text-xs px-2 py-0.5 ${badgeBgColor} ${badgeTextColor} rounded-full`}>
            {itemCount}
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className={`h-4 w-4 ${iconColor}`} aria-hidden="true" />
        ) : (
          <ChevronDown className={`h-4 w-4 ${iconColor}`} aria-hidden="true" />
        )}
      </button>
      {isExpanded && (
        <div id={`${sectionId}-content`} className="p-3 pt-0 space-y-2" role="region">
          {children}
        </div>
      )}
    </div>
  )
}
