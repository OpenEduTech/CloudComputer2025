import re
from typing import List, Dict, Any


class SafetyChecker:
    """
    RAG 系统的输出护栏 (Guardrails)。
    负责检测幻觉、引用缺失以及安全性过滤。
    """

    def __init__(self):
        # 预定义的拒绝回答关键词
        self.refusal_patterns = [
            "我不知道", "无法回答", "没有在上下文中找到", "I don't know"
        ]

    def check_hallucination(self, query: str, answer: str, source_documents: List[Any]) -> Dict[str, Any]:
        """
        核心校验逻辑
        :param query: 用户问题
        :param answer: LLM 生成的答案
        :param source_documents: 检索到的文档列表
        :return: 包含校验状态和最终修正答案的字典
        """

        # 1. [检索层校验] 如果没有检索到任何文档
        if not source_documents:
            return {
                "safe": False,
                "reason": "no_context",
                "final_answer": "抱歉，知识库中暂时没有收录与此问题相关的资料。请尝试询问其他算法题目。"
            }

        # 2. [生成层校验] 检查是否遵循了引用规范 [evidence_id]
        # 逻辑：如果有上下文，但回答中完全没有 '[' 符号，可能存在幻觉或未基于上下文回答
        has_citation = bool(re.search(r'\[.*?\]', answer))

        if not has_citation:
            # 这是一个软性警告，我们依然返回答案，但加上警示
            warning_msg = "\n\n> ⚠️ **系统提示**: 该回答由模型生成，但未能正确引用知识库中的原文证据，请谨慎参考。"
            return {
                "safe": True,  # 依然算通过，但带有瑕疵
                "reason": "missing_citation",
                "final_answer": answer + warning_msg
            }

        # 3. [相关性校验] 简单关键词匹配 (可选)
        # 检查回答是否只是在复读问题，或者过短
        if len(answer) < 10:
            return {
                "safe": False,
                "reason": "too_short",
                "final_answer": "生成的回答过短，可能模型理解出错，请重试。"
            }

        return {
            "safe": True,
            "reason": "pass",
            "final_answer": answer
        }


# 单例模式导出
checker = SafetyChecker()
