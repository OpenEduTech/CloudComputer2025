import json
import random
from typing import List, Dict, Any, Generator
from openai import OpenAI
import hashlib
from models import Chunk, Question

class QuestionGenerator:
    """基于学习资料生成题目"""
    
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL
        )
    
    def generate_questions(
        self, 
        chunks: List[Chunk], 
        num_questions: int = 5,
        question_types: List[str] = None,
        pre_extracted_concepts: Dict = None
    ) -> List[Question]:
        """生成题目"""
        if not question_types:
            question_types = list(self.config.QUESTION_TYPES)
        
        # 使用预提取的概念或提取新概念
        if pre_extracted_concepts is None:
            key_concepts = self._extract_key_concepts_for_questions(chunks)
        else:
            key_concepts = pre_extracted_concepts
        
        questions = []
        for i in range(num_questions):
            q_type = random.choice(question_types)
            difficulty = self._select_difficulty(i, num_questions)
            
            if q_type == "multiple_choice":
                question = self._generate_multiple_choice(
                    chunks, key_concepts, difficulty
                )
            elif q_type == "short_answer":
                question = self._generate_short_answer(
                    chunks, key_concepts, difficulty
                )
            elif q_type == "true_false":
                question = self._generate_true_false(
                    chunks, key_concepts, difficulty
                )
            else:
                continue
            
            questions.append(question)
        
        return questions
    
    def generate_questions_stream(
        self,
        chunks: List[Chunk],
        num_questions: int = 5,
        question_types: List[str] = None,
        pre_extracted_concepts: Dict = None,
        on_question_start: callable = None,
        on_question_chunk: callable = None,
        on_question_complete: callable = None
    ) -> List[Question]:
        """流式生成题目，实时回调通知进度
        
        Args:
            chunks: 学习资料块
            num_questions: 题目数量
            question_types: 题目类型列表
            pre_extracted_concepts: 预提取的概念
            on_question_start: 开始生成题目时的回调 (question_index, total)
            on_question_chunk: 生成过程中流式回调 (chunk_text)
            on_question_complete: 题目生成完成时的回调 (question_object)
        """
        if not question_types:
            question_types = list(self.config.QUESTION_TYPES)
        
        # 使用预提取的概念或提取新概念
        if pre_extracted_concepts is None:
            key_concepts = self._extract_key_concepts_for_questions(chunks)
        else:
            key_concepts = pre_extracted_concepts
        
        questions = []
        for i in range(num_questions):
            q_type = random.choice(question_types)
            difficulty = self._select_difficulty(i, num_questions)
            
            # 通知开始生成
            if on_question_start:
                on_question_start(i + 1, num_questions)
            
            if q_type == "multiple_choice":
                question = self._generate_multiple_choice_stream(
                    chunks, key_concepts, difficulty, on_question_chunk
                )
            elif q_type == "short_answer":
                question = self._generate_short_answer_stream(
                    chunks, key_concepts, difficulty, on_question_chunk
                )
            elif q_type == "true_false":
                question = self._generate_true_false_stream(
                    chunks, key_concepts, difficulty, on_question_chunk
                )
            else:
                continue
            
            # 通知完成
            if on_question_complete:
                on_question_complete(question)
            
            questions.append(question)
        
        return questions
    
    def _generate_multiple_choice(
        self, 
        chunks: List[Chunk], 
        key_concepts: Dict,
        difficulty: str
    ) -> Question:
        """生成选择题"""
        # 选择相关的内容块
        relevant_chunks = random.sample(chunks, min(3, len(chunks)))
        context = "\n".join([chunk.text for chunk in relevant_chunks])
        
        prompt = f"""基于以下学习内容生成一道{difficulty}难度的选择题：

        学习内容：
        {context}

        要求：
        1. 问题应该测试对核心概念的理解
        2. 提供4个选项，其中一个是正确答案
        3. 错误选项应该是有迷惑性的常见误解
        4. 提供详细的解释说明为什么正确答案正确，其他选项为什么错误

        返回JSON格式：
        {{
            "question": "问题文本",
            "options": ["选项A", "选项B", "选项C", "选项D"],
            "correct_answer": "正确选项的完整文本",
            "explanation": "详细的解释",
            "tags": ["标签1", "标签2"],
            "difficulty": "{difficulty}"
        }}
        """
        
        response = self.client.chat.completions.create(
            model=self.config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content)
        
        # 生成唯一ID
        question_id = hashlib.md5(
            f"{data['question']}_{difficulty}".encode()
        ).hexdigest()[:8]
        
        return Question(
            question_id=question_id,
            question_type="multiple_choice",
            content=data["question"],
            options=data["options"],
            correct_answer=data["correct_answer"],
            explanation=data["explanation"],
            difficulty=difficulty,
            source_chunks=[chunk.text for chunk in relevant_chunks],
            tags=data.get("tags", []),
            metadata={"generation_method": "llm"}
        )
    
    def _generate_short_answer(
        self, 
        chunks: List[Chunk], 
        key_concepts: Dict,
        difficulty: str
    ) -> Question:
        """生成简答题"""
        relevant_chunks = random.sample(chunks, min(2, len(chunks)))
        context = "\n".join([chunk.text for chunk in relevant_chunks])
        
        prompt = f"""基于以下学习内容生成一道{difficulty}难度的简答题：

        学习内容：
        {context}

        要求：
        1. 问题应该测试对概念的理解和应用能力
        2. 提供参考答案要点
        3. 提供评分标准

        返回JSON格式：
        {{
            "question": "问题文本",
            "reference_answer": "参考答案",
            "scoring_criteria": ["要点1", "要点2", "要点3"],
            "explanation": "题目考察的知识点和解题思路",
            "tags": ["标签1", "标签2"],
            "difficulty": "{difficulty}"
        }}
        """
        
        response = self.client.chat.completions.create(
            model=self.config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content)
        
        question_id = hashlib.md5(
            f"{data['question']}_{difficulty}".encode()
        ).hexdigest()[:8]
        
        return Question(
            question_id=question_id,
            question_type="short_answer",
            content=data["question"],
            options=[],  # 简答题无选项
            correct_answer=data["reference_answer"],
            explanation=data["explanation"],
            difficulty=difficulty,
            source_chunks=[chunk.text for chunk in relevant_chunks],
            tags=data.get("tags", []),
            metadata={
                "scoring_criteria": data.get("scoring_criteria", []),
                "generation_method": "llm"
            }
        )
    
    def _extract_key_concepts_for_questions(self, chunks: List[Chunk]) -> Dict:
        """提取用于生成题目的关键概念"""
        # 简化的概念提取，实际可以使用更复杂的方法
        combined = " ".join([chunk.text[:500] for chunk in chunks[:5]])
        
        prompt = f"""提取以下内容中的关键概念：
        {combined}
        
        返回重要概念列表"""
        
        response = self.client.chat.completions.create(
            model=self.config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return {"concepts": response.choices[0].message.content.split("\n")}
    
    def _select_difficulty(self, index: int, total: int) -> str:
        """根据位置选择难度，实现难度梯度"""
        if total <= 3:
            difficulties = ["easy", "medium", "hard"]
            return difficulties[min(index, 2)]
        
        # 根据索引位置分配难度
        thresholds = {
            "easy": total * 0.4,      # 前40%简单
            "medium": total * 0.7,    # 30%中等
            "hard": total             # 30%困难
        }
        
        if index < thresholds["easy"]:
            return "easy"
        elif index < thresholds["medium"]:
            return "medium"
        else:
            return "hard"
    
    def _generate_true_false(
        self,
        chunks: List[Chunk],
        key_concepts: Dict,
        difficulty: str
    ) -> Question:
        """生成真假题"""
        # 选择相关的内容块
        relevant_chunks = random.sample(chunks, min(2, len(chunks)))
        context = "\n".join([chunk.text for chunk in relevant_chunks])
        
        prompt = f"""基于以下学习内容，生成一个真假题（True/False Question）。
        
        学习内容:
        {context}
        
        难度: {difficulty}
        
        请生成一个JSON格式的真假题，包含以下字段：
        - statement: 陈述句（需要判断真假）
        - correct_answer: 正确答案（"True" 或 "False"）
        - explanation: 解释为什么这个答案是正确的
        - difficulty: 难度等级
        
        返回格式: {{"statement": "...", "correct_answer": "...", "explanation": "...", "difficulty": "{difficulty}"}}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            # 从chunks中获取source块IDs
            source_chunk_ids = [f"chunk_{i}" for i in range(len(relevant_chunks))]
            
            question = Question(
                question_id=hashlib.md5(result["statement"].encode()).hexdigest()[:12],
                question_type="true_false",
                content=result["statement"],
                options=["True", "False"],
                correct_answer=result["correct_answer"],
                explanation=result["explanation"],
                difficulty=difficulty,
                source_chunks=source_chunk_ids,
                tags=["true_false", difficulty],
                metadata={
                    "statement": result["statement"],
                    "source": "generated"
                }
            )
            
            return question
        except Exception as e:
            # 备选真假题
            fallback_statements = [
                "机器学习是人工智能的一个重要分支。",
                "所有监督学习算法都需要标记数据。",
                "过拟合发生在模型过于复杂时。",
                "准确率是评估分类模型的唯一指标。",
                "交叉验证是一种评估模型的技术。"
            ]
            
            statement = random.choice(fallback_statements)
            
            question = Question(
                question_id=hashlib.md5(statement.encode()).hexdigest()[:12],
                question_type="true_false",
                content=statement,
                options=["True", "False"],
                correct_answer="True",
                explanation="这是一个真命题。",
                difficulty=difficulty,
                source_chunks=[f"chunk_{i}" for i in range(len(relevant_chunks))],
                tags=["true_false", difficulty],
                metadata={"source": "fallback"}
            )
            
            return question
    def _generate_multiple_choice_stream(
        self,
        chunks: List[Chunk],
        key_concepts: Dict,
        difficulty: str,
        on_chunk: callable = None
    ) -> Question:
        """流式生成选择题"""
        relevant_chunks = random.sample(chunks, min(3, len(chunks)))
        context = "\n".join([chunk.text for chunk in relevant_chunks])
        
        prompt = f"""基于以下学习内容生成一道{difficulty}难度的选择题：

        学习内容：
        {context}

        要求：
        1. 问题应该测试对核心概念的理解
        2. 提供4个选项，其中一个是正确答案
        3. 错误选项应该是有迷惑性的常见误解
        4. 提供详细的解释说明为什么正确答案正确，其他选项为什么错误

        返回JSON格式：
        {{
            "question": "问题文本",
            "options": ["选项A", "选项B", "选项C", "选项D"],
            "correct_answer": "正确选项的完整文本",
            "explanation": "详细的解释",
            "tags": ["标签1", "标签2"],
            "difficulty": "{difficulty}"
        }}
        """
        
        # 使用流式API
        full_content = ""
        with self.client.chat.completions.create(
            model=self.config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
            stream=True
        ) as stream:
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    if on_chunk:
                        on_chunk(content)
        
        data = json.loads(full_content)
        
        question_id = hashlib.md5(
            f"{data['question']}_{difficulty}".encode()
        ).hexdigest()[:8]
        
        return Question(
            question_id=question_id,
            question_type="multiple_choice",
            content=data["question"],
            options=data["options"],
            correct_answer=data["correct_answer"],
            explanation=data["explanation"],
            difficulty=difficulty,
            source_chunks=[chunk.text for chunk in relevant_chunks],
            tags=data.get("tags", []),
            metadata={"generation_method": "llm_stream"}
        )
    
    def _generate_short_answer_stream(
        self,
        chunks: List[Chunk],
        key_concepts: Dict,
        difficulty: str,
        on_chunk: callable = None
    ) -> Question:
        """流式生成简答题"""
        relevant_chunks = random.sample(chunks, min(2, len(chunks)))
        context = "\n".join([chunk.text for chunk in relevant_chunks])
        
        prompt = f"""基于以下学习内容生成一道{difficulty}难度的简答题：

        学习内容：
        {context}

        要求：
        1. 问题应该测试对概念的理解和应用能力
        2. 提供参考答案要点
        3. 提供评分标准

        返回JSON格式：
        {{
            "question": "问题文本",
            "reference_answer": "参考答案",
            "scoring_criteria": ["要点1", "要点2", "要点3"],
            "explanation": "题目考察的知识点和解题思路",
            "tags": ["标签1", "标签2"],
            "difficulty": "{difficulty}"
        }}
        """
        
        # 使用流式API
        full_content = ""
        with self.client.chat.completions.create(
            model=self.config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
            stream=True
        ) as stream:
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    if on_chunk:
                        on_chunk(content)
        
        data = json.loads(full_content)
        
        question_id = hashlib.md5(
            f"{data['question']}_{difficulty}".encode()
        ).hexdigest()[:8]
        
        return Question(
            question_id=question_id,
            question_type="short_answer",
            content=data["question"],
            options=[],
            correct_answer=data["reference_answer"],
            explanation=data["explanation"],
            difficulty=difficulty,
            source_chunks=[chunk.text for chunk in relevant_chunks],
            tags=data.get("tags", []),
            metadata={
                "scoring_criteria": data.get("scoring_criteria", []),
                "generation_method": "llm_stream"
            }
        )
    
    def _generate_true_false_stream(
        self,
        chunks: List[Chunk],
        key_concepts: Dict,
        difficulty: str,
        on_chunk: callable = None
    ) -> Question:
        """流式生成真假题"""
        relevant_chunks = random.sample(chunks, min(2, len(chunks)))
        context = "\n".join([chunk.text for chunk in relevant_chunks])
        
        prompt = f"""基于以下学习内容，生成一个真假题（True/False Question）。
        
        学习内容:
        {context}
        
        难度: {difficulty}
        
        请生成一个JSON格式的真假题，包含以下字段：
        - statement: 陈述句（需要判断真假）
        - correct_answer: 正确答案（"True" 或 "False"）
        - explanation: 解释为什么这个答案是正确的
        - difficulty: 难度等级
        
        返回格式: {{"statement": "...", "correct_answer": "...", "explanation": "...", "difficulty": "{difficulty}"}}
        """
        
        try:
            # 使用流式API
            full_content = ""
            with self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"},
                stream=True
            ) as stream:
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        if on_chunk:
                            on_chunk(content)
            
            result = json.loads(full_content)
            
            source_chunk_ids = [f"chunk_{i}" for i in range(len(relevant_chunks))]
            
            question = Question(
                question_id=hashlib.md5(result["statement"].encode()).hexdigest()[:12],
                question_type="true_false",
                content=result["statement"],
                options=["True", "False"],
                correct_answer=result["correct_answer"],
                explanation=result["explanation"],
                difficulty=difficulty,
                source_chunks=source_chunk_ids,
                tags=["true_false", difficulty],
                metadata={
                    "statement": result["statement"],
                    "source": "generated_stream"
                }
            )
            
            return question
        except Exception as e:
            # 备选真假题
            fallback_statements = [
                "机器学习是人工智能的一个重要分支。",
                "所有监督学习算法都需要标记数据。",
                "过拟合发生在模型过于复杂时。",
                "准确率是评估分类模型的唯一指标。",
                "交叉验证是一种评估模型的技术。"
            ]
            
            statement = random.choice(fallback_statements)
            
            question = Question(
                question_id=hashlib.md5(statement.encode()).hexdigest()[:12],
                question_type="true_false",
                content=statement,
                options=["True", "False"],
                correct_answer="True",
                explanation="这是一个真命题。",
                difficulty=difficulty,
                source_chunks=[f"chunk_{i}" for i in range(len(relevant_chunks))],
                tags=["true_false", difficulty],
                metadata={"source": "fallback"}
            )
            
            return question