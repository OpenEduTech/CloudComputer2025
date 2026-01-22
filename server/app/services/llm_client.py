"""
PatPat-Inconsistency-Hunter DeepSeek LLM 客户端
封装与DeepSeek API的所有交互
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel
import httpx

from ..config import settings
from ..utils.logger import logger

T = TypeVar("T", bound=BaseModel)


class DeepSeekClient:
    """DeepSeek大语言模型客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        timeout: int = 120,
    ):
        """
        初始化DeepSeek客户端
        
        Args:
            api_key: DeepSeek API密钥
            api_base: API基础URL
            model: 使用的模型名称
            temperature: 生成温度
            max_tokens: 最大生成token数
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.api_base = api_base or settings.DEEPSEEK_API_BASE
        self.model = model or settings.DEEPSEEK_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        if not self.api_key:
            logger.warning("DeepSeek API密钥未配置，请设置DEEPSEEK_API_KEY环境变量")
        
        self._client = httpx.AsyncClient(
            base_url=self.api_base,
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )
    
    async def close(self):
        """关闭客户端连接"""
        await self._client.aclose()
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 生成温度（可选）
            max_tokens: 最大token数（可选）
            response_format: 响应格式（可选，用于JSON模式）
        
        Returns:
            模型生成的文本响应
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": False,
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        try:
            response = await self._client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            logger.debug(f"LLM响应: {content[:200]}...")
            return content
            
        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API请求失败: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"DeepSeek API请求失败: {e.response.status_code}")
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {str(e)}")
            raise
    
    async def chat_with_json(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        发送聊天请求并解析JSON响应
        
        Args:
            messages: 消息列表
            temperature: 生成温度（可选）
            max_tokens: 最大token数（可选）
        
        Returns:
            解析后的JSON字典
        """
        response = await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        
        try:
            # 尝试解析JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试修复常见的JSON格式问题
            return self._repair_json(response)
    
    async def chat_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> T:
        """
        发送聊天请求并返回结构化Pydantic模型
        
        Args:
            messages: 消息列表
            response_model: Pydantic模型类
            temperature: 生成温度（可选）
            max_tokens: 最大token数（可选）
        
        Returns:
            解析后的Pydantic模型实例
        """
        # 在消息中添加JSON Schema提示
        schema = response_model.model_json_schema()
        schema_prompt = f"\n\n请严格按照以下JSON Schema格式返回响应:\n```json\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n```"
        
        # 修改最后一条用户消息以包含schema
        modified_messages = messages.copy()
        if modified_messages and modified_messages[-1]["role"] == "user":
            modified_messages[-1] = {
                "role": "user",
                "content": modified_messages[-1]["content"] + schema_prompt
            }
        
        json_response = await self.chat_with_json(
            messages=modified_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        try:
            return response_model.model_validate(json_response)
        except Exception as e:
            logger.error(f"结构化响应解析失败: {e}")
            logger.debug(f"原始响应: {json_response}")
            raise ValueError(f"无法将响应解析为{response_model.__name__}: {e}")
    
    def _repair_json(self, text: str) -> Dict[str, Any]:
        """
        尝试修复格式不正确的JSON
        
        Args:
            text: 可能包含JSON的文本
        
        Returns:
            解析后的JSON字典
        """
        import re
        
        # 尝试提取JSON块
        json_patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'\{[\s\S]*\}',
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, text)
            if match:
                json_str = match.group(1) if match.lastindex else match.group(0)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        # 如果都失败了，尝试用json-repair库
        try:
            from json_repair import repair_json
            repaired = repair_json(text)
            return json.loads(repaired)
        except Exception:
            logger.error(f"JSON修复失败，原始文本: {text[:500]}")
            raise ValueError("无法解析JSON响应")
    
    async def batch_chat(
        self,
        messages_list: List[List[Dict[str, str]]],
        max_concurrency: int = 5,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> List[str]:
        """
        批量发送聊天请求
        
        Args:
            messages_list: 消息列表的列表
            max_concurrency: 最大并发数
            temperature: 生成温度（可选）
            max_tokens: 最大token数（可选）
        
        Returns:
            响应文本列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def limited_chat(messages):
            async with semaphore:
                try:
                    return await self.chat(messages, temperature, max_tokens)
                except Exception as e:
                    logger.error(f"批量请求失败: {e}")
                    return None
        
        tasks = [limited_chat(messages) for messages in messages_list]
        return await asyncio.gather(*tasks)
    
    async def batch_chat_structured(
        self,
        messages_list: List[List[Dict[str, str]]],
        response_model: Type[T],
        max_concurrency: int = 5,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> List[Optional[T]]:
        """
        批量发送聊天请求并返回结构化响应
        
        Args:
            messages_list: 消息列表的列表
            response_model: Pydantic模型类
            max_concurrency: 最大并发数
            temperature: 生成温度（可选）
            max_tokens: 最大token数（可选）
        
        Returns:
            Pydantic模型实例列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def limited_structured_chat(messages):
            async with semaphore:
                try:
                    return await self.chat_structured(
                        messages, response_model, temperature, max_tokens
                    )
                except Exception as e:
                    logger.error(f"批量结构化请求失败: {e}")
                    return None
        
        tasks = [limited_structured_chat(messages) for messages in messages_list]
        return await asyncio.gather(*tasks)


# 创建全局客户端实例
_client_instance: Optional[DeepSeekClient] = None


def get_llm_client() -> DeepSeekClient:
    """获取LLM客户端单例"""
    global _client_instance
    if _client_instance is None:
        _client_instance = DeepSeekClient()
    return _client_instance


async def close_llm_client():
    """关闭LLM客户端"""
    global _client_instance
    if _client_instance is not None:
        await _client_instance.close()
        _client_instance = None

