
        title = (s.get("title", "") or "").strip()
        url = (s.get("url", "") or "").strip()
        if not title and not url:
            continue
        if url:
            print(f"- {title}\n  {url}")
        else:
            print(f"- {title}")

    # 所有分析结束后：生成 Markdown 报告（emoji + 红绿高亮）并写入 report/
    try:
        from report import call_qwen_for_markdown, save_markdown_report