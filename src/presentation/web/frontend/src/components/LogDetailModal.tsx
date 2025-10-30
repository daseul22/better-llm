import { X, Maximize2 } from 'lucide-react'
import { LogItem } from '@/stores/workflowStore'
import { ParsedContent } from './ParsedContent'
import { AutoScrollContainer } from './AutoScrollContainer'

interface NodeLogSection {
  nodeId: string
  nodeName: string
  logs: LogItem[]
}

interface LogDetailModalProps {
  isOpen: boolean
  onClose: () => void
  sections: NodeLogSection[]
  title?: string
}

export function LogDetailModal({ isOpen, onClose, sections, title = "실행 로그 상세" }: LogDetailModalProps) {
  if (!isOpen) return null

  const hasSections = sections.length > 0
  const singleSection = sections.length === 1

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full h-full max-w-7xl max-h-[90vh] flex flex-col shadow-2xl border border-gray-200">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center gap-2">
            <Maximize2 className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            {hasSections && (
              <span className="text-sm text-gray-600">
                ({sections.length}개 노드)
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* 로그 내용 */}
        <div className="flex-1 overflow-hidden">
          {!hasSections ? (
            <div className="h-full flex items-center justify-center text-gray-500">
              로그가 없습니다
            </div>
          ) : singleSection ? (
            // 단일 노드: 전체 화면
            <div className="h-full p-4 bg-gray-50">
              <LogSection section={sections[0]} />
            </div>
          ) : (
            // 다중 노드: 좌우 분할 또는 그리드
            <div className={`h-full grid ${sections.length === 2 ? 'grid-cols-2' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'} gap-4 p-4 overflow-y-auto bg-gray-50`}>
              {sections.map((section) => (
                <div key={section.nodeId} className="border border-gray-200 rounded-lg overflow-hidden bg-white">
                  <LogSection section={section} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 푸터 */}
        <div className="p-4 border-t border-gray-200 bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-900 rounded-lg transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  )
}

function LogSection({ section }: { section: NodeLogSection }) {
  // 로그 타입별 분류
  const inputLogs = section.logs.filter(log => log.type === 'input')
  const executionLogs = section.logs.filter(log => log.type === 'execution')
  const outputLogs = section.logs.filter(log => log.type === 'output')
  const errorLogs = section.logs.filter(log => log.type === 'error')
  const otherLogs = section.logs.filter(log => !['input', 'execution', 'output', 'error'].includes(log.type))

  return (
    <div className="flex flex-col h-full">
      {/* 노드 제목 */}
      <div className="p-3 bg-gray-100 border-b border-gray-200">
        <h3 className="font-semibold text-gray-900">{section.nodeName}</h3>
        <p className="text-xs text-gray-600 mt-1">Node ID: {section.nodeId}</p>
      </div>

      {/* 로그 내용 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-white">
        {section.logs.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            로그가 없습니다
          </div>
        ) : (
          <>
            {/* 입력 섹션 */}
            {inputLogs.length > 0 && (
              <div className="border rounded-md overflow-hidden">
                <div className="bg-blue-50 px-3 py-2 border-b border-blue-200">
                  <h4 className="text-sm font-semibold text-blue-900">📥 입력</h4>
                </div>
                <AutoScrollContainer
                  className="p-3"
                  maxHeight="200px"
                  dependency={inputLogs.length}
                >
                  <div className="space-y-2">
                    {inputLogs.map((log, idx) => (
                      <LogItemComponent key={idx} log={log} />
                    ))}
                  </div>
                </AutoScrollContainer>
              </div>
            )}

            {/* 실행 과정 섹션 */}
            {executionLogs.length > 0 && (
              <div className="border rounded-md overflow-hidden">
                <div className="bg-purple-50 px-3 py-2 border-b border-purple-200">
                  <h4 className="text-sm font-semibold text-purple-900">🔧 실행 과정</h4>
                </div>
                <AutoScrollContainer
                  className="p-3"
                  maxHeight="300px"
                  dependency={executionLogs.length}
                >
                  <div className="space-y-2">
                    {executionLogs.map((log, idx) => (
                      <LogItemComponent key={idx} log={log} />
                    ))}
                  </div>
                </AutoScrollContainer>
              </div>
            )}

            {/* 출력 섹션 */}
            {outputLogs.length > 0 && (
              <div className="border rounded-md overflow-hidden">
                <div className="bg-green-50 px-3 py-2 border-b border-green-200">
                  <h4 className="text-sm font-semibold text-green-900">📤 출력</h4>
                </div>
                <AutoScrollContainer
                  className="p-3"
                  maxHeight="300px"
                  dependency={outputLogs.length}
                >
                  <div className="space-y-2">
                    {outputLogs.map((log, idx) => (
                      <LogItemComponent key={idx} log={log} />
                    ))}
                  </div>
                </AutoScrollContainer>
              </div>
            )}

            {/* 에러 섹션 */}
            {errorLogs.length > 0 && (
              <div className="border rounded-md overflow-hidden">
                <div className="bg-red-50 px-3 py-2 border-b border-red-200">
                  <h4 className="text-sm font-semibold text-red-900">❌ 에러</h4>
                </div>
                <AutoScrollContainer
                  className="p-3"
                  maxHeight="250px"
                  dependency={errorLogs.length}
                >
                  <div className="space-y-2">
                    {errorLogs.map((log, idx) => (
                      <LogItemComponent key={idx} log={log} />
                    ))}
                  </div>
                </AutoScrollContainer>
              </div>
            )}

            {/* 기타 로그 */}
            {otherLogs.length > 0 && (
              <div className="border rounded-md overflow-hidden">
                <div className="bg-gray-50 px-3 py-2 border-b border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-900">📝 기타</h4>
                </div>
                <AutoScrollContainer
                  className="p-3"
                  maxHeight="200px"
                  dependency={otherLogs.length}
                >
                  <div className="space-y-2">
                    {otherLogs.map((log, idx) => (
                      <LogItemComponent key={idx} log={log} />
                    ))}
                  </div>
                </AutoScrollContainer>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function LogItemComponent({ log }: { log: LogItem }) {
  return (
    <div className="bg-white rounded p-2 border border-gray-200 shadow-sm">
      <div className="text-xs text-gray-500 mb-1">
        {new Date(log.timestamp).toLocaleString()}
      </div>
      <ParsedContent content={log.message} />
    </div>
  )
}
