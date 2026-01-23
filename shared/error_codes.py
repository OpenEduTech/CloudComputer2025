"""错误码规范"""


class ErrorCode:
    """统一错误码定义"""
    
    # 通用错误 (1000-1999)
    UNKNOWN_ERROR = "ERR_1000"
    INVALID_REQUEST = "ERR_1001"
    VALIDATION_ERROR = "ERR_1002"
    TIMEOUT = "ERR_1003"
    
    # Agent相关错误 (2000-2999)
    LLM_API_ERROR = "ERR_2001"         # LLM调用失败
    LLM_TIMEOUT = "ERR_2002"           # LLM超时
    PROMPT_ERROR = "ERR_2003"          # Prompt错误
    VERIFICATION_FAILED = "ERR_2004"   # 验证失败
    NO_CONCEPTS_FOUND = "ERR_2005"     # 未找到相关概念
    LOW_CREDIBILITY = "ERR_2006"       # 可信度过低
    
    # 数据库相关错误 (3000-3999)
    NEO4J_CONNECTION_ERROR = "ERR_3001"
    NEO4J_QUERY_ERROR = "ERR_3002"
    MILVUS_CONNECTION_ERROR = "ERR_3003"
    REDIS_ERROR = "ERR_3004"
    
    # 业务逻辑错误 (4000-4999)
    CONCEPT_NOT_FOUND = "ERR_4001"
    INVALID_DISCIPLINE = "ERR_4002"
    GRAPH_TOO_LARGE = "ERR_4003"       # 图谱节点过多
    DUPLICATE_CONCEPT = "ERR_4004"


# 错误消息映射
ERROR_MESSAGES = {
    ErrorCode.UNKNOWN_ERROR: "未知错误，请联系管理员",
    ErrorCode.INVALID_REQUEST: "请求参数无效",
    ErrorCode.VALIDATION_ERROR: "数据验证失败",
    ErrorCode.TIMEOUT: "请求超时",
    
    ErrorCode.LLM_API_ERROR: "大模型调用失败，请稍后重试",
    ErrorCode.LLM_TIMEOUT: "大模型响应超时",
    ErrorCode.PROMPT_ERROR: "Prompt格式错误",
    ErrorCode.VERIFICATION_FAILED: "概念验证失败",
    ErrorCode.NO_CONCEPTS_FOUND: "未找到相关概念，请尝试其他关键词",
    ErrorCode.LOW_CREDIBILITY: "生成的关联可信度过低，已过滤",
    
    ErrorCode.NEO4J_CONNECTION_ERROR: "图数据库连接失败",
    ErrorCode.NEO4J_QUERY_ERROR: "图数据库查询失败",
    ErrorCode.MILVUS_CONNECTION_ERROR: "向量数据库连接失败",
    ErrorCode.REDIS_ERROR: "缓存服务错误",
    
    ErrorCode.CONCEPT_NOT_FOUND: "概念不存在",
    ErrorCode.INVALID_DISCIPLINE: "无效的学科类别",
    ErrorCode.GRAPH_TOO_LARGE: "图谱节点数过多，请缩小范围",
    ErrorCode.DUPLICATE_CONCEPT: "概念已存在"
}


def get_error_message(error_code: str) -> str:
    """获取错误消息"""
    return ERROR_MESSAGES.get(error_code, ERROR_MESSAGES[ErrorCode.UNKNOWN_ERROR])
