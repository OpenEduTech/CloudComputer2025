/**
 * PatPat-Inconsistency-Hunter 富文本编辑器组件
 * 基于 TipTap 实现，支持字体、颜色、图片、表格等功能
 */

import { Extension } from '@tiptap/core'
import { useEditor, EditorContent, BubbleMenu } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextStyle from '@tiptap/extension-text-style'
import Color from '@tiptap/extension-color'
import FontFamily from '@tiptap/extension-font-family'
import Highlight from '@tiptap/extension-highlight'
import Image from '@tiptap/extension-image'
import Link from '@tiptap/extension-link'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import TextAlign from '@tiptap/extension-text-align'
import Placeholder from '@tiptap/extension-placeholder'
import CharacterCount from '@tiptap/extension-character-count'
import { Plugin, PluginKey } from 'prosemirror-state'
import { Decoration, DecorationSet } from 'prosemirror-view'
import { useCallback, useRef, useState, useEffect } from 'react'
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Strikethrough,
  Code,
  List,
  ListOrdered,
  Quote,
  Undo,
  Redo,
  Link as LinkIcon,
  Unlink,
  Image as ImageIcon,
  Table as TableIcon,
  AlignLeft,
  AlignCenter,
  AlignRight,
  AlignJustify,
  Heading1,
  Heading2,
  Heading3,
  Palette,
  Type,
  Highlighter,
  Plus,
  Minus,
  Trash2,
  MoreHorizontal,
} from 'lucide-react'

// 字体列表
const FONT_FAMILIES = [
  { value: '', label: '默认字体' },
  { value: 'Microsoft YaHei', label: '微软雅黑' },
  { value: 'SimSun', label: '宋体' },
  { value: 'SimHei', label: '黑体' },
  { value: 'KaiTi', label: '楷体' },
  { value: 'Arial', label: 'Arial' },
  { value: 'Georgia', label: 'Georgia' },
  { value: 'Times New Roman', label: 'Times New Roman' },
  { value: 'Courier New', label: 'Courier New' },
]

// 自定义字体大小扩展
const FontSizeExtension = Extension.create({
  name: 'fontSize',
  addGlobalAttributes() {
    return [
      {
        types: ['textStyle'],
        attributes: {
          fontSize: {
            default: null,
            renderHTML: attributes => {
              if (!attributes.fontSize) return {}
              return { style: `font-size: ${attributes.fontSize}` }
            },
            parseHTML: element => element.style.fontSize || null,
          },
        },
      },
    ]
  },
})

// 字号列表
const FONT_SIZES = [
  { value: '12px', label: '12' },
  { value: '14px', label: '14' },
  { value: '16px', label: '16' },
  { value: '18px', label: '18' },
  { value: '20px', label: '20' },
  { value: '24px', label: '24' },
  { value: '28px', label: '28' },
  { value: '32px', label: '32' },
  { value: '36px', label: '36' },
  { value: '48px', label: '48' },
]

// 颜色列表
const COLORS = [
  '#000000', '#333333', '#666666', '#999999', '#cccccc',
  '#ef4444', '#f97316', '#eab308', '#22c55e', '#14b8a6',
  '#0ea5e9', '#6366f1', '#a855f7', '#ec4899', '#f43f5e',
]

// 高亮颜色
const HIGHLIGHT_COLORS = [
  '#fef08a', '#bbf7d0', '#bfdbfe', '#ddd6fe', '#fbcfe8',
]

const SEARCH_HIGHLIGHT_CLASS = 'search-highlight'
const highlightPluginKey = new PluginKey('searchHighlight')

