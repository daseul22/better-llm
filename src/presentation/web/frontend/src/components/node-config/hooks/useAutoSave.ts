/**
 * 자동 저장 Hook
 *
 * 변경사항이 있을 때 지정된 시간 후 자동으로 저장합니다 (debounce).
 */

import { useEffect, useRef } from 'react'

export interface UseAutoSaveOptions {
  hasChanges: boolean
  onSave: () => void
  delay?: number // 밀리초, 기본값 3000 (3초)
  enabled?: boolean // 자동 저장 활성화 여부, 기본값 true
}

/**
 * 자동 저장 Hook
 *
 * @example
 * useAutoSave({
 *   hasChanges: true,
 *   onSave: () => saveFn(),
 *   delay: 3000,
 *   enabled: true
 * })
 */
export function useAutoSave({
  hasChanges,
  onSave,
  delay = 3000,
  enabled = true,
}: UseAutoSaveOptions): void {
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    // 자동 저장이 비활성화되어 있거나 변경사항이 없으면 종료
    if (!enabled || !hasChanges) {
      return
    }

    // 기존 타이머 취소
    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }

    // 새 타이머 설정
    timerRef.current = window.setTimeout(() => {
      console.log(`💾 자동 저장 실행 (${delay}ms 후)`)
      onSave()
    }, delay)

    // 클린업: 타이머 취소
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [hasChanges, onSave, delay, enabled])
}
