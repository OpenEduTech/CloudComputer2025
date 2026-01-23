"""
LLM Agent 与工具链封装。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from langchain_openai import ChatOpenAI

from core.ppt_parser import Slide
from core.vector_store import query_similar_slides
from core.external_knowledge import search_external_knowledge


# 为了避免在代码仓库中硬编码密钥，这里通过环境变量读取：
# - SILICONFLOW_API_KEY:    硅基流动提供的 API Key
# - SILICONFLOW_BASE_URL:  可选，自定义 Base URL；默认使用官方兼容地址
# - DEEPSEEK_MODEL:        可选，自定义模型名；默认使用 deepseek-ai/DeepSeek-V3.2-Exp
SILICONFLOW_API_KEY_ENV = "SILICONFLOW_API_KEY"
SILICONFLOW_BASE_URL_ENV = "SILICONFLOW_BASE_URL"
DEEPSEEK_MODEL_ENV = "DEEPSEEK_MODEL"


@dataclass
class AgentConfig:
    """Agent 的基础配置。"""

    use_wikipedia: bool = True
    top_k_slides: int = 5
    top_k_wiki: int = 3


def build_slide_context_from_retrieval(
    slide: Slide,
    top_k: int,
    ppt_id: str | None = None,
) -> str:
    """基于当前 slide 的标题做一次语义检索，返回可供拼接的文本上下文。"""

    parts: List[str] = []
    if slide.title:
        parts.append(slide.title)
    if slide.bullets:
        parts.extend(slide.bullets[:8])
    query_text = "\n".join([p.strip() for p in parts if p and p.strip()])
    if not query_text.strip():
        return ""

    results = query_similar_slides(query_text=query_text, n_results=top_k)
    metadatas = results.get("metadatas", [[]])[0]
    documents = results.get("documents", [[]])[0]

    lines: List[str] = []
    for meta, doc in zip(metadatas, documents):
        if not isinstance(meta, dict):
            continue
        if ppt_id and meta.get("ppt_id") != ppt_id:
            continue
        idx = meta.get("slide_index")
        title = meta.get("title")
        lines.append(f"[相关页 index={idx}, title={title}]\n{doc}")

    return "\n\n".join(lines)


def build_prompt_for_slide_expansion(
    slide: Slide,
    retrieved_context: str,
    wiki_snippets: List[str],
) -> str:
    """构造用于 DeepSeek 等 LLM 的扩展提示词。"""

    wiki_block = "\n\n".join(wiki_snippets) if wiki_snippets else "无"
    bullets_block = "\n- ".join(slide.bullets) if slide.bullets else "无"

    return f"""你是一个帮助学生考前复习的智能助教，需要根据 PPT 内的一页内容，
结合相关页面与外部知识，生成结构化的扩展讲解笔记。

重要约束：
1. 只允许基于下方提供的「当前 PPT 页面」「PPT 内部相关页面（检索得到）」「外部知识片段」进行推理与改写；
2. 若材料中找不到支撑某个结论/数字/定义，请明确写“材料不足/待查证/可能”，不要编造；
3. 尽量在关键结论句末尾标注来源标签：[PPT] / [检索] / [arXiv: 论文标题]，例如：[arXiv: PyramidTNT]。

在生成最终答案前，请显式执行一个两阶段的 Checklayer 过程：
1. Self-consistency 检查：对你即将输出的要点、公式、示例代码进行自我审查，避免前后矛盾、逻辑不一致或同一段内容反复重复；
2. 事实与上下文校验：对照下面给出的「PPT 内部相关页面」和「arXiv」，判断关键结论是否与上下文明显冲突，如发现冲突或高度不确定，请在答案中标注“可能/待查证”，并避免给出过于确定的错误结论。

【当前 PPT 页面】
索引: {slide.index}
标题: {slide.title}
要点:
- {bullets_block}
备注: {slide.notes or '无'}

【PPT 内部相关页面（检索得到）】
{retrieved_context or '无相关页面'}

