/**
 * 키보드 단축키 Hook
 *
 * 노드 설정 패널에서 사용되는 키보드 단축키를 등록합니다.
 */

import { useEffect } from 'react'

export interface KeyboardShortcutHandlers {
  onSave?: () => void // Cmd/Ctrl+S
  onReset?: () => void // Esc
  onSearch?: () => void // Cmd/Ctrl+K
}

export interface UseKeyboardShortcutsOptions {
  handlers: KeyboardShortcutHandlers
  enabled?: boolean // 단축키 활성화 여부, 기본값 true
}

/**
 * 키보드 단축키 Hook
 *
 * @example
 * useKeyboardShortcuts({
 *   handlers: {
 *     onSave: () => save(),
 *     onReset: () => reset(),
 *     onSearch: () => searchInputRef.current?.focus()
 *   },
 *   enabled: true
 * })
 */
export function useKeyboardShortcuts({
  handlers,
  enabled = true,
}: UseKeyboardShortcutsOptions): void {
  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
      const cmdOrCtrl = isMac ? e.metaKey : e.ctrlKey

      // Cmd/Ctrl+S: 저장
      if (cmdOrCtrl && e.key === 's' && handlers.onSave) {
        e.preventDefault()
        handlers.onSave()
      }

      // Cmd/Ctrl+K: 검색 포커스
      if (cmdOrCtrl && e.key === 'k' && handlers.onSearch) {
        e.preventDefault()
        handlers.onSearch()
      }

      // Esc: 초기화
      if (e.key === 'Escape' && handlers.onReset) {
        e.preventDefault()
        handlers.onReset()
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [handlers, enabled])
}
