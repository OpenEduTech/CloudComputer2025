import json
import os
import re
from typing import Any, Dict, List, Optional


from llm_client import LLMClient

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _read_prompt(filename: str) -> str:
    path = os.path.join(PROMPT_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _extract_json_object(text: str) -> str:
    """
    更稳：提取第一个完整闭合的 JSON 对象 {...}
    - 处理字符串与转义，避免 details/evidence 中出现 { } 干扰
    - 返回从第一个 '{' 到与之匹配的 '}' 的子串
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model output")

    depth = 0
    in_str = False
    esc = False

    for i in range(start, len(text)):
        ch = text[i]

        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

    raise ValueError("Unclosed JSON object in model output")



def _strip_control_chars(s: str) -> str:
    # 删除 JSON 不允许的控制字符（保留 \n \r \t）
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)


def _repair_missing_commas_in_array(array_text: str) -> str:
    """
    只用于数组片段 [...]，修复常见的对象之间漏逗号问题：} { / }\n{
    注意：不要对整个 JSON blob 调用，避免误伤字符串内容。
    """
    s = array_text
    s = re.sub(r"}\s*{", "},{", s)
    return s


def _repair_json_heuristic(text: str) -> str:
    """
    保守启发式修复：
    1) 去掉 ``` 包裹
    2) 去掉多余尾逗号：,] / ,} -> ] / }
    3) 去控制字符（保留 \n \r \t）
    """
    s = text.strip()
    s = _strip_control_chars(s)

    # 去掉代码块包裹
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)

    # 去掉尾逗号
    s = re.sub(r",(\s*[\]}])", r"\1", s)

    return s


def _repair_edges_json_heuristic(s: str) -> str:
    s = _strip_control_chars(s)

    # 1) 统一去掉代码块
    s = re.sub(r"^```(?:json)?\s*", "", s.strip())
    s = re.sub(r"\s*```$", "", s)

    # 2) 修复 0, 85 这种“逗号小数”（只在数字上下文）
    #    允许空格：0,85 / 0, 85 / 0 ,85
    s = re.sub(r'(\d)\s*,\s*(\d)', r'\1.\2', s)

    # 3) 修复 "confidence": 0.9  "evidence": ... 中间缺逗号
    s = re.sub(r'("confidence"\s*:\s*[0-9]*\.?[0-9]+)\s+("evidence"\s*:)', r'\1, \2', s)

    # 4) 修复连续逗号：, ,  或  ,\s*,  -> ,
    s = re.sub(r',\s*,+', ',', s)

    # 5) 修复尾逗号（你已有，但再做一次无妨）
    s = re.sub(r",(\s*[\]}])", r"\1", s)

    return s



def _rule_filter(concept: str) -> Optional[Dict[str, Any]]:
    """
    规则层过滤明显无效输入：
    - 空/超长
    - URL
    - 明显疑问句/请求句（长度较长且包含疑问词）
    """
    raw = (concept or "").strip()

    if not raw:
        return {
            "valid": False,
            "normalized_concept": "",
            "canonical_en": "",
            "aliases": [],
            "reason": "输入为空。",
        }

    if len(raw) > 60:
        return {
            "valid": False,
            "normalized_concept": "",
            "canonical_en": "",
            "aliases": [],
            "reason": "输入过长，不像单一概念。",
        }

    if re.search(r"https?://|www\.", raw, re.IGNORECASE):
        return {
            "valid": False,
            "normalized_concept": "",
            "canonical_en": "",
            "aliases": [],
            "reason": "输入包含链接，不像学术概念。",
        }

    if len(raw) >= 10 and re.search(r"(怎么|为什么|如何|能不能|可不可以|请问|是不是)", raw):
        return {
            "valid": False,
            "normalized_concept": "",
            "canonical_en": "",
            "aliases": [],
            "reason": "输入更像问题句，不是概念词。",
        }

    if re.fullmatch(r"[\d\W_]+", raw):
        return {
            "valid": False,
            "normalized_concept": "",
            "canonical_en": "",
            "aliases": [],
            "reason": "输入缺少有效概念信息。",
        }

    return None


