/**
 * PatPat-Inconsistency-Hunter 仪表盘页面
 * 展示分析统计和可视化图表
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  BarChart3,
  PieChart,
  TrendingUp,
  FileText,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import {
  PieChart as RechartsPie,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { getStatsOverview, getStatsDetailed, getUserDashboardStats } from '../api'
import { useAuth } from '../contexts/AuthContext'

const COLOR_VARS = {
  mist: 'var(--mist-blue)',
  leaf: 'var(--leaf-green)',
  cream: 'var(--sun-cream)',
  evergreen: 'var(--deep-green)',
  ink: 'var(--forest-ink)',
}

// 图表颜色
const COLORS = {
  primary: COLOR_VARS.mist,
  accent: COLOR_VARS.leaf,
  success: COLOR_VARS.cream,
  warning: 'rgba(251, 252, 205, 0.85)',
  danger: '#3c6a53',
  slate: COLOR_VARS.ink,
}

const PIE_COLORS = [COLORS.primary, COLORS.accent, COLORS.warning, COLORS.success]

const RADIAN = Math.PI / 180
const renderPieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }) => {
  const radius = innerRadius + (outerRadius - innerRadius) * 1.15
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)

  return (
    <text
      x={x}
      y={y}
      fill="var(--forest-ink)"
      fontWeight={600}
      fontSize={12}
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
    >
      {`${name} ${(percent * 100).toFixed(0)}%`}
    </text>
  )
}

const STAT_COLOR_PRESETS = {
  primary: {
    gradient: `linear-gradient(135deg, ${COLOR_VARS.mist}, #f5fbfd)`,
    labelColor: 'rgba(31, 59, 51, 0.55)',
    valueColor: COLOR_VARS.ink,
    iconBg: 'rgba(205, 226, 232, 0.75)',
  },
  success: {
    gradient: `linear-gradient(135deg, ${COLOR_VARS.leaf}, rgba(188, 221, 190, 0.65))`,
    labelColor: 'rgba(47, 74, 64, 0.6)',
    valueColor: '#2f5b47',
    iconBg: 'rgba(188, 221, 190, 0.8)',
  },
  warning: {
    gradient: `linear-gradient(135deg, ${COLOR_VARS.cream}, #fffced)`,
    labelColor: 'rgba(82, 78, 38, 0.6)',
    valueColor: '#5b5327',
    iconBg: 'rgba(251, 252, 205, 0.85)',
  },
  danger: {
    gradient: 'linear-gradient(135deg, rgba(122,139,129,0.18), rgba(60,106,83,0.12))',
    labelColor: 'rgba(60, 106, 83, 0.6)',
    valueColor: '#3c6a53',
    iconBg: 'rgba(60, 106, 83, 0.25)',
  },
}

// 统计卡片组件
function StatCard({ icon: Icon, label, value, color, trend }) {
  const palette = STAT_COLOR_PRESETS[color] || STAT_COLOR_PRESETS.primary

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl p-6 shadow-lg border border-white/40"
      style={{ background: palette.gradient }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm mb-1" style={{ color: palette.labelColor }}>{label}</p>
          <p className="text-3xl font-bold" style={{ color: palette.valueColor }}>{value}</p>
          {trend && (
            <div className="flex items-center gap-1 mt-2 text-xs" style={{ color: palette.labelColor }}>
              <TrendingUp className="w-4 h-4" />
              {trend}
            </div>
          )}
        </div>
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center shadow-lg"
          style={{ background: palette.iconBg, color: '#fff', boxShadow: '0 15px 30px rgba(0,0,0,0.08)' }}
        >
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </motion.div>
  )
}

function DashboardPage() {
  const { user, isAuthenticated } = useAuth()
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState(null)
  const [detailedStats, setDetailedStats] = useState(null)
  const [userStats, setUserStats] = useState(null)
  const [error, setError] = useState(null)

  // 为图表数据添加颜色
  const getSeverityColor = (name) => {
    const colorMap = {
      '严重': COLORS.danger,
      '较高': COLORS.warning,
      '中等': COLORS.primary,
      '轻微': COLORS.success,
    }
    return colorMap[name] || COLORS.slate
  }

  // 从API获取的数据，如果为空则使用占位数据
  const conflictTypeData = detailedStats?.conflict_type_distribution?.length > 0
    ? detailedStats.conflict_type_distribution
    : [{ name: '暂无数据', value: 1 }]

  const severityData = detailedStats?.severity_distribution?.length > 0
    ? detailedStats.severity_distribution.map(item => ({
        ...item,
        fill: getSeverityColor(item.name),
      }))
    : [
        { name: '严重', count: 0, fill: COLORS.danger },
        { name: '较高', count: 0, fill: COLORS.warning },
        { name: '中等', count: 0, fill: COLORS.primary },
        { name: '轻微', count: 0, fill: COLORS.success },
      ]

  const trendData = detailedStats?.weekly_trend?.length > 0
    ? detailedStats.weekly_trend
    : [
        { date: '周一', tasks: 0, conflicts: 0 },
        { date: '周二', tasks: 0, conflicts: 0 },
        { date: '周三', tasks: 0, conflicts: 0 },
        { date: '周四', tasks: 0, conflicts: 0 },
        { date: '周五', tasks: 0, conflicts: 0 },
        { date: '周六', tasks: 0, conflicts: 0 },
        { date: '周日', tasks: 0, conflicts: 0 },
      ]

  // 加载数据
  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    setLoading(true)
    setError(null)
    try {
      // 并行加载概览和详细数据
      const promises = [
        getStatsOverview(),
        getStatsDetailed(),
      ]
      
      // 如果用户已登录，也获取用户统计
      if (isAuthenticated) {
        promises.push(getUserDashboardStats())
      }
      
      const results = await Promise.all(promises)
      setStats(results[0])
      setDetailedStats(results[1])
      
      if (isAuthenticated && results[2]) {
        setUserStats(results[2])
      }
    } catch (err) {
      console.error('加载统计数据失败:', err)
      setError(err.message)
      // 使用默认空数据
      setStats({
        total_tasks: 0,
        completed_tasks: 0,
        total_facts_extracted: 0,
        total_conflicts_detected: 0,
      })
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
          <p className="text-slate-600">正在加载仪表盘数据...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* 标题 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">数据仪表盘</h1>
            <p className="text-slate-600 mt-1">系统运行数据统计与可视化分析</p>
          </div>
          <button onClick={loadStats} className="btn-ghost">
            <RefreshCw className="w-4 h-4" />
            刷新数据
          </button>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            icon={FileText}
            label="分析任务总数"
            value={stats?.total_tasks || 0}
            color="primary"
          />
          <StatCard
            icon={CheckCircle}
            label="完成任务数"
            value={stats?.completed_tasks || 0}
            color="success"
          />
          <StatCard
            icon={BarChart3}
            label="提取事实总数"
            value={stats?.total_facts_extracted?.toLocaleString() || 0}
            color="warning"
          />
          <StatCard
            icon={AlertTriangle}
            label="检测冲突总数"
            value={stats?.total_conflicts_detected || 0}
            color="danger"
          />
        </div>

        {/* 用户统计卡片（仅登录用户显示） */}
        {isAuthenticated && userStats && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="card p-6 mb-8"
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-slate-900">
                我的统计 <span className="text-primary-500">({user?.display_name || user?.username})</span>
              </h3>
              <span className="text-xs text-slate-500">累计数据</span>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div
                className="relative overflow-hidden p-4 rounded-xl shadow-md border border-white/60"
                style={{ background: 'linear-gradient(135deg, rgba(205,226,232,0.28), rgba(255,255,255,0.75))' }}
              >
                <div
                  className="absolute -right-4 -top-4 w-16 h-16 rounded-full"
                  style={{ background: 'rgba(205,226,232,0.4)' }}
                />
                <p className="text-3xl font-bold relative" style={{ color: 'var(--forest-ink)' }}>
                  {userStats.user_stats?.total_documents || 0}
                </p>
                <p className="text-sm mt-1" style={{ color: 'rgba(31,59,51,0.65)' }}>累计文档</p>
                <div className="mt-2 text-xs" style={{ color: 'rgba(31,59,51,0.6)' }}>
                  每份文档独立计数
                </div>
              </div>
              <div
                className="relative overflow-hidden p-4 rounded-xl shadow-md border border-white/60"
                style={{ background: 'linear-gradient(135deg, rgba(188,221,190,0.35), rgba(255,255,255,0.78))' }}
              >
                <div
                  className="absolute -right-4 -top-4 w-16 h-16 rounded-full"
                  style={{ background: 'rgba(188,221,190,0.35)' }}
                />
                <p className="text-3xl font-bold relative" style={{ color: '#2f5b47' }}>
                  {userStats.user_stats?.completed_analyses || 0}
                </p>
                <p className="text-sm mt-1" style={{ color: 'rgba(47,74,64,0.6)' }}>完成分析</p>
                <div className="mt-2 text-xs" style={{ color: 'rgba(47,74,64,0.65)' }}>
                  {userStats.user_stats?.total_documents > 0 
                    ? `${Math.round((userStats.user_stats?.completed_analyses / userStats.user_stats?.total_documents) * 100)}% 完成率`
                    : '0% 完成率'
                  }
                </div>
              </div>
              <div
                className="relative overflow-hidden p-4 rounded-xl shadow-md border border-white/60"
                style={{ background: 'linear-gradient(135deg, rgba(253,252,205,0.4), rgba(255,255,255,0.8))' }}
              >
                <div
                  className="absolute -right-4 -top-4 w-16 h-16 rounded-full"
                  style={{ background: 'rgba(251,252,205,0.45)' }}
                />
                <p className="text-3xl font-bold relative" style={{ color: '#5b5327' }}>
                  {(userStats.user_stats?.total_facts || 0).toLocaleString()}
                </p>
                <p className="text-sm mt-1" style={{ color: 'rgba(82,78,38,0.6)' }}>累计提取事实</p>
                <div className="mt-2 text-xs" style={{ color: 'rgba(82,78,38,0.65)' }}>
                  {userStats.user_stats?.completed_analyses > 0 
                    ? `平均 ${Math.round(userStats.user_stats?.total_facts / userStats.user_stats?.completed_analyses)}/文档`
                    : '平均 0/文档'
                  }
                </div>
              </div>
              <div
                className="relative overflow-hidden p-4 rounded-xl shadow-md border border-white/60"
                style={{ background: 'linear-gradient(135deg, rgba(31,59,51,0.08), rgba(100,163,134,0.15))' }}
              >
                <div
                  className="absolute -right-4 -top-4 w-16 h-16 rounded-full"
                  style={{ background: 'rgba(31,59,51,0.12)' }}
                />
                <p className="text-3xl font-bold relative" style={{ color: '#3c6a53' }}>
                  {userStats.user_stats?.total_conflicts || 0}
                </p>
                <p className="text-sm mt-1" style={{ color: 'rgba(60,106,83,0.65)' }}>累计发现冲突</p>
                <div className="mt-2 text-xs" style={{ color: 'rgba(60,106,83,0.6)' }}>
                  {userStats.user_stats?.completed_analyses > 0 
                    ? `平均 ${(userStats.user_stats?.total_conflicts / userStats.user_stats?.completed_analyses).toFixed(1)}/文档`
                    : '平均 0/文档'
                  }
                </div>
              </div>
            </div>
            
            {/* 最近活动 */}
            {userStats.recent_activity && userStats.recent_activity.length > 0 && (
              <div className="mt-6 pt-6 border-t border-slate-100">
                <h4 className="text-sm font-medium text-slate-700 mb-3">最近活动</h4>
                <div className="space-y-2">
                  {userStats.recent_activity.slice(0, 3).map((activity, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${activity.status === 'completed' ? 'bg-success-500' : 'bg-warning-500'}`} />
                        <span className="text-sm text-slate-700">{activity.title}</span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-slate-500">
                        <span>{activity.total_facts || 0} 事实</span>
                        <span>{activity.total_conflicts || 0} 冲突</span>
                        <span>{activity.created_at ? new Date(activity.created_at).toLocaleDateString('zh-CN') : '-'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* 协作统计 */}
            <div className="mt-6 pt-6 border-t border-slate-100">
              <h4 className="text-sm font-medium text-slate-700 mb-3">协作统计</h4>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-3 bg-slate-50 rounded-lg">
                  <p className="text-2xl font-bold text-slate-700">
                    {userStats.collaboration_stats?.rooms_created || 0}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">创建房间</p>
                </div>
                <div className="text-center p-3 bg-slate-50 rounded-lg">
                  <p className="text-2xl font-bold text-slate-700">
                    {userStats.collaboration_stats?.rooms_joined || 0}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">参与房间</p>
                </div>
                <div className="text-center p-3 bg-slate-50 rounded-lg">
                  <p className="text-2xl font-bold text-slate-700">
                    {userStats.collaboration_stats?.total_collaborations || 0}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">协作次数</p>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* 图表区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* 冲突类型分布 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="card p-6"
          >
            <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <PieChart className="w-5 h-5 text-primary-500" />
              冲突类型分布
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsPie>
                  <Pie
                    data={conflictTypeData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                    labelLine={false}
                    label={renderPieLabel}
                  >
                    {conflictTypeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </RechartsPie>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* 严重程度分布 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="card p-6"
          >
            <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-warning-500" />
              严重程度分布
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={severityData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" />
                  <YAxis dataKey="name" type="category" width={60} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {severityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        </div>

        {/* 趋势图 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card p-6"
        >
          <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-success-500" />
            本周分析趋势
          </h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="tasks" name="分析任务" fill={COLORS.primary} radius={[4, 4, 0, 0]} />
                <Bar dataKey="conflicts" name="发现冲突" fill={COLORS.danger} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* 系统信息 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card p-6 mt-6"
        >
          <h3 className="text-lg font-semibold text-slate-900 mb-4">系统信息</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-slate-500">版本</span>
              <p className="font-medium text-slate-900">1.0.0</p>
            </div>
            <div>
              <span className="text-slate-500">LLM模型</span>
              <p className="font-medium text-slate-900">DeepSeek</p>
            </div>
            <div>
              <span className="text-slate-500">数据库</span>
              <p className="font-medium text-slate-900">Redis + PostgreSQL</p>
            </div>
            <div>
              <span className="text-slate-500">部署方式</span>
              <p className="font-medium text-slate-900">Docker Compose</p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default DashboardPage

