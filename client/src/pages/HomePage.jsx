/**
 * PatPat-Inconsistency-Hunter 首页
 * 展示产品介绍和快速入口
 */

import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  FileSearch, 
  AlertTriangle, 
  CheckCircle, 
  Zap,
  Shield,
  BarChart3,
  ArrowRight,
  Sparkles,
  Users,
  Lock,
} from 'lucide-react'

const features = [
  {
    icon: FileSearch,
    title: '智能事实提取',
    description: '自动从长文档中提取关键事实，包括数据、日期、结论和人名等核心信息',
    color: 'primary',
  },
  {
    icon: AlertTriangle,
    title: '冲突检测',
    description: '扫描全文识别前后不一致的描述，如第一章和第五章对同一数据的引用冲突',
    color: 'warning',
  },
  {
    icon: CheckCircle,
    title: '溯源校验',
    description: '分析冲突事实的合理性，提供修正建议帮助作者快速定位和解决问题',
    color: 'success',
  },
  {
    icon: Users,
    title: '多人协作',
    description: '支持实时协同编辑和分章节锁定两种模式，边写边检测冲突',
    color: 'accent',
  },
]

const stats = [
  { 
    value: '5000+', 
    label: '支持字数', 
    gradient: 'linear-gradient(135deg, var(--mist-blue), #f5fbfd)', 
    labelColor: 'rgba(31,59,51,0.55)', 
    valueColor: 'var(--forest-ink)' 
  },
  { 
    value: '7种', 
    label: '冲突类型', 
    gradient: 'linear-gradient(135deg, var(--leaf-green), rgba(188, 221, 190, 0.7))', 
    labelColor: 'rgba(47,74,64,0.6)', 
    valueColor: '#2f5b47' 
  },
  { 
    value: '实时', 
    label: '进度反馈', 
    gradient: 'linear-gradient(135deg, var(--sun-cream), #fffced)', 
    labelColor: 'rgba(82,78,38,0.6)', 
    valueColor: '#5b5327' 
  },
  { 
    value: '云原生', 
    label: '架构设计', 
    gradient: 'linear-gradient(135deg, rgba(100,163,134,0.25), rgba(161,197,211,0.65))', 
    labelColor: 'rgba(46,72,66,0.6)', 
    valueColor: 'var(--forest-ink)' 
  },
]

