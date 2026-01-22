"""
图谱解析与归一化（增强版）
- 支持：模型直接输出 JSON；或输出混杂文本（会尝试提取 JSON）
- 归一化：去重、补全字段、重新分配整数 id
- 输出：适配前端（id/source/target）与 Neo4j 导入
"""
import json
import re
from typing import Dict, Any, List, Tuple

def _extract_json(text: str) -> str:
    """从文本中尽量提取 JSON（兼容模型偶尔加的```json```）"""
    if not text:
        raise ValueError("empty text")
    # 去掉 ```json ``` 包裹
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if m:
        return m.group(1)
    # 直接找第一段 { ... }（贪婪到最后一个 }，再逐步回退）
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    raise ValueError("no json object found")

def _norm_float(x, default=0.6):
    try:
        v = float(x)
        if v < 0: v = 0.0
        if v > 1: v = 1.0
        return v
    except Exception:
        return float(default)

def normalize_graph(raw: Dict[str, Any], core_concept: str) -> Dict[str, Any]:
    """去重 + 重新编号 + 生成 edges 的整数 source/target"""
    nodes_in = raw.get("nodes", [])
    edges_in = raw.get("edges", [])

    # 强制核心节点
    core_name = raw.get("core_concept") or core_concept
    core_node = {
        "name": core_name,
        "discipline": "核心概念",
        "level": 0,
        "type": "concept",
        "description": f"核心概念：{core_name}",
        "confidence": 0.95
    }

    # 去重：按 (name_lower, discipline) 去重，优先保留更高 confidence
    def key(n): 
        return (str(n.get("name","")).strip().lower(), str(n.get("discipline","")).strip())
    best = {}
    for n in nodes_in:
        name = str(n.get("name","")).strip()
        disc = str(n.get("discipline","")).strip()
        if not name:
            continue
        nn = {
            "name": name,
            "discipline": disc or "未知",
            "level": int(n.get("level", 1)) if str(n.get("level","")).isdigit() else 1,
            "type": n.get("type","concept"),
            "description": str(n.get("description","")).strip()[:500],
            "confidence": _norm_float(n.get("confidence", 0.6))
        }
        k = key(nn)
        if k not in best or nn["confidence"] > best[k]["confidence"]:
            best[k] = nn

    # 确保核心节点存在且唯一
    best[(core_name.strip().lower(), "核心概念")] = core_node

    nodes = list(best.values())

    # disciplines
    disciplines = raw.get("disciplines") or []
    if "数学" not in disciplines: disciplines.append("数学")
    if "计算机科学" not in disciplines: disciplines.append("计算机科学")
    if "生物学" not in disciplines: disciplines.append("生物学")
    if "核心概念" not in disciplines: disciplines.insert(0, "核心概念")

    # 重新编号
    name_to_id = {}
    out_nodes = []
    for i, n in enumerate(nodes):
        out = dict(n)
        out["id"] = i
        out_nodes.append(out)
        name_to_id[out["name"]] = i

    # 处理边：丢弃找不到节点的边；自环保留但降置信度
    out_edges = []
    seen = set()
    eid = 0
    for e in edges_in:
        s = str(e.get("source","")).strip()
        t = str(e.get("target","")).strip()
        if not s or not t:
            continue
        if s not in name_to_id or t not in name_to_id:
            continue
        rel = str(e.get("relation","RELATES_TO")).strip() or "RELATES_TO"
        logic = str(e.get("logic","")).strip()[:800]
        conf = _norm_float(e.get("confidence", 0.6))
        if s == t:
            conf = min(conf, 0.4)
        k = (name_to_id[s], name_to_id[t], rel)
        if k in seen:
            continue
        seen.add(k)
        out_edges.append({
            "id": eid,
            "source": name_to_id[s],
            "target": name_to_id[t],
            "relation": rel,
            "logic": logic,
            "confidence": conf
        })
        eid += 1

    return {
        "core_concept": core_name,
        "disciplines": disciplines,
        "nodes": out_nodes,
        "edges": out_edges,
        "node_count": len(out_nodes),
        "edge_count": len(out_edges)
    }

class GraphParser:
    """兼容旧接口：parse(agent_output, core_concept) -> graph_data"""
    def parse(self, agent_output: str, core_concept: str) -> Dict[str, Any]:
        json_str = _extract_json(agent_output)
        raw = json.loads(json_str)
        return normalize_graph(raw, core_concept)

    def parse_to_json(self, agent_output: str, core_concept: str) -> str:
        graph = self.parse(agent_output, core_concept)
        return json.dumps(graph, ensure_ascii=False, indent=2)
