# zhipu_client.py
from zhipuai import ZhipuAI
from config import ZHIPU_API_KEY, MODEL_NAME, DEFAULT_MAX_TOKENS, TEMPERATURE
import time
import logging

# 初始化日志（可选，便于调试）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化智谱AI客户端
client = ZhipuAI(api_key=ZHIPU_API_KEY)


def call_glm(
    messages,
    max_tokens=None,
    temperature=None,
    retries=2,
    retry_delay=1
):
    """
    调用智谱AI的 glm-4-flash 模型进行推理。
    
    Args:
        messages (list): 对话消息列表，格式如 [{"role": "user", "content": "..."}]
        max_tokens (int, optional): 最大生成 token 数
        temperature (float, optional): 采样温度
        retries (int): 失败时重试次数
        retry_delay (int): 重试前等待秒数
    
    Returns:
        str or None: 模型返回的文本内容，失败时返回 None
    """
    if max_tokens is None:
        max_tokens = DEFAULT_MAX_TOKENS
    if temperature is None:
        temperature = TEMPERATURE

    for attempt in range(retries + 1):
        try:
            logger.info(f"Calling ZhipuAI model '{MODEL_NAME}' (attempt {attempt + 1})...")
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False  # 同步调用
            )
            content = response.choices[0].message.content.strip()
            logger.info("ZhipuAI call succeeded.")
            return content

        except Exception as e:
            logger.error(f"ZhipuAI API error on attempt {attempt + 1}: {e}")
            if attempt < retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("All retries failed. Returning None.")
                return None

    return None