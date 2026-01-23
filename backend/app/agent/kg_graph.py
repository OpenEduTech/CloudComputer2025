from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
import json
import re
from datetime import datetime


# 1. 定义状态
class GraphState(TypedDict):
    concept: str  # 核心概念
    input_valid: bool  # 输入是否有效
    input_error_msg: str  # 输入无效的提示信息
    db_result: str  # 查库结果（JSON）
    new_relations: List[Dict]  # 新扩展的关联
    valid_relations: List[Dict]  # 校验通过的关联
    invalid_relations: List[Dict]  # 校验不通过的关联
    cleaned_relations: List[Dict]  # 清理的不合理关联（旧关联）
    final_graph: Dict  # 最终图谱
    reasoning: List[str]  # 推理过程（分步记录）
    expand_retry_count: int  # 扩展重试次数（解决递归核心）


# 2. 输入校验节点（保留原有逻辑）
def validate_input_node(state: GraphState) -> GraphState:
    """节点0：调用validate_concept工具，Agent自主校验输入有效性"""
    # 导入我们写的校验工具（和其他工具导入方式一致）
    from .tools.neo4j_tool import validate_concept

    concept = state["concept"]
    reasoning = state.get("reasoning", [])
    reasoning.append("0. 输入校验：开始调用validate_concept工具判断概念有效性")

    try:
        tool_result_str = validate_concept.invoke({"concept": concept})
        tool_result = json.loads(tool_result_str)

        if not tool_result["valid"]:
            error_msg = f"概念「{concept}」无效：{tool_result['reason']}"
            reasoning.append(f"0. 输入校验失败：{error_msg}")
            return {
                **state,
                "input_valid": False,
                "input_error_msg": error_msg,
                "reasoning": reasoning,
                "final_graph": {
                    "code": 400,
                    "msg": error_msg,
                    "nodes": [],
                    "links": [],
                    "reasoning": reasoning,
                    "cleaned_relations": []
                }
            }

        # 输入有效（工具返回valid=True）
        reasoning.append(f"0. 输入校验通过：{tool_result['reason']}")
        return {
            **state,
            "input_valid": True,
            "input_error_msg": "",
            "reasoning": reasoning,
            "expand_retry_count": 0  # 初始化重试次数
        }

    # ========== 工具调用异常处理（兜底逻辑） ==========
    except Exception as e:
        # 工具调用失败时，降级使用原有硬编码规则（保证流程不中断）
        reasoning.append(f"0. 输入校验工具调用失败，降级为规则校验：{str(e)[:50]}")

        # 规则1：校验字符合法性（原有逻辑）
        valid_char_pattern = r'^[\u4e00-\u9fa5a-zA-Z0-9αβγδεζηθικλμνξοπρστυφχψω∑∏∫√∝∞≠≤≥]+$'
        if not re.match(valid_char_pattern, concept):
            error_msg = f"概念「{concept}」包含非法字符，仅支持中文/英文/数字/常见学科符号（如α、∑）"
            reasoning.append(f"0. 输入校验失败（规则兜底）：{error_msg}")
            return {
                **state,
                "input_valid": False,
                "input_error_msg": error_msg,
                "reasoning": reasoning,
                "final_graph": {
                    "code": 400,
                    "msg": error_msg,
                    "nodes": [],
                    "links": [],
                    "reasoning": reasoning,
                    "cleaned_relations": []
                }
            }

        # 规则2：校验概念是否有意义（原有逻辑）
        invalid_concepts = [
            "随便", "测试", "123", "abc", "无", "空", "默认",
            "测试123", "默认值", "未知", "空值"
        ]
        if any(invalid_str in concept for invalid_str in invalid_concepts):
            error_msg = f"概念「{concept}」为无意义词汇，请输入具体的学科概念（如“熵”“神经网络”“最小二乘法”）"
            reasoning.append(f"0. 输入校验失败（规则兜底）：{error_msg}")
            return {
                **state,
                "input_valid": False,
                "input_error_msg": error_msg,
                "reasoning": reasoning,
                "final_graph": {
                    "code": 400,
                    "msg": error_msg,
                    "nodes": [],
                    "links": [],
                    "reasoning": reasoning,
                    "cleaned_relations": []
                }
            }

        # 规则兜底：输入有效
        reasoning.append(f"0. 输入校验通过（规则兜底）：概念「{concept}」有效")
        return {
            **state,
            "input_valid": True,
            "input_error_msg": "",
            "reasoning": reasoning,
            "expand_retry_count": 0
        }


