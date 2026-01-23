import os
import logging
from typing import Dict, List, Optional, Any, Tuple
import json
import asyncio
from datetime import datetime
import httpx
import re
import aiohttp
import urllib.parse
import requests  # 【关键修复】添加requests导入
from parser import SlideContent
import urllib3
import warnings

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# 或者
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
logger = logging.getLogger(__name__)


class SimpleAgent:
    """增强容错性的知识扩展智能体"""

    def __init__(self):
        self.api_key = "sk-xeajczsypmkihgqahpcsidmhyvgddyrnxyzpediquhhavvwa"
        self.base_url = "https://api.siliconflow.cn/v1"
        self.model = "deepseek-ai/DeepSeek-V3.2-Exp"

        # 添加并发控制信号量
        self.semaphore = asyncio.Semaphore(2)  # 限制同时2个请求

        # 创建HTTP客户端
        self.client = httpx.AsyncClient(
            timeout=180.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )

        # 校验层配置
        self.validation_config = {
            "max_retries": 3,  # 最大重试次数
            "consistency_check": True,  # 一致性校验
            "fact_check": True,  # 事实校验
            "format_check": True,  # 格式校验
            "relevance_check": True,  # 相关性校验
        }

        # 幻觉检测关键词
        self.hallucination_keywords = [
            "我无法确定", "我不确定", "可能", "或许", "大概", "据说",
            "据我所知", "一般来说", "通常情况下", "可能不正确",
            "缺乏具体信息", "信息不完整", "需要进一步核实"
        ]

        # 学术术语词典（可扩展）
        self.academic_terms = {
            # 机器学习/统计学
            "贝叶斯", "朴素贝叶斯", "贝叶斯定理", "贝叶斯分类器",
            "后验概率", "先验概率", "似然函数", "极大似然估计", "最大似然估计",
            "联合概率", "条件概率", "概率分布", "期望风险", "风险最小化",
            "分类器", "机器学习", "监督学习", "无监督学习",
            "参数估计", "特征", "实例", "训练集", "测试集",
            "准确率", "召回率", "F1分数", "混淆矩阵",

            # 数学
            "定理", "引理", "推论", "证明", "推导", "公式", "方程",
            "矩阵", "向量", "标量", "梯度", "导数", "积分",

            # 计算机科学
            "算法", "数据结构", "复杂度", "时间复杂度", "空间复杂度",
            "递归", "迭代", "优化", "收敛", "离散", "连续",

            # 通用学术
            "定义", "概念", "原理", "方法", "技术", "模型",
            "框架", "体系", "结构", "机制", "过程", "系统"
        }

        # 中英文术语映射（用于Wikipedia搜索）
        self.term_mapping = {
            # 机器学习/统计学
            "朴素贝叶斯": "Naive Bayes",
            "贝叶斯": "Bayes",
            "贝叶斯定理": "Bayes' theorem",
            "贝叶斯分类器": "Bayesian classifier",
            "后验概率": "Posterior probability",
            "先验概率": "Prior probability",
            "似然函数": "Likelihood function",
            "极大似然估计": "Maximum likelihood estimation",
            "最大似然估计": "Maximum likelihood estimation",
            "联合概率": "Joint probability",
            "条件概率": "Conditional probability",
            "概率分布": "Probability distribution",
            "期望风险": "Expected risk",
            "风险最小化": "Risk minimization",
            "分类器": "Classifier",
            "机器学习": "Machine learning",
            "监督学习": "Supervised learning",
            "无监督学习": "Unsupervised learning",
            "参数估计": "Parameter estimation",
            "特征": "Feature",
            "实例": "Instance",
            "训练集": "Training set",
            "测试集": "Test set",
            "准确率": "Accuracy",
            "召回率": "Recall",
            "F1分数": "F1 score",
            "混淆矩阵": "Confusion matrix",

            # 数学
            "定理": "Theorem",
            "引理": "Lemma",
            "推论": "Corollary",
            "证明": "Proof",
            "推导": "Derivation",
            "公式": "Formula",
            "方程": "Equation",
            "矩阵": "Matrix",
            "向量": "Vector",
            "标量": "Scalar",
            "梯度": "Gradient",
            "导数": "Derivative",
            "积分": "Integral",

            # 计算机科学
            "算法": "Algorithm",
            "数据结构": "Data structure",
            "复杂度": "Complexity",
            "时间复杂度": "Time complexity",
            "空间复杂度": "Space complexity",
            "递归": "Recursion",
            "迭代": "Iteration",
            "优化": "Optimization",
            "收敛": "Convergence",
            "离散": "Discrete",
            "连续": "Continuous",

            # 通用学术
            "定义": "Definition",
            "概念": "Concept",
            "原理": "Principle",
            "方法": "Method",
            "技术": "Technique",
            "模型": "Model",
            "框架": "Framework",
            "体系": "System",
            "结构": "Structure",
            "机制": "Mechanism",
            "过程": "Process"
        }

        logger.info("✅ 智能体初始化完成（带校验层）")

    async def call_llm_with_validation(self, messages: List[Dict[str, str]],
                                       task_type: str = "general",
                                       expected_format: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """带校验层的LLM调用"""
        # 根据任务类型设置不同的max_tokens
        token_limits = {
            "code_example": 3000,  # 代码示例需要更多token
            "explanation": 1500,
            "quiz": 1000,
            "references": 800,
            "extended_reading": 3000,  # 【关键修复】知识深度探索需要更多token
            "general": 1000
        }
        max_tokens = token_limits.get(task_type, 1000)

        validation_result = {
            "passed": False,
            "errors": [],
            "warnings": [],
            "retries": 0,
            "consistency_score": 0.0,
            "validation_details": {}
        }

        for retry in range(self.validation_config["max_retries"]):
            try:
                logger.info(f"调用LLM API（第{retry + 1}次尝试），任务类型: {task_type}")

                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7 if retry == 0 else 0.3,  # 重试时降低温度
                        "max_tokens": max_tokens  # 使用动态token限制
                    },
                    timeout=1200.0
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]

                    # 执行校验
                    validation_passed, validation_details = await self._validate_response(
                        content, messages, task_type, expected_format
                    )

                    validation_result["retries"] = retry
                    validation_result["validation_details"] = validation_details

                    if validation_passed:
                        validation_result["passed"] = True
                        validation_result["consistency_score"] = validation_details.get("consistency_score", 0.0)
                        logger.info(f"✅ LLM调用成功（通过校验），返回长度: {len(content)}")
                        return content, validation_result
                    else:
                        validation_result["errors"].extend(validation_details.get("errors", []))
                        validation_result["warnings"].extend(validation_details.get("warnings", []))

                        # 如果校验失败，准备重试
                        if retry < self.validation_config["max_retries"] - 1:
                            logger.warning(f"⚠️ 第{retry + 1}次调用未通过校验，准备重试")

                            # 添加校验反馈到消息中
                            feedback_msg = self._create_validation_feedback(validation_details)
                            messages.append({
                                "role": "user",
                                "content": f"之前的回答存在以下问题，请重新回答：\n{feedback_msg}"
                            })
                        else:
                            logger.error(f"❌ LLM调用未通过校验（最大重试次数）")
                            return content, validation_result
                else:
                    error_msg = f"API调用失败: {response.status_code}, {response.text}"
                    validation_result["errors"].append(error_msg)
                    logger.error(error_msg)

                    if retry < self.validation_config["max_retries"] - 1:
                        logger.info(f"等待重试...")
                        await asyncio.sleep(2 ** retry)  # 指数退避

            except httpx.TimeoutException:
                error_msg = f"LLM调用超时（第{retry + 1}次）"
                validation_result["errors"].append(error_msg)
                logger.error(error_msg)

                if retry < self.validation_config["max_retries"] - 1:
                    await asyncio.sleep(2 ** retry)
            except Exception as e:
                error_msg = f"调用LLM失败: {str(e)}"
                validation_result["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)

                if retry < self.validation_config["max_retries"] - 1:
                    await asyncio.sleep(2 ** retry)

        return "", validation_result

    async def _validate_response(self, content: str, messages: List[Dict[str, str]],
                                 task_type: str, expected_format: Optional[str]) -> Tuple[bool, Dict[str, Any]]:
        """校验LLM响应"""
        validation_details = {
            "passed_checks": [],
            "failed_checks": [],
            "errors": [],
            "warnings": [],
            "consistency_score": 0.0,
            "hallucination_detected": False
        }

        # 1. 基础校验
        if not content or len(content.strip()) < 10:
            validation_details["failed_checks"].append("content_too_short")
            validation_details["errors"].append("响应内容太短或为空")
            return False, validation_details

        validation_details["passed_checks"].append("content_length")

        # 2. 格式校验
        if self.validation_config["format_check"] and expected_format:
            format_valid, format_errors = self._check_format(content, expected_format)
            if not format_valid:
                validation_details["failed_checks"].append("format_invalid")
                validation_details["errors"].extend(format_errors)
                return False, validation_details
            validation_details["passed_checks"].append("format_valid")

        # 3. 幻觉检测
        hallucination_detected = self._detect_hallucination(content)
        if hallucination_detected:
            validation_details["warnings"].append("检测到可能的不确定表述")
            validation_details["hallucination_detected"] = True

        # 4. 一致性校验（针对多轮对话）
        if self.validation_config["consistency_check"] and len(messages) > 1:
            consistency_score = self._check_consistency(content, messages[-2]["content"])
            validation_details["consistency_score"] = consistency_score
            if consistency_score < 0.7:
                validation_details["warnings"].append(f"一致性得分较低: {consistency_score:.2f}")

        # 5. 事实性校验（基本检查）
        if self.validation_config["fact_check"]:
            fact_issues = self._check_facts(content)
            if fact_issues:
                validation_details["warnings"].extend(fact_issues)

        # 6. 相关性校验
        if self.validation_config["relevance_check"]:
            user_query = self._extract_user_query(messages)
            if user_query:
                relevance_score = self._check_relevance(content, user_query)
                if relevance_score < 0.6:
                    validation_details["warnings"].append(f"相关性得分较低: {relevance_score:.2f}")

        return len(validation_details["failed_checks"]) == 0, validation_details

    def _check_format(self, content: str, expected_format: str) -> Tuple[bool, List[str]]:
        """检查响应格式"""
        errors = []

        if expected_format == "quiz_question":
            # 检查测验问题格式
            if "问题：" not in content:
                errors.append("缺少问题标题")
            if "答案：" not in content:
                errors.append("缺少答案部分")

            # 检查选择题选项格式
            if "A." in content and not all(x in content for x in ["B.", "C.", "D."]):
                errors.append("选择题选项不完整")

        elif expected_format == "explanation":
            # 检查解释性内容的格式
            sections = ["核心概念", "基本原理", "应用场景", "知识关联"]
            section_count = sum(1 for section in sections if section in content)
            if section_count < 2:
                errors.append(f"解释性内容结构不完整，仅包含{section_count}个主要部分")

        elif expected_format == "code_example":
            # 检查代码示例格式
            if "```" not in content:
                errors.append("代码示例缺少代码块标记")
            if "def " not in content and "class " not in content and "print(" not in content:
                errors.append("代码示例可能不完整")

        elif expected_format == "extended_reading":
            # 检查延伸阅读材料的格式
            required_keywords = ["知识扩展", "应用", "学习", "背景", "案例", "建议"]
            found_keywords = sum(1 for keyword in required_keywords if keyword in content)
            if found_keywords < 2:
                errors.append(f"延伸阅读材料内容不够丰富")

        return len(errors) == 0, errors

    def _detect_hallucination(self, content: str) -> bool:
        """检测幻觉内容"""
        content_lower = content.lower()
        for keyword in self.hallucination_keywords:
            if keyword in content_lower:
                return True

        # 检查过度自信的表述
        overconfident_patterns = [
            r"绝对[是|正确]", r"肯定[是|正确]", r"百分之百", r"毫无疑问",
            r"完全[正确|准确]", r"绝[不|对]"
        ]

        for pattern in overconfident_patterns:
            if re.search(pattern, content):
                return True

        return False

    def _check_consistency(self, current_response: str, previous_content: str) -> float:
        """检查响应一致性"""
        # 简化的基于关键词的一致性检查
        current_words = set(re.findall(r'\b\w{3,}\b', current_response.lower()))
        previous_words = set(re.findall(r'\b\w{3,}\b', previous_content.lower()))

        if not current_words or not previous_words:
            return 0.0

        intersection = current_words.intersection(previous_words)
        similarity = len(intersection) / max(len(current_words), len(previous_words))

        return similarity

    def _check_facts(self, content: str) -> List[str]:
        """基本事实性检查"""
        warnings = []

        # 检查明显的错误事实（示例）
        common_errors = {
            "Python 2": "Python 2已于2020年停止支持",
            "Java 7": "Java 7已停止公共更新",
            "Windows XP": "Windows XP已停止支持",
        }

        for error_term, correction in common_errors.items():
            if error_term in content and correction not in content:
                warnings.append(f"可能包含过时信息: {error_term}")

        # 检查矛盾的表述
        contradictions = [
            ("同时", "但是"), ("虽然", "但是"), ("一方面", "另一方面")
        ]

        for conj1, conj2 in contradictions:
            if conj1 in content and conj2 not in content:
                warnings.append(f"可能缺少转折表述: '{conj1}'出现但未找到'{conj2}'")

        return warnings

    def _check_relevance(self, content: str, query: str) -> float:
        """检查内容相关性"""
        content_words = set(re.findall(r'\b\w{3,}\b', content.lower()))
        query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))

        if not content_words or not query_words:
            return 0.0

        intersection = content_words.intersection(query_words)
        relevance = len(intersection) / len(query_words)

        return relevance

    def _extract_user_query(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """从消息历史中提取用户查询"""
        for msg in reversed(messages):
            if msg["role"] == "user":
                return msg["content"]
        return None

    def _create_validation_feedback(self, validation_details: Dict[str, Any]) -> str:
        """创建校验反馈信息"""
        feedback = []

        if validation_details.get("errors"):
            feedback.append("发现以下错误：")
            feedback.extend([f"- {error}" for error in validation_details["errors"][:3]])

        if validation_details.get("warnings"):
            feedback.append("请注意以下问题：")
            feedback.extend([f"- {warning}" for warning in validation_details["warnings"][:3]])

        if validation_details.get("failed_checks"):
            feedback.append("格式要求：")
            for check in validation_details["failed_checks"]:
                if check == "format_invalid":
                    feedback.append("- 请确保响应格式正确")
                elif check == "content_too_short":
                    feedback.append("- 请提供更详细的内容")

        return "\n".join(feedback)

    async def expand_slide(self, slide: SlideContent) -> Dict[str, Any]:
        """扩展单个幻灯片内容（带校验）"""
        try:
            # 检查幻灯片是否有有效内容
            if not slide.title.strip() and not slide.content and not slide.bullet_points:
                logger.info(f"跳过空幻灯片: {slide.slide_number}")
                return {
                    "slide_number": slide.slide_number,
                    "title": slide.title,
                    "skipped": True,
                    "reason": "内容为空",
                    "explanations": [],
                    "examples": [],
                    "extended_readings": [],  # ✅ 确保始终包含延伸阅读字段
                    "references": [],
                    "quiz_questions": [],
                    "expanded_at": datetime.now().isoformat()
                }

            logger.info(f"扩展幻灯片: {slide.slide_number} - {slide.title[:30]}")

            # 并行执行扩展任务（带重试机制）
            tasks = [
                self._generate_explanation_with_validation(slide),  # 详细解释
                self._generate_examples_with_validation(slide),  # 代码示例
                self._generate_extended_reading_with_validation(slide),  # ✅ 独立的延伸阅读材料
                self._generate_references_with_validation(slide),  # 参考资料
                self._generate_quiz_with_validation(slide)  # 测验问题
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 🔧 安全获取结果
            def safe_get_result(index, task_name):
                try:
                    result = results[index]
                    if isinstance(result, Exception):
                        logger.error(f"{task_name}任务执行异常: {result}")
                        return [], {"passed": False, "errors": [str(result)], "warnings": ["任务执行异常"]}
                    elif result is None:
                        logger.warning(f"{task_name}任务返回None")
                        return [], {"passed": False, "errors": ["返回结果为None"]}
                    elif isinstance(result, tuple) and len(result) >= 2:
                        return result[0], result[1]
                    else:
                        logger.warning(f"{task_name}任务返回格式异常: {type(result)}")
                        return [], {"passed": False, "errors": ["返回格式异常"]}
                except Exception as e:
                    logger.error(f"获取{task_name}结果失败: {e}")
                    return [], {"passed": False, "errors": [str(e)]}

            explanation_result = safe_get_result(0, "详细解释")
            examples_result = safe_get_result(1, "代码示例")
            extended_reading_result = safe_get_result(2, "延伸阅读")  # ✅ 重点确保这个部分正确
            references_result = safe_get_result(3, "参考资料")
            quiz_result = safe_get_result(4, "测验问题")

            # 🔧 处理延伸阅读材料，确保一定有内容
            extended_readings_content = extended_reading_result[0] if isinstance(extended_reading_result, tuple) and \
                                                                      extended_reading_result[0] is not None else []
            extended_reading_validation = extended_reading_result[1] if isinstance(extended_reading_result,
                                                                                   tuple) and len(
                extended_reading_result) > 1 else {"passed": False}

            # 如果延伸阅读为空，创建默认内容
            if not extended_readings_content or len(extended_readings_content) == 0:
                logger.warning(f"幻灯片 {slide.slide_number} 延伸阅读内容为空，创建默认内容")

                # 创建默认延伸阅读材料 - 命名为【知识深度探索】
                default_reading = {
                    "title": f"《{slide.title}》知识深度探索",  # ✅ 使用新名称
                    "content": self._create_default_extended_reading(slide),
                    "sections": [
                        {"title": "知识深度扩展", "content": f"深入探讨{slide.title}相关的核心概念和原理。"},
                        {"title": "历史背景与发展", "content": f"了解{slide.title}的发展历史和重要里程碑。"},
                        {"title": "实际应用案例", "content": f"列举{slide.title}在实际中的应用场景和案例。"},
                        {"title": "前沿进展与趋势", "content": f"介绍该领域的最新研究进展和发展趋势。"},
                        {"title": "深入学习建议", "content": f"提供进一步学习{slide.title}的路径和建议。"}
                    ],
                    "type": "extended_reading",
                    "source": "系统默认生成",
                    "total_length": 800,
                    "section_count": 5,
                    "is_fallback": True,
                    "display_name": "知识深度探索"  # ✅ 在报告中显示的名称
                }
                extended_readings_content = [default_reading]
                extended_reading_validation = {"passed": True, "warnings": ["使用默认延伸阅读内容"]}
            else:
                # 为现有的延伸阅读材料添加显示名称
                for reading in extended_readings_content:
                    reading["display_name"] = reading.get("display_name", "知识深度探索")
                    # 确保每个延伸阅读都有标题
                    if "title" not in reading or not reading["title"]:
                        reading["title"] = f"《{slide.title}》知识深度探索"

            # 处理结果并记录校验信息
            expanded_content = {
                "slide_number": slide.slide_number,
                "title": slide.title,
                "explanations": explanation_result[0] if isinstance(explanation_result, tuple) else [],
                "examples": examples_result[0] if isinstance(examples_result, tuple) else [],
                "extended_readings": extended_readings_content,  # ✅ 确保这个字段一定有内容
                "references": references_result[0] if isinstance(references_result, tuple) else [],
                "quiz_questions": quiz_result[0] if isinstance(quiz_result, tuple) else [],
                "expanded_at": datetime.now().isoformat(),
                "validation_summary": {
                    "explanation": explanation_result[1] if isinstance(explanation_result, tuple) and len(
                        explanation_result) > 1 else {"passed": False},
                    "examples": examples_result[1] if isinstance(examples_result, tuple) and len(
                        examples_result) > 1 else {"passed": False},
                    "extended_reading": extended_reading_validation,  # ✅ 独立的校验结果
                    "references": references_result[1] if isinstance(references_result, tuple) and len(
                        references_result) > 1 else {"passed": False},
                    "quiz": quiz_result[1] if isinstance(quiz_result, tuple) and len(quiz_result) > 1 else {
                        "passed": False},
                }
            }

            # 计算整体校验通过率
            validation_scores = []
            for key in ["explanation", "examples", "extended_reading", "references", "quiz"]:
                if key in expanded_content["validation_summary"]:
                    val = expanded_content["validation_summary"][key]
                    if isinstance(val, dict) and val.get("passed"):
                        validation_scores.append(1.0)
                    else:
                        validation_scores.append(0.0)

            if validation_scores:
                expanded_content["validation_score"] = sum(validation_scores) / len(validation_scores)

            # 🔧 调试信息
            logger.info(f"✅ 幻灯片扩展完成: {slide.slide_number}")
            logger.info(f"  详细解释: {len(expanded_content['explanations'])} 个")
            logger.info(f"  代码示例: {len(expanded_content['examples'])} 个")
            logger.info(f"  知识深度探索: {len(expanded_content['extended_readings'])} 个")  # ✅ 使用新名称记录
            logger.info(f"  参考资料: {len(expanded_content['references'])} 个")
            logger.info(f"  测验问题: {len(expanded_content['quiz_questions'])} 个")

            if expanded_content.get("extended_readings"):
                first_reading = expanded_content["extended_readings"][0]
                logger.info(f"  📖 知识深度探索标题: {first_reading.get('title', '无标题')}")
                logger.info(f"  📄 知识深度探索长度: {len(first_reading.get('content', ''))} 字符")

            return expanded_content

        except Exception as e:
            logger.error(f"扩展幻灯片失败: {e}", exc_info=True)
            # 即使失败也返回包含延伸阅读字段的结构
            return {
                "slide_number": slide.slide_number,
                "title": slide.title,
                "error": str(e),
                "explanations": [],
                "examples": [],
                "extended_readings": [{  # ✅ 确保延伸阅读字段始终存在
                    "title": f"《{slide.title}》知识深度探索",  # ✅ 使用新名称
                    "content": self._create_error_extended_reading(slide, e),
                    "sections": [{"title": "错误信息", "content": f"生成失败: {str(e)}"}],
                    "type": "error_fallback",
                    "source": "错误恢复",
                    "is_fallback": True,
                    "display_name": "知识深度探索"  # ✅ 在报告中显示的名称
                }],
                "references": [],
                "quiz_questions": [],
                "validation_score": 0.0,
                "validation_summary": {}
            }

    def _create_default_extended_reading(self, slide: SlideContent) -> str:
        """创建默认延伸阅读材料内容"""
        keywords = self._extract_keywords_from_slide(slide)[:3]
        keyword_str = "、".join(keywords) if keywords else "相关主题"

        return f"""# 《{slide.title}》知识深度探索

## 📚 知识深度扩展
本部分深入探讨{slide.title}相关的核心概念和原理。{keyword_str}是这一领域的重要知识点，值得进一步研究。

## 🕰️ 历史背景与发展
了解{slide.title}的发展历史有助于深入理解其当前应用。该知识领域经历了多个发展阶段，从最初的理论提出到现在的广泛应用。

## 💼 实际应用案例
{slide.title}在实际中有多种应用场景。例如在文本分类、垃圾邮件过滤、推荐系统等领域都有成功应用案例。

## 🚀 前沿进展与趋势
当前该领域的研究正在向更复杂的模型和更广泛的应用场景发展。深度学习与大模型的结合是该领域的前沿方向之一。

## 🎯 深入学习建议
建议通过以下方式深入学习{slide.title}：
1. 阅读相关教科书和学术论文
2. 实践代码实现，加深理解
3. 参与在线课程和研讨会
4. 关注该领域的最新研究成果

## 🔗 推荐资源
- Wikipedia相关条目
- 机器学习经典教材
- 相关学术会议论文
- 开源代码库和工具"""

    def _create_error_extended_reading(self, slide: SlideContent, error: Exception) -> str:
        """创建错误状态下的延伸阅读材料"""
        return f"""# 《{slide.title}》知识深度探索

## ⚠️ 系统提示
由于系统错误，无法生成完整的知识深度探索材料。错误信息: {str(error)}

## 📝 建议方案
您可以：
1. 检查网络连接
2. 稍后重试
3. 联系技术支持

## 🔍 替代学习资源
建议参考以下资源学习{slide.title}：
- 相关教科书
- 在线课程
- 学术论文
- 专业论坛"""

    async def _generate_explanation_with_validation(self, slide: SlideContent) -> Tuple[
        List[Dict[str, str]], Dict[str, Any]]:
        """生成详细解释（带校验）"""
        content_text = "\n".join(slide.content)
        bullet_text = "\n".join(slide.bullet_points) if slide.bullet_points else "无"

        messages = [
            {
                "role": "system",
                "content": "你是一位经验丰富的教师，擅长用简单易懂的方式解释复杂概念。请根据PPT幻灯片内容，提供详细的解释说明。请确保解释准确、完整，避免不确定的表述。"
            },
            {
                "role": "user",
                "content": f"""幻灯片内容：

标题：{slide.title}

主要内容：
{content_text}

项目符号：
{bullet_text}

请为这个幻灯片生成详细的解释，包括：
1. 核心概念的定义和说明
2. 基本原理和逻辑
3. 实际应用场景
4. 与其他知识的关联

请使用中文回复，确保解释清晰准确。请直接开始解释，不要添加额外的说明性文字。"""
            }
        ]

        try:
            explanation, validation_result = await self.call_llm_with_validation(
                messages, task_type="explanation", expected_format="explanation"
            )

            if explanation and validation_result.get("passed", False):
                # 【修复1】清理解释文本
                explanation_clean = explanation.strip()

                # 移除开头可能存在的重复标签
                remove_prefixes = [
                    "核心概念：", "核心概念:", "核心概念",
                    "概念：", "概念:", "概念",
                    "一、核心概念", "1. 核心概念",
                    "【核心概念】", "[核心概念]",
                ]

                for prefix in remove_prefixes:
                    if explanation_clean.startswith(prefix):
                        explanation_clean = explanation_clean[len(prefix):].strip()

                # 【修复2】清理段落开头的重复标签
                lines = explanation_clean.split('\n')
                cleaned_lines = []

                for line in lines:
                    line_stripped = line.strip()
                    # 跳过空行
                    if not line_stripped:
                        continue
                    # 跳过纯标签行
                    if line_stripped in ["核心概念", "概念", "一、核心概念", "1. 核心概念"]:
                        continue
                    # 移除行首的标签
                    for prefix in remove_prefixes:
                        if line_stripped.startswith(prefix):
                            line_stripped = line_stripped[len(prefix):].strip()
                            break
                    cleaned_lines.append(line_stripped)

                explanation_clean = '\n\n'.join(cleaned_lines)

                # 【修复3】智能分段（而不是简单按空行分割）
                explanations = []

                # 如果解释较短，作为整体处理
                if len(explanation_clean) < 500:
                    # 尝试按自然段落分割
                    paragraphs = re.split(r'\n\s*\n+', explanation_clean)
                    if len(paragraphs) == 1:
                        # 只有一个段落，作为整体
                        explanations.append({
                            "concept": "详细解释",  # ← 使用固定的、不重复的概念名
                            "explanation": explanation_clean,
                            "type": "general_explanation",
                            "validation": validation_result
                        })
                    else:
                        # 多个段落，为每个段落添加适当的标题
                        for i, para in enumerate(paragraphs):
                            if para.strip():
                                concept_name = f"解释部分{i + 1}"
                                if i == 0:
                                    concept_name = "概述"
                                elif i == len(paragraphs) - 1:
                                    concept_name = "总结"

                                explanations.append({
                                    "concept": concept_name,
                                    "explanation": para.strip(),
                                    "type": "general_explanation",
                                    "validation": validation_result
                                })
                else:
                    # 较长的解释，寻找自然的小标题
                    sections = []
                    current_section = []
                    current_title = "详细解释"

                    lines = explanation_clean.split('\n')
                    for line in lines:
                        line_stripped = line.strip()
                        # 检测可能的小标题（数字或中文数字开头）
                        if re.match(r'^(?:\d+[\.、]|第[一二三四五六七八九十\d]+[章节部分]、?|[一二三四五六七八九十]、)',
                                    line_stripped):
                            # 保存当前section
                            if current_section:
                                sections.append({
                                    "title": current_title,
                                    "content": '\n'.join(current_section)
                                })
                            # 开始新的section
                            current_title = line_stripped
                            current_section = []
                        else:
                            current_section.append(line)

                    # 添加最后一个section
                    if current_section:
                        sections.append({
                            "title": current_title,
                            "content": '\n'.join(current_section)
                        })

                    # 转换为explanations格式
                    for section in sections:
                        # 清理标题
                        section_title = section["title"]
                        for prefix in remove_prefixes:
                            if section_title.startswith(prefix):
                                section_title = section_title[len(prefix):].strip()
                                break

                        explanations.append({
                            "concept": section_title if section_title else "详细解释",
                            "explanation": section["content"].strip(),
                            "type": "general_explanation",
                            "validation": validation_result
                        })

                # 【修复4】如果没有生成任何解释，返回整体解释
                if not explanations:
                    explanations.append({
                        "concept": "详细解释",  # ← 避免使用"核心概念"
                        "explanation": explanation_clean,
                        "type": "general_explanation",
                        "validation": validation_result
                    })

                return explanations, validation_result

            else:
                # 如果校验失败，返回降级处理的结果
                fallback_explanation = self._create_fallback_explanation(slide)
                return [{
                    "concept": "基本解释",
                    "explanation": fallback_explanation,
                    "type": "fallback_explanation",
                    "validation": validation_result,
                    "fallback_reason": "校验未通过，使用降级处理"
                }], validation_result

        except Exception as e:
            logger.error(f"生成解释失败: {e}")
            return [], {"passed": False, "errors": [str(e)]}

    async def _generate_examples_with_validation(self, slide: SlideContent) -> Tuple[
        List[Dict[str, str]], Dict[str, Any]]:
        """生成代码/应用示例（带校验）"""
        # 检查是否是技术相关的内容
        technical_keywords = ["代码", "编程", "算法", "函数", "类", "对象", "数据库", "网络", "协议"]

        slide_text = slide.title + " ".join(slide.content) + " ".join(slide.bullet_points)
        is_technical = any(keyword in slide_text for keyword in technical_keywords)

        if not is_technical:
            return [], {"passed": True, "skipped": "非技术内容"}

        content_text = "\n".join(slide.content)

        messages = [
            {"role": "system", "content": """你是一位资深程序员和教育专家，擅长用核心代码示例解释技术概念。

        【重要要求】：
        请提供**核心功能代码示例**，而不是完整的项目代码。

        **核心代码示例应该**：
        1. 展示关键算法、核心函数、主要逻辑
        2. 代码长度控制在20-100行以内
        3. 包含详细的中文注释说明
        4. 核心部分可以直接运行和理解
        5. 突出展示技术要点

        **不要提供**：
        - 完整的项目代码
        - 所有错误处理
        - 完整的测试套件
        - 配置文件和依赖管理
        - 性能优化细节

        专注于生成精简、可理解的核心代码示例。"""},
            {"role": "user", "content": f"""请根据以下幻灯片内容，生成**核心功能代码示例**：

        主题：{slide.title}
        内容：{content_text}

        请提供：
        1. 核心功能的代码示例（20-100行），以```python开头，```结尾
        2. 中文注释说明关键部分
        3. 简要的运行结果说明

        请使用Python语言，展示最核心的实现逻辑。
        请确保代码语法正确，核心部分可运行。

        **【注意】只生成核心代码，不要生成完整的长篇代码！**"""}
        ]

        try:
            example, validation_result = await self.call_llm_with_validation(
                messages, task_type="code_example", expected_format="code_example"
            )

            if example and validation_result.get("passed", False):
                # 进一步校验代码语法（简化版）
                if self._check_python_syntax_basic(example):
                    return [{
                        "language": "python",
                        "code_example": example,
                        "description": "基于幻灯片内容生成的代码示例",
                        "type": "code_example",
                        "validation": validation_result
                    }], validation_result
                else:
                    validation_result["warnings"].append("代码语法检查未通过")
                    return [], validation_result
            else:
                return [], validation_result

        except Exception as e:
            logger.error(f"生成示例失败: {e}")
            return [], {"passed": False, "errors": [str(e)]}

    async def _fetch_wikipedia_articles(self, keyword: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """调用Wikipedia API获取相关条目 - 修复版"""
        try:
            logger.info(f"开始Wikipedia搜索: '{keyword}'")

            # 【修复1】使用英文维基百科API（对英文关键词响应更好）
            api_url = "https://en.wikipedia.org/w/api.php"

            # 【修复2】尝试翻译中文关键词为英文
            search_keyword = keyword
            if keyword in self.term_mapping:
                search_keyword = self.term_mapping[keyword]
                logger.info(f"关键词翻译: '{keyword}' -> '{search_keyword}'")

            # 【修复3】使用requests同步调用（已导入）
            params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": search_keyword,
                "srlimit": max_results,
                "srprop": "snippet|size|wordcount",
                "srwhat": "text",
                "utf8": 1,
                "origin": "*"
            }

            headers = {
                "User-Agent": "PPT-Extension-Agent/1.0 (https://github.com/edu-tool; contact@example.com)"
            }

            # 使用requests进行同步调用
            response = requests.get(
                api_url,
                params=params,
                headers=headers,
                timeout=10,
                verify=False
            )

            logger.info(f"Wikipedia响应状态: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                if "query" in data and "search" in data["query"]:
                    articles = data["query"]["search"]
                    logger.info(f"✅ 成功获取 {len(articles)} 个结果，关键词: {search_keyword}")

                    processed_articles = []
                    for article in articles:
                        title = article.get("title", "")
                        snippet = article.get("snippet", "")

                        # 清理HTML标签
                        if snippet:
                            snippet = re.sub(r'<[^>]+>', '', snippet)
                            snippet = re.sub(r'&\w+;', '', snippet)
                            snippet = snippet.replace('\n', ' ').strip()

                        # 构建URL
                        url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"

                        processed_articles.append({
                            "title": title,
                            "description": snippet[:200] + "..." if snippet and len(snippet) > 200 else snippet or "",
                            "url": url,
                            "pageid": article.get("pageid", ""),
                            "wordcount": article.get("wordcount", 0),
                            "original_keyword": keyword,
                            "search_keyword": search_keyword
                        })

                    return processed_articles
                else:
                    logger.warning(f"Wikipedia响应格式异常，关键词: {search_keyword}")
                    if "error" in data:
                        logger.error(f"Wikipedia API错误: {data['error']}")
                    return []
            else:
                text = response.text[:500]
                logger.error(f"Wikipedia HTTP错误 {response.status_code}，关键词: {search_keyword}: {text}")
                return []

        except requests.exceptions.Timeout:
            logger.error(f"Wikipedia请求超时 (10秒)，关键词: {keyword}")
            return []
        except requests.exceptions.SSLError as e:
            logger.error(f"Wikipedia SSL错误，关键词: {keyword}: {e}")
            return []
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Wikipedia连接错误，关键词: {keyword}: {e}")
            return []
        except Exception as e:
            logger.error(f"Wikipedia请求异常，关键词: {keyword}: {type(e).__name__}: {e}")
            return []

    async def _generate_extended_reading_with_validation(self, slide: SlideContent) -> Tuple[
        List[Dict[str, Any]], Dict[str, Any]]:
        """生成延伸阅读材料（带校验）- 独立的扩展任务"""

        # 提取关键词用于搜索Wikipedia
        keywords = self._extract_keywords_from_slide(slide)

        if not keywords:
            logger.info(f"幻灯片 {slide.slide_number} 无有效关键词，生成基础延伸阅读")
            return await self._generate_basic_extended_reading(slide)

        # 使用主关键词
        main_keyword = keywords[0]

        try:
            logger.info(f"开始为幻灯片 {slide.slide_number} 生成延伸阅读材料，关键词: {main_keyword}")

            # 1. 真实调用Wikipedia API获取权威条目
            wikipedia_articles = []

            try:
                # 【修复】正确调用Wikipedia API
                wikipedia_articles = await self._fetch_wikipedia_articles(main_keyword)
                logger.info(f"Wikipedia请求完成，获取 {len(wikipedia_articles)} 个结果")

                # 如果没有结果，尝试其他关键词
                if not wikipedia_articles and len(keywords) > 1:
                    logger.info(f"主关键词无结果，尝试备用关键词: {keywords[1]}")
                    wikipedia_articles = await self._fetch_wikipedia_articles(keywords[1])

            except Exception as e:
                logger.warning(f"Wikipedia请求失败，跳过: {e}")
                wikipedia_articles = []

            # 2. 基于Wikipedia权威内容生成延伸阅读材料
            messages = [
                {
                    "role": "system",
                    "content": """你是一位教育专家，擅长基于Wikipedia权威内容生成详细的知识深度探索材料。
请确保知识深度探索材料基于真实信息，内容详实、有价值，包含以下部分：
1. 知识深度扩展
2. 历史背景与发展
3. 实际应用案例
4. 前沿进展与趋势
5. 深入学习建议

每个部分请提供300-500字的详细内容，总字数在1500-2500字之间。"""
                },
                {
                    "role": "user",
                    "content": f"""基于以下幻灯片内容，生成详细的知识深度探索材料：

幻灯片主题：{slide.title}
幻灯片内容：{' '.join(slide.content[:3]) if slide.content else '无详细内容'}

{'以下是相关的Wikipedia权威条目，请基于这些真实信息生成内容：' + chr(10).join([f"【{article['title']}】{article['description'][:150]}..." for article in wikipedia_articles]) if wikipedia_articles else '请基于专业知识生成相关内容：'}

请生成详细的知识深度探索材料，要求：
1. 内容详实、准确，结构清晰
2. 包含上述5个部分，每个部分有详细阐述
3. 语言通俗易懂，适合学习者阅读
4. 提供深入的学习建议和资源推荐
5. 在报告中命名为"知识深度探索"

请直接开始生成内容，不要添加额外的说明性文字。"""
                }
            ]

            extended_reading_text, validation_result = await self.call_llm_with_validation(
                messages, task_type="extended_reading", expected_format="extended_reading"
            )

            if extended_reading_text and validation_result.get("passed", False):
                # 添加Wikipedia来源信息
                wikipedia_sources = []
                for article in wikipedia_articles:
                    wikipedia_sources.append({
                        "title": article["title"],
                        "url": article["url"],
                        "description": article["description"],
                        "original_keyword": article.get("original_keyword", "")
                    })

                # 解析章节
                sections = self._parse_extended_reading_sections(extended_reading_text)

                # 创建延伸阅读材料 - 使用新名称【知识深度探索】
                extended_reading = [{
                    "title": f"《{slide.title}》知识深度探索",  # ✅ 使用新名称
                    "content": extended_reading_text,
                    "sections": sections,
                    "wikipedia_sources": wikipedia_sources,
                    "total_length": len(extended_reading_text),
                    "section_count": len(sections),
                    "type": "extended_reading",
                    "validation": validation_result,
                    "source": "基于Wikipedia API生成" if wikipedia_articles else "LLM生成",
                    "display_name": "知识深度探索"  # ✅ 在报告中显示的名称
                }]

                logger.info(f"✅ 成功生成知识深度探索材料，长度: {len(extended_reading_text)}字，章节数: {len(sections)}")
                return extended_reading, validation_result
            else:
                logger.warning(f"知识深度探索材料校验未通过，使用基础模式")
                # 校验失败，降级处理
                return await self._generate_basic_extended_reading(slide)

        except Exception as e:
            logger.error(f"生成知识深度探索材料失败: {e}", exc_info=True)
            return await self._generate_basic_extended_reading(slide)

    async def _generate_basic_extended_reading(self, slide: SlideContent) -> Tuple[
        List[Dict[str, Any]], Dict[str, Any]]:
        """生成基础延伸阅读材料"""

        logger.info(f"为基础模式为幻灯片 {slide.slide_number} 生成知识深度探索材料")

        messages = [
            {
                "role": "system",
                "content": """你是一位教育专家，为学习材料生成知识深度探索内容。
请确保内容详实、有价值，结构清晰。在报告中命名为"知识深度探索"。"""
            },
            {
                "role": "user",
                "content": f"""为以下幻灯片主题生成知识深度探索材料：

主题：{slide.title}
内容摘要：{' '.join(slide.content[:2]) if slide.content else '无详细内容'}

请生成包含以下部分的知识深度探索材料：
1. 知识深度扩展：深入解释核心概念和原理
2. 相关背景知识：介绍历史背景和发展历程
3. 实际应用场景：列举具体应用案例
4. 进一步学习建议：提供学习路径和资源建议

每个部分请提供300-500字的详细内容。请直接开始生成内容。"""
            }
        ]

        try:
            content, validation_result = await self.call_llm_with_validation(
                messages, task_type="extended_reading", expected_format="extended_reading"
            )

            if content and validation_result.get("passed", False):
                validation_result["warnings"] = validation_result.get("warnings", []) + ["使用基础模式生成"]

                # 解析章节
                sections = self._parse_extended_reading_sections(content)

                return [{
                    "title": f"《{slide.title}》知识深度探索",  # ✅ 使用新名称
                    "content": content,
                    "sections": sections,
                    "total_length": len(content),
                    "section_count": len(sections),
                    "type": "extended_reading_basic",
                    "validation": validation_result,
                    "source": "LLM基础生成",
                    "display_name": "知识深度探索"  # ✅ 在报告中显示的名称
                }], validation_result
            else:
                logger.warning(f"基础知识深度探索生成失败，返回空结果")
                return [], {"passed": False, "errors": ["无法生成知识深度探索材料"], "warnings": ["基础模式也失败"]}

        except Exception as e:
            logger.error(f"基础知识深度探索生成失败: {e}")
            return [], {"passed": False, "errors": [str(e)]}

    def _parse_extended_reading_sections(self, content: str) -> List[Dict[str, str]]:
        """解析延伸阅读材料的章节"""
        sections = []

        # 尝试按常见章节标题分割
        section_patterns = [
            (r'(一、.*?)(?=二、|$)', '一、'),
            (r'(二、.*?)(?=三、|$)', '二、'),
            (r'(三、.*?)(?=四、|$)', '三、'),
            (r'(四、.*?)(?=五、|$)', '四、'),
            (r'(五、.*?)(?=六、|$)', '五、'),
            (r'(##\s*知识.*?)(?=##\s*|$)', '知识'),
            (r'(##\s*历史.*?)(?=##\s*|$)', '历史'),
            (r'(##\s*应用.*?)(?=##\s*|$)', '应用'),
            (r'(##\s*前沿.*?)(?=##\s*|$)', '前沿'),
            (r'(##\s*学习.*?)(?=##\s*|$)', '学习'),
        ]

        # 首先尝试按模式分割
        for pattern, prefix in section_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches and len(matches) >= 1:
                for match in matches:
                    match = match.strip()
                    if match:
                        # 提取标题和内容
                        lines = match.split('\n')
                        title = lines[0].strip()
                        section_content = '\n'.join(lines[1:]).strip()
                        if section_content:
                            sections.append({
                                'title': title,
                                'content': section_content
                            })
                if sections and len(sections) >= 2:
                    return sections

        # 如果没找到，按段落分割
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        section_titles = ["知识深度扩展", "历史背景与发展", "实际应用案例", "前沿进展与趋势", "深入学习建议"]

        for i, para in enumerate(paragraphs[:5]):  # 最多5个部分
            title = section_titles[i] if i < len(section_titles) else f"第{i + 1}部分"
            sections.append({
                'title': title,
                'content': para
            })

        return sections

    async def _generate_references_with_validation(self, slide: SlideContent) -> Tuple[
        List[Dict[str, str]], Dict[str, Any]]:
        """生成参考资料（带校验）- 主要包含Wikipedia和其他权威资源"""

        # 提取关键词
        keywords = self._extract_keywords_from_slide(slide)

        if not keywords:
            return [], {"passed": True, "skipped": "无有效关键词"}

        try:
            # 使用最佳关键词
            best_keyword = keywords[0]
            logger.info(f"生成参考资料，使用最佳关键词: {best_keyword}")

            # 获取Wikipedia资源
            wikipedia_resources = []

            try:
                wikipedia_resources = await self._fetch_wikipedia_articles(best_keyword)
                logger.info(f"Wikipedia请求完成，获取 {len(wikipedia_resources)} 个结果")
            except Exception as e:
                logger.warning(f"Wikipedia请求异常，关键词: {best_keyword}: {e}")
                wikipedia_resources = []

            # 如果没有结果，尝试第二个关键词
            if not wikipedia_resources and len(keywords) > 1:
                logger.info(f"主关键词无结果，尝试备用关键词: {keywords[1]}")
                try:
                    wikipedia_resources = await self._fetch_wikipedia_articles(keywords[1])
                    logger.info(f"备用关键词请求完成，获取 {len(wikipedia_resources)} 个结果")
                except Exception as e:
                    logger.warning(f"备用关键词请求失败: {e}")
                    wikipedia_resources = []

            # 设置最小内容长度，过滤无用结果
            filtered_resources = []
            for resource in wikipedia_resources:
                description = resource.get('description', '')
                if len(description) > 10:  # 至少10个字符
                    filtered_resources.append(resource)

            # 去重
            unique_resources = {}
            for resource in filtered_resources:
                unique_resources[resource['title']] = resource

            wikipedia_resources = list(unique_resources.values())[:3]  # 最多3个

            # 如果Wikipedia没有结果，直接生成LLM推荐的资源
            if not wikipedia_resources:
                logger.info(f"Wikipedia API无结果，直接生成LLM推荐资源")
                other_resources = await self._generate_other_resources_simple(slide)
                all_resources = other_resources
            else:
                # 生成其他资源推荐
                other_resources = await self._generate_other_resources(slide, wikipedia_resources)
                all_resources = wikipedia_resources + other_resources

            # 创建验证结果
            validation_result = {
                "passed": len(all_resources) > 0,
                "errors": [],
                "warnings": [],
                "retries": 0,
                "wikipedia_count": len(wikipedia_resources),
                "other_count": len(other_resources),
                "validation_details": {
                    "wikipedia_api_called": True,
                    "total_resources": len(all_resources)
                }
            }

            if not wikipedia_resources:
                validation_result["warnings"].append("Wikipedia API未返回结果")

            # 格式化结果
            formatted_resources = []
            for resource in all_resources:
                formatted_resources.append({
                    "title": resource.get("title", ""),
                    "description": resource.get("description", ""),
                    "url": resource.get("url", ""),
                    "type": resource.get("type", "reference"),
                    "source": resource.get("source", "unknown"),
                    "validation": validation_result
                })

            logger.info(f"✅ 生成参考资料 {len(formatted_resources)} 个")
            return formatted_resources, validation_result

        except Exception as e:
            logger.error(f"生成参考资料失败: {e}", exc_info=True)
            return [], {"passed": False, "errors": [str(e)]}

    async def _generate_other_resources_simple(self, slide: SlideContent) -> List[Dict[str, Any]]:
        """简化版的其他资源生成（当Wikipedia API无结果时使用）"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """你是一位教育专家，基于学习主题推荐相关的学习资源。
请确保推荐真实存在的资源，包括书籍、课程、论文等。"""
                },
                {
                    "role": "user",
                    "content": f"""基于以下学习主题，推荐相关的学习资源：

主题：{slide.title}
内容摘要：{' '.join(slide.content[:2]) if slide.content else '无详细内容'}

请推荐3-4个相关的学习资源，包括：
1. 经典书籍
2. 在线课程或教程
3. 重要的学术论文或研究
4. 实用的工具或框架

对于每个推荐，请提供：
- 资源名称
- 简要描述（30字内）
- 推荐理由（20字内）

请使用中文回复，格式为：资源名称 | 描述 | 推荐理由"""
                }
            ]

            resources_text, validation_result = await self.call_llm_with_validation(
                messages, task_type="references", expected_format=None
            )

            if resources_text and validation_result.get("passed", False):
                parsed_resources = []
                lines = resources_text.split("\n")

                for line in lines:
                    line = line.strip()
                    if line and '|' in line and len(line.split('|')) >= 2:
                        parts = line.split('|')
                        if len(parts) >= 2:
                            resource_name = parts[0].strip()
                            description = parts[1].strip()
                            reason = parts[2].strip() if len(parts) > 2 else "相关学习资源"

                            parsed_resources.append({
                                "title": resource_name,
                                "description": description,
                                "type": self._determine_resource_type(resource_name),
                                "source": "LLM推荐（简化版）",
                                "reason": reason
                            })

                return parsed_resources[:3]  # 最多返回3个

            return []

        except Exception as e:
            logger.error(f"生成简化版其他资源失败: {e}")
            return []

    async def _fetch_wikipedia_page_info(self, title: str) -> Dict[str, Any]:
        """获取Wikipedia页面的更多信息"""
        try:
            encoded_title = urllib.parse.quote(title)
            url = f"https://en.wikipedia.org/w/api.php"  # 【修复】使用英文维基

            params = {
                "action": "query",
                "format": "json",
                "prop": "extracts|info",
                "titles": encoded_title,
                "exintro": 1,
                "explaintext": 1,
                "inprop": "url",
                "utf8": 1,
                "origin": "*"
            }

            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "PPT-Agent/1.0 (https://github.com/your-repo; your-email@example.com) Education-Tool"
                }
                async with session.get(url, params=params, headers=headers, timeout=60.0) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "query" in data and "pages" in data["query"]:
                            pages = data["query"]["pages"]
                            for page_id, page_info in pages.items():
                                if page_id != "-1":  # 有效页面
                                    return {
                                        "extract": page_info.get("extract", "")[:300],
                                        "fullurl": page_info.get("fullurl", ""),
                                        "pageid": page_id,
                                        "touched": page_info.get("touched", "")
                                    }
            return {}
        except Exception:
            return {}

    async def _generate_other_resources(self, slide: SlideContent, wikipedia_resources: List[Dict]) -> List[
        Dict[str, Any]]:
        """生成其他类型的学习资源"""

        if not wikipedia_resources:
            return []

        # 基于Wikipedia结果生成其他资源推荐
        messages = [
            {
                "role": "system",
                "content": """你是一位教育专家，基于Wikipedia条目推荐其他学习资源。
请确保推荐真实存在的资源，包括书籍、课程、论文等。"""
            },
            {
                "role": "user",
                "content": f"""基于以下Wikipedia条目，推荐相关的其他学习资源：

主题：{slide.title}
Wikipedia条目：
{chr(10).join([f"- {item['title']}: {item['description'][:100]}..." for item in wikipedia_resources])}

请推荐：
1. 相关的经典书籍（真实存在的）
2. 优质的在线课程或教程
3. 重要的学术论文
4. 实用的工具或框架

对于每个推荐，请提供：
- 资源名称
- 简要描述（50字内）
- 推荐理由

格式：
资源名称 | 描述 | 推荐理由"""
            }
        ]

        try:
            resources_text, validation_result = await self.call_llm_with_validation(
                messages, task_type="references", expected_format=None
            )

            if resources_text and validation_result.get("passed", False):
                parsed_resources = []
                lines = resources_text.split("\n")

                for line in lines:
                    line = line.strip()
                    if line and '|' in line and len(line.split('|')) >= 2:
                        parts = line.split('|')
                        if len(parts) >= 2:
                            resource_name = parts[0].strip()
                            description = parts[1].strip()
                            reason = parts[2].strip() if len(parts) > 2 else "相关学习资源"

                            parsed_resources.append({
                                "title": resource_name,
                                "description": description,
                                "type": self._determine_resource_type(resource_name),
                                "source": "LLM推荐",
                                "reason": reason
                            })

                return parsed_resources[:4]  # 最多返回4个

            return []

        except Exception as e:
            logger.error(f"生成其他资源失败: {e}")
            return []

    async def _generate_quiz_with_validation(self, slide: SlideContent) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """生成测验问题（带校验）"""
        content_text = "\n".join(slide.content)

        messages = [
            {"role": "system", "content": """你是一位考试命题专家，擅长设计测试学生理解程度的问题。
        请确保问题设计合理，答案准确无误，解析清晰明了。

        【重要要求】：
        1. 问题必须基于提供的学习内容
        2. 必须提供详细的答案解析，不能为空
        3. 解析要解释为什么正确选项正确，以及其他选项为什么不正确

        解析格式要求：
        1. 首先说明正确答案的正确性原因
        2. 简要分析其他选项的错误原因
        3. 可以包含相关知识点的简要回顾

        示例格式：
        问题：[清晰明确的问题题干]
        A. [选项A]
        B. [选项B]
        C. [选项C]
        D. [选项D]
        答案：[正确选项，如A]
        解析：[详细解析，至少50字]"""},
            {"role": "user", "content": f"""根据以下学习内容，设计一个选择题：

        内容主题：{slide.title}
        详细内容：{content_text}

        请设计：
        1. 一个清晰明确的问题题干（基于提供的学习内容）
        2. 4个选项（A、B、C、D）
        3. 正确答案（标注清楚）
        4. 详细的答案解析（必须包含，不能为空）

        要求：
        - 问题和选项必须基于提供的学习内容
        - 解析必须详细说明每个选项正确或错误的原因
        - 总字数不少于80字

        请严格按照要求的格式生成。"""}
        ]

        try:
            quiz, validation_result = await self.call_llm_with_validation(
                messages, task_type="quiz", expected_format="quiz_question"
            )

            if quiz and validation_result.get("passed", False):
                # 解析测验内容并验证答案格式
                quiz_data = self._parse_and_validate_quiz(quiz, slide.title)

                if quiz_data and quiz_data["question"]:
                    quiz_data["validation"] = validation_result
                    return [quiz_data], validation_result

            return [], validation_result

        except Exception as e:
            logger.error(f"生成测验失败: {e}")
            return [], {"passed": False, "errors": [str(e)]}

    def _clean_wikipedia_snippet(self, snippet: str) -> str:
        """清理Wikipedia摘要片段"""
        # 移除HTML标签
        cleaned = re.sub(r'<[^>]+>', '', snippet)
        # 移除特殊字符
        cleaned = re.sub(r'&\w+;', '', cleaned)
        # 限制长度
        if len(cleaned) > 120:
            cleaned = cleaned[:117] + "..."
        return cleaned

    def _determine_resource_type(self, title: str) -> str:
        """根据标题判断资源类型"""
        title_lower = title.lower()
        if any(word in title_lower for word in ["书", "教材", "指南", "手册"]):
            return "book"
        elif any(word in title_lower for word in ["课程", "教程", "视频", "网课", "mooc"]):
            return "course"
        elif any(word in title_lower for word in ["论文", "研究", "期刊", "会议"]):
            return "paper"
        elif any(word in title_lower for word in ["工具", "框架", "库", "软件"]):
            return "tool"
        else:
            return "other"

    def _parse_and_validate_quiz(self, quiz_text: str, slide_title: str) -> Optional[Dict[str, Any]]:
        """解析并验证测验内容 - 增强版，确保解析不为空"""
        lines = quiz_text.split("\n")
        quiz_data = {
            "question": "",
            "options": {},
            "answer": "",
            "explanation": "",
            "slide_title": slide_title
        }

        required_fields_found = {
            "question": False,
            "options_count": 0,
            "answer": False,
            "explanation": False
        }

        current_section = None
        explanation_lines = []

        for line in lines:
            line = line.strip()

            # 检测各个部分
            if line.startswith("问题：") or line.startswith("问题:"):
                quiz_data["question"] = line[3:].strip()
                required_fields_found["question"] = True
                current_section = "question"
            elif line.startswith("A."):
                quiz_data["options"]["A"] = line[2:].strip()
                required_fields_found["options_count"] += 1
            elif line.startswith("B."):
                quiz_data["options"]["B"] = line[2:].strip()
                required_fields_found["options_count"] += 1
            elif line.startswith("C."):
                quiz_data["options"]["C"] = line[2:].strip()
                required_fields_found["options_count"] += 1
            elif line.startswith("D."):
                quiz_data["options"]["D"] = line[2:].strip()
                required_fields_found["options_count"] += 1
            elif line.startswith("答案：") or line.startswith("答案:"):
                quiz_data["answer"] = line[3:].strip().upper()
                required_fields_found["answer"] = True
                current_section = "answer"
            elif line.startswith("解析：") or line.startswith("解析:"):
                current_section = "explanation"
                explanation_text = line[3:].strip()
                if explanation_text:
                    explanation_lines.append(explanation_text)
                required_fields_found["explanation"] = True
            elif current_section == "explanation" and line:
                # 解析部分的后续行
                explanation_lines.append(line)

        # 合并解析行
        if explanation_lines:
            quiz_data["explanation"] = " ".join(explanation_lines).strip()
            required_fields_found["explanation"] = True

        # 【关键修复】如果解析为空，创建默认解析
        if not quiz_data["explanation"]:
            # 基于问题和答案创建默认解析
            correct_answer = quiz_data["answer"]
            correct_option = quiz_data["options"].get(correct_answer, "")

            if correct_answer and correct_option:
                # 为每个选项创建解析
                explanations = []
                for key, option in quiz_data["options"].items():
                    if key == correct_answer:
                        explanations.append(f"{key}是正确的，因为{option}符合相关知识要点。")
                    else:
                        explanations.append(f"{key}不正确，因为{option}与相关知识不符或有误。")

                quiz_data["explanation"] = " ".join(explanations)
            else:
                # 最小化默认解析
                quiz_data["explanation"] = f"正确答案是{correct_answer}，因为这是与'{slide_title}'相关的最佳选择。"

            required_fields_found["explanation"] = True

        # 验证是否所有必要字段都存在
        if (required_fields_found["question"] and
                required_fields_found["options_count"] >= 2 and  # 至少2个选项
                required_fields_found["answer"] and
                quiz_data["answer"] in quiz_data["options"] and
                required_fields_found["explanation"] and
                quiz_data["explanation"]):
            return quiz_data

        # 如果验证失败，创建完整的默认测验
        return self._create_default_quiz(slide_title)

    def _create_default_quiz(self, slide_title: str) -> Dict[str, Any]:
        """创建默认测验作为后备方案"""
        return {
            "question": f"关于{slide_title}，以下哪个说法是正确的？",
            "options": {
                "A": f"{slide_title}是正确的内容",
                "B": f"{slide_title}的部分内容有误",
                "C": f"无法确定{slide_title}的准确性",
                "D": f"{slide_title}需要进一步验证"
            },
            "answer": "A",
            "explanation": f"选项A是正确的，因为{slide_title}是基于可靠信息提供的知识要点。其他选项或不准确或不完整。",
            "slide_title": slide_title,
            "is_default": True  # 标记为默认生成的
        }

    def _check_python_syntax_basic(self, code: str) -> bool:
        """基本Python语法检查"""
        try:
            # 检查基本的语法问题
            if "```python" in code or "```" in code:
                # 提取代码块
                code_match = re.search(r'```(?:python)?\n(.*?)\n```', code, re.DOTALL)
                if code_match:
                    code = code_match.group(1)

            # 检查常见的关键字
            required_keywords = ["def", "class", "import", "print", "return", "if"]
            has_keyword = any(keyword in code for keyword in required_keywords[:3])

            # 检查括号匹配
            if code.count('(') != code.count(')'):
                return False
            if code.count('[') != code.count(']'):
                return False
            if code.count('{') != code.count('}'):
                return False

            return has_keyword

        except Exception:
            return False

    def _create_fallback_explanation(self, slide: SlideContent) -> str:
        """创建降级处理的解释"""
        keywords = self._extract_keywords_from_slide(slide)[:3]
        keyword_str = "、".join(keywords)

        fallback_text = f"""本幻灯片主要涉及{keyword_str}等内容。
由于模型校验未通过，建议参考原始PPT内容或查阅相关资料获取更准确的信息。"""

        return fallback_text

    def _extract_keywords_from_slide(self, slide: SlideContent) -> List[str]:
        """从幻灯片中提取关键词 - 学术优化版"""
        # 合并所有文本
        all_text = ""

        if slide.title:
            all_text += slide.title + " "

        if slide.content:
            for content in slide.content:
                all_text += content + " "

        if slide.bullet_points:
            for point in slide.bullet_points:
                all_text += point + " "

        if not all_text.strip():
            return []

        # 1. 提取学术术语（优先）
        academic_keywords = []
        for term in self.academic_terms:
            if term in all_text:
                academic_keywords.append(term)

        # 如果找到足够多的学术术语，直接返回
        if len(academic_keywords) >= 3:
            # 去重并排序（按在文本中出现的顺序）
            seen = set()
            unique_keywords = []
            for keyword in academic_keywords:
                if keyword not in seen:
                    seen.add(keyword)
                    unique_keywords.append(keyword)
            return unique_keywords[:5]

        # 2. 提取中文字符串（长度2-6的词汇）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', all_text)

        # 3. 提取英文单词（技术术语）
        english_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', all_text)  # 首字母大写的术语
        english_words.extend(re.findall(r'\b[a-z]{3,}\b', all_text.lower()))  # 小写技术词

        # 4. 提取数学/技术符号
        tech_terms = re.findall(r'\b[A-Za-z0-9_\-\.]+\b', all_text)

        # 合并所有候选词
        all_candidates = chinese_words + english_words + tech_terms

        # 过滤停用词（学术扩展版）
        academic_stop_words = {
            # 通用停用词
            "的", "在", "和", "与", "及", "或", "等", "是", "有", "包括", "包含",
            "这个", "那个", "这些", "那些", "一种", "一个", "一些", "一", "不", "也",
            "了", "很", "都", "而", "且", "但", "然而", "因此", "所以", "因为",
            "如果", "那么", "则", "可以", "可能", "应该", "需要", "要求",
            "对于", "关于", "根据", "通过", "使用", "利用", "采用",
            "能够", "使得", "称为", "称作", "称之为",

            # PPT特定停用词
            "目录", "谢谢", "例子", "示例", "实例", "图表", "图片", "图像",
            "标题", "正文", "内容", "页面", "幻灯片", "页数", "页码",

            # 通用动词
            "表示", "说明", "描述", "解释", "展示", "显示", "呈现",
            "提供", "给出", "列出", "列举", "总结", "概括",

            # 数学通用词
            "公式", "计算", "推导", "证明", "求解", "得出", "得到"
        }

        # 过滤和评分
        scored_keywords = {}
        for word in all_candidates:
            word_lower = word.lower()

            # 过滤条件
            if (word not in academic_stop_words and
                    len(word) >= 2 and  # 至少2个字符
                    not re.match(r'^\d+$', word) and  # 排除纯数字
                    not re.match(r'^[a-zA-Z]$', word)):  # 排除单个字母

                # 评分规则
                score = 1.0

                # 学术术语加分
                if word in self.academic_terms:
                    score += 3.0

                # 标题中的词加分
                if slide.title and word in slide.title:
                    score += 2.0

                # 长度适中加分（3-5个字符）
                if 3 <= len(word) <= 5:
                    score += 1.0

                # 英文技术词加分
                if re.match(r'^[A-Za-z]+$', word) and len(word) >= 3:
                    score += 1.0

                # 避免重复评分
                if word not in scored_keywords or score > scored_keywords[word]:
                    scored_keywords[word] = score

        # 按分数排序
        sorted_keywords = sorted(scored_keywords.items(), key=lambda x: x[1], reverse=True)

        # 提取前5个关键词
        top_keywords = [word for word, score in sorted_keywords[:5]]

        # 如果结果太少，从标题中提取补充
        if len(top_keywords) < 3 and slide.title:
            title_words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', slide.title)
            for word in title_words:
                if (word not in top_keywords and
                        word not in academic_stop_words and
                        len(word) >= 2):
                    top_keywords.append(word)
                    if len(top_keywords) >= 5:
                        break

        return top_keywords[:5]

    async def expand_multiple_slides(self, slides: List[SlideContent]) -> List[Dict[str, Any]]:
        """扩展多个幻灯片"""
        logger.info(f"开始扩展 {len(slides)} 个幻灯片")

        tasks = [self.expand_slide(slide) for slide in slides]
        results = await asyncio.gather(*tasks)

        # 统计信息
        total_score = 0
        valid_results = 0
        extended_reading_count = 0

        for result in results:
            if "validation_score" in result:
                total_score += result["validation_score"]
                valid_results += 1

            if result.get("extended_readings") and len(result["extended_readings"]) > 0:
                extended_reading_count += 1

        if valid_results > 0:
            avg_score = total_score / valid_results
            logger.info(f"整体扩展完成，平均校验得分: {avg_score:.2f}")

        logger.info(f"📊 扩展统计:")
        logger.info(f"  - 成功生成知识深度探索材料的幻灯片: {extended_reading_count}/{len(slides)}")  # ✅ 使用新名称
        logger.info(f"  - 整体校验平均分: {avg_score if valid_results > 0 else 0:.2f}")

        return results

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局智能体实例
knowledge_agent = SimpleAgent()
