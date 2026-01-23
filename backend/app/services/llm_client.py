"""
LLM 客户端服务
封装 DeepSeek API 调用
"""
import os
import json
import asyncio
import httpx
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """DeepSeek LLM 客户端"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY 未设置，LLM 功能将不可用")
    
    def is_available(self) -> bool:
        """检查 LLM 是否可用"""
        return bool(self.api_key)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Optional[str]:
        """
        调用 DeepSeek Chat API
        
        Args:
            messages: 对话消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成 token 数
        
        Returns:
            生成的文本内容，失败返回 None
        """
        if not self.is_available():
            raise ValueError("DEEPSEEK_API_KEY 未配置")
        
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # 重试机制：网络波动或 API 超时时自动重试
        max_retries = 2
        retry_delay = 3  # 秒
        
        for attempt in range(max_retries + 1):
            try:
                # 增加超时到 120 秒（处理长文本需要更多时间）
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return content
                    
            except httpx.ReadTimeout as e:
                if attempt < max_retries:
                    logger.warning(f"LLM 调用超时 (尝试 {attempt + 1}/{max_retries + 1})，{retry_delay}秒后重试...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"LLM 调用超时: {type(e).__name__}: {str(e) or repr(e)} (已重试 {max_retries} 次)")
                    raise
            except httpx.HTTPStatusError as e:
                logger.error(f"LLM API 请求失败: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"LLM 调用异常: {type(e).__name__}: {str(e) or repr(e)}")
                raise
    
    async def extract_facts(
        self,
        text: str,
        section_title: str = "",
        section_index: int = 0
    ) -> List[Dict[str, Any]]:
        """
        从文本中提取事实信息（带 token 限制检查）
        
        Args:
            text: 待提取的文本
            section_title: 章节标题（用于位置信息）
            section_index: 章节索引
        
        Returns:
            提取的事实列表，每个事实包含：
            - type: 事实类型（数据/日期/人名/结论/事件）
            - content: 事实内容
            - original_text: 原文引用
            - location: 位置信息
            - confidence: 置信度
        """
        # Token 预估（粗略估算：1 token ≈ 1.5 中文字符）
        estimated_tokens = len(text) // 1.5 + 1000  # 文本 + Prompt 开销
        if estimated_tokens > 6000:
            logger.warning(f"章节 '{section_title}' 预估 token 数过高 ({int(estimated_tokens)}), 建议分片处理")
        
        prompt = self._build_extraction_prompt(text, section_title)
        
        messages = [
            {
                "role": "system",
                "content": """你是一个专业的事实提取助手。你的任务是从给定文本中准确提取关键事实信息，并以结构化字段输出，便于后续一致性/冲突检测。

提取原则：
1. 提取完整事实，避免碎片化：将紧密相关的信息合并成一条完整事实。
2. 去除重复：如果一个完整事实已包含元素（人名、机构名、地点），不要再单独提取这些元素。
3. 识别可验证性：
   - verifiable_type: "public" → 可通过公开信息验证（历史事件、机构、人物、已发布政策/指南）
   - verifiable_type: "internal" → 内部数据/上下文相关（未公开的营收、内部项目日期、流程状态）
4. 结构化字段：尽量填写以下字段以支持后续检测：
   - subject（主体，谁/哪个项目/哪个机构）
   - predicate（谓词/关系，如“完成”、“符合”、“安排”、“投资额为”）
   - object（客体/目标，如“居民协调”、“新版指南”、“预约系统”）
   - value（数值或文本值，若涉及比例/金额/数量请保留原单位在 modifiers.units）
   - modifiers（字典，可包含 units、scope、condition 等说明）
   - time（规范化日期或时间范围，如 2026-03-20、2026年3月底）
   - polarity（"affirmative"/"negative"，肯定或否定陈述）

