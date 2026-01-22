"""LLM API调用模块"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from shared.error_codes import ErrorCode
from shared.constants import AgentConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端（支持OpenRouter + Gemini）"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "google/gemini-3-flash-preview",  # 使用最新的 3.0 flash 模型
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: int = 90,  # 增加超时到90秒
        base_url: Optional[str] = None,
        enable_reasoning: bool = False  # 默认关闭推理模式以提高稳定性
    ):
        """
        初始化LLM客户端
        
        Args:
            api_key: OpenRouter API密钥
            model: 模型名称（默认Gemini 3 Pro）
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间（秒）
            base_url: API base URL（默认OpenRouter）
            enable_reasoning: 是否启用推理模式
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set, LLM calls will fail")
        
        self.model = model or os.getenv("LLM_MODEL", "google/gemini-3-flash-preview")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.enable_reasoning = enable_reasoning
        
        # 使用OpenRouter作为默认base_url
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        
        # 初始化OpenAI客户端（兼容OpenRouter）
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"LLM Client initialized: model={self.model}, base_url={self.base_url}")
        else:
            self.client = None
    
    async def call_with_retry(
        self,
        prompt: str,
        system_role: str = "You are a helpful assistant.",
        max_retries: int = AgentConfig.MAX_RETRIES,
        messages_history: Optional[List[Dict]] = None
    ) -> str:
        """
        调用LLM（带重试机制和推理支持）
        
        Args:
            prompt: 用户提示
            system_role: 系统角色
            max_retries: 最大重试次数
            messages_history: 消息历史（用于多轮对话）
            
        Returns:
            LLM响应文本
            
        Raises:
            Exception: LLM调用失败
        """
        if not self.client:
            raise ValueError("LLM client not initialized. Please set OPENROUTER_API_KEY.")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling LLM (attempt {attempt + 1}/{max_retries}, model={self.model})")
                
                # 构建消息列表
                if messages_history:
                    messages = messages_history.copy()
                    messages.append({"role": "user", "content": prompt})
                else:
                    messages = [
                        {"role": "system", "content": system_role},
                        {"role": "user", "content": prompt}
                    ]
                
                # 构建请求参数
                request_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": min(0.3, self.temperature),  # 降低随机性，提高JSON格式准确性
                    "max_tokens": self.max_tokens
                }
                
                # Gemini 3 Pro支持推理模式
                if self.enable_reasoning and "gemini-3-pro" in self.model.lower():
                    request_params["extra_body"] = {"reasoning": {"enabled": True}}
                
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**request_params),
                    timeout=self.timeout
                )
                
                # 检查响应有效性
                if not response or not response.choices or len(response.choices) == 0:
                    logger.error(f"Invalid LLM response (attempt {attempt + 1})")
                    if attempt == max_retries - 1:
                        raise Exception(ErrorCode.LLM_API_ERROR)
                    await asyncio.sleep(AgentConfig.RETRY_DELAY * (2 ** attempt))
                    continue
                
                content = response.choices[0].message.content
                
                # 检查内容有效性
                if not content:
                    logger.error(f"Empty content in LLM response (attempt {attempt + 1})")
                    if attempt == max_retries - 1:
                        raise Exception(ErrorCode.LLM_API_ERROR)
                    await asyncio.sleep(AgentConfig.RETRY_DELAY * (2 ** attempt))
                    continue
                
                logger.info(f"LLM response received ({len(content)} chars)")
                
                # 记录推理详情（如果有）
                if hasattr(response.choices[0].message, 'reasoning_details'):
                    logger.debug(f"Reasoning details: {response.choices[0].message.reasoning_details}")
                
                return content
                
            except asyncio.TimeoutError:
                logger.error(f"LLM timeout (attempt {attempt + 1})")
                if attempt == max_retries - 1:
                    raise Exception(ErrorCode.LLM_TIMEOUT)
                await asyncio.sleep(AgentConfig.RETRY_DELAY * (2 ** attempt))
                
            except Exception as e:
                logger.error(f"LLM API error: {str(e)}")
                if attempt == max_retries - 1:
                    raise Exception(ErrorCode.LLM_API_ERROR)
                await asyncio.sleep(AgentConfig.RETRY_DELAY * (2 ** attempt))
        
        raise Exception(ErrorCode.LLM_API_ERROR)
    
    def _clean_json_response(self, response: str) -> str:
        """
        清理LLM响应，移除常见的JSON格式问题
        
        Args:
            response: 原始响应字符串
            
        Returns:
            清理后的响应
        """
        import re
        
        # 1. 提取JSON块（移除markdown包裹）
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        response = response.strip()
        
        # 2. 移除BOM和其他不可见字符
        response = response.replace('\ufeff', '').replace('\u200b', '')
        
        # 3. 找到第一个 { 或 [ 和最后一个 } 或 ]
        start_idx = min(
            (response.find('{') if '{' in response else len(response)),
            (response.find('[') if '[' in response else len(response))
        )
        
        end_idx = max(
            response.rfind('}') if '}' in response else -1,
            response.rfind(']') if ']' in response else -1
        )
        
        if start_idx < len(response) and end_idx >= 0:
            response = response[start_idx:end_idx + 1]
        
        return response
    
    async def call_json(
        self,
        prompt: str,
        system_role: str = "You are a helpful assistant.",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        调用LLM并解析JSON响应（带重试机制）
        
        Args:
            prompt: 用户提示
            system_role: 系统角色
            max_retries: 最大重试次数
            
        Returns:
            解析后的JSON对象
        """
        import json
        from agents.utils import validate_json_output
        
        for attempt in range(max_retries):
            try:
                response_text = await self.call_with_retry(
                    prompt=prompt,
                    system_role=system_role,
                    max_retries=2
                )
                
                # 检查响应是否为空
                if not response_text:
                    raise ValueError("LLM returned empty response")
                
                # 预清理响应
                cleaned_response = self._clean_json_response(response_text)
                
                # 尝试解析JSON
                return validate_json_output(cleaned_response)
                
            except ValueError as e:
                logger.debug(f"JSON解析失败 (attempt {attempt + 1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    # 重新请求LLM生成更规范的JSON
                    logger.debug("重新请求LLM生成规范JSON...")
                    prompt = f"""{prompt}

⚠️ 上一次返回的JSON格式有误，请重新生成。严格要求：
1. 必须是有效的JSON数组
2. 所有字符串不能包含换行符
3. reasoning字段80-120字
4. 直接返回JSON，不要用```包裹"""
                    continue
                else:
                    # 最后一次尝试失败，抛出异常
                    raise
            except Exception as e:
                logger.error(f"LLM调用失败 (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    continue
                else:
                    raise
        
        raise ValueError("JSON parsing failed after all retries")
    
    async def call_batch(
        self,
        prompts: List[str],
        system_role: str = "You are a helpful assistant."
    ) -> List[str]:
        """
        批量调用LLM
        
        Args:
            prompts: 提示列表
            system_role: 系统角色
            
        Returns:
            响应列表
        """
        tasks = [
            self.call_with_retry(prompt, system_role)
            for prompt in prompts
        ]
        return await asyncio.gather(*tasks)


# 全局LLM客户端实例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局LLM客户端实例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def set_llm_client(client: LLMClient):
    """设置全局LLM客户端实例"""
    global _llm_client
    _llm_client = client
