/**
 * 디렉토리 브라우저 컴포넌트
 *
 * 파일 시스템을 탐색하고 디렉토리를 선택할 수 있는 UI
 */

import React, { useState, useEffect } from 'react'
import { browseDirectory, getHomeDirectory, DirectoryBrowseResponse } from '@/lib/api'
import { Button } from './ui/button'
import { Folder, FolderOpen, Home, ArrowLeft, Loader2 } from 'lucide-react'

interface DirectoryBrowserProps {
  onSelectDirectory: (path: string) => void
  onCancel: () => void
}

export const DirectoryBrowser: React.FC<DirectoryBrowserProps> = ({
  onSelectDirectory,
  onCancel,
}) => {
  const [browseData, setBrowseData] = useState<DirectoryBrowseResponse | null>(null)
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 초기 로드 (홈 디렉토리)
  useEffect(() => {
    loadHomeDirectory()
  }, [])

  // ESC 키 핸들링
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onCancel])

  const loadHomeDirectory = async () => {
    try {
      setLoading(true)
      setError(null)

      const homeData = await getHomeDirectory()
      const browseResult = await browseDirectory(homeData.home_path)

      setBrowseData(browseResult)
      setSelectedPath(null)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setError(`홈 디렉토리 로드 실패: ${errorMsg}`)
    } finally {
      setLoading(false)
    }
  }

  const loadDirectory = async (path: string) => {
    try {
      setLoading(true)
      setError(null)

      const browseResult = await browseDirectory(path)

      setBrowseData(browseResult)
      setSelectedPath(null)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setError(`디렉토리 로드 실패: ${errorMsg}`)
    } finally {
      setLoading(false)
    }
  }

  const handleDirectoryDoubleClick = (path: string) => {
    // 더블 클릭 시 디렉토리 진입
    loadDirectory(path)
  }

  const handleDirectorySingleClick = (path: string) => {
    // 싱글 클릭 시 선택
    setSelectedPath(path)
  }

  const handleSelectCurrent = () => {
    if (browseData) {
      onSelectDirectory(browseData.current_path)
    }
  }

  const handleSelectChosen = () => {
    if (selectedPath) {
      onSelectDirectory(selectedPath)
    }
  }

  if (loading && !browseData) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2">디렉토리를 불러오는 중...</span>
      </div>
    )
  }

  if (error && !browseData) {
    return (
      <div className="p-4 text-center">
        <div className="text-red-600 mb-4">{error}</div>
        <Button onClick={loadHomeDirectory}>다시 시도</Button>
      </div>
    )
  }

  if (!browseData) {
    return <div>디렉토리 정보를 불러올 수 없습니다.</div>
  }

  return (
    <div className="flex flex-col h-full">
      {/* 헤더: 현재 경로 */}
      <div className="border-b p-3 bg-gray-50">
        <div className="flex items-center gap-2 mb-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={loadHomeDirectory}
            disabled={loading}
            title="홈 디렉토리"
          >
            <Home className="h-4 w-4" />
          </Button>

          {browseData.parent_path && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => loadDirectory(browseData.parent_path!)}
              disabled={loading}
              title="상위 디렉토리"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}

          <div className="text-sm font-mono text-gray-700 flex-1 truncate">
            {browseData.current_path}
          </div>
        </div>

        {loading && (
          <div className="flex items-center text-sm text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin mr-2" />
            불러오는 중...
          </div>
        )}
      </div>

      {/* 디렉토리 목록 */}
      <div className="flex-1 overflow-y-auto p-2">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded p-3 mb-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {browseData.entries.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            디렉토리가 비어 있습니다
          </div>
        ) : (
          <div className="space-y-1">
            {browseData.entries
              .filter((entry) => entry.is_directory)
              .map((entry) => {
                const isSelected = selectedPath === entry.path

                return (
                  <div
                    key={entry.path}
                    className={`
                      flex items-center gap-2 p-2 rounded cursor-pointer
                      hover:bg-gray-100 transition-colors
                      ${isSelected ? 'bg-blue-100 border border-blue-300' : 'border border-transparent'}
                      ${!entry.is_readable ? 'opacity-50 cursor-not-allowed' : ''}
                    `}
                    onClick={() => entry.is_readable && handleDirectorySingleClick(entry.path)}
                    onDoubleClick={() => entry.is_readable && handleDirectoryDoubleClick(entry.path)}
                  >
                    {isSelected ? (
                      <FolderOpen className="h-5 w-5 text-blue-600" />
                    ) : (
                      <Folder className="h-5 w-5 text-yellow-600" />
                    )}
                    <span className="text-sm flex-1 truncate">
                      {entry.name}
                    </span>
                    {!entry.is_readable && (
                      <span className="text-xs text-red-500">권한 없음</span>
                    )}
                  </div>
                )
              })}
          </div>
        )}
      </div>

      {/* 푸터: 액션 버튼 */}
      <div className="border-t p-3 bg-gray-50">
        <div className="flex items-center justify-between gap-2">
          <div className="text-sm text-muted-foreground flex-1">
            {selectedPath ? (
              <span className="font-mono truncate block">{selectedPath}</span>
            ) : (
              <span>디렉토리를 선택하거나 더블 클릭하여 진입하세요</span>
            )}
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={onCancel}>
              취소
            </Button>
            {selectedPath ? (
              <Button onClick={handleSelectChosen}>
                선택한 디렉토리 사용
              </Button>
            ) : (
              <Button onClick={handleSelectCurrent}>
                현재 디렉토리 사용
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
