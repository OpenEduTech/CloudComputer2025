/**
 * PatPat-Inconsistency-Hunter 分析页面
 * 支持多任务管理，任务列表显示，文档上传，富文本编辑
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  FileText, 
  Upload, 
  Loader2, 
  AlertCircle,
  CheckCircle,
  Info,
  Sparkles,
  List,
  Plus,
  Trash2,
  Clock,
  XCircle,
  FileUp,
  Edit3,
  RotateCcw,
} from 'lucide-react'
import { analyzeDocument, getTaskStatus, createProgressWebSocket, uploadDocumentImage, parseDocumentFile } from '../api'
import RichTextEditor from '../components/RichTextEditor'

// 示例文档内容
const sampleDocument = `第一章 项目概述

1.1 项目背景
本项目于2023年6月正式启动，预计2024年12月完成。项目总投资为500万元人民币，由张明担任项目负责人。

1.2 项目目标
项目的主要目标是开发一套智能文档管理系统，预计可以提升文档处理效率30%以上。团队共有15名成员参与开发。

第二章 技术方案

2.1 技术架构
系统采用微服务架构，后端使用Java语言开发，数据库选用MySQL。项目于2023年5月开始技术调研。

2.2 核心功能
系统支持最大100MB的文件上传，处理速度可达每秒1000个文档。项目负责人李华表示对进度很满意。

第三章 进度计划

3.1 里程碑
第一阶段（2023年6月-2023年9月）：完成需求分析和设计，投入资金200万元。
第二阶段（2023年10月-2024年6月）：完成核心功能开发，团队增加到20人。
第三阶段（2024年7月-2024年12月）：测试和上线，总投资达到600万元。

3.2 当前进度
截至目前，项目已完成60%的开发工作。系统可处理每秒500个文档，预计下月提升到800个。

第四章 风险分析

4.1 技术风险
技术选型方面存在一定风险，目前后端使用Python语言开发。需要注意数据库性能问题。

4.2 进度风险
项目启动时间为2023年7月，比原计划推迟了一个月。目前团队仅有12名成员，人手紧张。`

// localStorage keys
const TASKS_STORAGE_KEY = 'patpat_analysis_tasks'

// 任务状态
const TaskStatus = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
}

// 加载任务列表
const loadTasks = () => {
  try {
    const saved = localStorage.getItem(TASKS_STORAGE_KEY)
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
}

// 保存任务列表
const saveTasks = (tasks) => {
  localStorage.setItem(TASKS_STORAGE_KEY, JSON.stringify(tasks))
}

// 解析上传的文件内容 - 支持 TXT, MD, DOCX, PDF
const parseFileContent = async (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    const fileName = file.name.toLowerCase()
    
    if (fileName.endsWith('.txt') || file.type === 'text/plain') {
      // 纯文本文件
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = () => reject(new Error('文件读取失败'))
      reader.readAsText(file, 'UTF-8')
    } else if (fileName.endsWith('.md')) {
      // Markdown文件
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = () => reject(new Error('文件读取失败'))
      reader.readAsText(file, 'UTF-8')
    } else if (fileName.endsWith('.docx')) {
      // Word文档 - 使用简单解析
      reader.onload = async (e) => {
        try {
          const arrayBuffer = e.target.result
          // 简单解析docx（zip格式中的document.xml）
          const JSZip = (await import('jszip')).default
          const zip = await JSZip.loadAsync(arrayBuffer)
          const content = await zip.file('word/document.xml')?.async('text')
          if (!content) {
            reject(new Error('无法读取Word文档内容'))
            return
          }
          // 提取文本内容
          const textContent = content
            .replace(/<w:p[^>]*>/g, '\n')
            .replace(/<w:t[^>]*>([^<]*)<\/w:t>/g, '$1')
            .replace(/<[^>]+>/g, '')
            .replace(/\n{3,}/g, '\n\n')
            .trim()
          resolve(textContent)
        } catch (err) {
          reject(new Error('Word文档解析失败: ' + err.message))
        }
      }
      reader.onerror = () => reject(new Error('文件读取失败'))
      reader.readAsArrayBuffer(file)
    } else if (fileName.endsWith('.pdf')) {
      // PDF文件解析
      reader.onload = async (e) => {
        try {
          const arrayBuffer = e.target.result
          // 使用 pdf.js 解析 PDF
          const pdfjsLib = await import('pdfjs-dist')
          
          // 设置 worker
          pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`
          
          const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
          let fullText = ''
          
          // 遍历每一页提取文本
          for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i)
            const textContent = await page.getTextContent()
            const pageText = textContent.items.map(item => item.str).join(' ')
            fullText += pageText + '\n\n'
          }
          
          resolve(fullText.trim())
        } catch (err) {
          reject(new Error('PDF文档解析失败: ' + err.message))
        }
      }
      reader.onerror = () => reject(new Error('文件读取失败'))
      reader.readAsArrayBuffer(file)
    } else {
      reject(new Error('不支持的文件格式，请上传 .txt, .md, .docx 或 .pdf 文件'))
    }
  })
}

// 任务卡片组件 - 可点击进入详情
function TaskCard({ task, onClick, onDelete, isActive }) {
  const statusColors = {
    [TaskStatus.PENDING]: 'bg-slate-100 text-slate-600',
    [TaskStatus.RUNNING]: 'bg-primary-100 text-primary-600',
    [TaskStatus.COMPLETED]: 'bg-success-100 text-success-600',
    [TaskStatus.FAILED]: 'bg-danger-100 text-danger-600',
  }

  const statusIcons = {
    [TaskStatus.PENDING]: <Clock className="w-4 h-4" />,
    [TaskStatus.RUNNING]: <Loader2 className="w-4 h-4 animate-spin" />,
    [TaskStatus.COMPLETED]: <CheckCircle className="w-4 h-4" />,
    [TaskStatus.FAILED]: <XCircle className="w-4 h-4" />,
  }

  const statusText = {
    [TaskStatus.PENDING]: '等待中',
    [TaskStatus.RUNNING]: `${task.progress || 0}%`,
    [TaskStatus.COMPLETED]: '已完成',
    [TaskStatus.FAILED]: '失败',
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onClick(task)}
      className={`p-4 rounded-xl border-2 transition-all cursor-pointer shadow-sm hover:shadow-md ${
        isActive 
          ? 'border-primary-400 bg-primary-50 shadow-primary-100' 
          : 'border-slate-200 bg-white hover:border-primary-200'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <h4 className="font-semibold text-slate-800 truncate flex-1">
          {task.title || '未命名文档'}
        </h4>
        <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${statusColors[task.status]}`}>
          {statusIcons[task.status]}
          {statusText[task.status]}
        </span>
      </div>
      
      {task.status === TaskStatus.RUNNING && (
        <div className="mb-3">
          <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-gradient-to-r from-primary-400 to-primary-600"
              initial={{ width: 0 }}
              animate={{ width: `${task.progress || 0}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <p className="text-xs text-slate-500 mt-1.5 truncate">{task.currentStep || '处理中...'}</p>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>{new Date(task.createdAt).toLocaleString()}</span>
        <button 
          onClick={(e) => { e.stopPropagation(); onDelete(task.taskId); }}
          className="p-1.5 hover:bg-danger-100 rounded-lg text-danger-600 transition-colors"
          title="删除任务"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  )
}

function AnalyzePage() {
  const navigate = useNavigate()
  const [content, setContent] = useState('')
  const [editorContent, setEditorContent] = useState(null) // 富文本编辑器内容
  const [title, setTitle] = useState('')
  const [tasks, setTasks] = useState([])
  const [currentTaskId, setCurrentTaskId] = useState(null)
  const [error, setError] = useState(null)
  const [showForm, setShowForm] = useState(true)
  const [editMode, setEditMode] = useState('rich') // 富文本模式
  const [uploading, setUploading] = useState(false)
  const wsRefs = useRef({})
  const pollRefs = useRef({})
  const fileInputRef = useRef(null)

  // 初始化加载任务
  useEffect(() => {
    const savedTasks = loadTasks()
    setTasks(savedTasks)
    
    // 恢复正在运行的任务
    savedTasks.forEach(task => {
      if (task.status === TaskStatus.RUNNING) {
        startPolling(task.taskId)
      }
    })

    return () => {
      // 清理所有 WebSocket 和轮询
      Object.values(wsRefs.current).forEach(ws => ws?.close())
      Object.values(pollRefs.current).forEach(id => clearInterval(id))
    }
  }, [])

  // 保存任务列表
  useEffect(() => {
    saveTasks(tasks)
  }, [tasks])

  // 更新任务
  const updateTask = useCallback((taskId, updates) => {
    setTasks(prev => prev.map(t => 
      t.taskId === taskId ? { ...t, ...updates } : t
    ))
  }, [])

  // 删除任务
  const deleteTask = useCallback((taskId) => {
    if (wsRefs.current[taskId]) {
      wsRefs.current[taskId].close()
      delete wsRefs.current[taskId]
    }
    if (pollRefs.current[taskId]) {
      clearInterval(pollRefs.current[taskId])
      delete pollRefs.current[taskId]
    }
    setTasks(prev => prev.filter(t => t.taskId !== taskId))
    if (currentTaskId === taskId) {
      setCurrentTaskId(null)
      setShowForm(true)
    }
  }, [currentTaskId])

  // 轮询获取进度
  const startPolling = useCallback((taskId) => {
    if (pollRefs.current[taskId]) return

    pollRefs.current[taskId] = setInterval(async () => {
      try {
        const status = await getTaskStatus(taskId)
        
        updateTask(taskId, {
          progress: status.progress || 0,
          currentStep: status.current_step || '',
        })

        if (status.status === 'completed') {
          clearInterval(pollRefs.current[taskId])
          delete pollRefs.current[taskId]
          updateTask(taskId, { status: TaskStatus.COMPLETED, progress: 100 })
        } else if (status.status === 'failed') {
          clearInterval(pollRefs.current[taskId])
          delete pollRefs.current[taskId]
          updateTask(taskId, { 
            status: TaskStatus.FAILED, 
            error: status.error_message || '分析失败' 
          })
        }
      } catch (err) {
        console.error('获取状态失败:', err)
      }
    }, 2000)
  }, [updateTask])

  // 获取纯文本内容
  const getPlainTextContent = () => {
    if (editMode === 'rich' && editorContent) {
      // 从TipTap JSON格式提取纯文本
      const extractText = (node) => {
        if (node.type === 'text') return node.text || ''
        if (node.content) return node.content.map(extractText).join('')
        return ''
      }
      return editorContent.content?.map(extractText).join('\n') || ''
    }
    return content
  }

  // 提交分析
  const handleSubmit = async () => {
    const textContent = getPlainTextContent()
    
    if (textContent.length < 100) {
      setError('文档内容至少需要100个字符')
      return
    }

    setError(null)

    try {
      const response = await analyzeDocument({
        content: textContent,
        title: title || undefined,
        content_json: editMode === 'rich' ? editorContent : undefined,  // 发送富文本JSON
        skip_verification: false,
      })

      const newTask = {
        taskId: response.task_id,
        title: title || '未命名文档',
        status: TaskStatus.RUNNING,
        progress: 0,
        currentStep: '任务已提交',
        createdAt: Date.now(),
        contentLength: textContent.length,
      }

      setTasks(prev => [newTask, ...prev])
      setCurrentTaskId(response.task_id)
      setShowForm(false)

      // 清空表单
      setContent('')
      setEditorContent(null)
      setTitle('')

      // 尝试 WebSocket
      try {
        wsRefs.current[response.task_id] = createProgressWebSocket(
          response.task_id,
          (data) => {
            updateTask(response.task_id, {
              progress: data.progress || 0,
              currentStep: data.step || '',
            })
            if (data.progress >= 100) {
              updateTask(response.task_id, { status: TaskStatus.COMPLETED })
            }
          },
          () => {
            // WebSocket 失败，使用轮询
            startPolling(response.task_id)
          },
          () => {}
        )
      } catch {
        startPolling(response.task_id)
      }
    } catch (err) {
      // 处理特定错误码
      if (err.response?.status === 409) {
        const detail = err.response?.data?.detail || '该文档正在分析中，请等待分析完成后再试'
        setError(detail)
      } else {
        setError(err.message || '提交失败，请重试')
      }
    }
  }

  // 处理任务点击 - 进入结果页或查看进度
  const handleTaskClick = (task) => {
    if (task.status === TaskStatus.COMPLETED) {
      navigate(`/result/${task.taskId}`, { state: { from: '/analyze' } })
    } else {
      setCurrentTaskId(task.taskId)
      setShowForm(false)
    }
  }

  // 使用示例文档
  const useSampleDocument = () => {
    setContent(sampleDocument)
    setEditorContent({
      type: 'doc',
      content: [
        {
          type: 'paragraph',
          content: sampleDocument.split('\n').map(line => ({
            type: 'text',
            text: line || ' '
          }))
        }
      ]
    })
    setTitle('项目可行性报告（示例）')
  }

  // 处理文件上传（使用后端 API 解析，支持富文本格式）
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)

    try {
      // 调用后端 API 解析文件（支持富文本格式和图片）
      const result = await parseDocumentFile(file)
      
      // 设置解析结果
      if (result.content_json) {
        // 使用后端解析的富文本 JSON（包含格式和图片）
        setEditorContent(result.content_json)
        setContent(result.content || '')  // 纯文本作为后备
      } else {
        // 如果没有 content_json，使用纯文本
        setContent(result.content || '')
        setEditorContent({
          type: 'doc',
          content: (result.content || '').split('\n').map(line => ({
            type: 'paragraph',
            content: line ? [{ type: 'text', text: line }] : []
          }))
        })
      }
      
      // 设置标题（从后端解析或文件名）
      if (result.title) {
        setTitle(result.title)
      } else {
        const fileName = file.name.replace(/\.[^/.]+$/, '')
        setTitle(fileName)
      }
    } catch (err) {
      setError(err.message || '文件解析失败')
      console.error('文件解析失败:', err)
    } finally {
      setUploading(false)
      // 重置input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  // 获取当前任务
  const currentTask = tasks.find(t => t.taskId === currentTaskId)
  const runningTasks = tasks.filter(t => t.status === TaskStatus.RUNNING)
  const completedTasks = tasks.filter(t => t.status === TaskStatus.COMPLETED)
  const failedTasks = tasks.filter(t => t.status === TaskStatus.FAILED)
  const textContentLength = getPlainTextContent().length

  return (
    <div className="relative min-h-screen overflow-hidden gradient-bg">
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 标题 */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-3">
            文档分析
          </h1>
          <p className="text-slate-600">
            上传您的长文档，系统将自动检测其中的事实不一致性
          </p>
        </div>

        <div className="flex gap-6">
          {/* 左侧：任务列表 */}
          <div className="w-80 flex-shrink-0">
            <div className="card p-4 sticky top-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-slate-800 flex items-center gap-2">
                  <List className="w-5 h-5 text-primary-600" />
                  任务列表
                </h2>
                <button
                  onClick={() => { setShowForm(true); setCurrentTaskId(null); }}
                  className="p-2 bg-primary-100 hover:bg-primary-200 rounded-lg text-primary-600 transition-colors"
                  title="新建任务"
                >
                  <Plus className="w-5 h-5" />
                </button>
              </div>

              {/* 运行中任务 */}
              {runningTasks.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-xs font-medium text-slate-500 uppercase mb-2 flex items-center gap-1">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    运行中 ({runningTasks.length})
                  </h3>
                  <div className="space-y-2">
                    <AnimatePresence>
                      {runningTasks.map(task => (
                        <TaskCard
                          key={task.taskId}
                          task={task}
                          isActive={task.taskId === currentTaskId}
                          onClick={handleTaskClick}
                          onDelete={deleteTask}
                        />
                      ))}
                    </AnimatePresence>
                  </div>
                </div>
              )}

              {/* 已完成任务 */}
              {completedTasks.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-xs font-medium text-slate-500 uppercase mb-2 flex items-center gap-1">
                    <CheckCircle className="w-3 h-3 text-success-600" />
                    已完成 ({completedTasks.length})
                  </h3>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    <AnimatePresence>
                      {completedTasks.map(task => (
                        <TaskCard
                          key={task.taskId}
                          task={task}
                          isActive={task.taskId === currentTaskId}
                          onClick={handleTaskClick}
                          onDelete={deleteTask}
                        />
                      ))}
                    </AnimatePresence>
                  </div>
                </div>
              )}

              {/* 失败任务 */}
              {failedTasks.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-xs font-medium text-slate-500 uppercase mb-2 flex items-center gap-1">
                    <XCircle className="w-3 h-3 text-danger-600" />
                    失败 ({failedTasks.length})
                  </h3>
                  <div className="space-y-2">
                    <AnimatePresence>
                      {failedTasks.map(task => (
                        <TaskCard
                          key={task.taskId}
                          task={task}
                          isActive={task.taskId === currentTaskId}
                          onClick={handleTaskClick}
                          onDelete={deleteTask}
                        />
                      ))}
                    </AnimatePresence>
                  </div>
                </div>
              )}

              {tasks.length === 0 && (
                <div className="text-center py-8 text-slate-500">
                  <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">暂无分析任务</p>
                  <p className="text-xs text-slate-400 mt-1">点击上方 + 号创建</p>
                </div>
              )}
            </div>
          </div>

          {/* 右侧：表单/进度 */}
          <div className="flex-1">
            <AnimatePresence mode="wait">
              {showForm ? (
                <motion.div
                  key="form"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="space-y-6"
                >
                  {/* 文档标题输入 */}
                  <div className="card p-6">
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      文档标题（可选）
                    </label>
                    <input
                      type="text"
                      className="input"
                      placeholder="例如：毕业论文、项目报告..."
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                    />
                  </div>

                  {/* 文档内容输入 */}
                  <div className="card p-6">
                    <div className="flex items-center justify-between mb-4">
                      <label className="block text-sm font-medium text-slate-700">
                        文档内容
                      </label>
                      <div className="flex items-center gap-2">
                        {/* 上传文件 */}
                        <button
                          onClick={() => fileInputRef.current?.click()}
                          disabled={uploading}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
                        >
                          {uploading ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <FileUp className="w-4 h-4" />
                          )}
                          上传文件
                        </button>
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept=".txt,.md,.docx,.pdf"
                          className="hidden"
                          onChange={handleFileUpload}
                        />
                        
                        {/* 使用示例 */}
                        <button
                          onClick={useSampleDocument}
                          className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700"
                        >
                          <Sparkles className="w-4 h-4" />
                          示例文档
                        </button>
                      </div>
                    </div>
                    
                    <RichTextEditor
                      content={editorContent}
                      onChange={(json) => {
                        setEditorContent(json)
                        // 提取纯文本用于提交（包含图片占位符）
                        const extractText = (node) => {
                          if (node.type === 'text') return node.text || ''
                          // 图片节点生成占位符
                          if (node.type === 'image') {
                            const imageId = node.attrs?.['data-image-id'] || node.attrs?.imageId || ''
                            const alt = node.attrs?.alt || '图片'
                            if (imageId) {
                              return `[IMAGE:${imageId}:${alt}]`
                            }
                            return `[IMAGE:${alt}]`
                          }
                          if (node.content) return node.content.map(extractText).join('')
                          return ''
                        }
                        const text = json.content?.map(extractText).join('\n') || ''
                        setContent(text)
                      }}
                      onImageUpload={async (file) => {
                        // 上传图片到服务器并返回信息
                        const result = await uploadDocumentImage(file)
                        return {
                          url: result.file_url,
                          imageId: result.image_id,
                          alt: file.name,
                        }
                      }}
                      placeholder="请在此编辑您的文档内容（至少100字）...

支持上传格式：TXT、MD、DOCX、PDF
支持插入图片（将自动上传到服务器）"
                      minHeight="400px"
                      maxHeight="600px"
                    />
                    
                    <div className="flex items-center justify-between mt-3 text-sm">
                      <span className="text-slate-500">
                        当前字数: {textContentLength.toLocaleString()}
                      </span>
                      <span className={`${textContentLength >= 100 ? 'text-success-600' : 'text-slate-400'}`}>
                        {textContentLength >= 100 ? '✓ 已达到最小字数要求' : '至少100字'}
                      </span>
                    </div>
                  </div>

                  {/* 提示信息 */}
                  <div className="flex items-start gap-3 p-4 bg-gradient-to-r from-primary-50 to-primary-100 rounded-xl text-primary-700 border border-primary-200">
                    <Info className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <div className="text-sm">
                      <p className="font-medium mb-1">分析说明</p>
                      <ul className="list-disc list-inside space-y-1 text-primary-600">
                        <li>系统将自动提取文档中的关键事实</li>
                        <li>检测前后不一致的数据、日期、人名等信息</li>
                        <li>提供冲突修正建议</li>
                        <li>支持同时分析多个文档（点击左侧 + 号）</li>
                      </ul>
                    </div>
                  </div>

                  {/* 错误提示 */}
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-3 p-4 bg-danger-50 rounded-xl text-danger-700 border border-danger-200"
                    >
                      <AlertCircle className="w-5 h-5 flex-shrink-0" />
                      <span>{error}</span>
                    </motion.div>
                  )}

                  {/* 提交按钮 */}
                  <button
                    onClick={handleSubmit}
                    disabled={textContentLength < 100}
                    className="btn-primary w-full text-lg py-4 shadow-lg shadow-primary-200 hover:shadow-xl hover:shadow-primary-300 transition-all"
                  >
                    <Upload className="w-5 h-5" />
                    开始分析
                  </button>
                </motion.div>
              ) : currentTask ? (
                <motion.div
                  key="progress"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="card p-8"
                >
                  {/* 分析进度 */}
                  <div className="text-center">
                    <div className="w-32 h-32 mx-auto mb-6 relative">
                      {currentTask.status === TaskStatus.RUNNING ? (
                        <>
                          <svg className="w-32 h-32 transform -rotate-90">
                            <circle
                              cx="64"
                              cy="64"
                              r="56"
                              stroke="currentColor"
                              strokeWidth="8"
                              fill="none"
                              className="text-slate-200"
                            />
                            <circle
                              cx="64"
                              cy="64"
                              r="56"
                              stroke="currentColor"
                              strokeWidth="8"
                              fill="none"
                              strokeLinecap="round"
                              className="text-primary-500"
                              strokeDasharray={`${(currentTask.progress || 0) * 3.52} 352`}
                            />
                          </svg>
                          <div className="absolute inset-0 flex items-center justify-center">
                            <span className="text-3xl font-bold text-primary-600">
                              {Math.round(currentTask.progress || 0)}%
                            </span>
                          </div>
                        </>
                      ) : currentTask.status === TaskStatus.COMPLETED ? (
                        <div className="w-32 h-32 rounded-full bg-success-100 flex items-center justify-center">
                          <CheckCircle className="w-16 h-16 text-success-500" />
                        </div>
                      ) : (
                        <div className="w-32 h-32 rounded-full bg-danger-100 flex items-center justify-center">
                          <XCircle className="w-16 h-16 text-danger-500" />
                        </div>
                      )}
                    </div>

                    <h2 className="text-2xl font-bold text-slate-900 mb-2">
                      {currentTask.title}
                    </h2>
                    <p className="text-slate-600 mb-6">
                      {currentTask.status === TaskStatus.RUNNING 
                        ? (currentTask.currentStep || '正在处理...')
                        : currentTask.status === TaskStatus.COMPLETED
                        ? '分析完成！点击下方按钮查看详细结果'
                        : currentTask.error || '分析失败'
                      }
                    </p>

                    {currentTask.status === TaskStatus.RUNNING && (
                      <>
                        {/* 进度条 */}
                        <div className="h-3 bg-slate-200 rounded-full overflow-hidden mb-8">
                          <motion.div 
                            className="h-full bg-gradient-to-r from-primary-400 to-primary-600"
                            initial={{ width: 0 }}
                            animate={{ width: `${currentTask.progress || 0}%` }}
                            transition={{ duration: 0.5 }}
                          />
                        </div>

                        {/* 步骤说明 */}
                        <div className="grid grid-cols-4 gap-4 text-sm">
                          {[
                            { label: '文档处理', threshold: 10 },
                            { label: '事实提取', threshold: 50 },
                            { label: '冲突检测', threshold: 75 },
                            { label: '生成报告', threshold: 95 },
                          ].map((step, index) => {
                            const isActive = (currentTask.progress || 0) >= step.threshold
                            return (
                              <div 
                                key={index}
                                className={`flex flex-col items-center gap-2 transition-colors ${
                                  isActive ? 'text-primary-600' : 'text-slate-400'
                                }`}
                              >
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                                  isActive ? 'bg-primary-100' : 'bg-slate-100'
                                }`}>
                                  {isActive ? (
                                    <CheckCircle className="w-5 h-5" />
                                  ) : (
                                    <div className="w-3 h-3 rounded-full bg-current opacity-50" />
                                  )}
                                </div>
                                <span className="font-medium">{step.label}</span>
                              </div>
                            )
                          })}
                        </div>
                      </>
                    )}

                    {currentTask.status === TaskStatus.COMPLETED && (
                      <div className="flex gap-4 justify-center mt-6">
                        <button
                          onClick={() => handleTaskClick(currentTask)}
                          className="btn-primary px-8 py-3"
                        >
                          <FileText className="w-5 h-5" />
                          查看详细结果
                        </button>
                        <button
                          onClick={() => { setShowForm(true); setCurrentTaskId(null); }}
                          className="btn-secondary px-6 py-3"
                        >
                          <Plus className="w-5 h-5" />
                          分析新文档
                        </button>
                      </div>
                    )}

                    {currentTask.status === TaskStatus.FAILED && (
                      <div className="flex gap-4 justify-center mt-6">
                        <button
                          onClick={() => { setShowForm(true); setCurrentTaskId(null); }}
                          className="btn-primary px-8 py-3"
                        >
                          <RotateCcw className="w-5 h-5" />
                          重新分析
                        </button>
                      </div>
                    )}
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="card p-12 text-center"
                >
                  <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-slate-100 flex items-center justify-center">
                    <FileText className="w-12 h-12 text-slate-400" />
                  </div>
                  <h3 className="text-xl font-semibold text-slate-700 mb-2">
                    选择任务或创建新任务
                  </h3>
                  <p className="text-slate-500 mb-6">
                    从左侧任务列表选择一个任务查看，或点击下方按钮开始新的分析
                  </p>
                  <button
                    onClick={() => setShowForm(true)}
                    className="btn-primary px-8 py-3"
                  >
                    <Plus className="w-5 h-5" />
                    新建分析任务
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* 页脚 */}
        <div className="mt-12 text-center text-sm text-slate-400">
          <p>© 2026 PatPat-Inconsistency-Hunter | AI驱动的文档一致性检测工具</p>
        </div>
      </div>
    </div>
  )
}

export default AnalyzePage
