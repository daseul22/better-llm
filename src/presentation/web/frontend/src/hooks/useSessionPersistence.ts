/**
 * 세션 영속성 커스텀 훅
 *
 * localStorage를 사용하여 진행 중인 세션을 저장하고 복구하는 기능을 제공합니다.
 * 새로고침이나 백그라운드 실행 후 세션 복구에 사용됩니다.
 */

import { useCallback } from 'react'

interface Session {
  session_id: string
  status: 'generating' | 'completed' | 'error'
  [key: string]: any
}

interface UseSessionPersistenceOptions {
  /** localStorage 키 */
  storageKey: string
}

interface UseSessionPersistenceReturn {
  /** 세션 저장 */
  saveSession: (session: Session) => void
  /** 세션 로드 */
  loadSession: () => Session | null
  /** 세션 제거 */
  clearSession: () => void
}

/**
 * 세션 영속성 훅
 *
 * @example
 * const { saveSession, loadSession, clearSession } = useSessionPersistence({
 *   storageKey: 'custom_worker_session'
 * })
 *
 * // 세션 저장
 * saveSession({
 *   session_id: 'cw-123',
 *   status: 'generating',
 *   requirements: 'Create a worker...'
 * })
 *
 * // 세션 복구
 * const session = loadSession()
 * if (session?.status === 'generating') {
 *   // 재접속 로직
 * }
 *
 * // 완료 후 정리
 * clearSession()
 */
export const useSessionPersistence = ({
  storageKey,
}: UseSessionPersistenceOptions): UseSessionPersistenceReturn => {
  /** 세션 저장 */
  const saveSession = useCallback(
    (session: Session) => {
      try {
        localStorage.setItem(storageKey, JSON.stringify(session))
      } catch (error) {
        console.error('세션 저장 실패:', error)
      }
    },
    [storageKey]
  )

  /** 세션 로드 */
  const loadSession = useCallback((): Session | null => {
    try {
      const stored = localStorage.getItem(storageKey)
      return stored ? JSON.parse(stored) : null
    } catch (error) {
      console.error('세션 로드 실패:', error)
      return null
    }
  }, [storageKey])

  /** 세션 제거 */
  const clearSession = useCallback(() => {
    try {
      localStorage.removeItem(storageKey)
    } catch (error) {
      console.error('세션 제거 실패:', error)
    }
  }, [storageKey])

  return {
    saveSession,
    loadSession,
    clearSession,
  }
}
