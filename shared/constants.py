"""常量定义"""


class Discipline:
    """学科常量定义"""
    
    MATH = "数学"
    PHYSICS = "物理"
    CHEMISTRY = "化学"
    BIOLOGY = "生物"
    COMPUTER = "计算机"
    SOCIOLOGY = "社会学"
    
    ALL = [MATH, PHYSICS, CHEMISTRY, BIOLOGY, COMPUTER, SOCIOLOGY]
    
    # 学科颜色映射（前端可视化用）
    COLORS = {
        MATH: "#FF6B6B",       # 红色
        PHYSICS: "#4ECDC4",    # 青色
        CHEMISTRY: "#95E1D3",  # 绿色
        BIOLOGY: "#F38181",    # 粉色
        COMPUTER: "#AA96DA",   # 紫色
        SOCIOLOGY: "#FCBAD3"   # 橙色
    }
    
    # 学科拼音映射（用于生成节点ID）
    PINYIN = {
        MATH: "shuxue",
        PHYSICS: "wuli",
        CHEMISTRY: "huaxue",
        BIOLOGY: "shengwu",
        COMPUTER: "jisuanji",
        SOCIOLOGY: "shehuixue"
    }


class RelationType:
    """关系类型枚举"""
    
    IS_FOUNDATION_OF = "is_foundation_of"  # A是B的理论基础
    SIMILAR_TO = "similar_to"              # A和B在原理上相似
    APPLIED_IN = "applied_in"              # A应用于B领域
    GENERALIZES = "generalizes"            # A是B的泛化
    DERIVED_FROM = "derived_from"          # A由B推导而来
    
    ALL = [
        IS_FOUNDATION_OF,
        SIMILAR_TO,
        APPLIED_IN,
        GENERALIZES,
        DERIVED_FROM
    ]
    
    # 关系描述
    DESCRIPTIONS = {
        IS_FOUNDATION_OF: "是...的理论基础",
        SIMILAR_TO: "与...在原理上相似",
        APPLIED_IN: "应用于...领域",
        GENERALIZES: "是...的泛化",
        DERIVED_FROM: "由...推导而来"
    }


class AgentConfig:
    """Agent配置常量"""
    
    # 可信度阈值
    CREDIBILITY_THRESHOLD = 0.5
    
    # 最大重试次数
    MAX_RETRIES = 3
    
    # 重试延迟（秒）
    RETRY_DELAY = 2
    
    # LLM超时时间（秒）
    LLM_TIMEOUT = 60
    
    # 默认挖掘深度
    DEFAULT_DEPTH = 2
    
    # 默认最大概念数
    DEFAULT_MAX_CONCEPTS = 30
    
    # 默认温度参数
    DEFAULT_TEMPERATURE = 0.3
    
    # 默认最大Token数
    DEFAULT_MAX_TOKENS = 2000
