"""AI问答API模块"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import os
from openai import AsyncOpenAI

router = APIRouter()

# LLM客户端
_llm_client = None

def get_llm_client():
    """获取LLM客户端单例"""
    global _llm_client
    if _llm_client is None:
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            _llm_client = AsyncOpenAI(
                api_key=api_key,
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            )
    return _llm_client


class AIChatRequest(BaseModel):
    """AI问答请求模型"""
    concept: str = Field(..., description="当前讨论的概念")
    question: str = Field(..., min_length=1, max_length=500, description="用户问题")
    context: Optional[str] = Field(default="", description="概念的背景信息")


@router.post("/chat")
async def ai_chat(request: AIChatRequest):
    """AI问答接口 - 基于概念回答用户问题
    
    功能：
    1. 接收用户针对特定概念的提问
    2. 使用LLM生成专业回答
    3. 结合概念背景提供准确解答
    """
    client = get_llm_client()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="AI服务暂时不可用，请稍后重试"
        )
    
    try:
        # 构建提示词
        system_prompt = """你是一个专业的学术助手，擅长解答跨学科概念相关的问题。
请基于用户提供的概念背景，给出专业、准确、易懂的回答。
回答要求：
1. 简洁明了，控制在150字以内
2. 专业准确，引用可靠知识
3. 通俗易懂，适合非专业读者
4. 如果问题超出概念范围，礼貌说明"""
        
        user_prompt = f"""概念：{request.concept}

{f'背景信息：{request.context[:300]}' if request.context else ''}

用户提问：{request.question}

请回答上述问题。"""
        
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "google/gemini-3-flash-preview"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=300,
                extra_body={"reasoning": {"enabled": True}}
            ),
            timeout=30.0
        )
        
        if response and response.choices:
            answer = response.choices[0].message.content.strip()
            print(f"[SUCCESS] AI问答: {request.concept} - {request.question[:20]}...")
            return {
                "status": "success",
                "data": {
                    "concept": request.concept,
                    "question": request.question,
                    "answer": answer
                }
            }
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="AI响应超时，请稍后重试"
        )
    except Exception as e:
        print(f"[ERROR] AI问答失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"AI问答失败: {str(e)}"
        )
