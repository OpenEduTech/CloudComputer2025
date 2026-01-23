/**
 * PatPat-Inconsistency-Hunter 结果页面
 * 左右栏布局：左边原文（可编辑），右边分析结果（冲突/事实）
 * 支持光标对照，点击定位
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  AlertTriangle,
  CheckCircle,
  Clock,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Filter,
  Download,
  RefreshCw,
  Loader2,
  Info,
  Eye,
  EyeOff,
  Edit3,
  Save,
  FileDown,
  Copy,
  Check,
  Maximize2,
  Minimize2,
  Target,
} from 'lucide-react'
import { getTaskResult, getTaskStatus, getTaskFacts, getTaskConflicts, getDocumentContent, exportReport, exportTaskDocument, updateTaskDocument, reanalyzeTaskDocument } from '../api'
import RichTextEditor from '../components/RichTextEditor'

// 冲突类型中文映射
const conflictTypeMap = {
  numerical: '数值冲突',
  temporal: '时间冲突',
  entity: '实体冲突',
  categorical: '类别冲突',
  definition: '定义冲突',
  logical: '逻辑冲突',
  spatial: '空间冲突',
}

// 检查是否为图片来源的事实
const isImageFact = (fact) =>
  fact?.is_image_source || fact?.fact_type?.startsWith('image_')

// 检查冲突是否涉及图片
const isImageConflict = (conflict) =>
  conflict?.is_image_conflict || isImageFact(conflict?.fact_a) || isImageFact(conflict?.fact_b)

// 获取事实类型显示名称
const getFactTypeDisplay = (factType) => {
  if (!factType) return '未知'
  if (factType.startsWith('image_')) {
    const baseType = factType.replace('image_', '')
    return `📊 ${baseType}`
  }
  return factType
}

// 严重程度颜色
const severityColors = {
  critical: 'danger',
  high: 'warning',
  medium: 'primary',
  low: 'success',
}

const normalizeHighlightText = (value) => value.replace(/\s+/g, ' ').trim()

const extractSentence = (text, fallback = '') => {
  if (!text) return ''
  const normalized = normalizeHighlightText(text)
  if (!normalized) return ''
  if (fallback && normalized.includes(fallback)) return fallback
  const sentences = normalized.split(/(?<=[。！？!?])\s*/)
  return sentences.find(Boolean) || normalized
}

// 从 content_json 中提取所有图片信息
const extractImagesFromContent = (contentJson) => {
  if (!contentJson || !contentJson.content) return []
  const images = []
  let imageIndex = 0

  const traverse = (node) => {
    if (node.type === 'image') {
      const attrs = node.attrs || {}
      const imageId = attrs['data-image-id'] || attrs.imageId || ''
      const alt = attrs.alt || `图片${imageIndex + 1}`
      images.push({
        imageId,
        alt,
        index: imageIndex,
        // 支持多种匹配方式
        patterns: [
          imageId,
          alt,
          `图片${imageIndex + 1}`,
          `图片${imageIndex + 1}.png`,
          `图片${imageIndex + 1}.jpg`,
        ]
      })
      imageIndex++
    }
    if (node.content && Array.isArray(node.content)) {
      node.content.forEach(traverse)
    }
  }

  traverse(contentJson)
  return images
}