def _repair_json_via_llm(bad_json_text: str, client: LLMClient) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "你是 JSON 修复器。你的输出必须是严格 JSON："
                "只能使用双引号，不能有注释/省略号/尾逗号/多余文字。"
                "只输出一个 JSON 对象。"
            ),
        },
        {"role": "user", "content": f"修复为严格 JSON（字段含义不变）：\n{bad_json_text}"},
    ]
    # 不强依赖 json_mode（有些平台不生效），但开着也不坏
    return client.chat_completion(messages, temperature=0.0, max_tokens=900, json_mode=True)


def _extract_json_array_by_key(text: str, key: str) -> str:
    """
    提取形如: "key": [ ... ] 的最外层数组（保守解析）。
    """
    m = re.search(rf'"{re.escape(key)}"\s*:\s*\[', text)
    if not m:
        raise ValueError(f'No array key "{key}" found')
    start = m.end() - 1  # 指向 '['

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    raise ValueError(f'Unclosed array for key "{key}"')


def _extract_first_json_array(text: str) -> str:
    """
    从文本中提取第一个完整闭合的 JSON 数组 [...]（不依赖 key 是否合法）。
    处理字符串与转义，避免 evidence 里出现括号导致误判。
    """
    start = text.find("[")
    if start == -1:
        raise ValueError("No JSON array found")

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    raise ValueError("Unclosed JSON array")


def _parse_wrapped_array_best_effort(raw: str, key: str, client: LLMClient) -> Dict[str, Any]:
    # 1) 直接试
    try:
        return _parse_json_strict(raw, client)
    except Exception:
        pass

    # 2) 提取最外层 { ... }
    try:
        blob = _extract_json_object(raw)
    except Exception:
        blob = raw

    blob = _repair_json_heuristic(blob)

    # 3) 提取数组
    try:
        arr = _extract_json_array_by_key(blob, key)
    except Exception:
        m2 = re.search(r'^\s*{\s*"([^"]+)"\s*:\s*\[', blob)
        if m2:
            alt_key = m2.group(1)
            try:
                arr = _extract_json_array_by_key(blob, alt_key)
            except Exception:
                arr = _extract_first_json_array(blob)
        else:
            arr = _extract_first_json_array(blob)


    arr = _repair_json_heuristic(arr)
    if key == "edges":
        arr = _repair_edges_json_heuristic(arr)
    arr = _repair_missing_commas_in_array(arr)
    wrapped = json.dumps({key: []}, ensure_ascii=False).replace("[]", arr)
    wrapped = _repair_json_heuristic(wrapped)

    # 4) 先本地 loads
    try:
        return json.loads(wrapped)
    except json.JSONDecodeError:
        # 5) 让 LLM 修复“数组本身”
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 JSON 修复器。你的输出必须是严格 JSON 数组："
                    "只输出数组本身（以 [ 开头，以 ] 结尾），"
                    "必须使用英文双引号，不能有注释/省略号/尾逗号/多余文字。"
                ),
            },
            {"role": "user", "content": f"修复为严格 JSON 数组（字段含义不变）：\n{arr}"},
        ]
        fixed_arr = client.chat_completion(messages, temperature=0.0, max_tokens=1600, json_mode=True)
    
        s = _repair_json_heuristic(fixed_arr)

        # 先优先按 key 提取（如果 LLM 不小心包成 {"edges":[...]} 也能取到）
        try:
            arr2 = _extract_json_array_by_key(s, key)
        except Exception:
            # 再兜底提取“第一个完整闭合数组”
            arr2 = _extract_first_json_array(s)

        arr2 = _repair_json_heuristic(arr2)
        arr2 = _repair_missing_commas_in_array(arr2)  # 只对数组做 }{ -> },{
        # 注意：不要用 replace("[]", ...) 这种黑魔法，直接拼接最稳
        wrapped2 = f'{{"{key}":{arr2}}}'
        wrapped2 = _repair_json_heuristic(wrapped2)
        wrapped2 = _repair_edges_json_heuristic(wrapped2)  # ✅ 再兜一层
        return json.loads(wrapped2)
    


