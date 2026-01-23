/**
 * PPT 解析工具类
 * 用于解析 PowerPoint 文档结构
 */

export class PPTParser {
  constructor() {
    this.supportedFormats = ['.pptx', '.pdf']
    this.maxFileSize = 50 * 1024 * 1024 // 50MB
  }

  /**
   * 验证文件格式和大小
   */
  validateFile(file) {
    if (!file) {
      throw new Error('请选择文件')
    }

    const extension = '.' + file.name.split('.').pop().toLowerCase()

    if (!this.supportedFormats.includes(extension)) {
      throw new Error(`不支持的文件格式，请上传 ${this.supportedFormats.join(', ')}`)
    }

    if (file.size > this.maxFileSize) {
      throw new Error('文件大小不能超过 50MB')
    }

    return true
  }

  /**
   * 解析 PPT 文件结构
   */
  async parseFile(file) {
    this.validateFile(file)

    // 模拟解析过程
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(this.getMockStructure())
      }, 1000)
    })
  }

  /**
   * 提取语义层级
   */
  extractSemanticHierarchy(slides) {
    return slides.map(slide => ({
      pageNum: slide.page_num,
      title: slide.title,
      hierarchy: this.analyzeHierarchy(slide),
      keyPoints: slide.raw_points
    }))
  }

  /**
   * 分析文档层级结构
   */
  analyzeHierarchy(slide) {
    const points = slide.raw_points || []
    return {
      mainTopic: slide.title,
      subTopics: points,
      complexity: this.calculateComplexity(points),
      suggestedResources: this.suggestResources(slide.title)
    }
  }

  /**
   * 计算内容复杂度
   */
  calculateComplexity(points) {
    const keywords = ['公式', '推导', '证明', '算法', '原理', '机制']
    let score = 0

    points.forEach(point => {
      keywords.forEach(keyword => {
        if (point.includes(keyword)) score += 1
      })
    })

    if (score >= 3) return 'high'
    if (score >= 1) return 'medium'
    return 'low'
  }

  /**
   * 建议相关资源
   */
  suggestResources(title) {
    const resourceMap = {
      'transformer': ['arxiv:1706.03762', 'wikipedia:Transformer'],
      'attention': ['arxiv:1904.09925', 'wikipedia:Attention_mechanism'],
      'neural': ['arxiv:1801.05874', 'wikipedia:Neural_network']
    }

    const lowerTitle = title.toLowerCase()
    for (const [key, resources] of Object.entries(resourceMap)) {
      if (lowerTitle.includes(key)) {
        return resources
      }
    }

    return []
  }

  /**
   * 获取模拟结构数据
   */
  getMockStructure() {
    return {
      fileName: '深度学习架构分析.pptx',
      totalPages: 3,
      slides: [
        {
          page_num: 1,
          title: 'Transformer 结构 (Encoder)',
          raw_points: ['多头自注意力机制', '位置编码', '层归一化'],
          content_type: 'technical'
        },
        {
          page_num: 2,
          title: '自注意力机制详解',
          raw_points: ['Q、K、V 向量生成', '缩放点积注意力', '多头并行处理'],
          content_type: 'technical'
        },
        {
          page_num: 3,
          title: '位置编码 (Positional Encoding)',
          raw_points: ['正弦余弦函数编码', '固定编码 vs 学习编码', '相对位置信息'],
          content_type: 'technical'
        }
      ]
    }
  }
}

export default new PPTParser()
