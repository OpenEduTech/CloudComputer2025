from langchain_core.tools import tool
from app.db.neo4j_conn import get_neo4j_driver
import json
from datetime import datetime
import uuid


# 生成UUID工具函数
def generate_uuid() -> str:
    return str(uuid.uuid4())


import json
import re
from langchain_core.tools import tool
# 确保导入LLM配置
from app.agent.llm_config import get_llm
from langchain_core.prompts import ChatPromptTemplate


@tool
def validate_concept(concept: str) -> str:
    """
    工具0：验证输入概念的有效性（Agent自主语义判断+规则校验）
    Args:
        concept: 待校验的概念名称（如"熵"、"测试123"、"科学"）
    Returns:
        JSON字符串：{"valid": true/false, "reason": "校验理由（≤80字）"}
    """
    # 步骤1：基础规则校验（字符合法性）
    valid_char_pattern = r'^[\u4e00-\u9fa5a-zA-Z0-9αβγδεζηθικλμνξοπρστυφχψω∑∏∫√∝∞≠≤≥]+$'
    if not re.match(valid_char_pattern, concept):
        return json.dumps({
            "valid": False,
            "reason": f"包含非法字符，仅支持中文/英文/数字/常见学科符号（如α、∑）"
        })

    # 步骤2：Agent（LLM）语义校验（核心逻辑）
    try:
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template("""
        你是知识图谱概念有效性校验专家，基于以下规则判断概念是否有效：
        1. 有效概念：具体的、有科学/学科意义的概念（如"熵"、"神经网络"、"最小二乘法"）；
        2. 无效概念：无意义词汇/过于宽泛词汇/非学科概念（如"随便"、"科学"、"吃饭"）；
        严格遵守以下规则：
        1. 仅基于语义理解判断，禁止字面匹配；
        2. 不确定则返回valid: false，reason说明具体原因；
        3. 仅返回JSON字符串，格式：{{"valid": true/false, "reason": "具体理由"}}，无其他文字；
        4. reason长度≤80字，语言简洁。

        待判断概念：{concept}
        """)

        chain = prompt | llm
        response = chain.invoke({
            "concept": concept
        })
        # 直接返回LLM生成的JSON
        return response.content.strip()

    # 步骤3：LLM调用失败时的兜底校验（保证工具鲁棒性）
    except Exception as e:
        # 兜底规则：匹配无意义词汇列表
        invalid_concepts = ["随便", "测试", "123", "abc", "无", "空", "默认", "测试123", "默认值", "未知", "空值"]
        if any(invalid_str in concept for invalid_str in invalid_concepts):
            return json.dumps({
                "valid": False,
                "reason": f"无意义词汇，仅支持具体的学科概念（如“熵”“神经网络”）"
            })
        # 兜底判定为有效
        return json.dumps({
            "valid": True,
            "reason": f"概念有效（LLM校验异常兜底判断，错误：{str(e)[:20]}）"
        })

