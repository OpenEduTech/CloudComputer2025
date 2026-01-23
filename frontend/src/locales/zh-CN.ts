/**
 * 简体中文语言包
 */
export const zhCN = {
  // 通用
  common: {
    confirm: '确认',
    cancel: '取消',
    submit: '提交',
    save: '保存',
    delete: '删除',
    edit: '编辑',
    back: '返回',
    next: '下一步',
    previous: '上一步',
    loading: '加载中...',
    success: '成功',
    error: '错误',
    warning: '警告',
  },

  // 导航
  nav: {
    home: '首页',
    mistakes: '错题本',
    logout: '退出登录',
    appName: '智能学习系统',
  },

  // 登录页面
  login: {
    title: '欢迎回来',
    subtitle: '登录以继续学习',
    username: '用户名或邮箱',
    password: '密码',
    loginButton: '登录',
    noAccount: '还没有账号？',
    signUp: '立即注册',
    usernamePlaceholder: '请输入用户名或邮箱',
    passwordPlaceholder: '请输入密码',
    usernameRequired: '请输入用户名或邮箱',
    passwordRequired: '请输入密码',
    loginSuccess: '登录成功！',
    loginFailed: '登录失败，请检查您的凭据',
  },

  // 注册页面
  register: {
    title: '创建账号',
    subtitle: '注册以开始学习',
    username: '用户名',
    email: '邮箱',
    password: '密码',
    confirmPassword: '确认密码',
    registerButton: '注册',
    hasAccount: '已有账号？',
    login: '立即登录',
    usernamePlaceholder: '请输入用户名',
    emailPlaceholder: '请输入邮箱',
    passwordPlaceholder: '请输入密码',
    confirmPasswordPlaceholder: '请确认密码',
    usernameRequired: '请输入用户名',
    usernameMin: '用户名至少需要3个字符',
    usernameMax: '用户名不能超过50个字符',
    emailRequired: '请输入邮箱',
    emailInvalid: '请输入有效的邮箱地址',
    passwordRequired: '请输入密码',
    passwordMin: '密码至少需要6个字符',
    confirmPasswordRequired: '请确认密码',
    passwordMismatch: '两次输入的密码不一致',
    registerSuccess: '注册成功！请登录',
    registerFailed: '注册失败，请重试',
  },

  // 首页
  home: {
    uploadTitle: '上传学习资料',
    uploadSubtitle: '上传PDF文档以生成个性化测验并跟踪您的学习进度',
    materialsTitle: '您的资料',
    noMaterials: '还没有上传资料。上传PDF开始学习吧！',
    generateQuiz: '生成测验',
    uploaded: '上传于',
    fetchFailed: '获取资料失败',
  },

  // 上传组件
  upload: {
    dragText: '点击或拖拽PDF文件到此区域上传',
    hint: '支持单个PDF文件上传，文件大小不超过10MB',
    uploading: '上传中...',
    uploadSuccess: '上传成功！',
    uploadFailed: '上传失败',
    fileTypeError: '只能上传PDF文件',
    fileSizeError: '文件大小不能超过10MB',
  },

  // 资料状态
  materialStatus: {
    completed: '已完成',
    processing: '处理中',
    pending: '等待中',
    failed: '失败',
  },

  // 生成测验对话框
  generateQuizModal: {
    title: '生成测验',
    quizTitle: '测验标题',
    questionCount: '题目数量',
    quizTitlePlaceholder: '请输入测验标题',
    questionCountPlaceholder: '请输入题目数量',
    quizTitleRequired: '请输入测验标题',
    quizTitleMin: '标题至少需要3个字符',
    questionCountRequired: '请输入题目数量',
    questionCountRange: '题目数量必须在1到50之间',
    generateButton: '生成',
    generateSuccess: '测验生成成功！',
    generateFailed: '生成测验失败',
  },

  // 测验页面
  quiz: {
    title: '测验',
    question: '题目',
    of: '/',
    submit: '提交答案',
    submitQuiz: '提交测验',
    submitConfirm: '确定要提交测验吗？',
    submitConfirmDesc: '提交后将无法修改答案',
    selectAnswer: '请选择答案',
    submitSuccess: '提交成功！',
    submitFailed: '提交失败',
    loadFailed: '加载测验失败',
  },

  // 结果页面
  results: {
    title: '测验结果',
    score: '得分',
    correct: '正确',
    incorrect: '错误',
    accuracy: '正确率',
    reviewAnswers: '查看答案',
    backToHome: '返回首页',
    yourAnswer: '您的答案',
    correctAnswer: '正确答案',
    explanation: '解析',
    loadFailed: '加载结果失败',
  },

  // 错题本页面
  mistakes: {
    title: '错题本',
    noMistakes: '太棒了！您还没有错题',
    question: '题目',
    yourAnswer: '您的答案',
    correctAnswer: '正确答案',
    explanation: '解析',
    from: '来自',
    loadFailed: '加载错题失败',
  },

  // 页脚
  footer: {
    copyright: '智能学习系统',
  },
};

export type Locale = typeof zhCN;
