/**
 * 워크플로우 템플릿 갤러리
 *
 * 사전 정의된 템플릿을 표시하고 선택할 수 있는 모달 컴포넌트입니다.
 */

import { useState, useEffect } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from './ui/card'
import { Button } from './ui/button'
import { X, Upload, Trash2, Search } from 'lucide-react'
import {
  getTemplates,
  getTemplate,
  deleteTemplate,
  type TemplateMetadata,
  type Workflow,
} from '../lib/api'

interface TemplateGalleryProps {
  onClose: () => void
  onSelectTemplate: (workflow: Workflow) => void
  onImportTemplate: (workflow: Workflow) => void
}

export function TemplateGallery({
  onClose,
  onSelectTemplate,
  onImportTemplate,
}: TemplateGalleryProps) {
  const [templates, setTemplates] = useState<TemplateMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  // 템플릿 목록 로드
  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getTemplates()
      setTemplates(data)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setError(errorMsg)
      console.error('템플릿 목록 로드 실패:', err)
    } finally {
      setLoading(false)
    }
  }

  // 템플릿 선택 핸들러
  const handleSelectTemplate = async (templateId: string) => {
    try {
      const template = await getTemplate(templateId)
      onSelectTemplate(template.workflow)
      onClose()
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      alert(`템플릿 로드 실패: ${errorMsg}`)
    }
  }

  // 템플릿 삭제 핸들러
  const handleDeleteTemplate = async (templateId: string, isBuiltin: boolean) => {
    if (isBuiltin) {
      alert('내장 템플릿은 삭제할 수 없습니다')
      return
    }

    if (!confirm('정말 이 템플릿을 삭제하시겠습니까?')) {
      return
    }

    try {
      await deleteTemplate(templateId)
      await loadTemplates() // 목록 새로고침
      alert('템플릿이 삭제되었습니다')
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      alert(`템플릿 삭제 실패: ${errorMsg}`)
    }
  }

  // Import: JSON 파일에서 워크플로우 읽기
  const handleImportWorkflow = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'application/json,.json'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return

      try {
        const text = await file.text()
        const workflow: Workflow = JSON.parse(text)

        // 기본 유효성 검사
        if (!workflow.nodes || !workflow.edges) {
          throw new Error('유효하지 않은 워크플로우 파일입니다')
        }

        onImportTemplate(workflow)
        onClose()
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err)
        alert(`워크플로우 가져오기 실패: ${errorMsg}`)
      }
    }
    input.click()
  }

  // 카테고리 추출
  const categories = Array.from(new Set(templates.map((t) => t.category)))

  // 필터링된 템플릿
  const filteredTemplates = templates.filter((template) => {
    const matchesSearch =
      !searchQuery ||
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description?.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesCategory = !selectedCategory || template.category === selectedCategory

    return matchesSearch && matchesCategory
  })

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-2xl font-bold">템플릿 갤러리</h2>
            <p className="text-sm text-gray-600 mt-1">
              사전 정의된 워크플로우 템플릿을 선택하거나 직접 가져오세요
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Import/Export 버튼 */}
            <Button
              onClick={handleImportWorkflow}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <Upload className="h-4 w-4" />
              가져오기
            </Button>
            <Button onClick={onClose} variant="ghost" size="sm">
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>

        {/* 필터 & 검색 */}
        <div className="p-6 border-b space-y-4">
          {/* 검색 */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="템플릿 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* 카테고리 필터 */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-gray-700">카테고리:</span>
            <Button
              onClick={() => setSelectedCategory(null)}
              variant={selectedCategory === null ? 'default' : 'outline'}
              size="sm"
            >
              전체
            </Button>
            {categories.map((category) => (
              <Button
                key={category}
                onClick={() => setSelectedCategory(category)}
                variant={selectedCategory === category ? 'default' : 'outline'}
                size="sm"
              >
                {category}
              </Button>
            ))}
          </div>
        </div>

        {/* 템플릿 목록 */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex items-center justify-center h-40">
              <div className="text-gray-500">템플릿 로드 중...</div>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center h-40">
              <div className="text-red-500">오류: {error}</div>
            </div>
          )}

          {!loading && !error && filteredTemplates.length === 0 && (
            <div className="flex items-center justify-center h-40">
              <div className="text-gray-500">템플릿이 없습니다</div>
            </div>
          )}

          {!loading && !error && filteredTemplates.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredTemplates.map((template) => (
                <Card
                  key={template.id}
                  className="hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => handleSelectTemplate(template.id)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-base font-semibold">
                        {template.name}
                      </CardTitle>
                      {template.is_builtin && (
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                          내장
                        </span>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {/* 설명 */}
                    {template.description && (
                      <p className="text-sm text-gray-600 line-clamp-2">
                        {template.description}
                      </p>
                    )}

                    {/* 메타정보 */}
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>{template.node_count} 노드</span>
                      <span>{template.edge_count} 연결</span>
                    </div>

                    {/* 태그 */}
                    {template.tags && template.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {template.tags.slice(0, 3).map((tag) => (
                          <span
                            key={tag}
                            className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                        {template.tags.length > 3 && (
                          <span className="text-xs text-gray-500">
                            +{template.tags.length - 3}
                          </span>
                        )}
                      </div>
                    )}

                    {/* 액션 버튼 */}
                    <div className="flex items-center gap-2 pt-2">
                      <Button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleSelectTemplate(template.id)
                        }}
                        size="sm"
                        className="flex-1"
                      >
                        선택
                      </Button>
                      {!template.is_builtin && (
                        <Button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteTemplate(template.id, template.is_builtin)
                          }}
                          variant="outline"
                          size="sm"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* 푸터 */}
        <div className="p-4 border-t bg-gray-50 text-xs text-gray-600">
          <p>
            💡 팁: 템플릿을 선택하면 현재 워크플로우가 대체됩니다. 백업이 필요하면
            먼저 Export 하세요.
          </p>
        </div>
      </div>
    </div>
  )
}
