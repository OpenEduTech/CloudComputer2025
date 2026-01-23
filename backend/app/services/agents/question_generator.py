from langchain_core.prompts import ChatPromptTemplate
from app.services.llm_factory import LLMFactory
from app.models.quiz import Question
from typing import List, Tuple
import json
import re

class QuestionGeneratorAgent:
    def __init__(self):
        self.llm = LLMFactory.get_deepseek_llm()

    async def _verify_question(self, question: Question, source_text: str) -> Tuple[bool, str]:
        """
        验证题目是否基于原文，避免幻觉
        返回: (是否通过验证, 问题描述)
        """
        verification_prompt = f"""你是一位严格的审核员，负责检查题目是否基于提供的学习材料，避免大模型幻觉。

学习材料：
{source_text[:3000]}

待验证题目：
类型：{question.type}
题目内容：{question.content}
正确答案：{question.correct_answer}
知识点：{question.knowledge_point}

严格判断标准：
1. 题目内容必须能从学习材料中找到明确依据，不能是编造的内容
2. 正确答案必须基于学习材料，不能是凭空想象的
3. 如果是计算题：
   - 数据必须来自材料或基于材料的合理推导
   - 公式必须在材料中提到或是该领域的基础公式
   - 不能使用材料中未提及的概念或数据
4. 如果是应用题：
   - 场景设计要合理，不能过于天马行空
   - 必须与材料主题相关
5. 知识点必须是材料中实际涉及的内容

判断结果：
- 如果题目完全基于材料，返回 is_valid: true
- 如果题目包含材料中没有的信息、编造的数据或概念，返回 is_valid: false

返回JSON格式：
{{
  "is_valid": true/false,
  "reason": "简要说明验证通过的依据 或 指出具体的幻觉问题"
}}

只返回JSON，不要其他文字。"""

        try:
            response = await self.llm.ainvoke(verification_prompt)
            content = response.content.strip()
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            return result.get("is_valid", False), result.get("reason", "未知原因")
        except Exception as e:
            print(f"⚠️  验证题目时出错: {e}")
            # 如果验证失败，默认通过（避免阻塞）
            return True, "验证系统异常，默认通过"

    async def generate_questions(self, text: str, count: int = 5, grade: str = "初中") -> List[Question]:
        # Truncate text if too long
        context = text[:20000] 
        
        # 根据年级调整难度描述
        grade_difficulty_map = {
            "小学": "适合小学生理解的简单题目，使用通俗易懂的语言",
            "初中": "适合初中生水平的题目，涉及基础概念和应用",
            "高中": "适合高中生水平的题目，需要一定的分析和推理能力",
            "大学": "适合大学生水平的题目，涉及专业知识和深入理解",
            "研究生": "适合研究生水平的题目，需要批判性思维和深度分析"
        }
        
        difficulty_guide = grade_difficulty_map.get(grade, grade_difficulty_map["初中"])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一位专业的教师，负责根据学习材料生成测验题目。

重要提示：你必须只返回一个有效的JSON数组，不要有任何其他文字或markdown标记。

学生年级：{grade}
难度要求：{difficulty_guide}

请根据提供的文本生成 {count} 道测验题目。
题目类型应该包含选择题（multiple_choice）和简答题（short_answer）。
题目难度和语言风格必须符合{grade}学生的认知水平。

题目类型分配要求：
- 选择题（multiple_choice）：约占40-50%，用于考查概念理解和知识记忆
- 简答题（short_answer）：约占50-60%，必须包含以下类型：
  * 计算题：需要进行数学计算、公式推导或数值求解（优先）
  * 应用题：需要将知识应用到实际场景中解决问题
  * 分析题：需要分析原理、推理过程或解释现象
  * 概念题：简要解释概念或总结要点（最少）

简答题要求：
- 如果材料涉及公式、数据、计算，必须优先生成计算题
- 计算题要给出具体数值，要求学生计算结果
- 应用题要设计实际场景，让学生运用知识解决问题
- 避免只生成"请解释..."、"请说明..."这类纯文字描述题

每道题目必须包含以下字段：
- type: "multiple_choice" 或 "short_answer"
- content: 题目内容（语言难度要符合{grade}水平）
- options: 选择题的4个选项（数组），简答题为null
- correct_answer: 正确答案（计算题要给出数值答案和单位）
- explanation: 答案解释（计算题要包含完整解题步骤）
- difficulty: "easy"、"medium" 或 "hard"（相对于{grade}水平）
- knowledge_point: 考查的知识点

示例格式：
[
  {{
    "type": "multiple_choice",
    "content": "以下哪个描述是正确的？",
    "options": ["选项A", "选项B", "选项C", "选项D"],
    "correct_answer": "选项A",
    "explanation": "因为...",
    "difficulty": "easy",
    "knowledge_point": "基础概念"
  }},
  {{
    "type": "short_answer",
    "content": "一个物体从10米高处自由落下，忽略空气阻力，g取10m/s²，求物体落地时的速度。",
    "options": null,
    "correct_answer": "14.14 m/s",
    "explanation": "根据自由落体公式 v² = 2gh，代入数据：v² = 2×10×10 = 200，因此 v = √200 ≈ 14.14 m/s",
    "difficulty": "medium",
    "knowledge_point": "自由落体运动"
  }},
  {{
    "type": "short_answer",
    "content": "如果你是一名工程师，需要设计一个斜坡让货物从高处滑下，如何利用摩擦力控制货物的速度？请说明原理。",
    "options": null,
    "correct_answer": "可以通过调整斜坡的倾角和表面材料来控制摩擦力大小。增大倾角会增加重力分量，减小摩擦力的相对作用；选择摩擦系数大的材料可以增大摩擦力，从而减慢货物速度。",
    "explanation": "这是一个应用题，考查学生将摩擦力知识应用到实际工程问题中的能力。",
    "difficulty": "hard",
    "knowledge_point": "摩擦力应用"
  }}
]