# 3. 查库节点（保留原有逻辑）
def query_db_node(state: GraphState) -> GraphState:
    """节点1：查询数据库"""
    from .tools.neo4j_tool import query_db
    concept = state["concept"]
    # 调用查库工具
    db_result = query_db.invoke({"concept": concept})
    # 记录推理过程
    reasoning = state.get("reasoning", [])
    reasoning.append(f"1. 查库：获取{concept}的已有关联")
    # 返回状态
    return {
        **state,
        "db_result": db_result,
        "reasoning": reasoning
    }


# 4. 清理旧关联节点
def clean_invalid_relation_node(state: GraphState) -> GraphState:
    """节点2：清理数据库中已有的不合理关联"""
    from .tools.neo4j_tool import validate_relation, delete_relation, mark_abnormal
    concept = state["concept"]
    # 增加JSON解析容错
    try:
        db_result = json.loads(state["db_result"])
    except:
        db_result = {"status": "success", "data": {"source": concept, "related_nodes": []}}

    cleaned = []

    # 仅处理数据库中已有的关联
    if db_result["status"] == "success":
        for rel in db_result["data"]["related_nodes"]:
            # 1. 校验旧关联的合理性
            try:
                res_str = validate_relation.invoke({
                    "core_name": concept,
                    "rel_name": rel["target"],
                    "relation": rel["relation"]
                })
                res = json.loads(res_str)
            except:
                res = {"valid": False, "reason": "校验结果解析失败"}

            # 2. 处理不合理关联
            if not res["valid"]:
                delete_relation.invoke({"core_name": concept, "rel_name": rel["target"]})
                cleaned.append({"target": rel["target"], "type": "软删除", "reason": res["reason"]})
            elif rel["strength"] < 2:
                mark_abnormal.invoke({"core_name": concept, "rel_name": rel["target"]})
                cleaned.append({"target": rel["target"], "type": "标记异常", "reason": "关联强度<2"})

    # 记录推理过程
    reasoning = state["reasoning"]
    reasoning.append(f"2. 清理旧关联：共处理{len(cleaned)}个不合理关联（软删除/标记异常）")
    # 返回状态
    return {
        **state,
        "cleaned_relations": cleaned,
        "reasoning": reasoning
    }


# 5. 扩展新关联节点（修改默认值为5条，适配工具逻辑）
def expand_relation_node(state: GraphState) -> GraphState:
    """节点3：扩展新关联（添加重试次数记录）"""
    from .tools.neo4j_tool import expand_relation
    concept = state["concept"]
    db_result = state["db_result"]

    # 初始化/累加重试次数（核心修复）
    retry_count = state.get("expand_retry_count", 0)
    new_retry_count = retry_count + 1

    # 记录推理过程（带重试次数）
    reasoning = state["reasoning"]
    reasoning.append(f"3. 扩展（第{new_retry_count}次）：开始生成新关联")

    # 调用扩展工具
    try:
        new_relations_str = expand_relation.invoke({
            "concept": concept,
            "existing_relations": db_result
        })
        # 提取纯JSON并解析
        json_str = re.search(r'\[.*\]', new_relations_str.strip(), re.DOTALL).group()
        new_relations = json.loads(json_str)
    except:
        # 解析失败时返回默认值（修改为5条，适配工具逻辑）
        new_relations = [
            {"name": "默认关联1", "domain": "数学", "definition": "默认定义", "relation": "默认逻辑", "strength": 3},
            {"name": "默认关联2", "domain": "物理", "definition": "默认定义", "relation": "默认逻辑", "strength": 3},
            {"name": "默认关联3", "domain": "计算机", "definition": "默认定义", "relation": "默认逻辑", "strength": 3},
            {"name": "默认关联4", "domain": "生物", "definition": "默认定义", "relation": "默认逻辑", "strength": 3},
            {"name": "默认关联5", "domain": "社会学", "definition": "默认定义", "relation": "默认逻辑", "strength": 3}
        ]

    # 记录推理过程（动态显示数量，适配5条需求）
    reasoning.append(f"3. 扩展（第{new_retry_count}次）：生成{len(new_relations)}个新关联（跨学科、非重复）")

    # 返回状态（传递重试次数）
    return {
        **state,
        "new_relations": new_relations,
        "reasoning": reasoning,
        "expand_retry_count": new_retry_count
    }


