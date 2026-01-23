"""AI 助教对话服务"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # "user" | "assistant"
    content: str
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class AITutorService:
    """AI 助教服务"""
    
    def __init__(self, llm_config):
        self.llm = llm_config.create_llm(temperature=0.7)
        self.llm_config = llm_config
        
        # 每个页面一个独立的对话历史
        self.conversations: Dict[int, List[ChatMessage]] = {}
        self.page_context: Dict[int, Dict[str, Any]] = {}
    
    def set_page_context(
        self,
        page_id: int,
        title: str,
        content: str,
        knowledge_clusters: List[Dict[str, Any]],
        understanding_notes: str,
        knowledge_gaps: List[Dict[str, Any]] = None,
        expanded_content: List[Dict[str, Any]] = None
    ):
        """设置页面上下文 - 与新的知识结构对齐
        
        Args:
            page_id: 页面 ID
            title: 页面标题
            content: 页面原始内容
            knowledge_clusters: 知识聚类结果（包含难度分析）
            understanding_notes: 学生理解笔记
            knowledge_gaps: 识别的知识缺口（可选）
            expanded_content: 补充说明内容（可选）
        """
        self.page_context[page_id] = {
            "title": title,
            "content": content,
            "knowledge_clusters": knowledge_clusters,
            "understanding_notes": understanding_notes,
            "knowledge_gaps": knowledge_gaps or [],
            "expanded_content": expanded_content or []
        }
        
        # 初始化该页面的对话历史
        if page_id not in self.conversations:
            self.conversations[page_id] = []
    
    def get_assistant_greeting(self, page_id: int) -> str:
        """获取助教欢迎语"""
        context = self.page_context.get(page_id)
        if not context:
            return "你好！我是 AI 学习助教。请先加载页面内容。"
        
        # 提及识别到的难点
        difficult_concepts = [
            c["concept"] for c in context.get("knowledge_clusters", [])
            if c.get("difficulty_level", 0) >= 3
        ]
        
        greeting = f"你好！关于 \"{context['title']}\"，我已经准备好帮助你了。"
        
        if difficult_concepts:
            greeting += f"\n我注意到这部分内容中 {', '.join(difficult_concepts[:2])} 可能比较难理解，有什么想咨询的吗？"
        else:
            greeting += "\n有什么疑问吗？"
        
        return greeting
    
    def chat(self, page_id: int, user_message: str) -> str:
        """与用户进行对话
        
        Args:
            page_id: 页面 ID
            user_message: 用户消息
        
        Returns:
            助教回复
        """
        context = self.page_context.get(page_id)
        if not context:
            return "请先加载页面内容。"
        
        # 获取对话历史
        if page_id not in self.conversations:
            self.conversations[page_id] = []
        
        conversation_history = self.conversations[page_id]

        system_message = self._build_system_prompt(context, conversation_history)

        messages = [
            SystemMessagePromptTemplate.from_template(system_message).format()
        ]
        
        # 添加对话历史
        for msg in conversation_history[-6:]:  
            if msg.role == "user":
                messages.append(HumanMessagePromptTemplate.from_template("{text}").format(text=msg.content))
            else:
                from langchain_core.messages import AIMessage
                messages.append(AIMessage(content=msg.content))
        
        messages.append(HumanMessagePromptTemplate.from_template("{text}").format(text=user_message))
        
        response = self.llm.invoke(messages)
        assistant_message = response.content
        
        conversation_history.append(ChatMessage(role="user", content=user_message))
        conversation_history.append(ChatMessage(role="assistant", content=assistant_message))
        
        return assistant_message
    
    def _build_system_prompt(self, context: Dict[str, Any], history: List[ChatMessage]) -> str:
        """构建系统提示词"""
        template = """你是一位耐心的 AI 学习助教，帮助学生理解和掌握知识。

【页面标题】: {title}

【原始内容】:
{content}

【学生学习笔记】:
{understanding_notes}

【知识要点分析】:
{concepts_analysis}

【可能的理解障碍】:
{gaps_info}

【补充说明】:
{expanded_content}

