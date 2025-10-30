/**
 * 자동 스크롤 컨테이너 컴포넌트
 *
 * 내용이 업데이트될 때 자동으로 맨 아래로 스크롤합니다.
 * 사용자가 수동으로 스크롤하면 자동 스크롤이 일시 중지됩니다.
 */

import React, { useRef, useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { ArrowDown } from 'lucide-react'

interface AutoScrollContainerProps {
  children: React.ReactNode
  className?: string
  maxHeight?: string
  dependency?: any // 이 값이 변경되면 자동 스크롤 트리거
}

export const AutoScrollContainer: React.FC<AutoScrollContainerProps> = ({
  children,
  className = '',
  maxHeight = '500px',
  dependency,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // 자동 스크롤 (dependency가 변경될 때만)
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [dependency, autoScroll])

  // 스크롤 이벤트 핸들러 (수동 스크롤 감지)
  const handleScroll = () => {
    if (!containerRef.current) return

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50 // 50px 여유

    // 맨 아래에 있으면 자동 스크롤 활성화, 아니면 비활성화
    setAutoScroll(isAtBottom)
  }

  // 맨 아래로 스크롤 버튼
  const scrollToBottom = () => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: 'smooth'
      })
      setAutoScroll(true)
    }
  }

  return (
    <div className="relative">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="overflow-y-auto scroll-smooth"
        style={{ height: maxHeight, maxHeight }}
      >
        {/* 자동 스크롤 비활성화 알림 (스크롤 컨테이너 내부 상단에 sticky) */}
        {!autoScroll && (
          <div className="sticky top-0 z-10 flex justify-center mb-2">
            <div className="bg-gray-800 text-white text-xs px-3 py-1.5 rounded-full shadow-lg">
              자동 스크롤 일시 중지됨
            </div>
          </div>
        )}

        <div className={className}>
          {children}
        </div>
      </div>

      {/* 맨 아래로 버튼 (컨테이너 외부 우측 하단) */}
      {!autoScroll && (
        <div className="absolute bottom-2 right-2">
          <Button
            size="sm"
            variant="outline"
            onClick={scrollToBottom}
            className="h-8 px-3 text-xs shadow-lg"
          >
            <ArrowDown className="h-3 w-3 mr-1" />
            맨 아래로
          </Button>
        </div>
      )}
    </div>
  )
}