// 清理文本：移除 markdown 格式、多余空白等
const normalizeHighlightText = (value) => {
  if (!value) return ''
  return value
    .replace(/\*\*([^*]+)\*\*/g, '$1')  // 移除 **粗体**
    .replace(/\*([^*]+)\*/g, '$1')      // 移除 *斜体*
    .replace(/__([^_]+)__/g, '$1')      // 移除 __粗体__
    .replace(/_([^_]+)_/g, '$1')        // 移除 _斜体_
    .replace(/`([^`]+)`/g, '$1')        // 移除 `代码`
    .replace(/#+\s*/g, '')              // 移除 # 标题标记
    .replace(/\s+/g, ' ')               // 合并多个空白
    .trim()
}

const findHighlightRange = (doc, highlightTexts = []) => {
  if (!highlightTexts || highlightTexts.length === 0) {
    console.log('🔍 [findHighlightRange] highlightTexts 为空')
    return null
  }

  const normalizedList = highlightTexts
    .map(normalizeHighlightText)
    .filter(Boolean)

  console.log('🔍 [findHighlightRange] 搜索文本数量:', normalizedList.length, '第一个:', normalizedList[0]?.substring(0, 50))

  // 收集文档中的所有文本内容用于调试
  let allText = ''
  const textNodes = []
  doc.descendants((node, pos) => {
    if (node.isText) {
      textNodes.push({ pos, text: node.text })
      allText += node.text
    }
    return true
  })
  console.log('📄 [findHighlightRange] 文档文本节点数:', textNodes.length, '总文本长度:', allText.length)
  console.log('📄 [findHighlightRange] 文档内容预览:', allText.substring(0, 200))

  for (const searchText of normalizedList) {
    const searchLower = searchText.toLowerCase()
    let foundRange = null

    // 方法1: 精确匹配单个节点
    doc.descendants((node, pos) => {
      if (foundRange) return false
      if (!node.isText) return true
      const text = node.text || ''
      const index = text.toLowerCase().indexOf(searchLower)
      if (index !== -1) {
        foundRange = {
          from: pos + index,
          to: pos + index + searchText.length,
        }
        console.log('✅ [findHighlightRange] 方法1找到匹配:', { from: foundRange.from, to: foundRange.to, text: text.substring(index, index + 50) })
        return false
      }
      return true
    })

    if (foundRange) return foundRange

    // 方法2: 尝试在全文中查找（处理跨节点的情况）
    const allTextLower = allText.toLowerCase()
    const globalIndex = allTextLower.indexOf(searchLower)
    if (globalIndex !== -1) {
      console.log('✅ [findHighlightRange] 方法2在全文中找到:', globalIndex)
      // 计算实际的文档位置
      let currentPos = 0
      let accumulatedLength = 0
      for (const { pos, text } of textNodes) {
        if (accumulatedLength + text.length > globalIndex) {
          const offsetInNode = globalIndex - accumulatedLength
          foundRange = {
            from: pos + offsetInNode,
            to: pos + offsetInNode + Math.min(searchText.length, text.length - offsetInNode),
          }
          console.log('✅ [findHighlightRange] 方法2计算位置:', foundRange)
          return foundRange
        }
        accumulatedLength += text.length
      }
    }

    // 方法3: 尝试部分匹配（取搜索文本的前半部分）
    if (!foundRange && searchText.length > 10) {
      const partialSearch = searchText.substring(0, Math.min(30, searchText.length))
      const partialLower = partialSearch.toLowerCase()
      
      doc.descendants((node, pos) => {
        if (foundRange) return false
        if (!node.isText) return true
        const text = node.text || ''
        const index = text.toLowerCase().indexOf(partialLower)
        if (index !== -1) {
          foundRange = {
            from: pos + index,
            to: pos + index + partialSearch.length,
          }
          console.log('✅ [findHighlightRange] 方法3部分匹配:', { from: foundRange.from, to: foundRange.to })
          return false
        }
        return true
      })
      
      if (foundRange) return foundRange
    }
  }

  console.log('⚠️ [findHighlightRange] 未找到任何匹配')
  return null
}

const buildHighlightDecorations = (doc, highlightRange, highlightTexts) => {
  const maxPos = doc.content.size
  const decorations = []

  if (highlightRange && Number.isFinite(highlightRange.from) && Number.isFinite(highlightRange.to)) {
    const from = Math.max(0, Math.min(highlightRange.from, maxPos))
    const to = Math.max(0, Math.min(highlightRange.to, maxPos))
    if (from < to) {
      decorations.push(Decoration.inline(from, to, { class: SEARCH_HIGHLIGHT_CLASS }))
    }
  }

  if (decorations.length === 0) {
    const textRange = findHighlightRange(doc, highlightTexts)
    if (textRange) {
      const from = Math.max(0, Math.min(textRange.from, maxPos))
      const to = Math.max(0, Math.min(textRange.to, maxPos))
      if (from < to) {
        decorations.push(Decoration.inline(from, to, { class: SEARCH_HIGHLIGHT_CLASS }))
      }
    }
  }

  return decorations.length > 0 ? DecorationSet.create(doc, decorations) : DecorationSet.empty
}

const SearchHighlight = Extension.create({
  name: 'searchHighlight',
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: highlightPluginKey,
        state: {
          init: () => ({ decorations: DecorationSet.empty }),
          apply(tr, pluginState) {
            const meta = tr.getMeta(highlightPluginKey)
            if (meta?.decorations) {
              return { decorations: meta.decorations }
            }
            if (tr.docChanged) {
              return { decorations: pluginState.decorations.map(tr.mapping, tr.doc) }
            }
            return pluginState
          },
        },
        props: {
          decorations(state) {
            return this.getState(state).decorations
          },
        },
      }),
    ]
  },
})

// 工具栏按钮组件
function ToolbarButton({ onClick, active, disabled, title, children }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`p-1.5 rounded hover:bg-slate-200 transition-colors ${
        active ? 'bg-primary-100 text-primary-600' : 'text-slate-600'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {children}
    </button>
  )
}

