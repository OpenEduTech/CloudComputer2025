# output_formatter.py
import json
import os
from datetime import datetime


def format_as_markdown(results, title="PPT内容扩展报告"):
    """
    将处理结果格式化为 Markdown 文档。
    
    Args:
        results (list): 来自 agent_core.process_ppt_slides 的结果列表
        title (str): 报告标题
    
    Returns:
        str: 完整的 Markdown 内容
    """
    md_lines = []
    md_lines.append(f"# {title}")
    md_lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    for res in results:
        page_num = res["slide_index"] + 1
        status_icon = "✅" if res["is_verified"] else "⚠️"
        status_text = "已校验" if res["is_verified"] else f"未通过校验: {res['verification_reason']}"

        md_lines.append(f"## 第 {page_num} 页 {status_icon} {status_text}\n")

        md_lines.append("### 原始内容")
        md_lines.append("```text")
        md_lines.append(res["original"])
        md_lines.append("```\n")

        md_lines.append("### 扩展内容")
        if res["expanded"].strip():
            md_lines.append(res["expanded"])
        else:
            md_lines.append("_扩展内容生成失败_")
        md_lines.append("\n---\n")

    return "\n".join(md_lines)


def format_as_json(results, indent=2):
    """
    将结果格式化为 JSON 字符串（便于 API 返回）。
    
    Args:
        results (list): 处理结果列表
        indent (int): JSON 缩进
    
    Returns:
        str: JSON 字符串
    """
    return json.dumps(results, ensure_ascii=False, indent=indent)


def save_markdown_report(results, output_path="output/report.md"):
    """
    将 Markdown 报告保存到文件。
    
    Args:
        results (list): 处理结果
        output_path (str): 输出路径（自动创建目录）
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    markdown_content = format_as_markdown(results)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"✅ Markdown 报告已保存至: {output_path}")


# 可选：未来可扩展为生成新 PPT
# def format_as_new_pptx(results, output_path="output/expanded.pptx"):
#     from pptx import Presentation
#     prs = Presentation()
#     for res in results:
#         slide = prs.slides.add_slide(prs.slide_layouts[1])  # 标题+内容版式
#         title = slide.shapes.title
#         content = slide.placeholders[1]
#         title.text = f"第 {res['slide_index']+1} 页（扩展）"
#         content.text = res["expanded"] if res["is_verified"] else "[校验未通过，略]"
#     prs.save(output_path)