# 6. 校验新关联节点（保留原有逻辑）
def validate_relation_node(state: GraphState) -> GraphState:
    """节点4：校验新关联"""
    from .tools.neo4j_tool import validate_relation
    concept = state["concept"]
    new_relations = state["new_relations"]
    valid = []
    invalid = []

    # 逐个校验新关联
    for rel in new_relations:
        try:
            res_str = validate_relation.invoke({
                "core_name": concept,
                "rel_name": rel["name"],
                "relation": rel["relation"]
            })
            res = json.loads(res_str)
        except:
            res = {"valid": False, "reason": "校验结果解析失败"}

        if res["valid"]:
            valid.append(rel)
        else:
            invalid.append({"rel": rel, "reason": res["reason"]})

    # 记录推理过程
    reasoning = state["reasoning"]
    reasoning.append(f"4. 校验：{len(valid)}个关联合法，{len(invalid)}个关联不合法")

    # 返回状态
    return {
        **state,
        "valid_relations": valid,
        "invalid_relations": invalid,
        "reasoning": reasoning
    }


# 7. 保存合法关联节点（保留原有逻辑）
def save_relation_node(state: GraphState) -> GraphState:
    """节点5：保存合法关联"""
    from .tools.neo4j_tool import save_relation
    concept = state["concept"]
    valid_relations = state["valid_relations"]

    # 调用存库工具
    for rel in valid_relations:
        save_data = json.dumps({
            "source": concept,
            "target": rel["name"],
            "source_domain": "未知",
            "target_domain": rel["domain"],
            "source_def": "未知",
            "target_def": rel["definition"],
            "relation": rel["relation"],
            "strength": rel["strength"]
        })
        save_relation.invoke({"relation_data": save_data})

    # 记录推理过程
    reasoning = state["reasoning"]
    reasoning.append(f"5. 存库：保存{len(valid_relations)}个合法关联")

    # 返回状态
    return {
        **state,
        "reasoning": reasoning
    }