function HomePage() {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 lg:py-32">
        {/* 背景装饰 */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-200/30 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-accent-200/30 rounded-full blur-3xl" />
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-100 text-primary-700 text-sm font-medium mb-6">
                <Sparkles className="w-4 h-4" />
                基于大语言模型的智能分析
              </div>
              
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-slate-900 mb-6 leading-tight">
                长文本
                <span className="gradient-text"> 事实卫士</span>
              </h1>
              
              <p className="text-xl text-slate-600 max-w-3xl mx-auto mb-10 text-balance">
                自动检测长文档中的事实不一致性，帮助您确保毕业论文、可行性报告等重要文档的逻辑自洽和数据准确
              </p>

              <div className="flex flex-wrap items-center justify-center gap-4">
                <Link to="/analyze" className="btn-primary text-lg">
                  <FileSearch className="w-5 h-5" />
                  开始分析
                  <ArrowRight className="w-5 h-5" />
                </Link>
                <Link to="/collaborate" className="btn-secondary text-lg">
                  <Users className="w-5 h-5" />
                  协作空间
                </Link>
                <Link to="/dashboard" className="btn-outline-solid text-lg">
                  <BarChart3 className="w-5 h-5" />
                  仪表盘
                </Link>
              </div>
            </motion.div>

            {/* 统计数据 */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-6"
            >
              {stats.map((stat, index) => (
                <div 
                  key={index} 
                  className="rounded-2xl p-5 text-left shadow-lg shadow-[rgba(155,157,175,0.15)] border border-white/40"
                  style={{ background: stat.gradient }}
                >
                  <div 
                    className="text-sm font-medium tracking-wide"
                    style={{ color: stat.labelColor }}
                  >
                    {stat.label}
                  </div>
                  <div 
                    className="text-3xl sm:text-4xl font-bold mt-2"
                    style={{ color: stat.valueColor }}
                  >
                    {stat.value}
                  </div>
                </div>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
              核心功能
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              基于先进的大语言模型技术，为您提供全方位的文档一致性检测服务
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => {
              const Icon = feature.icon
              const colorClasses = {
                primary: 'from-primary-500 to-primary-600 shadow-primary-500/25',
                warning: 'from-warning-500 to-warning-600 shadow-warning-500/25',
                success: 'from-success-500 to-success-600 shadow-success-500/25',
                accent: 'from-accent-500 to-accent-600 shadow-accent-500/25',
              }
              
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className="card-hover p-6"
                >
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${colorClasses[feature.color]} flex items-center justify-center mb-4 shadow-lg`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-slate-600 text-sm">
                    {feature.description}
                  </p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* How it works Section */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
              工作流程
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              简单三步，快速完成文档一致性检测
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: '01',
                title: '上传文档',
                description: '将您的长文档内容粘贴到分析页面，支持5000字以上的文档',
              },
              {
                step: '02',
                title: '智能分析',
                description: '系统自动提取事实、检测冲突、验证结果，实时展示进度',
              },
              {
                step: '03',
                title: '查看报告',
                description: '获取详细的分析报告，包括冲突位置、类型和修正建议',
              },
            ].map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="relative"
              >
                <div className="card p-8 text-center relative z-10">
                  <div className="text-6xl font-bold text-slate-100 absolute top-4 left-4">
                    {item.step}
                  </div>
                  <div className="relative z-10">
                    <h3 className="text-xl font-semibold text-slate-900 mb-3">
                      {item.title}
                    </h3>
                    <p className="text-slate-600">
                      {item.description}
                    </p>
                  </div>
                </div>
                {index < 2 && (
                  <div className="hidden md:block absolute top-1/2 -right-4 transform -translate-y-1/2 z-20">
                    <ArrowRight className="w-8 h-8 text-slate-300" />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Collaboration Section */}
      <section className="py-20 bg-white/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
              多人协作，实时检测
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              团队协作编写文档时，系统自动检测跨章节的冲突，确保全文一致性
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
              className="card-hover p-8"
            >
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center mb-6 shadow-lg shadow-primary-500/25">
                <Users className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">
                实时协同编辑
              </h3>
              <p className="text-slate-600 mb-4">
                多人同时编辑同一文档，实时同步所有更改，支持光标位置和选区共享，像Google Docs一样流畅协作
              </p>
              <ul className="space-y-2 text-sm text-slate-500">
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-success-500" />
                  实时内容同步
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-success-500" />
                  多人光标显示
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-success-500" />
                  即时冲突检测
                </li>
              </ul>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
              className="card-hover p-8"
            >
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-accent-500 to-accent-600 flex items-center justify-center mb-6 shadow-lg shadow-accent-500/25">
                <Lock className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">
                分章节锁定编辑
              </h3>
              <p className="text-slate-600 mb-4">
                每个章节同一时间只能被一人编辑，避免冲突，适合分工明确的团队，如毕业论文多人分章撰写
              </p>
              <ul className="space-y-2 text-sm text-slate-500">
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-success-500" />
                  章节级别锁定
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-success-500" />
                  防止编辑冲突
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-success-500" />
                  跨章节冲突检测
                </li>
              </ul>
            </motion.div>
          </div>

          <div className="text-center mt-10">
            <Link to="/collaborate" className="btn-primary text-lg">
              <Users className="w-5 h-5" />
              进入协作空间
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-primary-600 to-accent-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Shield className="w-16 h-16 text-white/80 mx-auto mb-6" />
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              立即开始，守护您的文档质量
            </h2>
            <p className="text-xl text-white/80 mb-8">
              不再为文档中的数据冲突和逻辑矛盾担忧
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <Link 
                to="/analyze" 
                className="inline-flex items-center gap-2 px-8 py-4 bg-white text-primary-600 font-semibold rounded-xl hover:bg-slate-50 transition-colors shadow-lg"
              >
                <Zap className="w-5 h-5" />
                单文档分析
              </Link>
              <Link 
                to="/collaborate" 
                className="inline-flex items-center gap-2 px-8 py-4 bg-white/20 text-white font-semibold rounded-xl hover:bg-white/30 transition-colors"
              >
                <Users className="w-5 h-5" />
                多人协作
              </Link>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  )
}

export default HomePage