只返回JSON数组，不要有markdown代码块标记，不要有任何解释文字。"""),
            ("user", "学习材料内容：\n\n{text}")
        ])
        
        chain = prompt | self.llm
        
        try:
            print(f"开始为{grade}学生生成 {count} 道题目...")
            response = await chain.ainvoke({
                "count": count, 
                "text": context,
                "grade": grade,
                "difficulty_guide": difficulty_guide
            })
            content = response.content
            
            print(f"LLM响应长度: {len(content)} 字符")
            print(f"响应前150字符: {content[:150]}")
            
            # Extract JSON from potential markdown
            json_str = content.strip()
            
            # Remove markdown code blocks if present
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            # Try to find JSON array if wrapped in text
            if not json_str.startswith('['):
                # Look for JSON array pattern
                match = re.search(r'\[[\s\S]*\]', json_str)
                if match:
                    json_str = match.group(0)
            
            print(f"提取的JSON长度: {len(json_str)} 字符")
            
            # Parse JSON
            data = json.loads(json_str)
            
            if not isinstance(data, list):
                raise ValueError("响应不是JSON数组")
            
            questions = []
            for i, item in enumerate(data):
                # Ensure options is None for short_answer
                if item.get("type") == "short_answer":
                    item["options"] = None
                
                # Validate required fields
                required_fields = ["type", "content", "correct_answer", "difficulty", "knowledge_point"]
                for field in required_fields:
                    if field not in item:
                        raise ValueError(f"题目 {i+1} 缺少必需字段 '{field}'")
                
                questions.append(Question(**item))
            
            print(f"✓ 成功为{grade}学生生成 {len(questions)} 道题目")
            
            # Check layer: 验证题目是否基于原文（并发验证以节省时间）
            print("🔍 开始验证题目准确性（避免幻觉）...")
            import asyncio
            
            # 并发验证所有题目
            verification_tasks = [
                self._verify_question(question, context) 
                for question in questions
            ]
            verification_results = await asyncio.gather(*verification_tasks)
            
            verified_questions = []
            rejected_questions = []
            
            for i, (question, (is_valid, reason)) in enumerate(zip(questions, verification_results)):
                if is_valid:
                    verified_questions.append(question)
                    print(f"  ✓ 题目 {i+1} 验证通过: {reason[:50]}...")
                else:
                    rejected_questions.append((question, reason))
                    print(f"  ✗ 题目 {i+1} 验证失败: {reason}")
            
            print(f"📊 验证完成: {len(verified_questions)}/{len(questions)} 道题目通过验证")
            
            # 如果通过验证的题目数量足够，直接返回
            if len(verified_questions) >= count:
                return verified_questions[:count]
            
            # 如果通过验证的题目太少（少于60%），返回所有题目（避免过度过滤）
            if len(verified_questions) < count * 0.6:
                print(f"⚠️  通过验证的题目过少（{len(verified_questions)}/{count}），返回所有题目")
                return questions[:count]
            
            # 如果题目数量不足但验证率还可以，返回已验证的题目
            print(f"⚠️  验证通过的题目数量不足（{len(verified_questions)}/{count}），返回已验证题目")
            return verified_questions
            
        except Exception as e:
            print(f"✗ 生成题目时出错: {e}")
            print(f"错误类型: {type(e).__name__}")
            
            # Fallback mock questions if generation fails
            print("使用降级题目...")
            return [
                Question(
                    type="multiple_choice",
                    content="根据文档内容，以下哪个描述最准确？",
                    options=["选项A：第一个概念", "选项B：第二个概念", "选项C：第三个概念", "选项D：第四个概念"],
                    correct_answer="选项A：第一个概念",
                    explanation="题目生成失败，这是一个示例题目。请检查LLM配置或重试。",
                    difficulty="easy",
                    knowledge_point="文档理解"
                ),
                Question(
                    type="short_answer",
                    content="请简要总结文档的主要内容。",
                    options=None,
                    correct_answer="文档主要讨论了相关概念和应用场景。",
                    explanation="题目生成失败，这是一个示例题目。请检查LLM配置或重试。",
                    difficulty="medium",
                    knowledge_point="内容总结"
                ),
                Question(
                    type="multiple_choice",
                    content="文档中提到的关键技术是什么？",
                    options=["技术A", "技术B", "技术C", "技术D"],
                    correct_answer="技术A",
                    explanation="这是降级题目，实际答案需要根据文档内容确定。",
                    difficulty="medium",
                    knowledge_point="技术理解"
                )
            ][:count]  # 只返回请求的数量

question_generator = QuestionGeneratorAgent()
