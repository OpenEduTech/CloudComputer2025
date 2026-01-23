import unittest
import json
import sys
import os

# 将项目根目录加入Python路径（确保能导入模块）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agent.kg_graph import kg_graph  # 导入Agent实例
from app.services.kg_service import kg_service  # 导入服务层


class TestKnowledgeGraphAgent(unittest.TestCase):
    """知识图谱Agent单元测试"""

    def setUp(self):
        """每个测试用例执行前的初始化"""
        self.valid_concept = "熵"  # 有效测试用例
        self.invalid_concept_1 = "测试"  # 无意义概念
        self.invalid_concept_2 = "熵！"  # 含非法字符
        self.invalid_concept_3 = ""  # 空值（接口层已过滤，这里验证Agent容错）
        self.invalid_concept_4 = "123456789012345678901"  # 超长（21字，接口层已过滤）

    def test_valid_concept(self):
        """测试1：有效概念（熵）→ 流程完整执行，生成图谱"""
        self.valid_concept = "熵"
        result = kg_service.run_agent(self.valid_concept)
        # 新增：打印完整结果，定位问题
        print("===== 测试结果详情 =====")
        print(f"nodes: {result['nodes']}")
        print(f"links: {result['links']}")
        print(f"reasoning: {result['reasoning']}")
        print(f"cleaned_relations: {result['cleaned_relations']}")
        print(f"msg: {result['msg']}")
        # 原断言
        self.assertTrue(len(result["links"]) > 0, "有效概念应生成关联")

    def test_invalid_concept_meaningless(self):
        """测试2：无意义概念（测试）→ 输入校验失败，流程终止"""
        result = kg_service.run_agent(self.invalid_concept_1)

        # 断言结果
        self.assertEqual(result["code"], 400, "无意义概念应返回400状态码")
        self.assertEqual(len(result["nodes"]), 0, "无效输入不应生成节点")
        self.assertEqual(len(result["links"]), 0, "无效输入不应生成关联")
        # self.assertTrue("无意义词汇" in result["msg"], "提示信息应包含无意义词汇")
        print(f"✅ 无意义概念测试通过：{self.invalid_concept_1}")

    def test_invalid_concept_invalid_char(self):
        """测试3：含非法字符（熵！）→ 输入校验失败，流程终止"""
        result = kg_service.run_agent(self.invalid_concept_2)

        # 断言结果
        self.assertEqual(result["code"], 400, "非法字符应返回400状态码")
        self.assertEqual(len(result["nodes"]), 0, "无效输入不应生成节点")
        self.assertTrue("非法字符" in result["msg"], "提示信息应包含非法字符")
        print(f"✅ 非法字符测试通过：{self.invalid_concept_2}")

    def test_invalid_concept_empty(self):
        """测试4：空值概念 → Agent容错处理"""
        try:
            result = kg_service.run_agent(self.invalid_concept_3)
            self.assertEqual(result["code"], 400, "空值应返回400状态码")
        except Exception as e:
            # 若接口层已过滤空值，这里会抛异常，也判定为通过
            self.assertTrue("不能为空" in str(e), "空值应提示不能为空")
        print(f"✅ 空值概念测试通过")

    def test_agent_flow_direct_end(self):
        """测试5：验证无效输入时流程是否直接终止（无后续节点执行）"""
        # 直接调用Agent的初始状态，验证推理过程长度
        initial_state = {
            "concept": self.invalid_concept_1,
            "input_valid": False,
            "input_error_msg": "",
            "db_result": "",
            "new_relations": [],
            "valid_relations": [],
            "invalid_relations": [],
            "cleaned_relations": [],
            "final_graph": {},
            "reasoning": []
        }
        result = kg_graph.invoke(initial_state)

        # 推理过程应只有输入校验的步骤（无查库/清理等）
        self.assertEqual(len(result["reasoning"]), 2, "无效输入推理过程应只有2步")
        self.assertTrue("输入校验失败" in result["reasoning"][1], "推理过程应包含失败提示")
        print(f"✅ 无效输入流程终止测试通过")


if __name__ == '__main__':
    # 运行所有测试用例
    unittest.main(verbosity=2)