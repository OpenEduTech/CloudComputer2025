import openai
from openai import AsyncOpenAI
from typing import Dict, List, Any
import os
from dotenv import load_dotenv
import json

load_dotenv()

class LLMClient:
    def __init__(self, model: str = "gpt-4-turbo-preview"):
        """
        初始化LLM客户端
        支持OpenAI API或本地模型
        """
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        # 初始化客户端
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 定义知识扩展的Prompt模板
        self.extension_templates = {
            "default": """你是一个专业的教育内容扩展助手。
请基于以下PPT片段进行知识扩展：

【片段标题】：{title}
【片段内容】：{content}

请从以下方面扩展（如果适用）：
1. **背景与原理说明**：解释核心概念的历史背景和基本原理
2. **相关公式或推导**：提供关键公式及其推导过程
3. **代码示例**：给出实际的代码示例或伪代码
4. **实际应用场景**：说明该知识在现实中的应用
5. **常见误区**：指出学习者常见的理解误区

请保持语言严谨、结构清晰，每个部分使用Markdown格式。
如果某些方面不适用，可以省略。

扩展内容：""",
            
            "technical": """作为技术专家，请扩展以下技术内容：

【主题】：{title}
【内容】：{content}

请提供：
1. 技术原理深度解析
2. 相关算法或架构图描述
3. 性能指标与优化建议
4. 行业最佳实践
5. 学习资源推荐（书籍、论文、教程）

请使用专业术语，但保持解释清晰。""",
            
            "simple": """请用简单易懂的方式解释以下内容：

【主题】：{title}
【要点】：{content}

请解释：
1. 这是什么？（一句话定义）
2. 为什么重要？
3. 如何工作？（比喻说明）
4. 实际例子
5. 关键要点总结

请使用生活化的比喻和例子。"""
        }
    
    async def extend_knowledge(self, content: str, context: List[Dict] = None, 
                               template_type: str = "default") -> Dict[str, Any]:
        """
        调用LLM扩展知识
        """
        # 构建上下文
        context_text = ""
        if context:
            context_text = "\n相关上下文：\n"
            for idx, ctx in enumerate(context[:3], 1):
                context_text += f"{idx}. {ctx.get('content', '')[:200]}...\n"
        
        # 选择模板
        template = self.extension_templates.get(template_type, self.extension_templates["default"])
        
        # 构建Prompt
        prompt = template.format(
            title=content[:50] + "..." if len(content) > 50 else content,
            content=content[:1000]  # 限制长度
        ) + context_text
        
        try:
            # 调用LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业、准确、有帮助的教育助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
                response_format={"type": "json_object"}  # 请求JSON格式响应
            )
            
            # 解析响应
            result_text = response.choices[0].message.content
            
            # 尝试解析为JSON，如果失败则作为纯文本
            try:
                result_json = json.loads(result_text)
            except json.JSONDecodeError:
                result_json = {
                    "extended_content": result_text,
                    "sections": ["扩展内容"],
                    "format": "text"
                }
            
            # 添加元数据
            result_json.update({
                "model_used": self.model,
                "template_type": template_type,
                "timestamp": "2024-01-18T10:30:00Z"  # 实际使用时应该用datetime.now()
            })
            
            return result_json
            
        except Exception as e:
            # 优雅降级：返回结构化错误信息
            return {
                "error": str(e),
                "extended_content": "抱歉，知识扩展服务暂时不可用。",
                "sections": ["服务暂时不可用"],
                "fallback": True
            }
    
    async def generate_questions(self, content: str, question_type: str = "multiple_choice") -> List[Dict]:
        """
        生成相关问题
        """
        prompt = f"""基于以下内容生成3个{question_type}问题：

内容：{content[:500]}

要求：
1. 问题覆盖核心知识点
2. 包含正确答案和详细解析
3. 选项具有迷惑性但只有一个正确

请以JSON格式返回：{{"questions": [{{"question": "...", "options": ["...", ...], "answer": "...", "explanation": "..."}}]}}"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("questions", [])
            
        except Exception as e:
            return [{"error": str(e)}]
    
    async def check_facts(self, statements: List[str]) -> Dict[str, Any]:
        """
        事实核查
        """
        prompt = f"""请核查以下陈述的事实准确性：

陈述：
{chr(10).join([f'{i+1}. {s}' for i, s in enumerate(statements)])}

对每个陈述，请判断：
1. 准确性（正确/部分正确/错误/无法验证）
2. 置信度（高/中/低）
3. 简要证据或反驳

返回JSON格式：{{"checks": [{{"statement": "...", "accuracy": "...", "confidence": "...", "evidence": "..."}}]}}"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)