def _write_debug(name: str, content: str) -> None:
    """把 raw 输出落盘，方便你定位到底哪一行坏了。"""
    try:
        with open(name, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass



def _parse_json_strict(raw: str, client: LLMClient) -> Dict[str, Any]:
    """
    通用 JSON 解析：截取 -> 直接 loads -> 启发式 -> LLM 修复 -> 再启发式
    """
    json_blob = _extract_json_object(raw)

    # 1) 直接 parse
    try:
        return json.loads(json_blob)
    except json.JSONDecodeError:
        # 2) 启发式修复
        heuristic = _repair_json_heuristic(json_blob)
        try:
            return json.loads(heuristic)
        except json.JSONDecodeError:
            # 3) LLM 修复
            fixed = _repair_json_via_llm(heuristic, client)
            fixed_blob = _extract_json_object(fixed)
            fixed_blob = _repair_json_heuristic(fixed_blob)
            return json.loads(fixed_blob)



# -------------------------
# Step0
# -------------------------
def step0_validate_and_normalize(concept: str, client: LLMClient) -> Dict[str, Any]:
    """
    Step0：概念校验与规范化
    输出固定结构：
      {valid, normalized_concept, canonical_en, aliases, reason}
    """
    ruled = _rule_filter(concept)
    if ruled is not None:
        return ruled

    tpl = _read_prompt("step0_normalize.txt")
    prompt = tpl.replace("{concept}", concept.strip())

    messages = [
        {"role": "system", "content": "你是严谨的助手，只输出有效 JSON，不要输出多余文字。"},
        {"role": "user", "content": prompt},
    ]

    raw = client.chat_completion(messages, temperature=0.0, max_tokens=500, json_mode=True)

    try:
        obj = json.loads(_extract_json_object(raw))
    except json.JSONDecodeError:
        fixed = _repair_json_via_llm(raw, client)
        obj = json.loads(_extract_json_object(fixed))

    valid = bool(obj.get("valid", False))
    normalized = str(obj.get("normalized_concept", "")).strip()
    canonical_en = str(obj.get("canonical_en", "")).strip()
    aliases = obj.get("aliases", [])
    reason = str(obj.get("reason", "")).strip()

    if not isinstance(aliases, list):
        aliases = []
    aliases = [str(a).strip() for a in aliases if str(a).strip()][:3]

    if not valid:
        return {
            "valid": False,
            "normalized_concept": "",
            "canonical_en": "",
            "aliases": [],
            "reason": reason or "不确定是否为学术概念。",
        }

    if not normalized:
        normalized = concept.strip()

    if len(normalized) > 12:
        normalized = normalized[:12]

    return {
        "valid": True,
        "normalized_concept": normalized,
        "canonical_en": canonical_en,
        "aliases": aliases,
        "reason": reason or "判定为可用于图谱构建的抽象/学术概念。",
    }


# -------------------------
# Step1
# -------------------------
def step1_generate_candidates(step0: Dict[str, Any], client: LLMClient) -> Dict[str, Any]:
    """
    Step1：按 5 域生成候选 nodes（不生成 edges）
    返回：{"nodes":[...]}
    """
    tpl = _read_prompt("step1_candidates.txt")

    normalized = step0.get("normalized_concept", "").strip()
    canonical_en = step0.get("canonical_en", "").strip()
    aliases = step0.get("aliases", [])
    aliases_json = json.dumps(aliases, ensure_ascii=False)

    # 核心节点 id（安全可作为 key）
    core_id_raw = canonical_en or normalized
    core_id = re.sub(r"\W+", "_", core_id_raw).strip("_") or "CoreConcept"
    core_id = re.sub(r"[^A-Za-z0-9_\-]+", "_", core_id)

    prompt = (
        tpl.replace("{normalized_concept}", normalized)
           .replace("{canonical_en}", canonical_en)
           .replace("{aliases_json}", aliases_json)
           .replace("{core_id}", core_id)
    )

    messages = [
        {"role": "system", "content": "你是严谨的助手，只输出有效 JSON，不要输出多余文字。"},
        {"role": "user", "content": prompt},
    ]

    # ✅ 首选 JSON 模式（若服务端支持会更稳）
    raw = client.chat_completion(messages, temperature=0.2, max_tokens=1600, json_mode=True)

    # 只取出 JSON 主体再修复（避免 explanation 干扰）
    json_blob = _extract_json_object(raw)

    # 1) 直接 parse
    try:
        obj = json.loads(json_blob)
    except json.JSONDecodeError:
        # 2) 本地启发式修复后再 parse
        heuristic = _repair_json_heuristic(json_blob)
        try:
            obj = json.loads(heuristic)
        except json.JSONDecodeError:
            # 3) 仍失败：把“截取出的 JSON 子串”交给 LLM 修复（更容易成功）
            fixed = _repair_json_via_llm(heuristic, client)
            fixed_blob = _extract_json_object(fixed)
            fixed_blob = _repair_json_heuristic(fixed_blob)  # 再兜底一次
            obj = json.loads(fixed_blob)


    nodes = obj.get("nodes", [])
    if not isinstance(nodes, list) or len(nodes) == 0:
        raise ValueError("Step1 returned empty nodes")

    return {"nodes": nodes}

# -------------------------
# Step2
# -------------------------
def step2_enrich_nodes(step1: Dict[str, Any], client: LLMClient) -> Dict[str, Any]:
    """
    Step2：为每个 node 补充 details/key_points/reading_hint（用于前端点击展开）
    返回：{"nodes":[{id, details, key_points, reading_hint}, ...]}
    """
    nodes = step1.get("nodes", [])
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("Step2 input nodes empty")

    # 控制输入长度：只给模型必要字段（避免超长导致超时/截断）
    compact_nodes = []
    for n in nodes:
        compact_nodes.append(
            {
                "id": n.get("id"),
                "label": n.get("label"),
                "field": n.get("field"),
                "type": n.get("type"),
                "summary": n.get("summary"),
                "aliases": n.get("aliases", []),
            }
        )

    tpl = _read_prompt("step2_enrich.txt")
    prompt = tpl.replace("{nodes_json}", json.dumps(compact_nodes, ensure_ascii=False))

    messages = [
        {"role": "system", "content": "你是严谨的助手，只输出有效 JSON，不要输出多余文字。"},
        {"role": "user", "content": prompt},
    ]
    
    raw = client.chat_completion(messages, temperature=0.2, max_tokens=3200, json_mode=True)
    _write_debug("debug_step2_raw.txt", raw)

    try:
        obj = _parse_wrapped_array_best_effort(raw, "nodes", client)
    except ValueError as e:
        if 'Unclosed array for key "nodes"' in str(e):
            messages_retry = [
                {
                    "role": "system",
                    "content": (
                        '只输出严格 JSON 对象，根键必须为 "nodes"；'
                        '禁止任何额外文字；必须完整闭合所有括号与数组；'
                        'details 字段禁止真实换行。'
                    ),
                },
                {"role": "user", "content": prompt},
            ]
            raw2 = client.chat_completion(messages_retry, temperature=0.1, max_tokens=3600, json_mode=True)
            _write_debug("debug_step2_raw_retry.txt", raw2)
            obj = _parse_wrapped_array_best_effort(raw2, "nodes", client)
        else:
            raise


    enriched = obj.get("nodes", [])
    if not isinstance(enriched, list) or not enriched:
        raise ValueError("Step2 returned empty nodes")

    # 必须覆盖所有输入 id
    in_ids = [str(n.get("id")) for n in nodes if n.get("id") is not None]
    out_map = {str(x.get("id")): x for x in enriched if x.get("id") is not None}

    missing = [i for i in in_ids if i not in out_map]
    if missing:
        raise ValueError(f"Step2 missing ids: {missing}")

    cleaned = []
    for nid in in_ids:
        x = out_map[nid]
        kp = x.get("key_points", [])
        if not isinstance(kp, list):
            kp = []
        cleaned.append(
            {
                "id": nid,
                "details": str(x.get("details", "")).strip(),
                "key_points": [str(t).strip() for t in kp if str(t).strip()][:5],
                "reading_hint": str(x.get("reading_hint", "")).strip(),
            }
        )
    return {"nodes": cleaned}


def merge_step2_into_nodes(step1_nodes: List[Dict[str, Any]], step2_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    把 Step2 的 details/key_points/reading_hint 合并回 Step1 nodes
    """
    extra_map = {x["id"]: x for x in step2_nodes if "id" in x}
    merged = []
    for n in step1_nodes:
        nid = str(n.get("id"))
        nn = dict(n)
        extra = extra_map.get(nid, {})
        for k in ("details", "key_points", "reading_hint"):
            if k in extra:
                nn[k] = extra[k]
        merged.append(nn)
    return merged


# -------------------------
# Step3
# -------------------------
def step3_generate_edges(nodes_merged: List[Dict[str, Any]], client: LLMClient) -> Dict[str, Any]:
    """
    Step3：基于 nodes 生成 edges（关系必须可解释）
    返回：{"edges":[...]}
    - 重点：更稳输出、更稳解析、更稳兜底
    """
    if not isinstance(nodes_merged, list) or not nodes_merged:
        raise ValueError("Step3 input nodes_merged empty")

    # ---- 1) 压缩输入（避免 prompt 太长导致输出不稳/截断）----
    compact_nodes = []
    for n in nodes_merged:
        compact_nodes.append(
            {
                "id": n.get("id"),
                "label": n.get("label"),
                "field": n.get("field"),
                "type": n.get("type"),
                "summary": n.get("summary"),
                "aliases": n.get("aliases", []),
            }
        )

    tpl = _read_prompt("step3_edges.txt")
    prompt = tpl.replace("{nodes_json}", json.dumps(compact_nodes, ensure_ascii=False))

    # ---- 2) 统一的 ID 归一化工具（用于 source/target 修复）----
    def _norm_id(x: str) -> str:
        x = (x or "").strip().lower()
        x = re.sub(r"[\s\-]+", "_", x)
        x = re.sub(r"_+", "_", x)
        return x

    node_ids = [str(n.get("id")) for n in nodes_merged if n.get("id") is not None]
    node_id_set = set(node_ids)
    id_map = {_norm_id(i): i for i in node_ids}

    # ---- 3) 轻量 schema 清洗（只保留允许字段，修正小数/缺字段/非法值）----
    allowed_relation_types = {"直接关联", "类比关联", "数学关联", "先修依赖", "应用关联", "因果/机制", "相对/对比", "其他"}
    allowed_directions = {"directed", "undirected"}

    def _clean_edge(e: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(e, dict):
            return None

        s_raw = str(e.get("source", "")).strip()
        t_raw = str(e.get("target", "")).strip()
        if not s_raw or not t_raw:
            return None

        s_fixed = id_map.get(_norm_id(s_raw), s_raw)
        t_fixed = id_map.get(_norm_id(t_raw), t_raw)
        if s_fixed not in node_id_set or t_fixed not in node_id_set or s_fixed == t_fixed:
            return None

        relation = str(e.get("relation", "")).strip()
        relation_type = str(e.get("relation_type", "")).strip()
        evidence = str(e.get("evidence", "")).strip()
        direction = str(e.get("direction", "")).strip()

        if not relation or not evidence:
            return None
        if relation_type not in allowed_relation_types:
            return None
        if direction not in allowed_directions:
            return None

        # confidence：允许 "0.85" / 0.85 / "0,85" / 0,85（最后两种尽量修）
        conf = e.get("confidence", 0.0)
        if isinstance(conf, str):
            conf = conf.strip().replace(",", ".")
        try:
            conf_f = float(conf)
        except Exception:
            return None

        # 基本范围裁剪
        if conf_f < 0.0:
            conf_f = 0.0
        if conf_f > 1.0:
            conf_f = 1.0

        out = {
            "source": s_fixed,
            "target": t_fixed,
            "relation": relation[:16],            # 你 Step3 限制 <=16
            "relation_type": relation_type,
            "confidence": conf_f,
            "evidence": evidence[:40],           # 你 Step3 希望 35~40
            "direction": direction,
        }

        # 可选字段：reasoning_chain / bridge_concepts
        rc = e.get("reasoning_chain")
        if isinstance(rc, list):
            rc2 = [str(x).strip().replace("\n", " ").replace("\r", " ") for x in rc if str(x).strip()]
            if 2 <= len(rc2) <= 4:
                out["reasoning_chain"] = rc2[:4]

        bc = e.get("bridge_concepts")
        if isinstance(bc, list):
            bc2 = [str(x).strip() for x in bc if str(x).strip()]
            # 只保留存在的节点 id，防止污染
            bc2 = [id_map.get(_norm_id(x), x) for x in bc2]
            bc2 = [x for x in bc2 if x in node_id_set]
            if bc2:
                out["bridge_concepts"] = bc2[:3]

        return out

    # ---- 4) 请求 + 解析 + 清洗 的封装（方便重试）----
    def _run_once(*, temperature: float, max_tokens: int, suffix_rule: str, debug_name: str) -> List[Dict[str, Any]]:
        sys_msg = (
            '只输出严格 JSON 对象，根键必须为 "edges"；'
            "禁止任何额外字符；"
            "禁止输出 tags/sources 等非白名单字段；"
            "所有小数使用英文句点 '.'；"
            + suffix_rule
        )
        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": prompt},
        ]
        raw = client.chat_completion(messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)
        _write_debug(debug_name, raw)

        obj = _parse_wrapped_array_best_effort(raw, "edges", client)
        edges = obj.get("edges", [])
        if not isinstance(edges, list):
            return []

        cleaned = []
        seen = set()
        for e in edges:
            ce = _clean_edge(e)
            if not ce:
                continue
            k = (ce["source"], ce["target"], ce["relation_type"])
            if k in seen:
                continue
            seen.add(k)
            cleaned.append(ce)

        return cleaned

    # ---- 5) 策略：先用稳定输出（temp=0），失败/太少再重试（更短、更强约束）----
    # 第一次：正常目标（12-16条），但输出长度控制更合理
    edges1 = _run_once(
        temperature=0.0,
        max_tokens=4000,
        suffix_rule="若长度可能超出，请将 edges 数量控制在 12~16 条。",
        debug_name="debug_step3_raw.txt",
    )

    # 如果清洗后太少，第二次：更强约束，减少数量、缩短 evidence、限制 reasoning_chain
    if len(edges1) < 8:
        edges2 = _run_once(
            temperature=0.0,
            max_tokens=3600,
            suffix_rule=(
                "必须输出 10~12 条 edges；"
                "evidence 必须 <= 28 字；"
                "reasoning_chain 仅允许 2~3 步；"
                "优先保证数组与括号完整闭合。"
            ),
            debug_name="debug_step3_raw_retry.txt",
        )
        edges1 = edges2

    if len(edges1) < 8:
        raise ValueError("Step3 too many invalid edges filtered; check step3 prompt or model output stability")

    return {"edges": edges1}




def run_step0_only(concept: str) -> Dict[str, Any]:
    client = LLMClient()
    return step0_validate_and_normalize(concept, client)


def run_step0_step1(concept: str) -> Dict[str, Any]:
    client = LLMClient()
    step0 = step0_validate_and_normalize(concept, client)
    if not step0.get("valid"):
        return {"step0": step0, "step1": {"nodes": []}}
    step1 = step1_generate_candidates(step0, client)
    return {"step0": step0, "step1": step1}


def run_step0_step1_step2(concept: str) -> Dict[str, Any]:
    client = LLMClient()
    step0 = step0_validate_and_normalize(concept, client)
    if not step0.get("valid"):
        return {"step0": step0, "step1": {"nodes": []}, "step2": {"nodes": []}, "nodes_merged": []}

    step1 = step1_generate_candidates(step0, client)
    step2 = step2_enrich_nodes(step1, client)
    merged = merge_step2_into_nodes(step1["nodes"], step2["nodes"])
    return {"step0": step0, "step1": step1, "step2": step2, "nodes_merged": merged}
