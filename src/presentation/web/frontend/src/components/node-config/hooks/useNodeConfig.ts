/**
 * 노드 설정 공통 로직 Hook
 *
 * 저장, 초기화, 변경사항 추적 등 노드 설정 패널에서 공통으로 사용되는 로직을 제공합니다.
 */

import { useState, useEffect, useCallback } from 'react'
import { useWorkflowStore } from '@/stores/workflowStore'

export interface UseNodeConfigOptions<T> {
  nodeId: string
  initialData: T
  onValidate?: (data: T) => Record<string, string> // 검증 함수 (에러 객체 반환)
}

export interface UseNodeConfigReturn<T> {
  data: T
  setData: (data: T | ((prev: T) => T)) => void
  hasChanges: boolean
  saveMessage: string | null
  save: () => void
  reset: () => void
}

/**
 * 노드 설정 공통 로직 Hook
 *
 * @example
 * const { data, setData, hasChanges, save, reset } = useNodeConfig({
 *   nodeId: selectedNode.id,
 *   initialData: { taskTemplate: '', outputFormat: 'plain_text' },
 *   onValidate: (data) => {
 *     const errors = {}
 *     if (!data.taskTemplate) errors.taskTemplate = '작업 템플릿을 입력하세요'
 *     return errors
 *   }
 * })
 */
export function useNodeConfig<T extends Record<string, any>>({
  nodeId,
  initialData,
  onValidate,
}: UseNodeConfigOptions<T>): UseNodeConfigReturn<T> {
  const updateNode = useWorkflowStore((state) => state.updateNode)

  const [data, setData] = useState<T>(initialData)
  const [hasChanges, setHasChanges] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  // 초기 데이터 변경 시 로컬 상태 업데이트
  useEffect(() => {
    setData(initialData)
    setHasChanges(false)
  }, [JSON.stringify(initialData)]) // initialData 객체 비교

  // 변경사항 추적
  useEffect(() => {
    const changed = JSON.stringify(data) !== JSON.stringify(initialData)
    setHasChanges(changed)
  }, [data, JSON.stringify(initialData)])

  // 저장
  const save = useCallback(() => {
    // 검증
    if (onValidate) {
      const errors = onValidate(data)
      if (Object.keys(errors).length > 0) {
        console.warn('검증 실패:', errors)
        setSaveMessage('❌ 검증 실패')
        setTimeout(() => setSaveMessage(null), 3000)
        return
      }
    }

    // Zustand 스토어 업데이트
    updateNode(nodeId, data)
    setHasChanges(false)
    setSaveMessage('✅ 저장됨')

    // 3초 후 메시지 제거
    setTimeout(() => setSaveMessage(null), 3000)

    console.log('💾 노드 설정 저장:', { nodeId, data })
  }, [nodeId, data, updateNode, onValidate])

  // 초기화
  const reset = useCallback(() => {
    setData(initialData)
    setHasChanges(false)
    setSaveMessage(null)
  }, [initialData])

  return {
    data,
    setData,
    hasChanges,
    saveMessage,
    save,
    reset,
  }
}