输出要求：
- 必须返回有效的 JSON 数组
- 每个事实必须包含 original_text（原文引用）与 confidence（0-1）
- 字段尽量完整，但不要编造不存在的信息"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = await self.chat(messages, temperature=0.1)
            facts = self._parse_facts_response(response, section_title, section_index)
            return facts
        except Exception as e:
            logger.error(f"事实提取失败 (章节: {section_title}): {type(e).__name__}: {str(e) or repr(e)}")
            return []

    def _build_extraction_prompt(self, text: str, section_title: str) -> str:
        """构建事实提取提示词（结构化提取），加入材料驱动提示。"""
        # 轻量材料提示：从当前章节文本提取关键词/单位/时间短语
        try:
            from .prompt_tuner import prompt_tuner
            hints = prompt_tuner.derive_hints_from_text(text)
        except Exception:
            hints = {"keywords": [], "units": [], "time_phrases": []}
        keywords = ", ".join(hints.get("keywords", [])[:10])
        units = ", ".join(hints.get("units", [])[:6])
        times = ", ".join(hints.get("time_phrases", [])[:6])

        return f"""请从以下文本中提取关键事实信息，并以结构化字段输出。

章节：{section_title if section_title else "未知"}

文本内容：
---
{text}
---

材料驱动提示（来自本章节）：
- 领域关键词（参考）：{keywords if keywords else "(无明显关键词)"}
- 常用单位（参考）：{units if units else "(未检测到明显单位)"}
- 时间短语（参考）：{times if times else "(未检测到明显时间短语)"}

输出格式（JSON 数组，每个元素一个事实）：
[
  {{
    "type": "事件",
    "subject": "SpaceX",
    "predicate": "创立",
    "object": "航天公司",
    "value": "",
    "modifiers": {{"by": "埃隆·马斯克"}},
    "time": "2002-01-01",
    "polarity": "affirmative",
    "content": "SpaceX是由埃隆·马斯克于2002年创立的航天公司",
    "original_text": "SpaceX是由埃隆·马斯克创立的航天公司",
    "verifiable_type": "public",
    "confidence": 0.95
  }},
  {{
    "type": "数据",
    "subject": "公司",
    "predicate": "总营收",
    "object": "第一季度",
    "value": 1000,
    "modifiers": {{"units": "万美元"}},
    "time": "2024-Q1",
    "polarity": "affirmative",
    "content": "第一季度公司总营收为1000万美元",
    "original_text": "根据第一季度财报显示，公司总营收为 1000 万美元",
    "verifiable_type": "public",
    "confidence": 0.90
  }}
]

字段说明：
- type: ["数据", "日期", "人名", "机构", "结论", "事件"] 之一
- subject/predicate/object：主体/谓词/客体（尽量填写，便于后续冲突检测）
- value：数值或文本值；若为比例/金额请给出原始数值，单位放在 modifiers.units
- modifiers：附加说明（如 units、scope、condition）
- time：规范化日期或时间范围（如 2026-03-20、2026年3月底、2024-Q1）
- polarity：affirmative/negative 表示肯定或否定陈述
- content：完整、独立的事实描述（避免碎片化）
- original_text：原文引用

verifiable_type 判定规则（普适标准，适用于所有类型文本）：

判定为 "public"（可通过外部公开信息验证）需同时满足：
1. **时态判断**：描述**已发生的事件**或**已存在的状态**（而非未来计划）
2. **可验证性**：涉及**可从外部来源查证的信息**，如：
   - 历史事件的时间、地点、人物
   - 已公开发布的数据、统计、报告
   - 已公布的政策、法规、标准的名称或内容
   - 可观测的客观事实（如天气、事故、公开事件）
3. **非主观性**：是客观陈述，而非主观评价或意见

判定为 "internal"（本文内部观点，不应联网验证）的情况：
1. **未来承诺**：描述**将要做什么**、**计划如何**、**目标是什么**（时态：将、会、计划、拟）
2. **本文观点**：作者/组织的**主观评价、结论、建议**（如"我们认为""可以得出""建议"）
3. **内部数据**：本文作者提供的**无法外部查证的具体数字**（如"我们完成了65%""本项目投资1800万"）
4. **规划措施**：后续**整改措施、实施方案、管理机制**的描述

示例判定（跨领域普适）：
- "爱因斯坦于1879年出生于德国" → public（历史事实，可查证）
- "公司计划在2026年推出新产品" → internal（未来计划）
- "根据财报，2023年营收为50亿美元" → public（已公开数据，可查证）
- "我们的营收同比增长15%" → internal（本文提供的内部数据）
- "《巴黎协定》于2015年签署" → public（历史事件）
- "项目将建立每日通报机制" → internal（未来措施）
- "研究表明气温上升2°C会导致..." → public（已发表研究结论）
- "我们认为这项技术具有前景" → internal（主观评价）

- confidence：0-1 之间的置信度

请只返回 JSON 数组："""
    
    def _parse_facts_response(
        self,
        response: str,
        section_title: str,
        section_index: int
    ) -> List[Dict[str, Any]]:
        """解析 LLM 返回的事实数据"""
        try:
            # 尝试提取 JSON 内容
            content_to_parse = response.strip()
            
            # Robust JSON extraction (Handle potential model chatter/CoT)
            json_start = content_to_parse.find("```json")
            if json_start != -1:
                json_start += 7
                json_end = content_to_parse.find("```", json_start)
                if json_end != -1:
                    content_to_parse = content_to_parse[json_start:json_end]
                else:
                    content_to_parse = content_to_parse[json_start:]
            else:
                # Fallback: Find outer list structure
                start_idx = content_to_parse.find("[")
                end_idx = content_to_parse.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    content_to_parse = content_to_parse[start_idx:end_idx+1]
            
            content_to_parse = content_to_parse.strip()
            
            facts = json.loads(content_to_parse)
            
            if not isinstance(facts, list):
                facts = [facts]
            
            # 添加位置信息
            for i, fact in enumerate(facts):
                fact["location"] = {
                    "section_title": section_title,
                    "section_index": section_index
                }
                fact["fact_id"] = f"fact_{section_index}_{i}"
            
            return facts
            
        except json.JSONDecodeError as e:
            logger.error(f"解析事实 JSON 失败: {e}, 原始响应: {response[:200]}")
            return []


# 全局 LLM 客户端实例
llm_client = LLMClient()

