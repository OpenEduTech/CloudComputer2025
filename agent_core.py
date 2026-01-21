# agent_core.py
from zhipu_client import call_glm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def expand_slide_content(original_text):
    """
    对单页 PPT 内容进行扩展，并加入校验层防止幻觉。
    
    流程：
      Step 1: 理解并扩展内容（要求具体、有例子）
      Step 2: 让模型自我校验：“以上内容是否有事实错误或虚构？”
    
    Args:
        original_text (str): 原始 PPT 页面文本
    
    Returns:
        dict: 包含 'expanded' 和 'is_verified' 字段
    """
    # === Step 1: 扩展内容 ===
    expand_prompt = f"""你是一位专业的教学内容增强助手。请基于以下 PPT 页面内容，生成一段**补充说明**，要求：
- 保持原意，不歪曲事实
- 补充背景知识、实际案例、应用场景或通俗解释
- 语言简洁、适合学生理解
- 如果原文涉及专业术语，请简要定义
- 不要编造数据、人名、事件或不存在的引用

原始内容：
{original_text}

请直接输出扩展后的内容，不要加标题或前缀。"""

    expanded = call_glm([
        {"role": "user", "content": expand_prompt}
    ])

    if not expanded:
        logger.warning("扩展内容生成失败")
        return {"expanded": "", "is_verified": False, "error": "LLM call failed"}

    # === Step 2: 校验层（Check Layer）===
    verify_prompt = f"""请严格检查以下“扩展内容”是否包含以下问题：
- 虚构事实（如编造数据、事件、人物、论文）
- 与“原始内容”矛盾
- 过度推测或未经证实的断言

原始内容：
{original_text}

扩展内容：
{expanded}

请仅回答“通过”或“不通过”。如果“不通过”，请在下一行简要说明原因（不超过20字）。"""

    verification = call_glm([
        {"role": "user", "content": verify_prompt}
    ], temperature=0.1)  # 降低随机性，提高判断一致性

    is_verified = False
    reason = ""

    if verification:
        lines = verification.strip().split("\n")
        first_line = lines[0].strip()
        if "通过" in first_line:
            is_verified = True
        else:
            reason = lines[1].strip() if len(lines) > 1 else "未通过校验"

    logger.info(f"内容扩展 {'✅ 通过校验' if is_verified else '❌ 未通过校验'}")

    return {
        "expanded": expanded,
        "is_verified": is_verified,
        "verification_reason": reason if not is_verified else ""
    }


def process_ppt_slides(slides_data):
    """
    处理整个 PPT 的所有页面。
    
    Args:
        slides_data (list): 来自 input_handler.extract_text_from_pptx 的结果
    
    Returns:
        list: 每页处理结果，包含原始内容、扩展内容、校验状态
    """
    results = []
    for slide in slides_data:
        logger.info(f"正在处理第 {slide['slide_index'] + 1} 页...")
        result = expand_slide_content(slide["text"])
        results.append({
            "slide_index": slide["slide_index"],
            "original": slide["text"],
            **result
        })
    return results