/**
 * 입력 필드 힌트 컴포넌트
 *
 * 필드 아래에 표시되는 작은 힌트 텍스트와 툴팁 아이콘
 */

import React from 'react'
import { Info } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './tooltip'
import { cn } from '@/lib/utils'

interface FieldHintProps {
  /** 짧은 힌트 텍스트 (필드 아래 표시) */
  hint: string
  /** 긴 설명 (툴팁에 표시, 선택사항) */
  tooltip?: string
  /** 커스텀 className */
  className?: string
}

export const FieldHint: React.FC<FieldHintProps> = ({ hint, tooltip, className }) => {
  return (
    <div className={cn('flex items-start gap-1 mt-1', className)}>
      <p className="text-xs text-muted-foreground flex-1">{hint}</p>
      {tooltip && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="h-3 w-3 text-muted-foreground cursor-help flex-shrink-0 mt-0.5" />
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-xs">
              <p className="text-sm">{tooltip}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  )
}