@tool
def query_db(concept: str) -> str:
    """
    工具1：查询Neo4j数据库中指定概念的所有合法关联节点和关系
    Args:
        concept: 核心概念名称（如"熵"）
    Returns:
        JSON字符串：包含源概念、已有关联节点列表（名称、领域、关系、强度）
    """
    driver = None
    try:
        driver = get_neo4j_driver()
    except Exception as e:
        print(f"❌ 重新初始化driver失败：{e}")
    if not driver:
        return json.dumps({"status": "error", "msg": "数据库未连接"})

    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Concept {name: $concept})-[r:RELATION {is_valid: true}]->(related)
                RETURN c.name as source,
                       collect({
                           target: related.name,
                           domain: related.domain,
                           relation: r.relation,
                           strength: r.strength,
                           version: COALESCE(r.version, 1)
                       }) as related_nodes
            """, concept=concept)
            record = result.single()
            if not record:
                return json.dumps({
                    "status": "success",
                    "data": {"source": concept, "related_nodes": []}
                })
            return json.dumps({"status": "success", "data": record.data()})
    except Exception as e:
        return json.dumps({"status": "error", "msg": str(e)})


@tool
def expand_relation(concept: str, existing_relations: str) -> str:
    """
    工具2：基于核心概念和已有关联，扩展新的跨学科关联
    必须从数学/物理/计算机/生物/社会学/化学/经济学中选择不同领域的概念，避免重复
    Args:
        concept: 核心概念名称
        existing_relations: query_db工具返回的JSON字符串（已有关联）
    Returns:
        JSON字符串：包含3个新关联（名称、领域、定义、关系、强度）
    """
    from app.agent.llm_config import get_llm
    from langchain_core.prompts import ChatPromptTemplate
    llm = get_llm()

    # 解析已有关联，避免重复
    existing_data = json.loads(existing_relations)
    existing_nodes = [rel["target"] for rel in existing_data["data"].get("related_nodes", [])]
    prompt = ChatPromptTemplate.from_template("""
    你是跨学科关联挖掘专家，基于以下信息扩展新关联：
    1. 核心概念：{concept}
    2. 已有关联节点（避免重复）：{existing_nodes}
    3. 严格遵守以下规则：
       - 生成5个新的跨学科关联，每个关联来自不同学科领域（数学/物理/计算机/生物/社会学/化学/经济学）；
       - 禁止生成已有关联节点、自关联（如A→A）、无意义关联；
       - 每个关联必须基于客观科学知识，禁止编造不存在的概念/关联；
       - 关联逻辑必须包含具体科学依据，而非泛泛而谈；
       - 关联强度（strength）按相关性打分（1-5，越高越相关）；
       - 仅返回JSON数组，格式：[{{"name":"概念名","domain":"领域","definition":"1句话定义","relation":"2句话关联逻辑","strength":数值}}]，无其他文字。
    """)
    chain = prompt | llm
    response = chain.invoke({
        "concept": concept,
        "existing_nodes": existing_nodes
    })
    return response.content.strip()


@tool
def validate_relation(core_name: str, rel_name: str, relation: str) -> str:
    """
    工具3：验证核心概念与关联概念的逻辑合理性（反幻觉）
    Args:
        core_name: 核心概念名称
        rel_name: 关联概念名称
        relation: 关联逻辑描述
    Returns:
        JSON字符串：{"valid": true/false, "reason": "校验理由（≤50字）"}
    """
    from app.agent.llm_config import get_llm
    from langchain_core.prompts import ChatPromptTemplate
    llm = get_llm()

    prompt = ChatPromptTemplate.from_template("""
    你是科学知识逻辑校验专家，基于客观公开的科学知识判断以下关联是否合理：
    核心概念：{core_name}
    关联概念：{rel_name}
    关联逻辑：{relation}
    严格遵守以下规则：
    1. 若关联逻辑包含编造的事实/不存在的概念，返回valid: false，reason说明具体错误；
    2. 若关联逻辑泛泛而谈（如"两者有关联"），返回valid: false，reason要求补充具体依据；
    3. 仅基于科学知识判断，禁止猜测，不确定则返回valid: false；
    4. 仅返回JSON字符串，格式：{{"valid": true/false, "reason": "具体理由"}}，无其他文字。
    """)

    chain = prompt | llm
    response = chain.invoke({
        "core_name": core_name,
        "rel_name": rel_name,
        "relation": relation
    })
    return response.content.strip()


@tool
def save_relation(relation_data: str) -> str:
    """
    工具4：将校验通过的关联存入Neo4j数据库（MERGE去重）
    Args:
        relation_data: JSON字符串，包含source/target/source_domain/target_domain/source_def/target_def/relation/strength
    Returns:
        JSON字符串：存储结果
    """
    driver = None
    try:
        driver = get_neo4j_driver()
    except Exception as e:
        print(f"❌ 重新初始化driver失败：{e}")
    if not driver:
        return json.dumps({"status": "error", "msg": "数据库未连接"})

    try:
        data = json.loads(relation_data)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with driver.session() as session:
            # 保存核心节点
            session.run("""
                MERGE (c:Concept {name: $source})
                SET c.id = COALESCE(c.id, $source_id),
                    c.domain = $source_domain,
                    c.definition = $source_def,
                    c.create_time = COALESCE(c.create_time, $now),
                    c.update_time = $now
            """, source=data["source"], source_id=generate_uuid(),
                        source_domain=data.get("source_domain", "未知"),
                        source_def=data.get("source_def", "未知"), now=now)

            # 保存关联节点
            session.run("""
                MERGE (r:Concept {name: $target})
                SET r.id = COALESCE(r.id, $target_id),
                    r.domain = $target_domain,
                    r.definition = $target_def,
                    r.create_time = COALESCE(r.create_time, $now),
                    r.update_time = $now
            """, target=data["target"], target_id=generate_uuid(),
                        target_domain=data["target_domain"],
                        target_def=data["target_def"], now=now)

            # 保存关系（默认合法）
            session.run("""
                MATCH (c:Concept {name: $source}), (r:Concept {name: $target})
                MERGE (c)-[e:RELATION]->(r)
                SET e.relation = $relation,
                    e.strength = $strength,
                    e.is_valid = true,
                    e.version = COALESCE(e.version, 1),
                    e.create_time = COALESCE(e.create_time, $now),
                    e.update_time = $now
            """, source=data["source"], target=data["target"],
                        relation=data["relation"], strength=data["strength"], now=now)

        return json.dumps({"status": "success", "msg": f"成功存储{data['source']}→{data['target']}"})
    except Exception as e:
        return json.dumps({"status": "error", "msg": str(e)})


@tool
def delete_relation(core_name: str, rel_name: str) -> str:
    """
    工具5：软删除无效关联（置is_valid=false，保留记录）
    Args:
        core_name: 核心概念名称
        rel_name: 关联概念名称
    Returns:
        JSON字符串：删除结果
    """
    driver = None
    try:
        driver = get_neo4j_driver()
    except Exception as e:
        print(f"❌ 重新初始化driver失败：{e}")
    if not driver:
        return json.dumps({"status": "error", "msg": "数据库未连接"})

    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with driver.session() as session:
            session.run("""
                MATCH (c:Concept {name: $core_name})-[r:RELATION]->(r2:Concept {name: $rel_name})
                SET r.is_valid = false,
                    r.delete_time = $now,
                    r.update_time = $now
            """, core_name=core_name, rel_name=rel_name, now=now)
        return json.dumps({"status": "success", "msg": f"已标记{core_name}→{rel_name}为无效关联"})
    except Exception as e:
        return json.dumps({"status": "error", "msg": str(e)})


@tool
def update_relation(core_name: str, rel_name: str, new_relation: str, new_strength: int) -> str:
    """
    工具6：更新关联的逻辑/强度（保留版本）
    Args:
        core_name: 核心概念
        rel_name: 关联概念
        new_relation: 新的关联逻辑
        new_strength: 新的强度（1-5）
    Returns:
        JSON字符串：更新结果
    """
    driver = None
    try:
        driver = get_neo4j_driver()
    except Exception as e:
        print(f"❌ 重新初始化driver失败：{e}")
    if not driver:
        return json.dumps({"status": "error", "msg": "数据库未连接"})

    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with driver.session() as session:
            # 保留旧版本
            session.run("""
                MATCH (c:Concept {name: $core_name})-[r:RELATION]->(r2:Concept {name: $rel_name})
                SET r.old_relation = r.relation,
                    r.old_strength = r.strength,
                    r.version = COALESCE(r.version, 1) + 1,
                    r.update_time = $now
            """, core_name=core_name, rel_name=rel_name, now=now)

            # 更新新值
            session.run("""
                MATCH (c:Concept {name: $core_name})-[r:RELATION]->(r2:Concept {name: $rel_name})
                SET r.relation = $new_relation,
                    r.strength = $new_strength
            """, core_name=core_name, rel_name=rel_name,
                        new_relation=new_relation, new_strength=new_strength)

        return json.dumps({"status": "success", "msg": "关联更新成功"})
    except Exception as e:
        return json.dumps({"status": "error", "msg": str(e)})


@tool
def mark_abnormal(core_name: str, rel_name: str) -> str:
    """
    工具7：标记异常关联（强度低/理由模糊）
    Args:
        core_name: 核心概念
        rel_name: 关联概念
    Returns:
        JSON字符串：标记结果
    """
    driver = None
    try:
        driver = get_neo4j_driver()
    except Exception as e:
        print(f"❌ 重新初始化driver失败：{e}")
    if not driver:
        return json.dumps({"status": "error", "msg": "数据库未连接"})

    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with driver.session() as session:
            session.run("""
                MATCH (c:Concept {name: $core_name})-[r:RELATION]->(r2:Concept {name: $rel_name})
                SET r.abnormal = true,
                    r.mark_time = $now,
                    r.update_time = $now
            """, core_name=core_name, rel_name=rel_name, now=now)
        return json.dumps({"status": "success", "msg": "已标记为异常关联"})
    except Exception as e:
        return json.dumps({"status": "error", "msg": str(e)})


# 工具列表（供Agent绑定）
neo4j_tools = [
    query_db, expand_relation, validate_relation,
    save_relation, delete_relation, update_relation, mark_abnormal
]