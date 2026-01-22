/**
 * PatPat-Inconsistency-Hunter 协作房间页面
 * 支持实时协同编辑和分章节锁定编辑两种模式
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Users,
    Lock,
    Unlock,
    AlertTriangle,
    CheckCircle,
    FileText,
    Save,
    Loader2,
    ArrowLeft,
    Eye,
    Edit3,
    RefreshCw,
    Bell,
    X,
    Settings,
    Plus,
    Trash2,
    Crown,
    PanelRightOpen,
    PanelRightClose,
    ChevronDown,
    ChevronUp,
    Target,
    Sparkles,
} from 'lucide-react'
import {
    getRoom,
    updateContent,
    updateChapterContent,
    acquireLock,
    releaseLock,
    getRoomLocks,
    triggerDetection,
    getRoomConflicts,
    getDetectionStatus,
    cancelDetection,
    getRoomMembers,
    assignChapter,
    unassignChapter,
    addChapter,
    deleteChapter,
    updateRoomSettings,
    endRoom,
    exportRoomDocument,
    kickMember,
} from '../api/collaboration'
import { uploadDocumentImage } from '../api'
import { useAuth } from '../contexts/AuthContext'
import RichTextEditor from '../components/RichTextEditor'

// 用户头像组件
function UserAvatar({ username, color, isOnline, size = 'md', avatarUrl }) {
    const sizes = {
        sm: 'w-6 h-6 text-xs',
        md: 'w-8 h-8 text-sm',
        lg: 'w-10 h-10 text-base',
    }

    if (avatarUrl) {
        const avatarSrc = avatarUrl.includes('?') ? avatarUrl : `${avatarUrl}?t=${Date.now()}`
        return (
            <img
                src={avatarSrc}
                alt={username}
                className={`${sizes[size]} rounded-full object-cover relative border border-white`}
                title={username}
                onError={(e) => {
                    e.currentTarget.style.display = 'none'
                }}
            />
        )
    }

    return (
        <div
            className={`${sizes[size]} rounded-full flex items-center justify-center font-medium text-white relative`}
            style={{ backgroundColor: color }}
            title={username}
        >
            {username.charAt(0).toUpperCase()}
            {isOnline !== undefined && (
                <span className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white ${isOnline ? 'bg-success-500' : 'bg-slate-400'
                    }`} />
            )}
        </div>
    )
}

function DetectionNotification({ notice, onClose }) {
    if (!notice) return null
    const variantStyles = {
        info: 'text-primary-600',
        success: 'text-success-600',
        warn: 'text-warning-600',
        error: 'text-danger-600',
    }
    const iconColor = variantStyles[notice.variant || 'info'] || variantStyles.info
    return (
        <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-20 left-1/2 -translate-x-1/2 w-[420px] card shadow-xl z-50"
        >
            <div className="p-4 flex items-center justify-between gap-3">
                <div className={`flex items-center gap-2 ${iconColor}`}>
                    <Bell className="w-5 h-5" />
                    <span className="font-medium text-slate-700">{notice.message}</span>
                </div>
                <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
                    <X className="w-5 h-5" />
                </button>
            </div>
        </motion.div>
    )
}

// 协作者光标组件（显示其他用户的光标位置）
function CollaboratorCursor({ user, containerRef, editor }) {
    if (!containerRef?.current || !editor?.view || user?.position == null) return null

    try {
        const { view } = editor
        const container = containerRef.current
        const containerRect = container.getBoundingClientRect()

        const docSize = view.state.doc.content.size
        const safePosition = Math.min(Math.max(0, user.position), docSize)

        const coords = view.coordsAtPos(safePosition)

        const relativeLeft = coords.left - containerRect.left
        const relativeTop = coords.top - containerRect.top

        const cursorHeight = coords.bottom - coords.top

        if (relativeLeft < 0 || relativeTop < 0) return null

        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.5 }}
                transition={{ duration: 0.1 }}
                className="absolute pointer-events-none z-20 flex flex-col items-center"
                style={{
                    // 使用计算出的精确坐标
                    top: `${relativeTop}px`,
                    left: `${relativeLeft}px`,
                    transform: 'none'
                }}
            >
                {/* 光标线 */}
                <div
                    className="w-0.5 rounded-full"
                    style={{
                        height: `${cursorHeight || 20}px`, // 使用实际行高
                        backgroundColor: user.color,
                        boxShadow: `0 0 4px ${user.color}80`,
                    }}
                />

                {/* 用户信息标签 (放在光标上方) */}
                <div className="absolute bottom-full left-0 mb-1 flex flex-col items-start">
                    <div
                        className="px-1.5 py-0.5 rounded text-[10px] text-white whitespace-nowrap shadow-sm flex items-center gap-1"
                        style={{ backgroundColor: user.color }}
                    >
                        {user.avatar_url && (
                            <img
                                src={user.avatar_url}
                                alt=""
                                className="w-3 h-3 rounded-full border border-white/50"
                            />
                        )}
                        <span>{user.username}</span>
                    </div>
                </div>
            </motion.div>
        )
    } catch (error) {
        console.warn('光标渲染计算错误:', error)
        return null
    }
}

