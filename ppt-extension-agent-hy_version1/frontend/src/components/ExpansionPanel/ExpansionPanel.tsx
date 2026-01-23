import { useState } from 'react'
import { BookOpen, Lightbulb, Calculator, Code, CheckCircle, ExternalLink, Download, ChevronDown, ChevronUp } from 'lucide-react'
import MathRenderer from '../MathRenderer/MathRenderer'
import CodeHighlighter from '../CodeHighlighter/CodeHighlighter'

type ExpandedContent = {
  background: string
  principles: string
  formulas: string
  examples: string
  summary: string
  references: Array<{ 
    title: string
    url: string
    source?: string
    authors?: string[]
    year?: string
    venue?: string
    citation?: string
  }>
}

type ExpansionPanelProps = {
  content: ExpandedContent | null
  onExport?: (format: 'markdown' | 'pdf') => void
}

function ExpansionPanel({ content, onExport }: ExpansionPanelProps) {
  const [activeTab, setActiveTab] = useState<'background' | 'principles' | 'formulas' | 'examples' | 'summary'>('background')
  const [referencesExpanded, setReferencesExpanded] = useState(false)

  const tabs = [
    { id: 'background' as const, label: '背景说明', icon: BookOpen },
    { id: 'principles' as const, label: '原理阐述', icon: Lightbulb },
    { id: 'formulas' as const, label: '公式推导', icon: Calculator },
    { id: 'examples' as const, label: '代码示例', icon: Code },
    { id: 'summary' as const, label: '要点总结', icon: CheckCircle },
  ]

  if (!content) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-12">
          <Lightbulb className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <p className="text-gray-500">选择文本框并点击"扩展"按钮查看扩展内容</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {content && onExport && (
        <div className="border-b border-gray-200 bg-gray-50 px-6 py-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">导出选项</span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onExport('markdown')}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                <Download className="w-4 h-4" />
                Markdown
              </button>
              <button
                onClick={() => onExport('pdf')}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                <Download className="w-4 h-4" />
                PDF
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="border-b border-gray-200">
        <nav className="flex overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>

      <div className="p-6">
        {activeTab === 'background' && (
          <div className="space-y-4">
            <h4 className="text-lg font-semibold text-gray-900">背景说明</h4>
            <div className="prose prose-sm max-w-none text-gray-700">
              {content.background || '暂无背景说明'}
            </div>
          </div>
        )}

        {activeTab === 'principles' && (
          <div className="space-y-4">
            <h4 className="text-lg font-semibold text-gray-900">原理阐述</h4>
            <div className="prose prose-sm max-w-none text-gray-700">
              {content.principles || '暂无原理阐述'}
            </div>
          </div>
        )}

        {activeTab === 'formulas' && (
          <div className="space-y-4">
            <h4 className="text-lg font-semibold text-gray-900">公式推导</h4>
            <div className="prose prose-sm max-w-none text-gray-700">
              {content.formulas ? <MathRenderer content={content.formulas} /> : '暂无公式推导'}
            </div>
          </div>
        )}

        {activeTab === 'examples' && (
          <div className="space-y-4">
            <h4 className="text-lg font-semibold text-gray-900">代码示例</h4>
            <div className="prose prose-sm max-w-none text-gray-700">
              {content.examples ? <CodeHighlighter content={content.examples} /> : '暂无代码示例'}
            </div>
          </div>
        )}

        {activeTab === 'summary' && (
          <div className="space-y-4">
            <h4 className="text-lg font-semibold text-gray-900">要点总结</h4>
            <div className="prose prose-sm max-w-none text-gray-700">
              {content.summary || '暂无要点总结'}
            </div>
          </div>
        )}
      </div>

      {content.references && content.references.length > 0 && (
        <div className="border-t border-gray-200 bg-gradient-to-br from-blue-50 to-indigo-50">
          <button
            onClick={() => setReferencesExpanded(!referencesExpanded)}
            className="w-full flex items-center justify-between gap-2 p-6 hover:bg-blue-100/50 transition-colors text-left"
          >
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary-600" />
              <h4 className="text-lg font-semibold text-gray-900">参考文献</h4>
              <span className="text-sm text-gray-500">({content.references.length}篇)</span>
            </div>
            {referencesExpanded ? (
              <ChevronUp className="w-5 h-5 text-gray-600" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-600" />
            )}
          </button>
          {referencesExpanded && (
            <div className="px-6 pb-6 space-y-3">
            {content.references.map((ref, index) => (
              <div
                key={index}
                className="bg-white rounded-lg p-4 border border-gray-200 hover:border-primary-300 hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-100 text-primary-700 text-xs font-semibold flex items-center justify-center mt-0.5">
                        {index + 1}
                      </span>
                      <div className="flex-1">
                        <h5 className="text-sm font-semibold text-gray-900 mb-1 leading-tight">
                          {ref.title}
                        </h5>
                        {(ref.citation || (ref.authors && ref.authors.length > 0)) && (
                          <div className="text-xs text-gray-600 space-y-1">
                            {ref.citation ? (
                              <p className="italic">{ref.citation}</p>
                            ) : (
                              <>
                                {ref.authors && ref.authors.length > 0 && (
                                  <p>
                                    <span className="font-medium">作者:</span> {ref.authors.slice(0, 3).join(", ")}
                                    {ref.authors.length > 3 && " et al."}
                                  </p>
                                )}
                                {ref.year && (
                                  <p>
                                    <span className="font-medium">年份:</span> {ref.year}
                                  </p>
                                )}
                                {ref.venue && (
                                  <p>
                                    <span className="font-medium">期刊/会议:</span> {ref.venue}
                                  </p>
                                )}
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    {ref.source && (
                      <span className="inline-block ml-8 px-2 py-0.5 text-xs bg-primary-100 text-primary-700 rounded-md">
                        {ref.source}
                      </span>
                    )}
                  </div>
                  {ref.url && (
                    <a
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-shrink-0 p-2 text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded-md transition-colors"
                      title="查看原文"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
              </div>
            ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ExpansionPanel
