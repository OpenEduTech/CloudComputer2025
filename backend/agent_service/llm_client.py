"""
LLM客户端
封装OpenAI API调用
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI, AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端类"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
        
        logger.info(f"LLM Client initialized with model: {self.model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def call_llm(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        调用LLM API
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            LLM响应文本
        """
        try:
            logger.info(f"Calling LLM with prompt length: {len(prompt)}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            result = response.choices[0].message.content
            logger.info(f"LLM response received, length: {len(result)}")
            
            return result
            
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise
    
    async def call_llm_json(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        调用LLM并解析JSON响应
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            解析后的JSON对象
        """
        response_text = await self.call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        try:
            # 尝试提取JSON（处理可能的markdown代码块）
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Response text: {response_text}")
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
    
    async def call_llm_multiple(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        n: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> list[str]:
        """
        多次调用LLM（用于一致性检查）
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            n: 调用次数
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            多次调用的响应列表
        """
        tasks = [
            self.call_llm(prompt, system_prompt, temperature, max_tokens)
            for _ in range(n)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉异常结果
        valid_results = [r for r in results if not isinstance(r, Exception)]
        
        if not valid_results:
            raise Exception("All LLM calls failed")
        
        return valid_results