// 分析侧边栏组件
function AnalysisSidebar({ isOpen, onToggle, conflicts, facts, detecting, onTriggerDetection, onLocateInContent, isOwner, myChapterIds, taskId }) {
    const [activeTab, setActiveTab] = useState('conflicts')
    const [expandedItems, setExpandedItems] = useState({})
    const [sidebarWidth, setSidebarWidth] = useState(400)
    const [isResizing, setIsResizing] = useState(false)
    const sidebarRef = useRef(null)

    const toggleExpand = (id) => {
        setExpandedItems(prev => ({ ...prev, [id]: !prev[id] }))
    }

    // 拖拽调整宽度
    const handleMouseDown = (e) => {
        e.preventDefault()
        setIsResizing(true)
    }

    useEffect(() => {
        const handleMouseMove = (e) => {
            if (!isResizing) return
            const newWidth = window.innerWidth - e.clientX
            setSidebarWidth(Math.max(300, Math.min(600, newWidth)))
        }

        const handleMouseUp = () => {
            setIsResizing(false)
        }

        if (isResizing) {
            document.addEventListener('mousemove', handleMouseMove)
            document.addEventListener('mouseup', handleMouseUp)
        }

        return () => {
            document.removeEventListener('mousemove', handleMouseMove)
            document.removeEventListener('mouseup', handleMouseUp)
        }
    }, [isResizing])

    const conflictTypeMap = {
        numerical: '数值冲突',
        temporal: '时间冲突',
        entity: '实体冲突',
        categorical: '类别冲突',
        definition: '定义冲突',
        logical: '逻辑冲突',
        spatial: '空间冲突',
    }

    // 过滤显示的冲突（非房主只显示自己章节相关的）
    const filteredConflicts = isOwner ? conflicts : conflicts?.filter(c => {
        // 如果有章节信息，检查是否与用户章节相关
        if (!myChapterIds || myChapterIds.length === 0) return true
        // 简单匹配：如果冲突内容包含用户编辑的章节相关文本
        return true // 默认显示所有，由后端过滤
    })

    const filteredFacts = isOwner ? facts : facts?.filter(f => {
        if (!myChapterIds || myChapterIds.length === 0) return true
        return true
    })

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    ref={sidebarRef}
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: sidebarWidth, opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    className="h-full bg-white border-l border-slate-200 flex flex-col overflow-hidden relative"
                    style={{ minWidth: sidebarWidth }}
                >
                    {/* 拖拽调整宽度的手柄 */}
                    <div
                        className={`absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize hover:bg-primary-400 transition-colors ${isResizing ? 'bg-primary-500' : 'bg-transparent'}`}
                        onMouseDown={handleMouseDown}
                    />
                    {/* 侧边栏头部 */}
                    <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                        <div className="flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-primary-600" />
                            <h3 className="font-semibold text-slate-800">分析面板</h3>
                        </div>
                        <button
                            onClick={onToggle}
                            className="p-1 hover:bg-slate-200 rounded transition-colors"
                        >
                            <X className="w-5 h-5 text-slate-500" />
                        </button>
                    </div>

                    {/* 检测按钮 */}
                    <div className="p-4 border-b border-slate-200">
                        <button
                            onClick={onTriggerDetection}
                            disabled={detecting}
                            className="w-full btn-primary"
                        >
                            {detecting ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    检测中...
                                </>
                            ) : (
                                <>
                                    <Target className="w-4 h-4" />
                                    检测冲突
                                </>
                            )}
                        </button>
                        {detecting && (
                            <button
                                onClick={(event) => {
                                    event.stopPropagation()
                                    onTriggerDetection?.('cancel')
                                }}
                                className="w-full btn-secondary mt-2"
                            >
                                <X className="w-4 h-4" />
                                取消检测
                            </button>
                        )}
                        {/* 显示任务编号 */}
                        {taskId && (
                            <div className="mt-2 text-xs text-slate-500 text-center">
                                <span className="font-medium">任务编号:</span>
                                <code className="ml-1 px-1 py-0.5 bg-slate-100 rounded text-xs">{taskId}</code>
                            </div>
                        )}
                    </div>

                    {/* 标签页切换 */}
                    <div className="flex border-b border-slate-200">
                        <button
                            onClick={() => setActiveTab('conflicts')}
                            className={`flex-1 py-3 text-sm font-medium transition-colors ${activeTab === 'conflicts'
                                ? 'text-danger-600 border-b-2 border-danger-600 bg-danger-50'
                                : 'text-slate-600 hover:bg-slate-50'
                                }`}
                        >
                            <AlertTriangle className="w-4 h-4 inline mr-1" />
                            冲突 ({conflicts?.length || 0})
                        </button>
                        <button
                            onClick={() => setActiveTab('facts')}
                            className={`flex-1 py-3 text-sm font-medium transition-colors ${activeTab === 'facts'
                                ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50'
                                : 'text-slate-600 hover:bg-slate-50'
                                }`}
                        >
                            <FileText className="w-4 h-4 inline mr-1" />
                            事实 ({facts?.length || 0})
                        </button>
                    </div>

                    {/* 内容区域 */}
                    <div className="flex-1 overflow-y-auto p-3">
                        {activeTab === 'conflicts' ? (
                            <div className="space-y-2">
                                {!filteredConflicts || filteredConflicts.length === 0 ? (
                                    <div className="text-center py-8">
                                        <CheckCircle className="w-12 h-12 text-success-400 mx-auto mb-3" />
                                        <p className="text-slate-500 text-sm">暂无冲突</p>
                                        <p className="text-xs text-slate-400 mt-1">点击上方按钮进行检测</p>
                                    </div>
                                ) : (
                                    filteredConflicts.map((conflict, idx) => (
                                        <motion.div
                                            key={idx}
                                            className="rounded-lg border border-slate-200 overflow-hidden hover:shadow-md transition-shadow"
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                        >
                                            <div
                                                onClick={() => {
                                                    toggleExpand(`conflict-${idx}`)
                                                }}
                                                className="p-3 bg-slate-50 cursor-pointer hover:bg-slate-100 transition-colors"
                                            >
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-2">
                                                        <span className="px-2 py-0.5 text-xs rounded bg-danger-100 text-danger-700">
                                                            {conflictTypeMap[conflict.conflict_type] || conflict.conflict_type}
                                                        </span>
                                                        {conflict.is_image_conflict && (
                                                            <span className="px-2 py-0.5 text-xs rounded bg-purple-100 text-purple-700" title="此冲突涉及图片内容">
                                                                📷 图片
                                                            </span>
                                                        )}
                                                        <span className="text-xs text-slate-500">
                                                            {(conflict.severity * 100).toFixed(0)}%
                                                        </span>
                                                    </div>
                                                    {expandedItems[`conflict-${idx}`] ? (
                                                        <ChevronUp className="w-4 h-4 text-slate-400" />
                                                    ) : (
                                                        <ChevronDown className="w-4 h-4 text-slate-400" />
                                                    )}
                                                </div>
                                                <p className="text-sm text-slate-700 mt-2 line-clamp-2">
                                                    {conflict.description}
                                                </p>
                                            </div>
                                            {expandedItems[`conflict-${idx}`] && (
                                                <div className="p-3 border-t border-slate-100 text-sm space-y-3">
                                                    {conflict.suggestion && (
                                                        <div className="p-2 bg-primary-50 rounded text-primary-700">
                                                            <strong>建议:</strong> {conflict.suggestion}
                                                        </div>
                                                    )}
                                                    <div className="grid grid-cols-2 gap-2 text-xs">
                                                        <div
                                                            className="p-2 bg-danger-50 rounded group"
                                                        >
                                                            <div className="flex items-center justify-between">
                                                                <div className="flex items-center gap-1">
                                                                    <p className="font-medium text-danger-700">事实A</p>
                                                                    {conflict.fact_a?.is_image_source && (
                                                                        <span className="text-purple-500" title="来自图片">📷</span>
                                                                    )}
                                                                </div>
                                                                <Target className="w-3 h-3 text-danger-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                                                            </div>
                                                            <p className="text-slate-600 mt-1">{conflict.fact_a?.content || conflict.fact_a_content}</p>
                                                        </div>
                                                        <div
                                                            className="p-2 bg-warning-50 rounded group"
                                                        >
                                                            <div className="flex items-center justify-between">
                                                                <div className="flex items-center gap-1">
                                                                    <p className="font-medium text-warning-700">事实B</p>
                                                                    {conflict.fact_b?.is_image_source && (
                                                                        <span className="text-purple-500" title="来自图片">📷</span>
                                                                    )}
                                                                </div>
                                                                <Target className="w-3 h-3 text-warning-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                                                            </div>
                                                            <p className="text-slate-600 mt-1">{conflict.fact_b?.content || conflict.fact_b_content}</p>
                                                        </div>
                                                    </div>
                                                    {/* 定位按钮 - 使用事实对象进行定位（支持图片高亮） */}
                                                    <div className="flex gap-2">
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation()
                                                                // 传递完整的事实对象以支持图片高亮
                                                                const factA = conflict.fact_a || {
                                                                    source_text: conflict.fact_a_content,
                                                                    content: conflict.fact_a_content
                                                                }
                                                                onLocateInContent?.(factA)
                                                            }}
                                                            className={`flex-1 flex items-center justify-center gap-1 py-2 text-xs rounded transition-colors ${conflict.fact_a?.is_image_source
                                                                ? 'text-purple-600 hover:bg-purple-50'
                                                                : 'text-danger-600 hover:bg-danger-50'
                                                                }`}
                                                        >
                                                            <Target className="w-3.5 h-3.5" />
                                                            定位事实A {conflict.fact_a?.is_image_source && '🖼️'}
                                                        </button>
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation()
                                                                // 传递完整的事实对象以支持图片高亮
                                                                const factB = conflict.fact_b || {
                                                                    source_text: conflict.fact_b_content,
                                                                    content: conflict.fact_b_content
                                                                }
                                                                onLocateInContent?.(factB)
                                                            }}
                                                            className={`flex-1 flex items-center justify-center gap-1 py-2 text-xs rounded transition-colors ${conflict.fact_b?.is_image_source
                                                                ? 'text-purple-600 hover:bg-purple-50'
                                                                : 'text-warning-600 hover:bg-warning-50'
                                                                }`}
                                                        >
                                                            <Target className="w-3.5 h-3.5" />
                                                            定位事实B {conflict.fact_b?.is_image_source && '🖼️'}
                                                        </button>
                                                    </div>
                                                </div>
                                            )}
                                        </motion.div>
                                    ))
                                )}
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {!filteredFacts || filteredFacts.length === 0 ? (
                                    <div className="text-center py-8">
                                        <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                                        <p className="text-slate-500 text-sm">暂无事实数据</p>
                                    </div>
                                ) : (
                                    filteredFacts.map((fact, idx) => (
                                        <motion.div
                                            key={idx}
                                            className={`p-3 rounded-lg border hover:shadow-md transition-all cursor-pointer group ${fact.is_image_source
                                                ? 'border-purple-200 hover:border-purple-400 bg-purple-50/30'
                                                : 'border-slate-200 hover:border-primary-300'
                                                }`}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: idx * 0.03 }}
                                            onClick={() => onLocateInContent?.(fact)}
                                        >
                                            <div className="flex items-center justify-between mb-1">
                                                <div className="flex items-center gap-2">
                                                    <span className="px-2 py-0.5 text-xs rounded bg-primary-100 text-primary-700">
                                                        {fact.fact_type}
                                                    </span>
                                                    {fact.is_image_source && (
                                                        <span className="px-2 py-0.5 text-xs rounded bg-purple-100 text-purple-700" title="来自图片内容">
                                                            📷 图片
                                                        </span>
                                                    )}
                                                </div>
                                                <Target className="w-3.5 h-3.5 text-slate-300 group-hover:text-primary-500 transition-colors" />
                                            </div>
                                            <p className="text-sm text-slate-700">{fact.content}</p>
                                            {fact.source_text && (
                                                <p className="text-xs text-slate-400 mt-2 line-clamp-1">
                                                    来源: {fact.source_text}
                                                </p>
                                            )}
                                        </motion.div>
                                    ))
                                )}
                            </div>
                        )}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    )
}

// 冲突通知组件
function ConflictNotification({ conflicts, onClose }) {
    if (!conflicts || conflicts.length === 0) return null

    return (
        <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-20 right-4 w-96 card shadow-xl z-50"
        >
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2 text-danger-600">
                    <AlertTriangle className="w-5 h-5" />
                    <span className="font-medium">检测到 {conflicts.length} 个冲突</span>
                </div>
                <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
                    <X className="w-5 h-5" />
                </button>
            </div>
            <div className="max-h-80 overflow-y-auto">
                {conflicts.slice(0, 3).map((conflict, idx) => (
                    <div key={idx} className="p-4 border-b border-slate-50 last:border-0">
                        <div className="flex items-center gap-2 mb-2">
                            <span className="badge badge-danger text-xs">{conflict.conflict_type}</span>
                            <span className="text-xs text-slate-500">
                                严重程度: {(conflict.severity * 100).toFixed(0)}%
                            </span>
                        </div>
                        <p className="text-sm text-slate-700 line-clamp-2">{conflict.description}</p>
                    </div>
                ))}
            </div>
            {conflicts.length > 3 && (
                <div className="p-3 text-center text-sm text-slate-500 border-t border-slate-100">
                    还有 {conflicts.length - 3} 个冲突...
                </div>
            )}
        </motion.div>
    )
}