【外部知识片段】
{wiki_block}

请用简体中文输出本页的扩展讲解，包含以下几个部分：
1. 背景说明
2. 知识点详细解释（可包含公式推导/关键步骤）
3. 示例（代码或生活类比均可）
4. 延伸阅读建议
5. AI 自评（见下方要求）
6. Checklayer

要求：
- 注意与原 PPT 标题和要点保持语义一致，不要偏题；
- 如不确定某个细节，请标明“可能”而不是编造确定性结论；
- 输出使用 Markdown 一级小标题分段；
- 示例代码只给出一份，保持简洁，不要多次重复相同的训练和预测语句或完全相同的代码块；
- 优先参考提供的检索结果和 Wikipedia 片段，避免明显违背这些上下文的“离谱内容”；
- 在正文最后增加一个名为“# AI 自评”的小节，用 3 行以内内容，按 1-5 分（5 为最好）简单评价：
  - 本次笔记的逻辑结构是否清晰（给出评分和一句理由，例如“4/5：结构清晰，但示例部分略短”）；
  - 联想内容与原 PPT 内容的语义相关度（给出评分和一句理由，例如“5/5：所有扩展都围绕原主题展开，没有明显跑题”）。
"""


def call_llm(prompt: str, api_key: Optional[str] = None) -> str:
    """调用 LLM 的占位函数。

    - 预留 DeepSeek API Key 的位置：
      默认从环境变量 `SILICONFLOW_API_KEY` 读取，如未提供则仅返回占位说明。
    - 使用硅基流动的 OpenAI 兼容接口，通过 LangChain 的 ChatOpenAI 客户端调用 DeepSeek 模型。
    """
    key = api_key or os.getenv(SILICONFLOW_API_KEY_ENV)
    if not key:
        # 无 API Key 时，返回占位内容，保证示例链路可在本地跑通
        return (
            "【占位输出】此处应为通过硅基流动调用 DeepSeek 模型后返回的扩展讲解内容。"
            "请在部署环境中配置 SILICONFLOW_API_KEY，并按 README 中说明设置 Base URL 与模型名。"
        )

    base_url = os.getenv(
        SILICONFLOW_BASE_URL_ENV, "https://api.siliconflow.cn/v1"
    )
    model = os.getenv(DEEPSEEK_MODEL_ENV, "deepseek-ai/DeepSeek-V3.2-Exp")

    try:
        chat = ChatOpenAI(
            api_key=key,
            base_url=base_url,
            model=model,
            max_retries=3,
            temperature=0.2,
        )

        from langchain_core.messages import SystemMessage, HumanMessage

        messages = [
            SystemMessage(content="你是一个严谨的学习辅导智能体。"),
            HumanMessage(content=prompt),
        ]

        response = chat.invoke(messages)
        return response.content
    except Exception as exc:
        # 网络/HTTP/客户端错误时，降级为占位输出
        return (
            "【占位输出】调用 DeepSeek LLM 过程中出现错误："
            f"{exc}。请检查网络、API Key、Base URL 以及 LangChain 配置。"
        )


def expand_slide_with_tools(
    slide: Slide,
    config: Optional[AgentConfig] = None,
    ppt_id: str | None = None,
) -> str:
    """综合使用向量检索与 外部知识源，生成单页 PPT 的扩展讲解。
    """

    cfg = config or AgentConfig()

    retrieved_context = build_slide_context_from_retrieval(
        slide, top_k=cfg.top_k_slides, ppt_id=ppt_id
    )

    wiki_snippets: List[str] = []
    if cfg.use_wikipedia and slide.title:
        wiki_snippets = search_external_knowledge(
            slide.title,
            max_results=cfg.top_k_wiki,
        )

    prompt = build_prompt_for_slide_expansion(
        slide=slide,
        retrieved_context=retrieved_context,
        wiki_snippets=wiki_snippets,
    )

    return call_llm(prompt)
