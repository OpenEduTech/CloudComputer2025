import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.agents.base_agent import BaseAgent

class QuizGenerator(BaseAgent):
    def generate_comprehensive_exam(self, context_text):
        """
        生成一套包含10道题目的完整试卷
        分布：6简单 + 3中等 + 1困难
        """
        # 开发模式下返回模拟的试卷数据
        if self.llm is None:  # 开发模式下llm为None
            print("🧠 开发模式: 返回模拟试卷数据")
            return [
                {
                    "id": 1,
                    "type": "choice",
                    "difficulty": "Easy",
                    "question": "云计算的核心特性不包括以下哪一项？",
                    "options": ["A. 按需自助服务", "B. 广泛网络接入", "C. 资源池化", "D. 固定成本模型"],
                    "answer": "D",
                    "knowledge_point": "云计算基本特征"
                },
                {
                    "id": 2,
                    "type": "choice",
                    "difficulty": "Easy",
                    "question": "IaaS代表什么？",
                    "options": ["A. 基础设施即服务", "B. 平台即服务", "C. 软件即服务", "D. 数据即服务"],
                    "answer": "A",
                    "knowledge_point": "云计算服务模型"
                },
                {
                    "id": 3,
                    "type": "choice",
                    "difficulty": "Easy",
                    "question": "以下哪个不是主流的云服务提供商？",
                    "options": ["A. AWS", "B. Azure", "C. Google Cloud", "D. Alibaba Cloud", "E. Tencent Cloud", "F. IBM Cloud", "G. Oracle Cloud", "H. Microsoft Office"],
                    "answer": "H",
                    "knowledge_point": "云服务提供商"
                },
                {
                    "id": 4,
                    "type": "choice",
                    "difficulty": "Easy",
                    "question": "虚拟机技术的核心优势是什么？",
                    "options": ["A. 资源隔离", "B. 提高硬件利用率", "C. 快速部署", "D. 以上都是"],
                    "answer": "D",
                    "knowledge_point": "虚拟化技术"
                },
                {
                    "id": 5,
                    "type": "choice",
                    "difficulty": "Easy",
                    "question": "容器技术与虚拟机技术相比，最大的优势是什么？",
                    "options": ["A. 更好的隔离性", "B. 更小的资源占用", "C. 更快的启动速度", "D. B和C"],
                    "answer": "D",
                    "knowledge_point": "容器技术"
                },
                {
                    "id": 6,
                    "type": "choice",
                    "difficulty": "Easy",
                    "question": "以下哪个是容器编排工具？",
                    "options": ["A. Docker", "B. Kubernetes", "C. OpenStack", "D. VMware"],
                    "answer": "B",
                    "knowledge_point": "容器编排"
                },
                {
                    "id": 7,
                    "type": "choice",
                    "difficulty": "Medium",
                    "question": "在混合云架构中，数据如何实现安全迁移？",
                    "options": ["A. 通过专用网络连接", "B. 使用加密技术", "C. 建立数据同步机制", "D. 以上都是"],
                    "answer": "D",
                    "knowledge_point": "混合云架构"
                },
                {
                    "id": 8,
                    "type": "choice",
                    "difficulty": "Medium",
                    "question": "云原生应用的设计原则不包括以下哪一项？",
                    "options": ["A. 微服务架构", "B. 容器化部署", "C. 集中式管理", "D. DevOps实践"],
                    "answer": "C",
                    "knowledge_point": "云原生应用"
                },
                {
                    "id": 9,
                    "type": "choice",
                    "difficulty": "Medium",
                    "question": "在云环境中，如何实现高可用性？",
                    "options": ["A. 多可用区部署", "B. 负载均衡", "C. 自动扩展", "D. 以上都是"],
                    "answer": "D",
                    "knowledge_point": "云架构设计"
                },
                {
                    "id": 10,
                    "type": "short_answer",
                    "difficulty": "Hard",
                    "question": "请简述云原生应用的核心特征和优势。",
                    "answer": "云原生应用的核心特征包括：1) 微服务架构，将应用拆分为独立的服务单元；2) 容器化部署，使用Docker等容器技术实现应用的打包和运行；3) 自动化管理，通过Kubernetes等编排工具实现应用的自动部署、扩展和管理；4) DevOps实践，实现开发和运维的紧密协作和自动化流程。云原生应用的优势包括：更高的可扩展性、更好的弹性、更快的部署速度、更低的运营成本、更好的资源利用率等。",
                    "knowledge_point": "云原生架构"
                }
            ]
            
        # 如果上下文太长，稍微截断以防止 Token 溢出，但在生成10题时需要足够的信息
        if len(context_text) > 4000:
            context_text = context_text[:4000] + "..."

        prompt = ChatPromptTemplate.from_template("""
        你是一个专业的云计算课程出题专家。请基于以下[教学内容]，生成一套包含 **10道题目** 的完整试卷。
        
        [教学内容]:
        {context}
        
        [出题结构与要求]:
        请严格按照以下顺序和难度出题，并确保**题目考察的知识点尽量不重复**，覆盖面要广：
        
        1. **题目 1-6 (共6题)**: 
           - 类型: 单选题 (Choice)
           - 难度: 简单 (Easy)
           - 目标: 考察基本概念、定义和术语记忆。
           
        2. **题目 7-9 (共3题)**: 
           - 类型: 单选题 (Choice)
           - 难度: 中等 (Medium)
           - 目标: 考察概念对比、场景应用或简单计算。
           
        3. **题目 10 (共1题)**: 
           - 类型: 简答题 (Short Answer)
           - 难度: 困难 (Hard)
           - 目标: 考察综合理解、架构设计或优缺点深度分析。
        
        [输出格式]:
        请严格返回一个包含10个对象的JSON数组，不要包含Markdown代码块标记(```json)，直接输出JSON字符串。格式范例：
        [
            {{
                "id": 1,
                "type": "choice",
                "difficulty": "Easy",
                "question": "云计算的哪个特性...",
                "options": ["A. 按需自助", "B. 广泛网络接入", "C. ...", "D. ..."],
                "answer": "A",
                "knowledge_point": "云计算特征"
            }},
            ...
            {{
                "id": 10,
                "type": "short_answer",
                "difficulty": "Hard",
                "question": "请阐述...",
                "answer": "核心要点包括...",
                "knowledge_point": "架构设计"
            }}
        ]
        """)
        
        chain = prompt | self.llm | StrOutputParser()
        print("🧠 Agent 正在生成 10 道题目 (6简/3中/1难)...")
        
        try:
            response = chain.invoke({"context": context_text})
            # 数据清洗
            clean_json = response.replace("```json", "").replace("```", "").strip()
            quiz_list = json.loads(clean_json)
            
            # 简单的校验，确保生成了列表
            if isinstance(quiz_list, list):
                print(f"✅ 成功生成 {len(quiz_list)} 道题目")
                return quiz_list
            else:
                print("❌ 生成格式错误: 不是列表")
                return []
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            print(f"原始返回片段: {response[:200]}...")
            return []
        except Exception as e:
            print(f"❌ 试卷生成未知错误: {e}")
            return []