// 工具栏分隔符
function ToolbarDivider() {
  return <div className="w-px h-6 bg-slate-200 mx-1" />
}

// 下拉选择框
function ToolbarSelect({ value, onChange, options, title }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      title={title}
      className="h-8 px-2 text-sm border border-slate-200 rounded hover:border-slate-300 focus:outline-none focus:border-primary-500"
    >
      {options.map(opt => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  )
}

// 颜色选择器
function ColorPicker({ colors, value, onChange, title }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        title={title}
        className="p-1.5 rounded hover:bg-slate-200 transition-colors text-slate-600 flex items-center gap-1"
      >
        <Palette className="w-4 h-4" />
        <div 
          className="w-3 h-3 rounded-sm border border-slate-300"
          style={{ backgroundColor: value || '#000000' }}
        />
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 p-2 bg-white rounded-lg shadow-lg border border-slate-200 z-50">
          <div className="grid grid-cols-5 gap-1">
            {colors.map(color => (
              <button
                key={color}
                onClick={() => { onChange(color); setOpen(false); }}
                className={`w-6 h-6 rounded border ${value === color ? 'border-primary-500 ring-2 ring-primary-200' : 'border-slate-200'}`}
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// 主编辑器组件
function RichTextEditor({
  content,
  onChange,
  onSave,
  placeholder = '请输入内容...',
  readOnly = false,
  minHeight = '300px',
  maxHeight = '600px',
  showToolbar = true,
  showWordCount = true,
  onImageUpload,
  className = '',
  highlightTexts = [],  // 需要高亮的文本数组
  highlightRange = null,
  highlightImageIds = [], // 需要高亮的图片ID数组
  onEditorReady,        // 编辑器就绪回调
  onSelectionUpdate,    // 光标/选区变化回调
}) {
  const [linkUrl, setLinkUrl] = useState('')
  const [showLinkInput, setShowLinkInput] = useState(false)
  const fileInputRef = useRef(null)
  const editorContainerRef = useRef(null)
  const highlightSignatureRef = useRef('')

  // 初始化编辑器
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Underline,
      TextStyle,
      FontSizeExtension,
      Color,
      FontFamily,
      Highlight.configure({
        multicolor: true,
      }),
      Image.configure({
        inline: true,
        allowBase64: true,
        HTMLAttributes: {
          class: 'rich-text-image',
        },
      }).extend({
        addAttributes() {
          return {
            ...this.parent?.(),
            'data-image-id': {
              default: null,
              parseHTML: element => element.getAttribute('data-image-id'),
              renderHTML: attributes => {
                if (!attributes['data-image-id']) {
                  return {}
                }
                return { 'data-image-id': attributes['data-image-id'] }
              },
            },
            imageId: {
              default: null,
              parseHTML: element => element.getAttribute('data-image-id'),
              renderHTML: attributes => ({}),
            },
          }
        },
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-primary-600 underline',
        },
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableCell,
      TableHeader,
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
      Placeholder.configure({
        placeholder,
      }),
      CharacterCount,
      SearchHighlight,
    ],
    content: content || '',
    editable: !readOnly,
    onUpdate: ({ editor }) => {
      if (onChange) {
        onChange(editor.getJSON())
      }
      if (onSelectionUpdate) {
        onSelectionUpdate(editor)
      }
    },
    onSelectionUpdate: ({ editor }) => {
      if (onSelectionUpdate) {
        onSelectionUpdate(editor)
      }
    },
  })

  // 更新内容
  const [contentLoaded, setContentLoaded] = useState(false)
  
  useEffect(() => {
    if (editor && content) {
      const currentContent = JSON.stringify(editor.getJSON())
      const newContent = JSON.stringify(content)
      if (currentContent !== newContent) {
        console.log('📝 [RichTextEditor] 加载内容到编辑器')
        editor.commands.setContent(content)
        setContentLoaded(true)
        // 内容加载后，延迟触发高亮更新
        setTimeout(() => {
          highlightSignatureRef.current = '' // 重置签名，强制重新应用高亮
        }, 100)
      } else if (!contentLoaded) {
        setContentLoaded(true)
      }
    }
  }, [content, editor])

  // 图片上传处理
  const handleImageUpload = useCallback(async (file) => {
    if (!file) return

    if (onImageUpload) {
      try {
        // 调用上传函数，返回包含 url 和 imageId 的对象
        const result = await onImageUpload(file)
        if (result && editor) {
          // 如果返回的是对象（包含url和imageId），使用完整信息
          if (typeof result === 'object') {
            editor.chain().focus().setImage({ 
              src: result.url || result.file_url,
              alt: result.alt || file.name,
              // 存储图片ID用于后续处理和占位
              'data-image-id': result.imageId || result.image_id,
            }).run()
          } else {
            // 兼容只返回URL的情况
            editor.chain().focus().setImage({ src: result }).run()
          }
        }
      } catch (error) {
        console.error('图片上传失败:', error)
        alert('图片上传失败: ' + (error.message || '未知错误'))
      }
    } else {
      // 如果没有上传函数，使用 base64（仅用于预览，不推荐）
      const reader = new FileReader()
      reader.onload = (e) => {
        if (editor) {
          // 生成临时ID
          const tempId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
          editor.chain().focus().setImage({ 
            src: e.target.result,
            alt: file.name,
            'data-image-id': tempId,
          }).run()
        }
      }
      reader.readAsDataURL(file)
    }
  }, [editor, onImageUpload])

  // 链接处理
  const handleSetLink = useCallback(() => {
    if (linkUrl) {
      editor.chain().focus().setLink({ href: linkUrl }).run()
    } else {
      editor.chain().focus().unsetLink().run()
    }
    setShowLinkInput(false)
    setLinkUrl('')
  }, [editor, linkUrl])

  // 表格操作
  const insertTable = useCallback(() => {
    editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
  }, [editor])

  // 编辑器就绪回调
  useEffect(() => {
    if (editor && onEditorReady) {
      onEditorReady(editor)
    }
  }, [editor, onEditorReady])

  const applyHighlightDecorations = useCallback(() => {
    if (!editor) {
      console.log('⚠️ [applyHighlightDecorations] editor 不存在')
      return
    }
    
    const normalizedTexts = Array.isArray(highlightTexts)
      ? highlightTexts.map(normalizeHighlightText).filter(Boolean)
      : []
    
    console.log('🔍 [applyHighlightDecorations] highlightTexts:', highlightTexts?.length, 'normalizedTexts:', normalizedTexts?.length)
    
    const signature = JSON.stringify({
      range: highlightRange && Number.isFinite(highlightRange.from) && Number.isFinite(highlightRange.to)
        ? { from: highlightRange.from, to: highlightRange.to }
        : null,
      texts: normalizedTexts,
    })
    
    console.log('🔍 [applyHighlightDecorations] 当前签名:', signature.substring(0, 100))
    console.log('🔍 [applyHighlightDecorations] 上次签名:', highlightSignatureRef.current?.substring(0, 100))
    
    if (highlightSignatureRef.current === signature) {
      console.log('⏭️ [applyHighlightDecorations] 签名相同，跳过更新')
      return
    }
    
    highlightSignatureRef.current = signature
    console.log('✅ [applyHighlightDecorations] 签名更新，应用装饰')
    
    const decorations = buildHighlightDecorations(editor.state.doc, highlightRange, normalizedTexts)
    console.log('🎨 [applyHighlightDecorations] 装饰数量:', decorations === DecorationSet.empty ? 0 : '有装饰')
    
    const tr = editor.state.tr.setMeta(highlightPluginKey, { decorations })
    editor.view.dispatch(tr)
    
    // 滚动到高亮位置
    setTimeout(() => {
      if (!editor?.view?.dom) return
      const highlightEl = editor.view.dom.querySelector(`.${SEARCH_HIGHLIGHT_CLASS}`)
      if (highlightEl) {
        console.log('📍 [文本高亮] 找到高亮元素，滚动到位置')
        highlightEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
      } else {
        console.log('⚠️ [文本高亮] 未找到高亮元素 (类名:', SEARCH_HIGHLIGHT_CLASS, ')')
      }
    }, 100)
  }, [editor, highlightRange, highlightTexts])

  useEffect(() => {
    console.log('🎯 [RichTextEditor useEffect] 触发高亮更新, editor:', !!editor, 'highlightTexts:', highlightTexts?.length, 'contentLoaded:', contentLoaded)
    if (!editor || !contentLoaded) {
      console.log('⏳ [RichTextEditor useEffect] 等待内容加载...')
      return
    }
    // 延迟执行确保编辑器内容已完全渲染
    const timeoutId = setTimeout(() => {
      applyHighlightDecorations()
    }, 50)
    return () => clearTimeout(timeoutId)
  }, [editor, applyHighlightDecorations, contentLoaded])

  // 处理图片高亮
  useEffect(() => {
    console.log('🖼️ [RichTextEditor] highlightImageIds 变化:', highlightImageIds, 'editor:', !!editor)
    
    if (!editor || !highlightImageIds || highlightImageIds.length === 0) {
      // 清除高亮
      if (editor?.view?.dom) {
        const previousHighlights = editor.view.dom.querySelectorAll('.image-highlight')
        previousHighlights.forEach(el => {
          el.classList.remove('image-highlight')
          el.style.outline = ''
          el.style.boxShadow = ''
        })
      }
      return
    }
    
    // 延迟执行以确保 DOM 已更新
    const timeoutId = setTimeout(() => {
      if (!editor?.view?.dom) return
      
      // 清除之前的图片高亮
      const previousHighlights = editor.view.dom.querySelectorAll('.image-highlight')
      previousHighlights.forEach(el => {
        el.classList.remove('image-highlight')
        el.style.outline = ''
        el.style.boxShadow = ''
      })
      
      let firstHighlightedImage = null
      
      for (const imageId of highlightImageIds) {
        if (!imageId) continue
        
        console.log('🔍 [图片高亮] 查找图片ID:', imageId)
        
        // 从 TipTap 的 DOM 中查找图片 - 尝试多种方式
        let img = editor.view.dom.querySelector(`img[data-image-id="${imageId}"]`)
        
        // 如果找不到，尝试不区分大小写或部分匹配
        if (!img) {
          const allImages = editor.view.dom.querySelectorAll('img')
          for (const candidateImg of allImages) {
            const candidateId = candidateImg.getAttribute('data-image-id') || candidateImg.getAttribute('imageId')
            if (candidateId === imageId || candidateId?.includes(imageId) || imageId.includes(candidateId)) {
              img = candidateImg
              console.log('✅ [图片高亮] 通过部分匹配找到图片:', candidateId, '->', imageId)
              break
            }
          }
        }
        
        if (img) {
          console.log('✅ [图片高亮] 找到并高亮图片:', imageId)
          img.classList.add('image-highlight')
          img.style.outline = '3px solid #a855f7'
          img.style.boxShadow = '0 0 0 6px rgba(168, 85, 247, 0.2)'
          img.style.borderRadius = '4px'
          img.style.transition = 'all 0.3s ease'
          
          if (!firstHighlightedImage) {
            firstHighlightedImage = img
          }
        } else {
          // 调试：打印所有可用图片
          const allImages = Array.from(editor.view.dom.querySelectorAll('img'))
          const availableIds = allImages.map(img => ({
            'data-image-id': img.getAttribute('data-image-id'),
            'imageId': img.getAttribute('imageId'),
            'src': img.getAttribute('src')?.substring(0, 50)
          }))
          console.warn('❌ [图片高亮] 未找到图片:', imageId, '可用图片:', availableIds)
        }
      }
      
      // 滚动到第一个高亮的图片
      if (firstHighlightedImage) {
        setTimeout(() => {
          firstHighlightedImage.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }, 100)
      }
    }, 200)
    
    return () => clearTimeout(timeoutId)
  }, [editor, highlightImageIds])

  if (!editor) {
    return <div className="animate-pulse bg-slate-100 rounded-lg h-64" />
  }

  return (
    <div className={`rich-text-editor border border-slate-200 rounded-lg overflow-hidden ${className}`}>
      {/* 工具栏 */}
      {showToolbar && !readOnly && (
        <div className="flex flex-wrap items-center gap-1 p-2 bg-slate-50 border-b border-slate-200">
          {/* 撤销/重做 */}
          <ToolbarButton
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            title="撤销"
          >
            <Undo className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            title="重做"
          >
            <Redo className="w-4 h-4" />
          </ToolbarButton>

          <ToolbarDivider />

          {/* 字体和字号 */}
          <ToolbarSelect
            value={editor.getAttributes('textStyle').fontFamily || ''}
            onChange={(value) => {
              if (value) {
                editor.chain().focus().setFontFamily(value).run()
              } else {
                editor.chain().focus().unsetFontFamily().run()
              }
            }}
            options={FONT_FAMILIES}
            title="字体"
          />
          <ToolbarSelect
            value={editor.getAttributes('textStyle').fontSize || ''}
            onChange={(value) => {
              if (value) {
                editor.chain().focus().setMark('textStyle', { fontSize: value }).run()
              } else {
                editor.chain().focus().setMark('textStyle', { fontSize: null }).run()
              }
            }}
            options={[{ value: '', label: '默认' }, ...FONT_SIZES]}
            title="字号"
          />

          <ToolbarDivider />

          {/* 标题 */}
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            active={editor.isActive('heading', { level: 1 })}
            title="标题1"
          >
            <Heading1 className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            active={editor.isActive('heading', { level: 2 })}
            title="标题2"
          >
            <Heading2 className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            active={editor.isActive('heading', { level: 3 })}
            title="标题3"
          >
            <Heading3 className="w-4 h-4" />
          </ToolbarButton>

          <ToolbarDivider />

          {/* 基本格式 */}
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBold().run()}
            active={editor.isActive('bold')}
            title="加粗"
          >
            <Bold className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleItalic().run()}
            active={editor.isActive('italic')}
            title="斜体"
          >
            <Italic className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            active={editor.isActive('underline')}
            title="下划线"
          >
            <UnderlineIcon className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleStrike().run()}
            active={editor.isActive('strike')}
            title="删除线"
          >
            <Strikethrough className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleCode().run()}
            active={editor.isActive('code')}
            title="行内代码"
          >
            <Code className="w-4 h-4" />
          </ToolbarButton>

          <ToolbarDivider />

          {/* 颜色 */}
          <ColorPicker
            colors={COLORS}
            value={editor.getAttributes('textStyle').color}
            onChange={(color) => editor.chain().focus().setColor(color).run()}
            title="文字颜色"
          />
          <ColorPicker
            colors={HIGHLIGHT_COLORS}
            value={editor.getAttributes('highlight').color}
            onChange={(color) => editor.chain().focus().toggleHighlight({ color }).run()}
            title="高亮颜色"
          />

          <ToolbarDivider />

          {/* 对齐 */}
          <ToolbarButton
            onClick={() => editor.chain().focus().setTextAlign('left').run()}
            active={editor.isActive({ textAlign: 'left' })}
            title="左对齐"
          >
            <AlignLeft className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().setTextAlign('center').run()}
            active={editor.isActive({ textAlign: 'center' })}
            title="居中"
          >
            <AlignCenter className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().setTextAlign('right').run()}
            active={editor.isActive({ textAlign: 'right' })}
            title="右对齐"
          >
            <AlignRight className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().setTextAlign('justify').run()}
            active={editor.isActive({ textAlign: 'justify' })}
            title="两端对齐"
          >
            <AlignJustify className="w-4 h-4" />
          </ToolbarButton>

          <ToolbarDivider />

          {/* 列表 */}
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            active={editor.isActive('bulletList')}
            title="无序列表"
          >
            <List className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            active={editor.isActive('orderedList')}
            title="有序列表"
          >
            <ListOrdered className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            active={editor.isActive('blockquote')}
            title="引用"
          >
            <Quote className="w-4 h-4" />
          </ToolbarButton>

          <ToolbarDivider />

          {/* 链接 */}
          <div className="relative">
            <ToolbarButton
              onClick={() => setShowLinkInput(!showLinkInput)}
              active={editor.isActive('link')}
              title="插入链接"
            >
              <LinkIcon className="w-4 h-4" />
            </ToolbarButton>
            {showLinkInput && (
              <div className="absolute top-full left-0 mt-1 p-2 bg-white rounded-lg shadow-lg border border-slate-200 z-50 flex gap-2">
                <input
                  type="url"
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  placeholder="输入链接地址"
                  className="w-48 px-2 py-1 text-sm border border-slate-200 rounded"
                  onKeyDown={(e) => e.key === 'Enter' && handleSetLink()}
                />
                <button
                  onClick={handleSetLink}
                  className="px-2 py-1 text-sm bg-primary-500 text-white rounded hover:bg-primary-600"
                >
                  确定
                </button>
              </div>
            )}
          </div>
          {editor.isActive('link') && (
            <ToolbarButton
              onClick={() => editor.chain().focus().unsetLink().run()}
              title="移除链接"
            >
              <Unlink className="w-4 h-4" />
            </ToolbarButton>
          )}

          {/* 图片 */}
          <ToolbarButton
            onClick={() => fileInputRef.current?.click()}
            title="插入图片"
          >
            <ImageIcon className="w-4 h-4" />
          </ToolbarButton>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) handleImageUpload(file)
              e.target.value = ''
            }}
          />

          {/* 表格 */}
          <ToolbarButton
            onClick={insertTable}
            title="插入表格"
          >
            <TableIcon className="w-4 h-4" />
          </ToolbarButton>

          {/* 表格操作 */}
          {editor.isActive('table') && (
            <>
              <ToolbarButton
                onClick={() => editor.chain().focus().addColumnAfter().run()}
                title="添加列"
              >
                <Plus className="w-4 h-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor.chain().focus().addRowAfter().run()}
                title="添加行"
              >
                <Plus className="w-4 h-4 rotate-90" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor.chain().focus().deleteColumn().run()}
                title="删除列"
              >
                <Minus className="w-4 h-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor.chain().focus().deleteRow().run()}
                title="删除行"
              >
                <Minus className="w-4 h-4 rotate-90" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor.chain().focus().deleteTable().run()}
                title="删除表格"
              >
                <Trash2 className="w-4 h-4" />
              </ToolbarButton>
            </>
          )}
        </div>
      )}

      {/* 编辑区域 */}
      <div 
        ref={editorContainerRef}
        className="prose prose-slate max-w-none"
        style={{ minHeight, maxHeight, overflow: 'auto' }}
      >
        <EditorContent 
          editor={editor} 
          className="p-4 focus:outline-none"
        />
      </div>

      {/* 字数统计 */}
      {showWordCount && (
        <div className="flex items-center justify-between px-4 py-2 bg-slate-50 border-t border-slate-200 text-sm text-slate-500">
          <span>
            {editor.storage.characterCount?.characters() || 0} 字符 / {editor.storage.characterCount?.words() || 0} 词
          </span>
          {onSave && (
            <button
              onClick={() => onSave(editor.getJSON())}
              className="px-3 py-1 bg-primary-500 text-white rounded hover:bg-primary-600 text-sm"
            >
              保存
            </button>
          )}
        </div>
      )}

      {/* 编辑器样式 */}
      <style>{`
        .ProseMirror {
          min-height: ${minHeight};
          outline: none;
        }
        .ProseMirror p.is-editor-empty:first-child::before {
          color: #adb5bd;
          content: attr(data-placeholder);
          float: left;
          height: 0;
          pointer-events: none;
        }
        .ProseMirror table {
          border-collapse: collapse;
          table-layout: fixed;
          width: 100%;
          margin: 1rem 0;
        }
        .ProseMirror th,
        .ProseMirror td {
          border: 1px solid #ddd;
          padding: 8px;
          vertical-align: top;
        }
        .ProseMirror th {
          background-color: #f4f4f4;
          font-weight: bold;
        }
        .ProseMirror img {
          max-width: 100%;
          height: auto;
        }
        .ProseMirror blockquote {
          border-left: 4px solid #ddd;
          margin: 1rem 0;
          padding-left: 1rem;
          color: #666;
        }
        .ProseMirror ul {
          list-style-type: disc;
          list-style-position: outside;
          padding-left: 1.5rem;
          margin: 0.75rem 0;
        }
        .ProseMirror ol {
          list-style-type: decimal;
          list-style-position: outside;
          padding-left: 1.5rem;
          margin: 0.75rem 0;
        }
        .ProseMirror li {
          margin: 0.25rem 0;
        }
        .ProseMirror .${SEARCH_HIGHLIGHT_CLASS} {
          background-color: #fef08a;
          border-radius: 2px;
          padding: 1px 2px;
          box-shadow: 0 0 0 2px #fef08a;
        }
        .ProseMirror pre {
          background: #f4f4f4;
          padding: 1rem;
          border-radius: 4px;
          overflow-x: auto;
        }
        .ProseMirror code {
          background: #f4f4f4;
          padding: 2px 4px;
          border-radius: 3px;
        }
      `}</style>
    </div>
  )
}

export default RichTextEditor

