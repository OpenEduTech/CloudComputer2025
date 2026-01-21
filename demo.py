# demo.py
import os
import sys
import argparse
from input_handler import extract_text_from_pptx
from agent_core import process_ppt_slides
from output_formatter import save_markdown_report, format_as_json

def main():
    parser = argparse.ArgumentParser(
        description="PPT内容扩展智能体 - 本地演示模式",
        epilog="示例: python demo.py sample.pptx --output results"
    )
    parser.add_argument(
        "ppt_file",
        help="要处理的 .pptx 文件路径（例如: sample.pptx）"
    )
    parser.add_argument(
        "--output",
        default="output",
        help="输出目录（默认: output）"
    )
    args = parser.parse_args()

    ppt_path = args.ppt_file
    output_dir = args.output

    print("🚀 启动 PPT 内容扩展智能体（本地演示模式）\n")

    # 检查文件是否存在
    if not os.path.exists(ppt_path):
        print(f"❌ 错误: 未找到文件 '{ppt_path}'")
        sys.exit(1)

    # 检查是否为 .pptx
    if not ppt_path.lower().endswith('.pptx'):
        print(f"❌ 错误: 仅支持 .pptx 格式，当前文件: {ppt_path}")
        sys.exit(1)

    try:
        # 1. 解析 PPT
        print(f"📄 正在解析 '{ppt_path}'...")
        slides_data = extract_text_from_pptx(ppt_path)
        print(f"✅ 成功提取 {len(slides_data)} 页内容\n")

        if not slides_data:
            print("⚠️  PPT 中未检测到有效文本内容。")
            return

        # 2. 处理每一页（扩展 + 校验）
        print("🧠 正在调用智谱AI进行内容扩展与事实校验...")
        results = process_ppt_slides(slides_data)
        print("✅ 扩展与校验完成！\n")

        # 3. 打印简要结果到终端
        verified_count = sum(1 for r in results if r["is_verified"])
        print(f"📊 处理总结: 共 {len(results)} 页，{verified_count} 页通过校验\n")

        for res in results:
            page_num = res["slide_index"] + 1
            status = "✅ 通过" if res["is_verified"] else f"❌ 失败 ({res['verification_reason']})"
            print(f"--- 第 {page_num} 页 --- [{status}]")
            print(f"【原始】{res['original'][:60]}{'...' if len(res['original']) > 60 else ''}")
            print(f"【扩展】{res['expanded'][:80]}{'...' if len(res['expanded']) > 80 else ''}\n")

        # 4. 保存完整 Markdown 报告
        os.makedirs(output_dir, exist_ok=True)
        save_markdown_report(results, os.path.join(output_dir, "report.md"))

        # 5. 保存 JSON 结果
        json_path = os.path.join(output_dir, "result.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(format_as_json(results))
        print(f"💾 完整结果已保存至:\n   - {os.path.join(output_dir, 'report.md')}\n   - {json_path}")

    except Exception as e:
        print(f"💥 运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()