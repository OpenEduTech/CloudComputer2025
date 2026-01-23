# config.py
import os

# 统一将数据写入项目根目录的 data/（Industry-Radar/data），避免相对路径随工作目录漂移。
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DEFAULT_KEYWORD = "半导体"

# --- 报告输出控制（精简版 / 详细版） ---
# compact: 面向展示的精简报告（默认）
# verbose: 保留更多调试/中间信息
REPORT_MODE = os.getenv("REPORT_MODE", "compact").strip().lower()

# 精简输出的条目上限（避免 final_analysis 过长）
MAX_DECISIONS = int(os.getenv("MAX_DECISIONS", "8"))
MAX_EVIDENCE_PER_DECISION = int(os.getenv("MAX_EVIDENCE_PER_DECISION", "2"))

# 是否在输出中包含调试字段（例如 confidence/key_numbers/snippet）
INCLUDE_DEBUG_FIELDS = os.getenv("INCLUDE_DEBUG_FIELDS", "0").strip() in {"1", "true", "yes"}

# --- LLM 运行配置 ---
LLM_MODEL = "deepseek-ai/DeepSeek-V3"
LLM_BASE_URL = "https://api.siliconflow.cn/v1"
LLM_TEMPERATURE = 0.1
LLM_MAX_RETRIES = 3

# --- 增强版全行业通用 Prompt ---
# config.py
SYSTEM_PROMPT = """你是一个专业的全行业分析助手。
对比【旧结论】与【新资讯】，识别关键指标变化并输出 JSON 数组。

【核心要求】：
1. 动态对齐：识别语义相同的指标。
2. 深度洞察：请为每个变动增加一个名为 'insight' 的字段，用一句话通俗易懂地解释这个变动意味着什么（不要只是重复数值，要说背后的行业逻辑）。

【输出格式示例】：
[
  {
    "field": "产能利用率",
    "old": "80%",
    "new": "92%",
    "status": "increased",
    "insight": "行业景气度爆发，头部厂家产线已接近满负荷运转。"
  }
]"""

USER_PROMPT_TEMPLATE = """
【旧快照中的已知指标】：
{old_text}

【新采集的行业资讯】：
{new_text}

请识别差异并输出 JSON 列表：
"""