【你的教学风格】:
1. 以学生为中心 - 始终考虑学生的理解水平
2. 明确重点 - 突出最重要的概念和易错点
3. 循序渐进 - 从简单到复杂，从具体到抽象
4. 举例说明 - 提供实际例子或类比帮助理解
5. 互动式 - 引导而不是直接给出答案，鼓励思考

【重点关注的概念难点】:
{difficult_concepts}

【禁止】:
- 不编造信息
- 不离开当前页面的范围
- 不过度复杂的数学或技术描述
- 不忽视学生的理解困难

现在请基于学生的问题和当前内容进行耐心、清晰的讲解。
"""
        
        # 提取信息
        concepts_analysis = self._format_concepts(context.get("knowledge_clusters", []))
        
        gaps_info = self._format_gaps(context.get("knowledge_gaps", []))
        
        expanded_content = self._format_expanded_content(context.get("expanded_content", []))
        
        # 找出难度高的概念
        difficult_concepts = [
            f"- {c['concept']} (难度: {c.get('difficulty_level', 0)}/5)"
            for c in context.get("knowledge_clusters", [])
            if c.get("difficulty_level", 0) >= 3
        ]
        difficult_str = "\n".join(difficult_concepts) if difficult_concepts else "- 无特别难点"
        
        return template.format(
            title=context.get("title", ""),
            content=context.get("content", "")[:800], 
            understanding_notes=context.get("understanding_notes", "")[:500],
            concepts_analysis=concepts_analysis,
            gaps_info=gaps_info,
            expanded_content=expanded_content,
            difficult_concepts=difficult_str
        )
    
    def _format_concepts(self, clusters: List[Dict[str, Any]]) -> str:
        """格式化知识聚类信息"""
        if not clusters:
            return "- 无特别分类"
        
        lines = []
        for c in clusters[:5]: 
            concept = c.get("concept", "未知")
            difficulty = c.get("difficulty_level", 0)
            why_difficult = c.get("why_difficult", "")
            
            line = f"- {concept} (难度: {difficulty}/5)"
            if why_difficult:
                line += f" - {why_difficult[:100]}"
            lines.append(line)
        
        return "\n".join(lines) if lines else "- 无特别分类"
    
    def _format_gaps(self, gaps: List[Dict[str, Any]]) -> str:
        """格式化知识缺口信息"""
        if not gaps:
            return "- 无识别到的重大缺口"
        
        lines = []
        for g in gaps[:3]: 
            concept = g.get("concept", "未知")
            gap_types = g.get("gap_types", [])
            priority = g.get("priority", 0)
            
            if gap_types:
                line = f"- {concept} ({gap_types[0]}, 优先级: {priority}/5)"
            else:
                line = f"- {concept} (优先级: {priority}/5)"
            lines.append(line)
        
        return "\n".join(lines) if lines else "- 无识别到的重大缺口"
    
    def _format_expanded_content(self, expanded: List[Dict[str, Any]]) -> str:
        """格式化补充说明内容"""
        if not expanded:
            return "- 无额外补充"
        
        lines = []
        for e in expanded[:3]:  
            concept = e.get("concept", "未知")
            content = e.get("content", "")[:100]
            
            line = f"- {concept}: {content}..."
            lines.append(line)
        
        return "\n".join(lines) if lines else "- 无额外补充"
    
    def clear_conversation(self, page_id: int):
        """清除特定页面的对话历史"""
        if page_id in self.conversations:
            self.conversations[page_id] = []
    
    def get_conversation_history(self, page_id: int) -> List[Dict[str, str]]:
        """获取对话历史"""
        if page_id not in self.conversations:
            return []
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in self.conversations[page_id]
        ]
    
    def switch_page(self, old_page_id: int, new_page_id: int):
        """切换页面时的处理
        
        Args:
            old_page_id: 旧页面 ID
            new_page_id: 新页面 ID
        """
        # 清除旧页面的对话历史（可选：也可以保留）
        # self.clear_conversation(old_page_id)
        
        # 初始化新页面的对话历史
        if new_page_id not in self.conversations:
            self.conversations[new_page_id] = []
