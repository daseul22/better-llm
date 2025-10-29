/**
 * 자동 스크롤 커스텀 훅
 *
 * 스트리밍 출력 시 자동으로 스크롤을 맨 아래로 이동하는 기능을 제공합니다.
 * 사용자가 수동으로 스크롤하면 자동 스크롤을 일시 중지합니다.
 */

import { useEffect, useState, RefObject } from 'react'

interface UseAutoScrollOptions {
  /** 스크롤할 컨테이너 ref */
  containerRef: RefObject<HTMLDivElement>
  /** 스크롤을 트리거할 의존성 (예: 출력 텍스트) */
  dependencies: any[]
  /** 자동 스크롤을 활성화할 조건 (예: step === 'generating') */
  enabled: boolean
}

interface UseAutoScrollReturn {
  /** 자동 스크롤 활성화 여부 */
  autoScroll: boolean
  /** 맨 아래로 스크롤하는 함수 */
  scrollToBottom: () => void
  /** 스크롤 이벤트 핸들러 (컨테이너에 연결) */
  handleScroll: () => void
}

/**
 * 자동 스크롤 훅
 *
 * @example
 * const { autoScroll, scrollToBottom, handleScroll } = useAutoScroll({
 *   containerRef: outputContainerRef,
 *   dependencies: [generatedOutput],
 *   enabled: step === 'generating'
 * })
 *
 * <div ref={outputContainerRef} onScroll={handleScroll}>
 *   {!autoScroll && <button onClick={scrollToBottom}>맨 아래로</button>}
 * </div>
 */
export const useAutoScroll = ({
  containerRef,
  dependencies,
  enabled,
}: UseAutoScrollOptions): UseAutoScrollReturn => {
  const [autoScroll, setAutoScroll] = useState(true)

  // 자동 스크롤 (의존성 변경 시)
  useEffect(() => {
    if (autoScroll && containerRef.current && enabled) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [...dependencies, autoScroll, enabled])

  // 스크롤 이벤트 핸들러 (수동 스크롤 감지)
  const handleScroll = () => {
    if (!containerRef.current) return

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50

    setAutoScroll(isAtBottom)
  }

  // 맨 아래로 스크롤
  const scrollToBottom = () => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: 'smooth',
      })
      setAutoScroll(true)
    }
  }

  return {
    autoScroll,
    scrollToBottom,
    handleScroll,
  }
}