const buildHighlightCandidates = (item, documentContentJson = null) => {
  if (!item) return { texts: [], imageIds: [] }
  const candidates = []
  const imageIds = []

  console.log('📦 [buildHighlightCandidates] 输入 item:', item)

  // 提取文档中的所有图片信息
  const documentImages = documentContentJson ? extractImagesFromContent(documentContentJson) : []
  console.log('📦 [buildHighlightCandidates] 文档中的图片:', documentImages)

  const addCandidate = (value) => {
    const normalized = value ? normalizeHighlightText(value) : ''
    if (!normalized) return
    if (!candidates.some((existing) => normalizeHighlightText(existing) === normalized)) {
      candidates.push(value)
    }
  }

  const addFactCandidates = (fact) => {
    if (!fact) return

    console.log('📦 [buildHighlightCandidates] 处理事实:', fact)
    console.log('📦 [buildHighlightCandidates] fact 的所有字段:', Object.keys(fact))
    console.log('📦 [buildHighlightCandidates] fact_type:', fact.fact_type, 'is_image_source:', fact.is_image_source, 'image_id:', fact.image_id)

    // 检查是否是图片来源的事实
    const factType = fact.fact_type || ''
    const factTypeStr = typeof factType === 'string' ? factType : String(factType)
    const isImageType = factTypeStr && factTypeStr.startsWith('image_')
    const content = (fact.content || fact.source_text || '').toString()
    // 更宽泛的图片关键词匹配
    const hasImageKeyword = /图片\d+|图片[\w]+|img_|\[IMAGE:|展示|显示.*图片/i.test(content)
    const mentionsImage = content.includes('图片') || content.includes('展示') || content.includes('显示')

    console.log('📦 [buildHighlightCandidates] 判断:', {
      factType: factTypeStr,
      isImageType,
      hasImageKeyword,
      mentionsImage,
      is_image_source: fact.is_image_source
    })

    // 辅助函数：尝试从文档图片列表中匹配
    const findImageIdFromDocument = (searchText, isImageTypeFact = false) => {
      if (!searchText || documentImages.length === 0) return null

      // 方法1: 精确匹配 patterns
      for (const img of documentImages) {
        for (const pattern of img.patterns) {
          if (pattern && searchText.includes(pattern)) {
            console.log(`✅ [buildHighlightCandidates] 从文档图片列表匹配: "${pattern}" -> ${img.imageId}`)
            return img.imageId
          }
        }
      }

      // 方法2: 匹配图片编号（如"图片1"、"图片2"）
      const imageNumberMatch = searchText.match(/图片(\d+)/i)
      if (imageNumberMatch) {
        const imageNumber = parseInt(imageNumberMatch[1])
        // 图片编号从1开始，数组索引从0开始
        if (imageNumber >= 1 && imageNumber <= documentImages.length) {
          const matchedImg = documentImages[imageNumber - 1]
          console.log(`✅ [buildHighlightCandidates] 从图片编号匹配: "图片${imageNumber}" -> ${matchedImg.imageId}`)
          return matchedImg.imageId
        }
      }

      // 方法3: 匹配 alt 文本
      for (const img of documentImages) {
        if (img.alt && searchText.includes(img.alt)) {
          console.log(`✅ [buildHighlightCandidates] 从 alt 文本匹配: "${img.alt}" -> ${img.imageId}`)
          return img.imageId
        }
      }

      // 方法4: 如果 fact_type 以 image_ 开头且内容提到"图片"，尝试更模糊的匹配
      if (isImageTypeFact && /图片|图表|示意图|流程图|截图|表格/i.test(searchText)) {
        // 如果只有一张图片，直接返回
        if (documentImages.length === 1) {
          console.log(`✅ [buildHighlightCandidates] 方法4: 文档只有一张图片，直接使用: ${documentImages[0].imageId}`)
          return documentImages[0].imageId
        }
        // 尝试从 source_text 匹配更具体的图片引用
        // 如果内容包含"第一张"或类似的序号词
        const ordinalMatch = searchText.match(/第([一二三四五六七八九十\d]+)[张幅个]/i)
        if (ordinalMatch) {
          const ordinalMap = { '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10 }
          const ordinal = ordinalMap[ordinalMatch[1]] || parseInt(ordinalMatch[1])
          if (ordinal >= 1 && ordinal <= documentImages.length) {
            console.log(`✅ [buildHighlightCandidates] 方法4: 从序号词匹配: "第${ordinalMatch[1]}张" -> ${documentImages[ordinal - 1].imageId}`)
            return documentImages[ordinal - 1].imageId
          }
        }
      }

      return null
    }

    // 方法1: 直接检查字段
    if (fact.is_image_source && fact.image_id) {
      if (!imageIds.includes(fact.image_id)) {
        imageIds.push(fact.image_id)
        console.log('✅ [buildHighlightCandidates] 方法1: 添加图片ID:', fact.image_id)
      }
    }
    // 方法2: 尝试提取图片ID（无论 fact_type 是什么，只要内容提到图片就尝试）
    else if (isImageType || hasImageKeyword || mentionsImage) {
      console.log('⚠️ [buildHighlightCandidates] 可能是图片来源，尝试提取图片ID')

      let foundImageId = null

      // 优先使用已有的 image_id
      if (fact.image_id) {
        foundImageId = fact.image_id
        console.log('✅ [buildHighlightCandidates] 方法2a: 使用已有的 image_id:', foundImageId)
      }
      // 尝试从内容中提取图片ID
      else {
        // 匹配模式1: img_xxxxx
        let imageIdMatch = content.match(/img_[\w]+/i)
        if (imageIdMatch) {
          foundImageId = imageIdMatch[0]
          console.log('✅ [buildHighlightCandidates] 方法2b: 从内容提取图片ID (img_xxx):', foundImageId)
        }

        // 匹配模式2: [IMAGE:image_id:alt]
        if (!foundImageId) {
          imageIdMatch = content.match(/\[IMAGE:([^\]:]+)/)
          if (imageIdMatch) {
            foundImageId = imageIdMatch[1]
            console.log('✅ [buildHighlightCandidates] 方法2c: 从内容提取图片ID ([IMAGE:):', foundImageId)
          }
        }

        // 匹配模式3: 从文档图片列表中匹配（如"图片1"、"图片1.png"）
        if (!foundImageId && documentImages.length > 0) {
          // 先尝试从 content 匹配
          foundImageId = findImageIdFromDocument(content, isImageType)
          if (foundImageId) {
            console.log('✅ [buildHighlightCandidates] 方法2d: 从 content 匹配:', foundImageId)
          }
          // 如果失败，尝试从 source_text 匹配
          if (!foundImageId && fact.source_text) {
            foundImageId = findImageIdFromDocument(fact.source_text, isImageType)
            if (foundImageId) {
              console.log('✅ [buildHighlightCandidates] 方法2e: 从 source_text 匹配:', foundImageId)
            }
          }
          // 如果失败，尝试从 image_description 匹配
          if (!foundImageId && fact.image_description) {
            foundImageId = findImageIdFromDocument(fact.image_description, isImageType)
            if (foundImageId) {
              console.log('✅ [buildHighlightCandidates] 方法2f: 从 image_description 匹配:', foundImageId)
            }
          }
        }
      }

      // 兜底逻辑：只有在文档只有一张图片时才自动选择
      if (!foundImageId && isImageType && documentImages.length === 1) {
        // 文档只有一张图片，可以安全地使用它
        foundImageId = documentImages[0].imageId
        console.log(`✅ [buildHighlightCandidates] 文档只有一张图片，自动使用: ${foundImageId}`)
      } else if (!foundImageId && isImageType && documentImages.length > 1) {
        // 文档有多张图片但无法确定是哪张，记录警告但不随意选择
        console.log(`⚠️ [buildHighlightCandidates] 无法确定具体图片，文档有 ${documentImages.length} 张图片`)
        // 不设置 foundImageId，避免错误高亮
      }

      if (foundImageId && !imageIds.includes(foundImageId)) {
        imageIds.push(foundImageId)
      }
    }

    const sourceSentence = extractSentence(fact.source_text, fact.content)
    if (sourceSentence) {
      addCandidate(sourceSentence)
    }
    if (fact.content) {
      addCandidate(fact.content)
    }
  }

  if (item.fact_a || item.fact_b) {
    addFactCandidates(item.fact_a)
    addFactCandidates(item.fact_b)
  }

  addFactCandidates(item)

  console.log('📦 [buildHighlightCandidates] 结果:', { texts: candidates.length, imageIds })
  return { texts: candidates, imageIds }
}

const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const findHighlightMatch = (line, candidates) => {
  if (!line || !candidates?.length) return null
  for (const candidate of candidates) {
    const normalized = normalizeHighlightText(candidate || '')
    if (!normalized) continue
    const tryMatch = (text) => {
      if (!text) return null
      const escaped = escapeRegExp(text).replace(/\s+/g, '\\s+')
      const regex = new RegExp(escaped, 'i')
      const match = regex.exec(line)
      if (match && match.index !== undefined) {
        return { index: match.index, length: match[0].length }
      }
      return null
    }
    const match = tryMatch(normalized) || tryMatch(normalized.slice(0, 80)) || tryMatch(normalized.slice(0, 50))
    if (match) return match
  }
  return null
}

// 冲突卡片组件
function ConflictCard({ conflict, index, onLocate, onLocateFact, isHighlighted }) {
  const [expanded, setExpanded] = useState(false)
  const severityLevel = conflict.severity >= 0.9 ? 'critical'
    : conflict.severity >= 0.6 ? 'high'
      : conflict.severity >= 0.3 ? 'medium' : 'low'
  const color = severityColors[severityLevel]
  const hasImageConflict = isImageConflict(conflict)

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className={`rounded-lg border-2 transition-all overflow-hidden ${isHighlighted
        ? 'border-primary-400 bg-primary-50 shadow-lg shadow-primary-100'
        : hasImageConflict
          ? 'border-purple-200 bg-purple-50/30 hover:border-purple-300'
          : 'border-slate-200 bg-white hover:border-slate-300'
        }`}
    >
      {/* 头部 */}
      <div
        className="p-3 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className={`badge badge-${color} text-xs`}>
                {conflictTypeMap[conflict.conflict_type] || conflict.conflict_type}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded-full bg-${color}-100 text-${color}-700`}>
                {(conflict.severity * 100).toFixed(0)}%
              </span>
              {hasImageConflict && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 flex items-center gap-1">
                  🖼️ 图文冲突
                </span>
              )}
            </div>
            <p className="text-sm text-slate-700 line-clamp-2">
              {conflict.description}
            </p>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                console.log('🔘 [按钮] 点击定位按钮，conflict:', conflict);
                onLocate(conflict);
              }}
              className="p-1.5 hover:bg-primary-100 rounded-lg text-primary-600 transition-colors"
              title="定位原文"
            >
              <Target className="w-4 h-4" />
            </button>
            <button className="p-1 text-slate-400 hover:text-slate-600">
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* 展开内容 */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-slate-100"
          >
            <div className="p-3 space-y-3">
              {/* 事实对比 */}
              <div className="grid grid-cols-1 gap-2">
                <div className={`rounded-lg p-3 border ${isImageFact(conflict.fact_a)
                  ? 'bg-purple-50 border-purple-200'
                  : 'bg-danger-50 border-danger-200'
                  }`}>
                  <div className="flex items-center justify-between mb-1">
                    <div className={`text-xs font-medium flex items-center gap-1 ${isImageFact(conflict.fact_a) ? 'text-purple-700' : 'text-danger-700'
                      }`}>
                      {isImageFact(conflict.fact_a) && <span>🖼️</span>}
                      事实 A
                      {isImageFact(conflict.fact_a) && (
                        <span className="text-purple-500">(图片来源)</span>
                      )}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        conflict.fact_a && onLocateFact?.(conflict.fact_a, conflict.conflict_id)
                      }}
                      className={`flex items-center gap-1 text-xs hover:opacity-80 ${isImageFact(conflict.fact_a) ? 'text-purple-600' : 'text-danger-600'
                        }`}
                    >
                      <Target className="w-3 h-3" />
                      回溯
                    </button>
                  </div>
                  <p className="text-sm text-slate-800 mb-1">{conflict.fact_a?.content}</p>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">类型:</span>
                    <span className="text-xs text-slate-600">{getFactTypeDisplay(conflict.fact_a?.fact_type)}</span>
                  </div>
                  <p className="text-xs text-slate-500 truncate mt-1">
                    来源: {conflict.fact_a?.source_text}
                  </p>
                </div>
                <div className={`rounded-lg p-3 border ${isImageFact(conflict.fact_b)
                  ? 'bg-purple-50 border-purple-200'
                  : 'bg-warning-50 border-warning-200'
                  }`}>
                  <div className="flex items-center justify-between mb-1">
                    <div className={`text-xs font-medium flex items-center gap-1 ${isImageFact(conflict.fact_b) ? 'text-purple-700' : 'text-warning-700'
                      }`}>
                      {isImageFact(conflict.fact_b) && <span>🖼️</span>}
                      事实 B
                      {isImageFact(conflict.fact_b) && (
                        <span className="text-purple-500">(图片来源)</span>
                      )}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        conflict.fact_b && onLocateFact?.(conflict.fact_b, conflict.conflict_id)
                      }}
                      className={`flex items-center gap-1 text-xs hover:opacity-80 ${isImageFact(conflict.fact_b) ? 'text-purple-600' : 'text-warning-600'
                        }`}
                    >
                      <Target className="w-3 h-3" />
                      回溯
                    </button>
                  </div>
                  <p className="text-sm text-slate-800 mb-1">{conflict.fact_b?.content}</p>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">类型:</span>
                    <span className="text-xs text-slate-600">{getFactTypeDisplay(conflict.fact_b?.fact_type)}</span>
                  </div>
                  <p className="text-xs text-slate-500 truncate mt-1">
                    来源: {conflict.fact_b?.source_text}
                  </p>
                </div>
              </div>

              {/* 修正建议 */}
              {conflict.suggestion && (
                <div className="p-3 bg-primary-50 rounded-lg border border-primary-200">
                  <div className="flex items-center gap-1 text-primary-700 font-medium mb-1 text-xs">
                    <Info className="w-3 h-3" />
                    修正建议
                  </div>
                  <p className="text-primary-600 text-sm">{conflict.suggestion}</p>
                </div>
              )}

              {/* 验证结果 */}
              {conflict.verification && (
                <div className="p-3 bg-success-50 rounded-lg border border-success-200">
                  <div className="flex items-center gap-1 text-success-700 font-medium mb-1 text-xs">
                    <CheckCircle className="w-3 h-3" />
                    验证结果 ({(conflict.verification.confidence * 100).toFixed(0)}%)
                  </div>
                  <p className="text-success-600 text-sm mb-1">
                    {conflict.verification.correct_fact || '无法确定正确事实'}
                  </p>
                  <p className="text-slate-600 text-xs">
                    {conflict.verification.reasoning}
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// 事实卡片组件
function FactCard({ fact, index, onLocate, isHighlighted }) {
  const isFromImage = isImageFact(fact)

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.02 }}
      className={`p-3 rounded-lg border-2 transition-all ${isHighlighted
        ? 'border-primary-400 bg-primary-50 shadow-lg shadow-primary-100'
        : isFromImage
          ? 'border-purple-200 bg-purple-50/30 hover:border-purple-300'
          : 'border-slate-200 bg-white hover:border-slate-300'
        }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`badge text-xs ${isFromImage ? 'badge-purple' : 'badge-primary'}`}>
              {getFactTypeDisplay(fact.fact_type)}
            </span>
            {isFromImage && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 flex items-center gap-1">
                🖼️ 图片来源
              </span>
            )}
            {fact.chapter && (
              <span className="text-xs text-slate-500">
                {fact.chapter}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-700">
            {fact.content}
          </p>
          {fact.source_text && (
            <p className="text-xs text-slate-500 mt-1 truncate">
              来源: {fact.source_text}
            </p>
          )}
        </div>
        <button
          onClick={() => onLocate(fact)}
          className={`p-1.5 rounded-lg transition-colors flex-shrink-0 ${isHighlighted
            ? 'bg-primary-200 text-primary-700'
            : isFromImage
              ? 'hover:bg-purple-100 text-purple-600'
              : 'hover:bg-primary-100 text-primary-600'
            }`}
          title="定位原文"
        >
          <Target className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  )
}

// 可高亮的 HTML 内容组件
function HighlightableContent({ html, highlightTexts }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !highlightTexts || highlightTexts.length === 0) {
      return
    }

    // 延迟执行以确保 DOM 已更新
    const timeoutId = setTimeout(() => {
      const container = containerRef.current
      if (!container) return

      // 清除之前的高亮
      const existingHighlights = container.querySelectorAll('.search-highlight')
      existingHighlights.forEach(el => {
        const parent = el.parentNode
        if (parent) {
          parent.replaceChild(document.createTextNode(el.textContent || ''), el)
          parent.normalize()
        }
      })

      // 在 DOM 中查找并高亮文本
      const walker = document.createTreeWalker(
        container,
        NodeFilter.SHOW_TEXT,
        null,
        false
      )

      let firstMatch = null
      let node
      while (node = walker.nextNode()) {
        const text = node.textContent || ''
        for (const searchText of highlightTexts) {
          if (!searchText) continue
          const searchKey = searchText.substring(0, Math.min(50, searchText.length))
          const index = text.indexOf(searchKey)

          if (index !== -1 && !firstMatch) {
            try {
              const range = document.createRange()
              range.setStart(node, index)
              range.setEnd(node, Math.min(index + searchKey.length, text.length))

              const span = document.createElement('span')
              span.className = 'search-highlight'
              span.style.cssText = 'background-color: var(--sun-cream); border-radius: 2px; padding: 1px 2px; box-shadow: 0 0 0 2px var(--sun-cream); transition: all 0.3s;'

              range.surroundContents(span)
              firstMatch = span
            } catch (e) {
              console.warn('高亮文本失败:', e)
            }
            break
          }
        }
        if (firstMatch) break
      }

      // 滚动到高亮位置
      if (firstMatch) {
        setTimeout(() => {
          firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }, 50)
      }
    }, 100)

    return () => clearTimeout(timeoutId)
  }, [highlightTexts])

  return (
    <div
      ref={containerRef}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

function ResultPage() {
  const { taskId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()

  // 数据状态
  const [loading, setLoading] = useState(true)
  const [result, setResult] = useState(null)
  const [conflicts, setConflicts] = useState([])
  const [facts, setFacts] = useState([])
  const [documentData, setDocumentData] = useState(null)
  const [error, setError] = useState(null)

  // UI状态
  const [activeTab, setActiveTab] = useState('conflicts')
  const [filterType, setFilterType] = useState('')
  const [exporting, setExporting] = useState(false)
  const [exportFormat, setExportFormat] = useState('markdown')
  const [highlightedItem, setHighlightedItem] = useState(null)
  const [editMode, setEditMode] = useState(false)
  const [editedContent, setEditedContent] = useState('')
  const [editedContentJson, setEditedContentJson] = useState(null)
  const [saving, setSaving] = useState(false)
  const [reanalyzing, setReanalyzing] = useState(false)
  const [copied, setCopied] = useState(false)
  const [leftPanelExpanded, setLeftPanelExpanded] = useState(true)

  // Refs
  const documentRef = useRef(null)
  const highlightRefs = useRef({})

  // 返回路径
  const returnPath = location.state?.from || '/analyze'

  // 加载数据
  useEffect(() => {
    loadData()
  }, [taskId])

  const loadData = async () => {
    setLoading(true)
    setError(null)

    try {
      const [resultData, conflictsData, factsData, docData] = await Promise.all([
        getTaskResult(taskId),
        getTaskConflicts(taskId, { page_size: 100 }),
        getTaskFacts(taskId, { page_size: 100 }),
        getDocumentContent(taskId).catch(() => null),
      ])

      setResult(resultData)
      setConflicts(conflictsData.conflicts || [])
      setFacts(factsData.facts || [])
      setDocumentData(docData)
      setEditedContent(docData?.content || '')
      setEditedContentJson(docData?.content_json || null)
    } catch (err) {
      setError(err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  // 导出报告
  const handleExport = async (format) => {
    setExporting(true)
    try {
      const response = await exportReport(taskId, format)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = window.document.createElement('a')
      a.href = url

      // 根据格式确定文件扩展名
      const extMap = {
        'json': 'json',
        'markdown': 'md',
        'md': 'md',
        'txt': 'txt',
        'pdf': 'pdf',
        'docx': 'docx'
      }
      const ext = extMap[format] || 'md'

      // 优先从响应头获取文件名
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `${result?.document_title || taskId}_report.${ext}`

      if (contentDisposition) {
        // 优先匹配 filename*=UTF-8''xxx（RFC 5987 编码，支持中文）
        const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
        if (filenameStarMatch) {
          try {
            filename = decodeURIComponent(filenameStarMatch[1])
          } catch (e) {
            console.warn('解码filename*失败:', e)
          }
        } else {
          // 降级匹配 filename="xxx"
          const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
          if (filenameMatch) {
            filename = filenameMatch[1].replace(/['"]/g, '')
          }
        }
      }

      a.download = filename
      window.document.body.appendChild(a)
      a.click()
      window.document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert('导出失败: ' + err.message)
    } finally {
      setExporting(false)
    }
  }

  // 导出原文（支持 TXT, MD, DOCX, PDF）- 使用后端 API 支持富文本格式
  const handleExportDocument = async (format) => {
    setExporting(true)
    try {
      const response = await exportTaskDocument(taskId, format)

      // 获取文件名 - 优先使用 RFC 5987 编码的 filename*，支持中文
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = ''

      if (contentDisposition) {
        // 优先匹配 filename*=UTF-8''xxx（RFC 5987 编码，支持中文）
        const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
        if (filenameStarMatch) {
          try {
            filename = decodeURIComponent(filenameStarMatch[1])
          } catch (e) {
            console.warn('解码文件名失败:', e)
          }
        }

        // 如果 filename* 解析失败，尝试普通的 filename
        if (!filename) {
          const filenameMatch = contentDisposition.match(/filename="?([^";\n]+)"?/i)
          if (filenameMatch) {
            filename = filenameMatch[1]
          }
        }
      }

      // 如果仍然没有文件名，使用文档标题或默认值
      if (!filename) {
        const docTitle = result?.document_title || documentData?.title || 'document'
        const ext = format === 'docx' ? 'docx' : format
        // 清理文件名中的特殊字符
        const cleanTitle = docTitle.replace(/[<>:"/\\|?*]/g, '_').substring(0, 100)
        filename = `${cleanTitle}.${ext}`
      }

      // 下载文件
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = window.document.createElement('a')
      a.href = url
      a.download = filename
      window.document.body.appendChild(a)
      a.click()
      window.document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('导出失败:', err)
      alert('导出失败: ' + (err.message || '未知错误'))
    } finally {
      setExporting(false)
    }
  }

  // 保存文档
  const handleSaveDocument = async () => {
    setSaving(true)
    try {
      const content_json = editedContentJson || documentData?.content_json
      const content = editedContent || documentData?.content || ''

      const response = await updateTaskDocument(taskId, {
        content,
        content_json,
        title: documentData?.title,
      })

      // 更新本地状态
      setDocumentData(prev => ({
        ...prev,
        content: response.content,
        content_json: response.content_json,
        content_html: response.content_html,
        title: response.title,
      }))

      // 退出编辑模式
      setEditMode(false)

      alert('文档已保存成功！')
    } catch (err) {
      console.error('保存失败:', err)
      alert('保存失败: ' + (err.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  // 检测冲突（重新分析）
  const handleReanalyze = async () => {
    if (!confirm('确定要重新分析文档并检测冲突吗？这将刷新冲突列表和事实列表。')) {
      return
    }

    setReanalyzing(true)
    let pollCount = 0
    const maxPolls = 300 // 最多轮询5分钟（300次 * 2秒）

    try {
      const response = await reanalyzeTaskDocument(taskId)

      // 提示用户正在分析
      alert('正在重新分析文档，请稍候...')

      // 轮询任务状态，等待分析完成
      const checkStatus = async () => {
        pollCount++

        // 防止无限轮询
        if (pollCount > maxPolls) {
          setReanalyzing(false)
          alert('分析超时，请刷新页面查看结果')
          return
        }

        try {
          const statusResponse = await getTaskStatus(taskId)
          const status = statusResponse.status || statusResponse.task_status

          if (status === 'completed') {
            // 重新加载数据
            await loadData()
            setReanalyzing(false)
            alert('重新分析完成！')
          } else if (status === 'failed') {
            setReanalyzing(false)
            alert('重新分析失败: ' + (statusResponse.error_message || '未知错误'))
          } else {
            // 继续轮询（analyzing 或 pending）
            setTimeout(checkStatus, 2000)
          }
        } catch (err) {
          console.error('检查状态失败:', err)

          // 如果错误太多，停止轮询
          if (pollCount > 10) {
            setReanalyzing(false)
            alert('无法获取分析状态，请稍后刷新页面查看结果')
          } else {
            // 继续尝试
            setTimeout(checkStatus, 2000)
          }
        }
      }

      // 等待一段时间后开始检查状态
      setTimeout(checkStatus, 2000)
    } catch (err) {
      console.error('启动重新分析失败:', err)
      alert('启动重新分析失败: ' + (err.message || '未知错误'))
      setReanalyzing(false)
    }
  }

  // 复制内容
  const handleCopyContent = async () => {
    const content = editMode ? editedContent : (documentData?.content || '')
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('复制失败:', err)
    }
  }

  // 获取需要高亮的文本和图片ID - 使用 useMemo 缓存结果
  const highlightData = useMemo(() => {
    console.log('📊 [highlightData] documentData:', documentData ? '存在' : '不存在')
    console.log('📊 [highlightData] content_json:', documentData?.content_json ? '存在' : '不存在')
    console.log('📊 [highlightData] content:', documentData?.content?.substring(0, 100))
    
    if (!highlightedItem) {
      console.log('📊 [highlightData] 没有 highlightedItem')
      return { texts: [], imageIds: [] }
    }
    const result = buildHighlightCandidates(highlightedItem, documentData?.content_json)
    console.log('📊 [highlightData] 计算结果:', result)
    return result
  }, [highlightedItem, documentData?.content_json])

  // 定位到冲突/事实在原文中的位置
  const handleLocate = useCallback((item, parentConflictId) => {
    console.log('🔍 [定位] 点击定位，item:', item)
    setHighlightedItem(item)

    // 如果左侧面板未展开，展开它
    if (!leftPanelExpanded) {
      setLeftPanelExpanded(true)
    }

    const { texts, imageIds } = buildHighlightCandidates(item, documentData?.content_json)
    console.log('🔍 [定位] 提取的图片ID:', imageIds, '文本:', texts)

    // 对于纯文本模式，使用 DOM 高亮
    if (!documentData?.content_json) {
      if (texts.length && documentRef.current) {
        setTimeout(() => {
          const highlightEl = documentRef.current.querySelector('.highlight-active')
          if (highlightEl) {
            highlightEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
        }, 100)
      }
    }
    // 富文本模式：RichTextEditor 内部会处理图片高亮和滚动
  }, [documentData, leftPanelExpanded])

  // 渲染带高亮的文档内容
  const renderDocumentContent = () => {
    const content = editMode ? editedContent : (documentData?.content || '')
    if (!content) return null

    const lines = content.split('\n')
    const highlightTexts = highlightData.texts

    return lines.map((line, index) => {
      const match = findHighlightMatch(line, highlightTexts)

      if (!match) {
        return (
          <p key={index} className="mb-2 leading-relaxed text-slate-700">
            {line || '\u00A0'}
          </p>
        )
      }

      const before = line.slice(0, match.index)
      const highlighted = line.slice(match.index, match.index + match.length)
      const after = line.slice(match.index + match.length)

      return (
        <p
          key={index}
          ref={(el) => {
            if (el) {
              highlightRefs.current[index] = el
            }
          }}
          className="mb-2 leading-relaxed text-slate-700"
        >
          {before}
          <span className="highlight-active bg-primary-100 border-b-2 border-primary-500 px-1 rounded">
            {highlighted}
          </span>
          {after}
        </p>
      )
    })
  }

  // 过滤冲突
  const filteredConflicts = filterType
    ? conflicts.filter(c => c.conflict_type === filterType)
    : conflicts

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-primary-50">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
          <p className="text-slate-600">正在加载分析结果...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-primary-50">
        <div className="text-center card p-8">
          <AlertTriangle className="w-12 h-12 text-danger-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-slate-900 mb-2">加载失败</h2>
          <p className="text-slate-600 mb-4">{error}</p>
          <button onClick={loadData} className="btn-primary">
            <RefreshCw className="w-4 h-4" />
            重试
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-primary-50">
      {/* 顶部导航栏 */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-[1920px] mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate(returnPath)}
                className="flex items-center gap-2 text-slate-600 hover:text-slate-900 transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span className="hidden sm:inline">返回</span>
              </button>
              <div className="h-6 w-px bg-slate-200" />
              <div>
                <h1 className="text-lg font-bold text-slate-900 truncate max-w-xs">
                  {result?.document_title || '分析结果'}
                </h1>
                <p className="text-xs text-slate-500">ID: {taskId}</p>
              </div>
            </div>

            {/* 统计信息 */}
            <div className="hidden md:flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-lg">
                <FileText className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-medium">{result?.document_length?.toLocaleString()} 字</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-primary-100 rounded-lg">
                <CheckCircle className="w-4 h-4 text-primary-600" />
                <span className="text-sm font-medium text-primary-700">{result?.total_facts} 事实</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-danger-100 rounded-lg">
                <AlertTriangle className="w-4 h-4 text-danger-600" />
                <span className="text-sm font-medium text-danger-700">{result?.total_conflicts} 冲突</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-lg">
                <Clock className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-medium">{result?.analysis_time?.toFixed(1)}s</span>
              </div>
            </div>

            {/* 导出按钮 */}
            <div className="flex items-center gap-2">
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
                className="input py-1.5 w-32 text-sm"
              >
                <option value="txt">纯文本 TXT</option>
                <option value="markdown">Markdown</option>
                <option value="json">JSON</option>
                <option value="docx">Word DOCX</option>
                <option value="pdf">PDF</option>
              </select>
              <button
                onClick={() => handleExport(exportFormat)}
                disabled={exporting}
                className="btn-primary py-1.5 px-3"
              >
                {exporting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                <span className="hidden sm:inline ml-1">导出报告</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 主内容区 - 左右布局 */}
      <div className="max-w-[1920px] mx-auto px-4 py-6">
        <div className="flex gap-6">
          {/* 左侧：原文区域 */}
          <div className={`transition-all duration-300 ${leftPanelExpanded ? 'w-1/2' : 'w-16'
            }`}>
            <div className="card h-[calc(100vh-180px)] flex flex-col sticky top-24">
              {/* 左侧头部 */}
              <div className="p-3 border-b border-slate-200 flex items-center justify-between bg-slate-50 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setLeftPanelExpanded(!leftPanelExpanded)}
                    className="p-1.5 hover:bg-slate-200 rounded-lg transition-colors"
                    title={leftPanelExpanded ? '收起' : '展开'}
                  >
                    {leftPanelExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                  </button>
                  {leftPanelExpanded && (
                    <>
                      <span className="font-medium text-slate-700">文档原文</span>
                      <span className="text-xs text-slate-500 bg-slate-200 px-2 py-0.5 rounded">
                        {(documentData?.content || '').length.toLocaleString()} 字
                      </span>
                    </>
                  )}
                </div>
                {leftPanelExpanded && (
                  <div className="flex items-center gap-1">
                    {editMode ? (
                      <>
                        <button
                          onClick={handleSaveDocument}
                          disabled={saving}
                          className="p-1.5 rounded-lg bg-primary-500 text-white hover:bg-primary-600 transition-colors disabled:opacity-50"
                          title="保存文档"
                        >
                          {saving ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Save className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => {
                            if (confirm('确定要退出编辑吗？未保存的更改将丢失。')) {
                              setEditMode(false)
                            }
                          }}
                          className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-600 transition-colors"
                          title="取消编辑"
                        >
                          ✕
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => setEditMode(!editMode)}
                          className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-600 transition-colors"
                          title="编辑原文"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={handleReanalyze}
                          disabled={reanalyzing}
                          className="p-1.5 rounded-lg bg-warning-500 text-white hover:bg-warning-600 transition-colors disabled:opacity-50"
                          title="检测冲突"
                        >
                          {reanalyzing ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <AlertTriangle className="w-4 h-4" />
                          )}
                        </button>
                      </>
                    )}
                    <button
                      onClick={handleCopyContent}
                      className="p-1.5 hover:bg-slate-200 rounded-lg text-slate-600 transition-colors"
                      title="复制内容"
                    >
                      {copied ? <Check className="w-4 h-4 text-success-600" /> : <Copy className="w-4 h-4" />}
                    </button>
                    <div className="relative group">
                      <button
                        className="p-1.5 hover:bg-slate-200 rounded-lg text-slate-600 transition-colors"
                        title="导出原文"
                      >
                        <FileDown className="w-4 h-4" />
                      </button>
                      <div className="absolute right-0 top-full mt-1 w-36 bg-white rounded-lg shadow-lg border border-slate-200 py-1 hidden group-hover:block z-10">
                        <button
                          onClick={() => handleExportDocument('txt')}
                          className="w-full px-3 py-1.5 text-left text-sm hover:bg-slate-100 transition-colors"
                        >
                          导出 TXT
                        </button>
                        <button
                          onClick={() => handleExportDocument('md')}
                          className="w-full px-3 py-1.5 text-left text-sm hover:bg-slate-100 transition-colors"
                        >
                          导出 Markdown
                        </button>
                        <button
                          onClick={() => handleExportDocument('docx')}
                          className="w-full px-3 py-1.5 text-left text-sm hover:bg-slate-100 transition-colors"
                        >
                          导出 DOCX
                        </button>
                        <button
                          onClick={() => handleExportDocument('pdf')}
                          className="w-full px-3 py-1.5 text-left text-sm hover:bg-slate-100 transition-colors"
                        >
                          导出 PDF
                        </button>
                      </div>
                    </div>
                    {highlightedItem && (
                      <button
                        onClick={() => setHighlightedItem(null)}
                        className="p-1.5 hover:bg-slate-200 rounded-lg text-slate-600 transition-colors"
                        title="清除高亮"
                      >
                        <EyeOff className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* 左侧内容 */}
              {leftPanelExpanded && (
                <div
                  ref={documentRef}
                  className="flex-1 overflow-y-auto p-4"
                >
                  {editMode ? (
                    <RichTextEditor
                      content={documentData?.content_json || {
                        type: 'doc',
                        content: (editedContent || documentData?.content || '').split('\n').map(line => ({
                          type: 'paragraph',
                          content: line ? [{ type: 'text', text: line }] : []
                        }))
                      }}
                      onChange={(json) => {
                        // 保存富文本 JSON
                        setEditedContentJson(json)
                        setDocumentData(prev => ({
                          ...prev,
                          content_json: json,
                        }))
                        // 也更新纯文本用于兼容
                        const extractText = (node) => {
                          if (node.type === 'text') return node.text || ''
                          if (node.content) return node.content.map(extractText).join('')
                          return ''
                        }
                        const text = json.content?.map(extractText).join('\n') || ''
                        setEditedContent(text)
                      }}
                      placeholder="编辑文档内容..."
                      minHeight="100%"
                      maxHeight="none"
                    />
                  ) : (
                    <div className="prose prose-slate max-w-none">
                      {documentData?.content_json ? (
                        // 如果有富文本 JSON，使用 RichTextEditor 只读模式显示
                        <>
                          {console.log('🖥️ [渲染] 使用 RichTextEditor, content_json:', JSON.stringify(documentData.content_json).substring(0, 200))}
                          <RichTextEditor
                            content={documentData.content_json}
                            readOnly={true}
                            placeholder=""
                            minHeight="100%"
                            maxHeight="none"
                            highlightTexts={highlightData.texts}
                            highlightImageIds={highlightData.imageIds}
                          />
                        </>
                      ) : documentData?.content_html ? (
                        // 如果有 HTML，直接渲染（带高亮支持）
                        <HighlightableContent
                          html={documentData.content_html}
                          highlightTexts={highlightData.texts}
                        />
                      ) : (
                        // 否则使用纯文本
                        renderDocumentContent()
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 右侧：分析结果 */}
          <div className={`transition-all duration-300 ${leftPanelExpanded ? 'w-1/2' : 'flex-1'
            }`}>
            <div className="card h-[calc(100vh-180px)] flex flex-col sticky top-24">
              {/* 右侧头部 - 标签切换 */}
              <div className="p-3 border-b border-slate-200 flex items-center justify-between bg-slate-50 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setActiveTab('conflicts')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium text-sm transition-all ${activeTab === 'conflicts'
                      ? 'bg-danger-100 text-danger-700'
                      : 'text-slate-600 hover:bg-slate-200'
                      }`}
                  >
                    <AlertTriangle className="w-4 h-4" />
                    冲突 ({conflicts.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('facts')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium text-sm transition-all ${activeTab === 'facts'
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-slate-600 hover:bg-slate-200'
                      }`}
                  >
                    <FileText className="w-4 h-4" />
                    事实 ({facts.length})
                  </button>
                </div>

                {/* 过滤器 */}
                {activeTab === 'conflicts' && (
                  <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-slate-400" />
                    <select
                      value={filterType}
                      onChange={(e) => setFilterType(e.target.value)}
                      className="input py-1 w-32 text-sm"
                    >
                      <option value="">全部类型</option>
                      {Object.entries(conflictTypeMap).map(([key, label]) => (
                        <option key={key} value={key}>{label}</option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {/* 右侧内容 */}
              <div className="flex-1 overflow-y-auto p-4">
                <AnimatePresence mode="wait">
                  {activeTab === 'conflicts' ? (
                    <motion.div
                      key="conflicts"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="space-y-3"
                    >
                      {filteredConflicts.length === 0 ? (
                        <div className="text-center py-12">
                          <CheckCircle className="w-16 h-16 text-success-500 mx-auto mb-4" />
                          <h3 className="text-lg font-bold text-slate-900 mb-2">
                            {filterType ? '没有此类型的冲突' : '未发现冲突'}
                          </h3>
                          <p className="text-slate-600 text-sm">
                            {filterType ? '尝试选择其他类型' : '文档内容一致性良好'}
                          </p>
                        </div>
                      ) : (
                        filteredConflicts.map((conflict, index) => (
                          <ConflictCard
                            key={conflict.conflict_id}
                            conflict={conflict}
                            index={index}
                            onLocate={handleLocate}
                            onLocateFact={handleLocate}
                            isHighlighted={highlightedItem?.conflict_id === conflict.conflict_id}
                          />
                        ))
                      )}
                    </motion.div>
                  ) : (
                    <motion.div
                      key="facts"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="space-y-2"
                    >
                      {facts.length === 0 ? (
                        <div className="text-center py-12">
                          <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                          <h3 className="text-lg font-bold text-slate-900 mb-2">
                            暂无事实数据
                          </h3>
                          <p className="text-slate-600 text-sm">
                            系统未从文档中提取到事实信息
                          </p>
                        </div>
                      ) : (
                        facts.map((fact, index) => (
                          <FactCard
                            key={fact.fact_id}
                            fact={fact}
                            index={index}
                            onLocate={handleLocate}
                            isHighlighted={highlightedItem?.fact_id === fact.fact_id}
                          />
                        ))
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 页脚 */}
      <div className="py-4 text-center text-sm text-slate-400">
        <p>© 2026 PatPat-Inconsistency-Hunter | AI驱动的文档一致性检测工具</p>
      </div>
    </div>
  )
}

export default ResultPage