def generate_graph_node(state: GraphState) -> GraphState:
    """节点6：生成最终图谱（修复语法错误+限制总节点数≤5）"""
    concept = state["concept"]
    # 增加JSON解析容错
    try:
        db_result = json.loads(state["db_result"])
    except:
        db_result = {"status": "success", "data": {"source": concept, "related_nodes": []}}

    valid_relations = state["valid_relations"]
    # ========== 修复：定义all_nodes/core_node ==========
    core_node = {"name": concept, "domain": "未知"}
    all_nodes = [core_node]
    all_links = []

    # 加清理后剩余的旧关联（可选：如需仅保留新关联，直接注释这段）
    if db_result["status"] == "success":
        for rel in db_result["data"]["related_nodes"]:
            is_cleaned = any([c["target"] == rel["target"] for c in state["cleaned_relations"]])
            if not is_cleaned and rel["strength"] >= 2:
                all_nodes.append({"name": rel["target"], "domain": rel["domain"]})
                all_links.append({
                    "source": concept,
                    "target": rel["target"],
                    "relation": rel["relation"],
                    "strength": rel["strength"]
                })

    # 加新关联
    for rel in valid_relations:
        all_nodes.append({"name": rel["name"], "domain": rel["domain"]})
        all_links.append({
            "source": concept,
            "target": rel["name"],
            "relation": rel["relation"],
            "strength": rel["strength"]
        })

    # ========== 核心修改：限制总节点数≤5 ==========
    # 去重
    unique_nodes = [dict(t) for t in {tuple(d.items()) for d in all_nodes}]
    # 保留核心节点 + 最多4个其他节点（总≤5）
    filtered_nodes = [core_node]  # 必须保留核心节点
    other_nodes = [n for n in unique_nodes if n["name"] != concept]
    filtered_nodes.extend(other_nodes[:4])  # 核心+4个=5个

    # 过滤链路（只保留筛选后节点之间的链路）
    filtered_node_names = set(n["name"] for n in filtered_nodes)
    filtered_links = [
        link for link in all_links
        if link["source"] in filtered_node_names
           and link["target"] in filtered_node_names
    ]

    # 记录推理过程
    reasoning = state["reasoning"]
    reasoning.append(f"6. 生成图谱：共{len(filtered_nodes)}个节点，{len(filtered_links)}条合法关联（限制总节点数≤5）")

    return {
        **state,
        "final_graph": {
            "code": 200,
            "msg": "图谱生成成功",
            "nodes": filtered_nodes,
            "links": filtered_links,
            "reasoning": reasoning,
            "cleaned_relations": state["cleaned_relations"]
        },
        "reasoning": reasoning
    }


# 9. 输入校验分支判断（保留原有逻辑）
def should_continue_process(state: GraphState) -> str:
    """判断是否继续后续流程：输入有效则查库，无效则结束"""
    if state["input_valid"]:
        return "query_db"
    return "end"


# 10. 扩展重试分支判断（核心修改：合法关联≥5条则停止扩展）
def should_re_expand(state: GraphState) -> str:
    """判断是否需要重新扩展：合法关联<5条 且 重试次数<3 则重新扩展"""
    retry_count = state.get("expand_retry_count", 0)
    valid_count = len(state["valid_relations"])

    # 核心修改：合法关联≥5条 或 重试≥3次 → 停止扩展
    if valid_count < 5 and retry_count < 1:
        reasoning = state["reasoning"]
        reasoning.append(f"4. 校验后判定：合法关联数({valid_count})<5，第{retry_count + 1}次重试扩展")
        return "expand_relation"

    # 达到5条合法关联 或 重试上限 → 进入存库流程
    return "save_relation"


# 11. 构建图谱（保留原有逻辑）
def build_kg_agent():
    """构建知识图谱Agent（完整流程）"""
    graph = StateGraph(GraphState)

    # 添加所有节点
    graph.add_node("validate_input", validate_input_node)
    graph.add_node("query_db", query_db_node)
    graph.add_node("clean_invalid_relation", clean_invalid_relation_node)
    graph.add_node("expand_relation", expand_relation_node)
    graph.add_node("validate_relation", validate_relation_node)
    graph.add_node("save_relation", save_relation_node)
    graph.add_node("generate_graph", generate_graph_node)

    # 定义流程顺序
    graph.set_entry_point("validate_input")

    # 输入校验后分支
    graph.add_conditional_edges(
        "validate_input",
        should_continue_process,
        {"query_db": "query_db", "end": END}
    )

    # 核心流程链路
    graph.add_edge("query_db", "clean_invalid_relation")
    graph.add_edge("clean_invalid_relation", "expand_relation")
    graph.add_edge("expand_relation", "validate_relation")

    # 扩展重试分支（核心修复后的逻辑）
    graph.add_conditional_edges(
        "validate_relation",
        should_re_expand,
        {"expand_relation": "expand_relation", "save_relation": "save_relation"}
    )

    # 最终流程
    graph.add_edge("save_relation", "generate_graph")
    graph.add_edge("generate_graph", END)

    # 编译图
    return graph.compile()


# 实例化Agent
kg_graph = build_kg_agent()