// 房主管理面板组件
function OwnerPanel({ room, members, chapters, locks, isRealtimeMode, onAssignChapter, onUnassignChapter, onAddChapter, onDeleteChapter, onUpdateSettings, onRefresh, onKickMember, onEndRoom, onExportDocument }) {
    const [showPanel, setShowPanel] = useState(false)
    const [activeTab, setActiveTab] = useState('members')
    const [newChapterTitle, setNewChapterTitle] = useState('')
    const [selectedMember, setSelectedMember] = useState('')
    const [selectedChapter, setSelectedChapter] = useState('')
    const [loading, setLoading] = useState(false)
    const [kickReason, setKickReason] = useState('')
    const [showEndRoomConfirm, setShowEndRoomConfirm] = useState(false)
    const [runDetectionBeforeEnd, setRunDetectionBeforeEnd] = useState(false)
    const [exportFormat, setExportFormat] = useState('md')
    const [includeAnalysis, setIncludeAnalysis] = useState(false)

    // 根据模式确定可用的标签页
    const availableTabs = isRealtimeMode
        ? ['members', 'settings']
        : ['members', 'chapters', 'settings']

    const handleAssignChapter = async () => {
        if (!selectedMember || !selectedChapter) {
            alert('请选择成员和章节')
            return
        }
        setLoading(true)
        try {
            await onAssignChapter(selectedChapter, selectedMember, true)
            setSelectedMember('')
            setSelectedChapter('')
            await onRefresh()
        } catch (error) {
            alert('分配失败: ' + error.message)
        } finally {
            setLoading(false)
        }
    }

    const handleAddChapter = async () => {
        if (!newChapterTitle.trim()) {
            alert('请输入章节标题')
            return
        }
        setLoading(true)
        try {
            await onAddChapter(newChapterTitle.trim())
            setNewChapterTitle('')
            await onRefresh()
        } catch (error) {
            alert('添加失败: ' + error.message)
        } finally {
            setLoading(false)
        }
    }

    const handleDeleteChapter = async (chapterId) => {
        if (!confirm('确定要删除这个章节吗？')) return
        setLoading(true)
        try {
            await onDeleteChapter(chapterId)
            await onRefresh()
        } catch (error) {
            alert('删除失败: ' + error.message)
        } finally {
            setLoading(false)
        }
    }

    const handleUnassignChapter = async (chapter) => {
        if (!chapter?.assigned_to) return
        const targetName = chapter.assigned_to_name || '该成员'
        if (!confirm(`确定取消 ${targetName} 对该章节的编辑权限吗？`)) return
        setLoading(true)
        try {
            await onUnassignChapter(chapter.id, chapter.assigned_to)
            await onRefresh()
        } catch (error) {
            alert('取消分配失败: ' + error.message)
        } finally {
            setLoading(false)
        }
    }

    const handleKickMember = async (userId) => {
        if (!confirm('确定要踢出这个成员吗？')) return
        setLoading(true)
        try {
            await onKickMember(userId, kickReason)
            setKickReason('')
            await onRefresh()
        } catch (error) {
            alert('踢出失败: ' + error.message)
        } finally {
            setLoading(false)
        }
    }

    const handleEndRoom = async () => {
        setLoading(true)
        try {
            await onEndRoom(runDetectionBeforeEnd)
            setShowEndRoomConfirm(false)
        } catch (error) {
            alert('结束房间失败: ' + error.message)
        } finally {
            setLoading(false)
        }
    }

    const handleExport = async () => {
        setLoading(true)
        try {
            await onExportDocument(exportFormat, includeAnalysis)
        } catch (error) {
            alert('导出失败: ' + error.message)
        } finally {
            setLoading(false)
        }
    }

    const getLockForChapter = (chapterId) => {
        return locks.find(l => l.chapter_id === chapterId)
    }

    return (
        <>
            <button
                onClick={() => setShowPanel(true)}
                className="btn-secondary"
            >
                <Settings className="w-4 h-4" />
                房间管理
            </button>

            <AnimatePresence>
                {showPanel && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
                        onClick={() => setShowPanel(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden"
                            onClick={e => e.stopPropagation()}
                        >
                            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                                <h2 className="text-xl font-bold text-slate-900">房间管理</h2>
                                <button onClick={() => setShowPanel(false)} className="text-slate-400 hover:text-slate-600">
                                    <X className="w-6 h-6" />
                                </button>
                            </div>

                            {/* 标签页 */}
                            <div className="flex border-b border-slate-100">
                                {availableTabs.map(tab => (
                                    <button
                                        key={tab}
                                        onClick={() => setActiveTab(tab)}
                                        className={`flex-1 py-3 text-sm font-medium ${activeTab === tab
                                            ? 'text-primary-600 border-b-2 border-primary-600'
                                            : 'text-slate-500 hover:text-slate-700'
                                            }`}
                                    >
                                        {tab === 'members' ? '成员管理' : tab === 'chapters' ? '章节管理' : '房间设置'}
                                    </button>
                                ))}
                            </div>

                            <div className="p-6 overflow-y-auto max-h-[60vh]">
                                {activeTab === 'members' && (
                                    <div className="space-y-4">
                                        <h3 className="font-medium text-slate-700 mb-3">当前成员 ({members.length}人)</h3>
                                        <div className="space-y-2">
                                            {members.map(member => (
                                                <div key={member.user_id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                                                    <div className="flex items-center gap-3">
                                                        <UserAvatar
                                                            username={member.username}
                                                            color={member.color}
                                                            avatarUrl={member.avatar_url}
                                                            isOnline={member.is_online}
                                                        />
                                                        <div>
                                                            <p className="font-medium text-slate-900">{member.username}</p>
                                                            <p className="text-xs text-slate-500">
                                                                {member.is_owner ? '房主' : '成员'}
                                                                {member.is_online && ' · 在线'}
                                                            </p>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        {member.is_owner ? (
                                                            <span className="badge badge-primary">房主</span>
                                                        ) : (
                                                            <button
                                                                onClick={() => handleKickMember(member.user_id)}
                                                                className="text-danger-600 hover:text-danger-700 p-1 hover:bg-danger-50 rounded"
                                                                title="踢出成员"
                                                                disabled={loading}
                                                            >
                                                                <X className="w-4 h-4" />
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {activeTab === 'chapters' && (
                                    <div className="space-y-6">
                                        {/* 章节分配 */}
                                        <div>
                                            <h3 className="font-medium text-slate-700 mb-3">分配章节编辑权</h3>
                                            <div className="grid grid-cols-2 gap-3 mb-3">
                                                <select
                                                    value={selectedMember}
                                                    onChange={e => setSelectedMember(e.target.value)}
                                                    className="input"
                                                >
                                                    <option value="">选择成员</option>
                                                    {members.map(m => (
                                                        <option key={m.user_id} value={m.user_id}>{m.username}</option>
                                                    ))}
                                                </select>
                                                <select
                                                    value={selectedChapter}
                                                    onChange={e => setSelectedChapter(e.target.value)}
                                                    className="input"
                                                >
                                                    <option value="">选择章节</option>
                                                    {chapters.map(ch => (
                                                        <option key={ch.id} value={ch.id}>{ch.title}</option>
                                                    ))}
                                                </select>
                                            </div>
                                            <button
                                                onClick={handleAssignChapter}
                                                className="btn-primary w-full"
                                                disabled={loading}
                                            >
                                                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
                                                分配编辑权
                                            </button>
                                        </div>

                                        {/* 添加章节 */}
                                        <div>
                                            <h3 className="font-medium text-slate-700 mb-3">添加新章节</h3>
                                            <div className="flex gap-3">
                                                <input
                                                    type="text"
                                                    value={newChapterTitle}
                                                    onChange={e => setNewChapterTitle(e.target.value)}
                                                    placeholder="输入章节标题，如：第一章 项目概述"
                                                    className="input flex-1"
                                                />
                                                <button
                                                    onClick={handleAddChapter}
                                                    className="btn-primary"
                                                    disabled={loading}
                                                >
                                                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                                                    添加
                                                </button>
                                            </div>
                                        </div>

                                        {/* 章节列表 */}
                                        <div>
                                            <h3 className="font-medium text-slate-700 mb-3">章节列表</h3>
                                            <div className="space-y-2">
                                                {chapters.map((chapter, index) => {
                                                    const lock = getLockForChapter(chapter.id)
                                                    return (
                                                        <div key={chapter.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                                                            <div className="flex items-center gap-3">
                                                                <span className="text-sm font-medium text-slate-500">{index + 1}</span>
                                                                <div>
                                                                    <p className="font-medium text-slate-900">{chapter.title}</p>
                                                                    {chapter.assigned_to_name && (
                                                                        <p className="text-xs text-primary-600">
                                                                            已分配给 {chapter.assigned_to_name}
                                                                        </p>
                                                                    )}
                                                                    {lock && (
                                                                        <p className="text-xs text-warning-600 flex items-center gap-1">
                                                                            <Lock className="w-3 h-3" />
                                                                            {lock.username} 正在编辑
                                                                        </p>
                                                                    )}
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center gap-2">
                                                                {chapter.assigned_to && (
                                                                    <button
                                                                        onClick={() => handleUnassignChapter(chapter)}
                                                                        className="text-amber-600 hover:text-amber-700 p-1"
                                                                        disabled={loading}
                                                                        title="取消分配"
                                                                    >
                                                                        <Unlock className="w-4 h-4" />
                                                                    </button>
                                                                )}
                                                                <button
                                                                    onClick={() => handleDeleteChapter(chapter.id)}
                                                                    className="text-danger-600 hover:text-danger-700 p-1"
                                                                    disabled={loading || lock}
                                                                    title={lock ? '章节正在被编辑，无法删除' : '删除章节'}
                                                                >
                                                                    <Trash2 className="w-4 h-4" />
                                                                </button>
                                                            </div>
                                                        </div>
                                                    )
                                                })}
                                                {chapters.length === 0 && (
                                                    <p className="text-slate-500 text-center py-4">暂无章节</p>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {activeTab === 'settings' && (
                                    <div className="space-y-6">
                                        {/* 房间信息 */}
                                        <div>
                                            <h3 className="font-medium text-slate-700 mb-3">房间信息</h3>
                                            <div className="space-y-3 bg-slate-50 rounded-lg p-4">
                                                <div className="flex justify-between">
                                                    <span className="text-slate-500">房间名称</span>
                                                    <span className="text-slate-900">{room?.room_name || '未命名'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-slate-500">文档标题</span>
                                                    <span className="text-slate-900">{room?.document_title || '未命名文档'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-slate-500">邀请码</span>
                                                    <span className="text-slate-900 font-mono">{room?.invite_code || '无'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-slate-500">协作模式</span>
                                                    <span className="text-slate-900">{isRealtimeMode ? '实时协作' : '分章节锁定'}</span>
                                                </div>
                                            </div>
                                        </div>

                                        {/* 导出文档 */}
                                        <div>
                                            <h3 className="font-medium text-slate-700 mb-3">导出文档</h3>
                                            <div className="space-y-3">
                                                <div className="flex gap-3">
                                                    <select
                                                        value={exportFormat}
                                                        onChange={e => setExportFormat(e.target.value)}
                                                        className="input flex-1"
                                                    >
                                                        <option value="txt">纯文本 (.txt)</option>
                                                        <option value="md">Markdown (.md)</option>
                                                        <option value="html">HTML (.html)</option>
                                                        <option value="docx">Word (.docx)</option>
                                                        <option value="pdf">PDF (.pdf)</option>
                                                    </select>
                                                    <button
                                                        onClick={handleExport}
                                                        className="btn-primary"
                                                        disabled={loading}
                                                    >
                                                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                                                        导出
                                                    </button>
                                                </div>
                                                <label className="flex items-center gap-2 text-sm">
                                                    <input
                                                        type="checkbox"
                                                        checked={includeAnalysis}
                                                        onChange={e => setIncludeAnalysis(e.target.checked)}
                                                        className="rounded border-slate-300"
                                                    />
                                                    <span className="text-slate-700">包含冲突和事实分析结果</span>
                                                </label>
                                            </div>
                                        </div>

                                        {/* 结束房间 */}
                                        <div className="border-t border-slate-200 pt-6">
                                            <h3 className="font-medium text-danger-700 mb-3">危险区域</h3>
                                            {!showEndRoomConfirm ? (
                                                <button
                                                    onClick={() => setShowEndRoomConfirm(true)}
                                                    className="btn bg-danger-50 text-danger-600 hover:bg-danger-100 w-full"
                                                >
                                                    <X className="w-4 h-4" />
                                                    结束房间
                                                </button>
                                            ) : (
                                                <div className="bg-danger-50 border border-danger-200 rounded-lg p-4 space-y-4">
                                                    <p className="text-danger-700 text-sm">
                                                        确定要结束房间吗？结束后所有成员将断开连接。
                                                    </p>
                                                    <label className="flex items-center gap-2 text-sm">
                                                        <input
                                                            type="checkbox"
                                                            checked={runDetectionBeforeEnd}
                                                            onChange={e => setRunDetectionBeforeEnd(e.target.checked)}
                                                            className="rounded border-slate-300"
                                                        />
                                                        <span className="text-slate-700">结束前进行冲突检测</span>
                                                    </label>
                                                    <div className="flex gap-2">
                                                        <button
                                                            onClick={() => setShowEndRoomConfirm(false)}
                                                            className="btn-secondary flex-1"
                                                        >
                                                            取消
                                                        </button>
                                                        <button
                                                            onClick={handleEndRoom}
                                                            className="btn bg-danger-600 text-white hover:bg-danger-700 flex-1"
                                                            disabled={loading}
                                                        >
                                                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <X className="w-4 h-4" />}
                                                            确认结束
                                                        </button>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    )
}

// 章节编辑器组件（分章节模式）- 使用富文本编辑器
function ChapterEditor({ chapter, lock, userId, onSave, onAcquireLock, onReleaseLock, highlightText, isOwner }) {
    const [content, setContent] = useState(chapter.content || '')
    const [editorContent, setEditorContent] = useState(() => {
        // 初始化富文本编辑器内容
        if (chapter.content) {
            return {
                type: 'doc',
                content: chapter.content.split('\n').map(line => ({
                    type: 'paragraph',
                    content: line ? [{ type: 'text', text: line }] : []
                }))
            }
        }
        return null
    })
    const [editing, setEditing] = useState(false)
    const [saving, setSaving] = useState(false)

    // 当 chapter.content 从父组件更新时，同步本地状态
    useEffect(() => {
        if (!editing && chapter.content !== content) {
            setContent(chapter.content || '')
            if (chapter.content) {
                setEditorContent({
                    type: 'doc',
                    content: chapter.content.split('\n').map(line => ({
                        type: 'paragraph',
                        content: line ? [{ type: 'text', text: line }] : []
                    }))
                })
            }
        }
    }, [chapter.content, editing])

    const isLocked = lock && lock.user_id !== userId
    const isMyLock = lock && lock.user_id === userId
    const assignedTo = chapter.assigned_to
    const assignedToName = chapter.assigned_to_name
    const canEdit = isOwner || assignedTo === userId

    // 检查当前章节是否包含高亮文本
    const hasHighlight = highlightText && (content || chapter.content || '')?.toLowerCase().includes(highlightText.toLowerCase())

    // 渲染高亮文本
    const renderHighlightedContent = (text) => {
        if (!highlightText || !text) return text

        const searchLower = highlightText.toLowerCase()
        const textLower = text.toLowerCase()
        const index = textLower.indexOf(searchLower)
        if (index === -1) return text

        const before = text.substring(0, index)
        const match = text.substring(index, index + highlightText.length)
        const after = text.substring(index + highlightText.length)

        return (
            <>
                {before}
                <mark className="bg-yellow-300 px-1 rounded animate-pulse font-semibold">{match}</mark>
                {after}
            </>
        )
    }

    const handleStartEdit = async () => {
        if (isLocked || !canEdit) return

        const success = await onAcquireLock(chapter.id)
        if (success) {
            setEditing(true)
        }
    }

    const handleSave = async () => {
        setSaving(true)
        await onSave(chapter.id, content)
        setSaving(false)
    }

    const handleStopEdit = async () => {
        setEditing(false)
        await onReleaseLock(chapter.id)
    }

    // 提取富文本内容为纯文本
    const handleEditorChange = (json) => {
        setEditorContent(json)
        const extractText = (node) => {
            if (node.type === 'text') return node.text || ''
            if (node.content) return node.content.map(extractText).join('')
            return ''
        }
        const text = json.content?.map(extractText).join('\n') || ''
        setContent(text)
    }

    return (
        <div className={`card overflow-hidden transition-all duration-300 ${hasHighlight ? 'ring-2 ring-yellow-400 ring-offset-2' : ''}`}>
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
                <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-slate-400" />
                    <h3 className="font-medium text-slate-900">{chapter.title}</h3>
                    {assignedToName && (
                        <span className="text-xs text-primary-600">
                            分配给 {assignedToName}
                        </span>
                    )}
                    {lock && (
                        <div className={`flex items-center gap-1 text-sm ${isMyLock ? 'text-success-600' : 'text-warning-600'}`}>
                            <Lock className="w-4 h-4" />
                            <span>{isMyLock ? '您正在编辑' : `${lock.username} 正在编辑`}</span>
                        </div>
                    )}
                    {hasHighlight && (
                        <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 rounded-full animate-pulse">
                            匹配
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    {editing ? (
                        <>
                            <button
                                onClick={handleSave}
                                className="btn-primary py-1.5 px-3 text-sm"
                                disabled={saving}
                            >
                                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                保存
                            </button>
                            <button onClick={handleStopEdit} className="btn-secondary py-1.5 px-3 text-sm">
                                <Unlock className="w-4 h-4" />
                                结束编辑
                            </button>
                        </>
                    ) : (
                        <button
                            onClick={handleStartEdit}
                            className={`btn py-1.5 px-3 text-sm ${isLocked || !canEdit ? 'btn-ghost opacity-50 cursor-not-allowed' : 'btn-primary'}`}
                            disabled={isLocked || !canEdit}
                        >
                            <Edit3 className="w-4 h-4" />
                            {isLocked ? '已被锁定' : !canEdit ? '无编辑权限' : '开始编辑'}
                        </button>
                    )}
                </div>
            </div>
            <div className="p-4">
                {editing ? (
                    <RichTextEditor
                        content={editorContent}
                        onChange={handleEditorChange}
                        onImageUpload={async (file) => {
                            const result = await uploadDocumentImage(file, null, chapter.chapter_id)
                            return {
                                url: result.file_url,
                                imageId: result.image_id,
                                alt: file.name,
                            }
                        }}
                        placeholder="输入章节内容..."
                        minHeight="200px"
                        maxHeight="400px"
                    />
                ) : (
                    <div className={`prose prose-slate max-w-none p-4 rounded-lg min-h-[100px] ${hasHighlight ? 'bg-yellow-50' : 'bg-slate-50'}`}>
                        <pre className="whitespace-pre-wrap text-sm text-slate-700 font-sans m-0">
                            {hasHighlight ? renderHighlightedContent(content || '（暂无内容）') : (content || '（暂无内容）')}
                        </pre>
                    </div>
                )}
            </div>
        </div>
    )
}

// 主页面组件
function CollaborateRoomPage() {
    const { roomId } = useParams()
    const navigate = useNavigate()
    const { user } = useAuth()

    const [room, setRoom] = useState(null)
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [content, setContent] = useState('')
    const [editorContent, setEditorContent] = useState(null) // 富文本编辑器内容
    const [locks, setLocks] = useState([])
    const [conflicts, setConflicts] = useState([])
    const [showConflicts, setShowConflicts] = useState(false)
    const [detecting, setDetecting] = useState(false)
    const [detectionLockInfo, setDetectionLockInfo] = useState(null)
    const [detectionNotice, setDetectionNotice] = useState(null)
    const [users, setUsers] = useState([])
    const [members, setMembers] = useState([])
    const [facts, setFacts] = useState([])
    const [showSidebar, setShowSidebar] = useState(false)
    const [userCursors, setUserCursors] = useState({}) // 存储其他用户的光标位置/鼠标位置
    const [detectionTaskId, setDetectionTaskId] = useState(null) // 检测任务编号

    const wsRef = useRef(null)
    const editorRef = useRef(null) // 编辑器引用，用于光标定位
    const contentContainerRef = useRef(null) // 内容容器引用，用于滚动定位
    const editorWrapperRef = useRef(null)
    const draftTimerRef = useRef(null)
    const pendingDraftRef = useRef({ content: '', contentJson: null })
    const suppressDraftRef = useRef(false)
    const cursorRafRef = useRef(null)
    const pendingSelectionRef = useRef(null)
    const lastCursorPosRef = useRef(null)
    const pendingRemoteCursorsRef = useRef({})
    const suppressRemoteSelectionRef = useRef(false)
    const suppressRemoteSelectionTimerRef = useRef(null)
    const detectionNoticeTimerRef = useRef(null)
    const [highlightText, setHighlightText] = useState(null) // 高亮显示的文本
    const [highlightRange, setHighlightRange] = useState(null)
    const [highlightImageIds, setHighlightImageIds] = useState([]) // 高亮显示的图片ID
    // 使用登录用户信息，如果未登录则使用localStorage中的
    const userId = user?.user_id || localStorage.getItem('patpat_user_id')
    const username = user?.display_name || user?.username || localStorage.getItem('patpat_username')

    // 判断当前用户是否是房主
    const isOwner = room && room.owner_id === userId
    const isRealtimeMode = room?.mode === 'realtime'

    // 获取当前用户锁定的章节ID列表
    const myChapterIds = locks
        .filter(l => l.user_id === userId)
        .map(l => l.chapter_id)

    // 加载房间数据
    useEffect(() => {
        loadRoom()
        loadLocks()
        loadConflicts()
        loadMembers()
        loadDetectionStatus()
    }, [roomId])

    const loadMembers = async () => {
        try {
            const data = await getRoomMembers(roomId)
            setMembers(data.members || [])
        } catch (error) {
            console.error('加载成员列表失败:', error)
        }
    }

    // WebSocket连接
    useEffect(() => {
        if (!room || !userId || !username) return

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${protocol}//${window.location.host}/api/collaboration/ws/${roomId}/${userId}/${username}`

        const ws = new WebSocket(wsUrl)

        ws.onopen = () => {
            console.log('WebSocket连接成功')
        }

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data)
            handleWebSocketMessage(message)
        }

        ws.onerror = (error) => {
            console.error('WebSocket错误:', error)
        }

        ws.onclose = () => {
            console.log('WebSocket连接关闭')
        }

        wsRef.current = ws

        // 定期发送心跳
        const heartbeat = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping', room_id: roomId }))
            }
        }, 30000)

        return () => {
            clearInterval(heartbeat)
            if (ws.readyState === WebSocket.OPEN) {
                ws.close()
            }
        }
    }, [room, userId, username, roomId])

    useEffect(() => {
        return () => {
            if (draftTimerRef.current) {
                clearTimeout(draftTimerRef.current)
            }
            if (cursorRafRef.current) {
                cancelAnimationFrame(cursorRafRef.current)
                cursorRafRef.current = null
            }
            if (suppressRemoteSelectionTimerRef.current) {
                clearTimeout(suppressRemoteSelectionTimerRef.current)
                suppressRemoteSelectionTimerRef.current = null
            }
            if (detectionNoticeTimerRef.current) {
                clearTimeout(detectionNoticeTimerRef.current)
                detectionNoticeTimerRef.current = null
            }
        }
    }, [])

    const buildEditorContentFromText = (rawText) => ({
        type: 'doc',
        content: (rawText || '').split('\n').map(line => ({
            type: 'paragraph',
            content: line ? [{ type: 'text', text: line }] : []
        }))
    })

    const flushPendingCursors = useCallback(() => {
        const editor = editorRef.current
        const docSize = editor?.state?.doc?.content?.size
        if (!docSize) return
        const pending = pendingRemoteCursorsRef.current
        const readyUserIds = Object.keys(pending).filter(userId => {
            const position = pending[userId]?.position
            return position != null && position <= docSize
        })
        if (!readyUserIds.length) return
        setUserCursors(prev => {
            const next = { ...prev }
            readyUserIds.forEach(uid => {
                next[uid] = {
                    ...(prev[uid] || {}),
                    ...pending[uid],
                }
            })
            return next
        })
        readyUserIds.forEach(uid => {
            delete pending[uid]
        })
    }, [])

    const suppressRemoteSelection = useCallback(() => {
        suppressRemoteSelectionRef.current = true
        if (suppressRemoteSelectionTimerRef.current) {
            clearTimeout(suppressRemoteSelectionTimerRef.current)
        }
        suppressRemoteSelectionTimerRef.current = setTimeout(() => {
            suppressRemoteSelectionRef.current = false
        }, 120)
    }, [])

    const pushDetectionNotice = useCallback((message, variant = 'info') => {
        if (!message) return
        setDetectionNotice({ message, variant })
        if (detectionNoticeTimerRef.current) {
            clearTimeout(detectionNoticeTimerRef.current)
        }
        detectionNoticeTimerRef.current = setTimeout(() => {
            setDetectionNotice(null)
        }, 4000)
    }, [])

    const loadDetectionStatus = useCallback(async () => {
        try {
            const status = await getDetectionStatus(roomId)
            setDetecting(Boolean(status?.is_detecting))
            setDetectionLockInfo(status?.lock || null)
            if (status?.is_detecting) {
                pushDetectionNotice('检测中，状态已同步', 'info')
            }
        } catch (error) {
            console.error('加载检测状态失败:', error)
        }
    }, [roomId, pushDetectionNotice])

    const runDetection = useCallback(async (contentOverride = null) => {
        if (detecting) {
            pushDetectionNotice('当前正在检测中，请稍后再试', 'warn')
            return
        }
        try {
            const result = await triggerDetection(roomId, true, contentOverride)
            if (result?.task_id) {
                setDetectionTaskId(result.task_id)
            }
            if (result?.conflicts) {
                setConflicts(result.conflicts)
                if (result.conflicts.length > 0) {
                    setShowConflicts(true)
                }
            }
            if (result?.facts) {
                setFacts(result.facts)
            }
            if (!showSidebar && (result?.conflicts?.length > 0 || result?.facts?.length > 0)) {
                setShowSidebar(true)
            }
        } catch (error) {
            const message = error?.message || '检测失败'
            if (message.includes('检测中') || message.includes('正在检测')) {
                setDetecting(true)
                setDetectionLockInfo({ message })
                pushDetectionNotice(message, 'warn')
            } else {
                setDetecting(false)
                setDetectionLockInfo(null)
                pushDetectionNotice(message, 'error')
            }
        }
    }, [detecting, pushDetectionNotice, roomId, showSidebar])

    const handleCancelDetection = useCallback(async () => {
        try {
            await cancelDetection(roomId)
            setDetecting(false)
            setDetectionLockInfo(null)
            pushDetectionNotice('检测已取消', 'warn')
        } catch (error) {
            console.error('取消检测失败:', error)
            pushDetectionNotice(error?.message || '取消检测失败', 'error')
        }
    }, [roomId, pushDetectionNotice])

    const handleWebSocketMessage = (message) => {
        console.log('WebSocket消息:', message.type, message.data)
        switch (message.type) {
            case 'user_list':
                setUsers(message.data.users || [])
                break
            case 'join':
                setUsers(prev => [...prev, {
                    user_id: message.data.user_id,
                    username: message.data.username,
                    avatar_url: message.data.avatar_url,
                }])
                break
            case 'leave':
                setUsers(prev => prev.filter(u => u.user_id !== message.data.user_id))
                setUserCursors(prev => {
                    if (!message.data?.user_id) return prev
                    const next = { ...prev }
                    delete next[message.data.user_id]
                    return next
                })
                break
            case 'content_update':
                suppressRemoteSelection()
                suppressDraftRef.current = true
                setContent(message.data.content || '')
                if (message.data?.content_json) {
                    setEditorContent(message.data.content_json)
                } else {
                    setEditorContent(buildEditorContentFromText(message.data.content || ''))
                }
                break
            case 'draft_update':
                suppressRemoteSelection()
                suppressDraftRef.current = true
                setContent(message.data?.content || '')
                if (message.data?.content_json) {
                    setEditorContent(message.data.content_json)
                } else {
                    setEditorContent(buildEditorContentFromText(message.data?.content || ''))
                }
                if (message.user_id) {
                    setTimeout(() => {
                        flushPendingCursors()
                    }, 0)
                }
                break
            case 'chapters_updated':
                // 更新章节列表
                if (message.data.chapters) {
                    setRoom(prev => prev ? { ...prev, chapters: message.data.chapters } : prev)
                }
                break
            case 'lock_status':
                setLocks(message.data.locks || [])
                break
            case 'conflict_detected':
                setConflicts(message.data.conflicts || [])
                setShowConflicts(true)
                break
            case 'detection_start':
                setDetecting(true)
                setDetectionLockInfo(message.data || {})
                pushDetectionNotice(message.data?.message || '正在检测文档冲突...', 'info')
                break
            case 'detection_complete':
                setDetecting(false)
                setDetectionLockInfo(null)
                {
                    const totalConflicts = message.data?.total_conflicts ?? message.data?.conflicts?.length ?? 0
                    const totalFacts = message.data?.total_facts ?? message.data?.facts?.length ?? 0
                    const variant = totalConflicts > 0 ? 'warn' : 'success'
                    pushDetectionNotice(`检测完成：${totalConflicts} 个冲突，${totalFacts} 个事实`, variant)
                }
                // 保存任务编号
                if (message.data?.task_id) {
                    setDetectionTaskId(message.data.task_id)
                }
                // 保存检测结果（冲突和事实）
                if (message.data?.conflicts) {
                    setConflicts(message.data.conflicts)
                    if (message.data.conflicts.length > 0 && !showSidebar) {
                        setShowSidebar(true)  // 自动打开侧边栏显示结果
                    }
                }
                if (message.data?.facts) {
                    setFacts(message.data.facts)
                }
                break
            case 'detection_cancel':
                setDetecting(false)
                setDetectionLockInfo(null)
                pushDetectionNotice(message.data?.message || '检测已取消', 'warn')
                break
            case 'cursor_update':
                // 更新其他用户的光标/鼠标位置
                const cursorUserId = message.user_id ?? message.data?.user_id
                if (cursorUserId && cursorUserId !== userId) {
                    const position = message.data.position
                    const docSize = editorRef.current?.state?.doc?.content?.size
                    if (docSize != null && position != null && position > docSize) {
                        pendingRemoteCursorsRef.current[cursorUserId] = {
                            position,
                            username: message.data.username,
                            color: message.data.color || '#64a386',
                            avatar_url: message.data.avatar_url,
                            mouse_x: message.data.mouse_x,
                            mouse_y: message.data.mouse_y,
                        }
                        break
                    }
                    setUserCursors(prev => ({
                        ...prev,
                        [cursorUserId]: {
                            position,
                            username: message.data.username,
                            color: message.data.color || '#64a386',
                            avatar_url: message.data.avatar_url,
                            mouse_x: message.data.mouse_x,
                            mouse_y: message.data.mouse_y,
                        }
                    }))
                }
                break
            case 'kicked':
                // 被踢出房间
                alert(message.data.message || '您已被移出房间')
                navigate('/collaborate')
                break
            case 'member_kicked':
                // 其他成员被踢出
                loadMembers()
                break
            case 'room_ended':
                // 房间已结束
                alert('房间已被房主结束')
                // 如果有文档内容，提供下载
                if (message.data.document_content) {
                    const shouldDownload = confirm('是否下载文档内容？')
                    if (shouldDownload) {
                        const blob = new Blob([message.data.document_content], { type: 'text/plain' })
                        const url = URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        a.download = `${message.data.document_title || '协作文档'}.txt`
                        a.click()
                        URL.revokeObjectURL(url)
                    }
                }
                navigate('/collaborate')
                break
            case 'permission_changed':
                // 权限变更通知（发给被分配用户）
                alert(message.data.message)
                loadLocks()
                break
            case 'chapter_assignment_changed':
                // 章节分配变更通知（发给所有用户）
                loadLocks()
                break
            case 'chapter_conflicts':
                // 收到与自己负责章节相关的冲突
                if (message.data?.conflicts) {
                    setConflicts(message.data.conflicts)
                    setShowSidebar(true)
                    alert(message.data.message || `检测到 ${message.data.conflicts.length} 个冲突`)
                }
                break
            case 'all_conflicts':
                // 房主收到所有冲突
                if (message.data?.conflicts) {
                    setConflicts(message.data.conflicts)
                    if (message.data.facts) {
                        setFacts(message.data.facts)
                    }
                    setShowSidebar(true)
                }
                break
            default:
                console.log('未处理的消息类型:', message.type)
        }
    }

    // 发送光标位置更新
    const sendCursorUpdate = useCallback((position, mouse) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                type: 'cursor_update',
                room_id: roomId,
                user_id: userId,
                data: {
                    position,
                    username,
                    mouse_x: mouse?.x,
                    mouse_y: mouse?.y,
                }
            }))
        }
    }, [roomId, userId, username])

    const sendDraftUpdate = useCallback((draftContent, draftJson) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                type: 'draft_update',
                room_id: roomId,
                user_id: userId,
                data: {
                    content: draftContent,
                    content_json: draftJson,
                }
            }))
        }
    }, [roomId, userId])

    // 处理编辑器光标变化（使用 TipTap selection 坐标）
    const handleEditorSelectionUpdate = useCallback((editor) => {
        if (!editorWrapperRef.current || !editor?.view) return
        if (wsRef.current?.readyState !== WebSocket.OPEN) return
        if (suppressRemoteSelectionRef.current) return
        pendingSelectionRef.current = editor
        if (cursorRafRef.current) return
        cursorRafRef.current = requestAnimationFrame(() => {
            cursorRafRef.current = null
            const currentEditor = pendingSelectionRef.current
            const position = currentEditor?.state?.selection?.from
            if (position == null) return
            if (lastCursorPosRef.current === position) return
            lastCursorPosRef.current = position
            sendCursorUpdate(position, null)
        })
    }, [sendCursorUpdate])

    const handleEditorReady = useCallback((editor) => {
        editorRef.current = editor
        flushPendingCursors()
    }, [])

    const setEditorContainerRef = useCallback((node) => {
        editorWrapperRef.current = node
        contentContainerRef.current = node
    }, [])

    useEffect(() => {
        flushPendingCursors()
    }, [editorContent, flushPendingCursors])

    const scheduleDraftUpdate = useCallback((draftContent, draftJson) => {
        if (!isRealtimeMode) return
        if (suppressDraftRef.current) {
            suppressDraftRef.current = false
            return
        }
        pendingDraftRef.current = { content: draftContent, contentJson: draftJson }
        if (draftTimerRef.current) {
            clearTimeout(draftTimerRef.current)
        }
        draftTimerRef.current = setTimeout(() => {
            const payload = pendingDraftRef.current
            sendDraftUpdate(payload.content, payload.contentJson)
        }, 200)
    }, [isRealtimeMode, sendDraftUpdate])

    const loadRoom = async () => {
        setLoading(true)
        try {
            const data = await getRoom(roomId)
            console.log('房间数据:', data)
            console.log('房间模式:', data.mode)
            console.log('章节数量:', data.chapters?.length)
            setRoom(data)
            setContent(data.content || '')
            // 初始化富文本编辑器内容
            if (data.content_json) {
                setEditorContent(data.content_json)
            } else if (data.content) {
                setEditorContent(buildEditorContentFromText(data.content))
            }
        } catch (error) {
            console.error('加载房间失败:', error)
            alert('房间不存在或已关闭')
            navigate('/collaborate')
        } finally {
            setLoading(false)
        }
    }

    const loadLocks = async () => {
        try {
            const data = await getRoomLocks(roomId)
            setLocks(data)
        } catch (error) {
            console.error('加载锁状态失败:', error)
        }
    }

    const loadConflicts = async () => {
        try {
            const data = await getRoomConflicts(roomId)
            console.log('加载检测结果:', data)
            // 保存任务编号
            if (data.task_id) {
                setDetectionTaskId(data.task_id)
            }
            if (data.conflicts) {
                setConflicts(data.conflicts)
            }
            // 同时加载事实列表
            if (data.facts) {
                setFacts(data.facts)
            }
        } catch (error) {
            console.error('加载冲突失败:', error)
        }
    }

    const handleSaveContent = async () => {
        setSaving(true)
        try {
            await updateContent(roomId, content, userId, editorContent)
            await runDetection(content)
        } catch (error) {
            console.error('保存失败:', error)
            alert('保存失败: ' + error.message)
        } finally {
            setSaving(false)
        }
    }

    const handleSaveChapter = async (chapterId, chapterContent) => {
        try {
            // 更新本地章节内容
            const updatedChapters = room.chapters.map(ch =>
                ch.id === chapterId ? { ...ch, content: chapterContent } : ch
            )
            setRoom({ ...room, chapters: updatedChapters })

            // 保存到服务器 - 使用章节更新 API
            await updateChapterContent(roomId, chapterId, chapterContent, userId)
            console.log('章节保存成功:', chapterId)
        } catch (error) {
            console.error('保存章节失败:', error)
            throw error
        }
    }

    const buildContentFromChapters = (chapters) => {
        return chapters.map(ch =>
            ch.title !== '全文' ? `${ch.title}\n\n${ch.content}` : ch.content
        ).join('\n\n')
    }

    const handleAcquireLock = async (chapterId) => {
        try {
            await acquireLock(roomId, chapterId, userId, username)
            await loadLocks()
            return true
        } catch (error) {
            alert('无法获取编辑权限: ' + error.message)
            return false
        }
    }

    const handleReleaseLock = async (chapterId) => {
        try {
            await releaseLock(roomId, chapterId, userId)
            await loadLocks()
        } catch (error) {
            console.error('释放锁失败:', error)
        }
    }

    // 房主管理功能
    const handleAssignChapter = async (chapterId, targetUserId, force = false) => {
        await assignChapter(roomId, chapterId, targetUserId, force)
    }

    const handleUnassignChapter = async (chapterId, targetUserId = null) => {
        await unassignChapter(roomId, chapterId, targetUserId)
    }

    const handleAddChapter = async (title) => {
        await addChapter(roomId, title)
    }

    const handleDeleteChapter = async (chapterId) => {
        await deleteChapter(roomId, chapterId)
    }

    const handleUpdateSettings = async (settings) => {
        await updateRoomSettings(roomId, settings)
    }

    const handleRefresh = async () => {
        await loadRoom()
        await loadLocks()
        await loadMembers()
    }

    const handleKickMember = async (targetUserId, reason = '') => {
        try {
            await kickMember(roomId, targetUserId, reason)
            await loadMembers()
        } catch (error) {
            throw error
        }
    }

    const handleEndRoom = async (runDetection = false) => {
        try {
            const result = await endRoom(roomId, runDetection)
            // 显示结果并导航回协作空间列表
            alert('房间已结束')
            navigate('/collaborate')
        } catch (error) {
            throw error
        }
    }

    const handleExportDocument = async (format = 'md', includeAnalysis = false) => {
        try {
            const result = await exportRoomDocument(roomId, format, includeAnalysis)

            let blob
            if (result.is_binary) {
                // 二进制内容（DOCX, PDF）- Base64解码
                const binaryString = atob(result.content)
                const bytes = new Uint8Array(binaryString.length)
                for (let i = 0; i < binaryString.length; i++) {
                    bytes[i] = binaryString.charCodeAt(i)
                }
                blob = new Blob([bytes], { type: result.content_type })
            } else {
                // 文本内容
                blob = new Blob([result.content], { type: result.content_type })
            }

            // 创建下载链接
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = result.filename
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
        } catch (error) {
            throw error
        }
    }

    const handleTriggerDetection = async (action = 'start') => {
        if (action === 'cancel') {
            await handleCancelDetection()
            return
        }
        await runDetection(content)
    }

    const getLockForChapter = (chapterId) => {
        return locks.find(l => l.chapter_id === chapterId)
    }

    const findTextRangeInEditor = useCallback((keyword) => {
        const editor = editorRef.current
        if (!editor || !keyword) return null

        const searchLower = keyword.toLowerCase()
        let foundRange = null

        editor.state.doc.descendants((node, pos) => {
            if (foundRange) return false
            if (!node.isText) return true

            const text = node.text || ''
            const index = text.toLowerCase().indexOf(searchLower)
            if (index !== -1) {
                foundRange = {
                    from: pos + index,
                    to: pos + index + keyword.length,
                }
                return false
            }
            return true
        })

        return foundRange
    }, [])

    const focusEditorByCandidates = useCallback((candidates) => {
        const editor = editorRef.current
        if (!editor) return null

        for (const candidate of candidates) {
            const range = findTextRangeInEditor(candidate)
            if (range) {
                const { view } = editor
                const start = view.domAtPos(range.from)
                const targetNode = start.node?.nodeType === Node.TEXT_NODE
                    ? start.node.parentElement
                    : start.node
                if (targetNode?.scrollIntoView) {
                    targetNode.scrollIntoView({ behavior: 'smooth', block: 'center' })
                } else {
                    view.dom.scrollIntoView({ behavior: 'smooth', block: 'center' })
                }
                return { keyword: candidate, range }
            }
        }
        return null
    }, [findTextRangeInEditor])

    // 定位到原文功能 - 支持文本和图片高亮
    const handleLocateInContent = useCallback((searchTextOrFact, imageIds = []) => {
        // 如果传入的是事实对象，提取相关信息
        let searchText = searchTextOrFact
        let imageIdsToHighlight = imageIds

        if (searchTextOrFact && typeof searchTextOrFact === 'object') {
            // 如果是事实对象
            searchText = searchTextOrFact.source_text || searchTextOrFact.content || ''
            if (searchTextOrFact.is_image_source && searchTextOrFact.image_id) {
                imageIdsToHighlight = [searchTextOrFact.image_id]
            }
        }

        // 设置图片高亮
        setHighlightImageIds(imageIdsToHighlight)

        // 如果有图片ID且在实时模式，滚动到图片位置
        if (imageIdsToHighlight.length > 0 && editorWrapperRef.current) {
            setTimeout(() => {
                for (const imageId of imageIdsToHighlight) {
                    const img = editorWrapperRef.current.querySelector(`img[data-image-id="${imageId}"]`)
                    if (img) {
                        img.scrollIntoView({ behavior: 'smooth', block: 'center' })
                        break
                    }
                }
            }, 100)
        }

        if (!searchText) return

        const normalizeText = (value) => value.replace(/\s+/g, ' ').trim()
        const normalizedText = normalizeText(searchText)
        if (!normalizedText) return

        const rawCandidates = [
            normalizedText,
            normalizedText.slice(0, 24),
            normalizedText.slice(Math.max(0, Math.floor(normalizedText.length / 2) - 12), Math.floor(normalizedText.length / 2) + 12),
            normalizedText.slice(-24),
        ].map(text => text.trim()).filter(Boolean)
        const candidates = rawCandidates.filter((text, index, list) => {
            if (list.indexOf(text) !== index) return false
            return text.length >= 6 || text === normalizedText
        })

        const matched = focusEditorByCandidates(candidates)
        const highlightKey = matched?.keyword || candidates[0] || normalizedText.slice(0, 24)
        setHighlightRange(matched?.range || null)

        setHighlightText(highlightKey)

        const isRealtime = room?.mode === 'realtime'
        if (!isRealtime && room?.chapters && room.chapters.length > 0) {
            const searchLower = normalizedText.toLowerCase()
            for (let i = 0; i < room.chapters.length; i++) {
                const chapter = room.chapters[i]
                const chapterContent = normalizeText(chapter.content || '')

                if (chapterContent.toLowerCase().includes(searchLower)) {
                    const chapterElement = document.getElementById(`chapter-${chapter.id}`)
                    if (chapterElement) {
                        chapterElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
                        chapterElement.classList.add('ring-2', 'ring-primary-500', 'ring-offset-2')
                        setTimeout(() => {
                            chapterElement.classList.remove('ring-2', 'ring-primary-500', 'ring-offset-2')
                        }, 3000)
                    }
                    break
                }
            }
        } else if (content) {
            const normalizedContent = normalizeText(content)
            if (normalizedContent.toLowerCase().includes(normalizedText.toLowerCase()) && contentContainerRef.current) {
                contentContainerRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }
        }
    }, [content, room, focusEditorByCandidates])

    const handleClearHighlight = useCallback(() => {
        setHighlightText(null)
        setHighlightRange(null)
        setHighlightImageIds([])
    }, [])

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
                    <p className="text-slate-600">正在加载协作房间...</p>
                </div>
            </div>
        )
    }

    if (!room) {
        return null
    }

    console.log('当前房间模式判断:', {
        'room.mode': room.mode,
        'isRealtimeMode': isRealtimeMode,
        '章节数': room.chapters?.length,
    })

    return (
        <div className="min-h-screen bg-slate-50">
            {/* 顶部工具栏 */}
            <div className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
                <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => navigate('/collaborate')}
                            className="text-slate-500 hover:text-slate-700"
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div>
                            <h1 className="font-semibold text-slate-900">{room.room_name}</h1>
                            <p className="text-sm text-slate-500">
                                {room.document_title} · {isRealtimeMode ? '实时协同' : '分章节锁定'}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        {/* 在线用户 */}
                        <div className="flex items-center gap-2">
                            <div className="flex -space-x-2">
                                {Object.values(room.members).slice(0, 5).map((member) => (
                                    <UserAvatar
                                        key={member.user_id}
                                        username={member.username}
                                        color={member.color}
                                        avatarUrl={member.avatar_url}
                                        isOnline={member.is_online}
                                        size="sm"
                                    />
                                ))}
                            </div>
                            <span className="text-sm text-slate-500">
                                {Object.values(room.members).filter(m => m.is_online).length} 在线
                            </span>
                        </div>
                        {/* --- ：清除高亮按钮 --- */}
                        <AnimatePresence>
                            {highlightText && (
                                <motion.button
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.8 }}
                                    onClick={handleClearHighlight}
                                    className="flex items-center gap-1 px-3 py-1.5 bg-yellow-100 text-yellow-700 rounded-full hover:bg-yellow-200 transition-colors border border-yellow-300 shadow-sm"
                                    title="点击清除文档高亮"
                                >
                                    <Eye className="w-4 h-4" />
                                    <span className="text-sm font-medium">清除高亮</span>
                                    <X className="w-3 h-3 ml-1 opacity-50" />
                                </motion.button>
                            )}
                        </AnimatePresence>
                        {/* 冲突提示 */}
                        {conflicts.length > 0 && (
                            <button
                                onClick={() => setShowConflicts(true)}
                                className="flex items-center gap-1 text-danger-600 hover:text-danger-700"
                            >
                                <AlertTriangle className="w-5 h-5" />
                                <span className="text-sm font-medium">{conflicts.length} 个冲突</span>
                            </button>
                        )}

                        {/* 分析侧边栏按钮 */}
                        <button
                            onClick={() => setShowSidebar(!showSidebar)}
                            className={`btn-ghost ${showSidebar ? 'bg-primary-100 text-primary-600' : ''}`}
                        >
                            {showSidebar ? (
                                <PanelRightClose className="w-4 h-4" />
                            ) : (
                                <PanelRightOpen className="w-4 h-4" />
                            )}
                            分析面板
                        </button>

                        {/* 检测按钮（在侧边栏关闭时显示） */}
                        {!showSidebar && (
                            <button
                                onClick={handleTriggerDetection}
                                className="btn-ghost"
                                disabled={detecting}
                            >
                                {detecting ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <RefreshCw className="w-4 h-4" />
                                )}
                                检测冲突
                            </button>
                        )}
                        {!showSidebar && detecting && (
                            <button
                                onClick={handleCancelDetection}
                                className="btn-secondary"
                            >
                                <X className="w-4 h-4" />
                                取消检测
                            </button>
                        )}

                        {/* 保存按钮（实时模式） */}
                        {isRealtimeMode && (
                            <button
                                onClick={handleSaveContent}
                                className="btn-primary"
                                disabled={saving}
                            >
                                {saving ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Save className="w-4 h-4" />
                                )}
                                保存
                            </button>
                        )}

                        {/* 房主管理按钮 */}
                        {isOwner && (
                            <OwnerPanel
                                room={room}
                                members={members}
                                chapters={room.chapters || []}
                                locks={locks}
                                isRealtimeMode={isRealtimeMode}
                                onAssignChapter={handleAssignChapter}
                                onUnassignChapter={handleUnassignChapter}
                                onAddChapter={handleAddChapter}
                                onDeleteChapter={handleDeleteChapter}
                                onUpdateSettings={handleUpdateSettings}
                                onRefresh={handleRefresh}
                                onKickMember={handleKickMember}
                                onEndRoom={handleEndRoom}
                                onExportDocument={handleExportDocument}
                            />
                        )}
                    </div>
                </div>
            </div>

            {/* 主内容区 - 带侧边栏的Flex布局 */}
            <div className="flex h-[calc(100vh-80px)]">
                {/* 主编辑区域 */}
                <div className="flex-1 overflow-auto">
                    <div className="max-w-5xl mx-auto px-4 py-6">
                        {isRealtimeMode ? (
                            // 实时协同编辑模式 - 富文本编辑器
                            <div className="card p-6 relative" ref={setEditorContainerRef}>
                                {/* 在线协作者指示器 */}
                                {Object.keys(userCursors).length > 0 && (
                                    <div className="mb-4 flex items-center gap-2 p-2 bg-slate-50 rounded-lg border border-slate-200">
                                        <span className="text-xs text-slate-500">正在协作:</span>
                                        {Object.entries(userCursors).map(([cursorUserId, cursor]) => (
                                            <div
                                                key={cursorUserId}
                                                className="flex items-center gap-1 px-2 py-1 bg-white rounded-full shadow-sm"
                                            >
                                                {cursor.avatar_url ? (
                                                    <img
                                                        src={cursor.avatar_url.includes('?') ? cursor.avatar_url : `${cursor.avatar_url}?t=${Date.now()}`}
                                                        alt={cursor.username}
                                                        className="w-4 h-4 rounded-full object-cover"
                                                    />
                                                ) : (
                                                    <div
                                                        className="w-4 h-4 rounded-full"
                                                        style={{ backgroundColor: cursor.color }}
                                                    />
                                                )}
                                                <span className="text-xs text-slate-600">{cursor.username}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                <AnimatePresence>
                                    {Object.entries(userCursors).map(([cursorUserId, cursor]) => (
                                        <CollaboratorCursor
                                            key={cursorUserId}
                                            user={cursor}
                                            containerRef={editorWrapperRef}
                                            editor={editorRef.current}
                                        />
                                    ))}
                                </AnimatePresence>

                                <RichTextEditor
                                    content={editorContent}
                                    onEditorReady={handleEditorReady}
                                    onSelectionUpdate={handleEditorSelectionUpdate}
                                    highlightTexts={highlightText ? [highlightText] : []}
                                    highlightRange={highlightRange}
                                    highlightImageIds={highlightImageIds}
                                    onChange={(json) => {
                                        setEditorContent(json)
                                        // 提取纯文本用于保存（包含图片占位符）
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
                                        scheduleDraftUpdate(text, json)
                                    }}
                                    onImageUpload={async (file) => {
                                        const result = await uploadDocumentImage(file, null, room?.room_id)
                                        return {
                                            url: result.file_url,
                                            imageId: result.image_id,
                                            alt: file.name,
                                        }
                                    }}
                                    placeholder="开始输入文档内容..."
                                    minHeight="500px"
                                    maxHeight="700px"
                                />
                            </div>
                        ) : (
                            // 分章节锁定编辑模式
                            <div className="space-y-6">
                                {room.chapters.length === 0 ? (
                                    <div className="card p-12 text-center">
                                        <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                                        <h3 className="text-lg font-medium text-slate-700 mb-2">暂无章节</h3>
                                        <p className="text-slate-500">文档内容为空，请先添加内容</p>
                                        {isOwner && (
                                            <p className="text-sm text-primary-600 mt-2">
                                                点击右上角"房间管理"添加章节
                                            </p>
                                        )}
                                    </div>
                                ) : (
                                    room.chapters.map((chapter) => (
                                        <ChapterEditor
                                            key={chapter.id}
                                            chapter={chapter}
                                            lock={getLockForChapter(chapter.id)}
                                            userId={userId}
                                            onSave={handleSaveChapter}
                                            onAcquireLock={handleAcquireLock}
                                            onReleaseLock={handleReleaseLock}
                                            highlightText={highlightText}
                                            isOwner={isOwner}
                                        />
                                    ))
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* 分析侧边栏 */}
                <AnalysisSidebar
                    isOpen={showSidebar}
                    onToggle={() => setShowSidebar(false)}
                    conflicts={conflicts}
                    facts={facts}
                    detecting={detecting}
                    onTriggerDetection={handleTriggerDetection}
                    onLocateInContent={handleLocateInContent}
                    isOwner={isOwner}
                    myChapterIds={myChapterIds}
                    taskId={detectionTaskId}
                />
            </div>

            {/* 冲突通知 */}
            <AnimatePresence>
                {showConflicts && conflicts.length > 0 && (
                    <ConflictNotification
                        conflicts={conflicts}
                        onClose={() => setShowConflicts(false)}
                    />
                )}
            </AnimatePresence>
            <AnimatePresence>
                {detectionNotice && (
                    <DetectionNotification
                        notice={detectionNotice}
                        onClose={() => setDetectionNotice(null)}
                    />
                )}
            </AnimatePresence>
        </div>
    )
}

export default CollaborateRoomPage

