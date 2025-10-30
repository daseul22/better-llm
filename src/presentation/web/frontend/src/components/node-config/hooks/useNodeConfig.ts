/**
 * 노드 설정 공통 로직 Hook
 *
 * 변경사항을 즉시 Zustand 스토어에 반영합니다.
 * 개별 저장 버튼은 제거되고, 워크플로우 저장 버튼으로 파일에 저장됩니다.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useWorkflowStore } from '@/stores/workflowStore'

export interface UseNodeConfigOptions<T> {
  nodeId: string
  initialData: T
  onValidate?: (data: T) => Record<string, string> // 검증 함수 (에러 객체 반환)
}

export interface UseNodeConfigReturn<T> {
  data: T
  setData: (data: T | ((prev: T) => T)) => void
  hasChanges: boolean  // 항상 false (호환성 유지용)
  saveMessage: string | null  // 항상 null (호환성 유지용)
  save: () => void  // 더 이상 사용되지 않음 (호환성 유지용)
  reset: () => void
}

/**
 * 노드 설정 공통 로직 Hook
 *
 * 변경사항은 디바운스(300ms) 후 자동으로 스토어에 반영됩니다.
 *
 * @example
 * const { data, setData, reset } = useNodeConfig({
 *   nodeId: selectedNode.id,
 *   initialData: { taskTemplate: '', outputFormat: 'plain_text' },
 * })
 */
export function useNodeConfig<T extends Record<string, any>>({
  nodeId,
  initialData,
  onValidate,
}: UseNodeConfigOptions<T>): UseNodeConfigReturn<T> {
  const updateNode = useWorkflowStore((state) => state.updateNode)

  const [data, setData] = useState<T>(initialData)
  const isInitialMount = useRef(true)
  const debounceTimer = useRef<NodeJS.Timeout | null>(null)

  // 초기 데이터 변경 시 로컬 상태 업데이트
  useEffect(() => {
    setData(initialData)
  }, [JSON.stringify(initialData)])

  // 데이터 변경 시 자동으로 스토어에 반영 (디바운스 적용)
  useEffect(() => {
    // 첫 마운트 시에는 스킵
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }

    // 초기 데이터와 동일하면 스킵
    if (JSON.stringify(data) === JSON.stringify(initialData)) {
      return
    }

    // 이전 타이머 취소
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current)
    }

    // 300ms 디바운스 후 스토어 업데이트
    debounceTimer.current = setTimeout(() => {
      // 검증 (실패 시 업데이트 안 함)
      if (onValidate) {
        const errors = onValidate(data)
        if (Object.keys(errors).length > 0) {
          console.warn('⚠️ 검증 실패 (스토어 업데이트 안 함):', errors)
          return
        }
      }

      // Zustand 스토어 업데이트
      updateNode(nodeId, data)
      console.log('💾 노드 설정 자동 저장:', { nodeId, data })
    }, 300)

    // 클린업
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current)
      }
    }
  }, [data, nodeId, updateNode, onValidate])

  // save() - 호환성 유지용 (더 이상 사용되지 않음)
  const save = useCallback(() => {
    console.log('ℹ️ save() 호출됨 (변경사항은 이미 스토어에 반영되어 있음)')
  }, [])

  // 초기화
  const reset = useCallback(() => {
    setData(initialData)
  }, [initialData])

  return {
    data,
    setData,
    hasChanges: false,  // 항상 false (호환성 유지용)
    saveMessage: null,  // 항상 null (호환성 유지용)
    save,
    reset,
  }
}
