from __future__ import annotations

import json
import os

from config import DEFAULT_KEYWORD
from storage_layer import StorageClient


def main() -> None:
    storage = StorageClient()
    known = storage.list_keywords()

    if known:
        print("已调研行业清单：")
        for idx, k in enumerate(known, start=1):
            print(f"  {idx}. {k}")
        print("输入编号可直接选择；或输入新的行业关键词开始新调研。")
    else:
        print("尚无历史调研行业记录，直接输入行业关键词开始调研。")

    raw = input(f"请输入查询行业（回车默认：{DEFAULT_KEYWORD}）：").strip()
    if not raw:
        keyword = DEFAULT_KEYWORD
    elif raw.isdigit() and known:
        i = int(raw)
        keyword = known[i - 1] if 1 <= i <= len(known) else raw
    else:
        keyword = raw

    # 延迟导入，避免与 orchestrator 的互相 import 产生循环依赖。
    from orchestrator import run_pipeline

    # 默认输出“指标评测”式的人类可读报告；需要原始 JSON 时可设置 env: OUTPUT_JSON=1
    output_json = os.getenv("OUTPUT_JSON", "0").strip() in {"1", "true", "yes"}

    result = run_pipeline(keyword=keyword, print_steps=not output_json)

    if output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("=" * 60)
    print(f"【今日行研雷达：{result.get('keyword', keyword)}】")
    print(result.get("global_summary", ""))
    print("=" * 60)

    print("\n【详细指标变动明细】")
    for d in (result.get("decisions", []) or []):
        field = d.get("field", "")
        old_v = (d.get("old_value", "") or "").strip()
        val = (d.get("value", "") or "").strip()
        status = (d.get("status", "") or "").strip()

        print(f"● 指标：{field}")
        if status:
            print(f"  状态：{status}")
        if old_v:
            print(f"  旧结论：{old_v}")
        print(f"  新结论：{val}")

        change = d.get("change")
        if change:
            print(f"  增量对比：{change}")

        arb = d.get("arbitration") or {}
        chosen = arb.get("chosen_source", "")
        pending = arb.get("pending_sources", []) or []
        conflicts = arb.get("conflicting_values", []) or []
        if chosen:
            msg = f"  仲裁：采纳={chosen}"
            if conflicts:
                msg += f"；候选={';'.join(conflicts[:3])}"
            if pending:
                msg += f"；待核实来源={','.join(pending)}"
            print(msg)
        else:
            print("  仲裁：无")

        reason = (d.get("reason", "") or "").strip()
        if reason:
            print(f"  分析建议：{reason}")
        print("-" * 40)

    print("\n【调研文章清单（title + url）】")
    for s in (result.get("sources", []) or []):
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

        md = call_qwen_for_markdown(ex_data=result)
        md_path = save_markdown_report(ex_data=result, markdown=md)
        print("\n【Markdown 报告】")
        print(f"已生成：{md_path}")
    except Exception as e:
        print("\n【Markdown 报告】")
        print(f"生成失败（不影响主流程）：{e}")


if __name__ == "__main__":
    main()
