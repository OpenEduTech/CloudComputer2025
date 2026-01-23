"""Report generator.

Generate an emoji-rich Markdown report with red/green highlights, using Tongyi Qwen.

Usage:
  python codes/report.py --example codes/ex.json

Env:
  DASHSCOPE_API_KEY (preferred) or TONGYI_API_KEY / QWEN_API_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional


def _project_root() -> str:
	return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _default_report_dir() -> str:
	return os.path.join(_project_root(), "report")


def _read_json(path: str) -> Dict[str, Any]:
	with open(path, "r", encoding="utf-8") as f:
		return json.load(f)


def _try_load_local_secrets_api_key() -> str:
	# 直接写明文 key（如 search_agent.py）
	return "sk-d64798271c204eb28e0744db0a8a480b"


def _get_qwen_api_key() -> str:
	api_key = (
		os.getenv("DASHSCOPE_API_KEY")
		or os.getenv("TONGYI_API_KEY")
		or os.getenv("QWEN_API_KEY")
		or ""
	).strip()

	if not api_key:
		# Local secret file (DO NOT COMMIT): codes/local_secrets.py
		#   DASHSCOPE_API_KEY = "填你的 Key"
		api_key = _try_load_local_secrets_api_key()
	if not api_key:
		raise RuntimeError(
			"未检测到通义千问 API Key。请设置环境变量 DASHSCOPE_API_KEY（推荐），或在 codes/local_secrets.py 里设置 DASHSCOPE_API_KEY。"
		)
	return api_key


def _sanitize_filename_component(text: str) -> str:
	# Windows invalid filename characters: <>:"/\\|?*
	text = re.sub(r'[<>:"/\\|?*]', "_", text)
	text = text.strip().strip(".")
	return text or "report"


def _build_messages(ex_data: Dict[str, Any]) -> List[Dict[str, str]]:
	system = (
		"你是一名资深行业研究分析师与报告撰稿人。"
		"你将收到一份结构化 JSON（包含 global_summary/decisions/sources 等）。"
		"请输出一份可直接发布的 Markdown 报告，满足以下强约束：\n"
		"1) 必须包含 emoji（每个一级小节标题至少 1 个）。\n"
		"2) 必须对关键数据做红绿高亮：用 HTML <span style=...> 实现。\n"
		"   - 绿色：正向/改善/新增/利好（例如 increased/improved/新增）。\n"
		"   - 红色：负向/下降/利空（例如 decreased）。\n"
		"   - 颜色建议：绿色 #16a34a，红色 #dc2626，并加粗 font-weight:600。\n"
		"3) 报告必须只输出 Markdown 正文，不要输出 JSON，不要用代码块包裹整篇报告。\n"
		"4) 报告结构固定为：\n"
		"   - 标题（包含 keyword）\n"
		"   - 全局总结（改写 global_summary，保留关键信息）\n"
		"   - 关键变化一览（表格：field/status/old/value/change/一句话解读）\n"
		"   - 风险与机会（条目化，至少各 3 条）\n"
		"   - 信息来源（列出 sources，标题+链接+时间）\n"
		"5) 若 change 为空，请根据 old/value 推断并补一句简短变化描述（不编造不存在的数值）。\n"
        "6）对每次红绿高亮后跟一个表示变化的emoji（增长/下降/好/坏）。\n"
	)

	user = (
		"请基于以下 JSON 生成报告。\n\n"
		"JSON：\n"
		+ json.dumps(ex_data, ensure_ascii=False, indent=2)
	)

	return [
		{"role": "system", "content": system},
		{"role": "user", "content": user},
	]


def call_qwen_for_markdown(
	*,
	ex_data: Dict[str, Any],
	model: str = "qwen-plus",
	temperature: float = 0.3,
	timeout_seconds: int = 90,
) -> str:
	"""Call Tongyi Qwen to produce a Markdown report."""

	api_key = _get_qwen_api_key()
	messages = _build_messages(ex_data)

	# Prefer dashscope SDK (already in requirements.txt)
	try:
		import dashscope  # type: ignore
		from dashscope import Generation  # type: ignore

		dashscope.api_key = api_key
		resp = Generation.call(
			model=model,
			messages=messages,
			temperature=temperature,
			result_format="message",
		)

		if getattr(resp, "status_code", None) != 200:
			raise RuntimeError(f"DashScope 调用失败：status_code={getattr(resp, 'status_code', None)}，message={getattr(resp, 'message', None)}")

		content = resp.output.choices[0].message.content
		return (content or "").strip()

	except Exception:
		# Fallback: OpenAI-compatible endpoint
		import requests

		base_url = os.getenv(
			"DASHSCOPE_COMPATIBLE_BASE_URL",
			"https://dashscope.aliyuncs.com/compatible-mode/v1",
		).rstrip("/")
		url = f"{base_url}/chat/completions"

		headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
		payload = {
			"model": model,
			"messages": messages,
			"temperature": temperature,
		}
		r = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
		r.raise_for_status()
		data = r.json()
		content = data["choices"][0]["message"]["content"]
		return (content or "").strip()


def save_markdown_report(
	*,
	ex_data: Dict[str, Any],
	markdown: str,
	out_dir: Optional[str] = None,
) -> str:
	keyword = _sanitize_filename_component(str(ex_data.get("keyword", "keyword")))
	generated_at = _sanitize_filename_component(str(ex_data.get("generated_at", "")))
	filename = f"{keyword}{generated_at}.md"

	output_dir = out_dir or _default_report_dir()
	os.makedirs(output_dir, exist_ok=True)
	out_path = os.path.join(output_dir, filename)

	with open(out_path, "w", encoding="utf-8") as f:
		f.write(markdown.strip() + "\n")

	return out_path


def generate_report_from_example(
	*,
	example_json_path: str,
	out_dir: Optional[str] = None,
	model: str = "qwen-plus",
	temperature: float = 0.3,
) -> str:
	ex_data = _read_json(example_json_path)
	markdown = call_qwen_for_markdown(ex_data=ex_data, model=model, temperature=temperature)
	return save_markdown_report(ex_data=ex_data, markdown=markdown, out_dir=out_dir)


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Generate Markdown report (emoji + red/green highlights) via Tongyi Qwen.")
	parser.add_argument("--example", default=os.path.join("codes", "ex.json"), help="Path to ex.json example")
	parser.add_argument("--out-dir", default=_default_report_dir(), help="Output directory (default: report/)")
	parser.add_argument("--model", default="qwen-plus", help="Qwen model name (e.g., qwen-plus, qwen-turbo)")
	parser.add_argument("--temperature", type=float, default=0.3, help="Sampling temperature")
	return parser.parse_args()


def main() -> None:
	args = _parse_args()
	out_path = generate_report_from_example(
		example_json_path=args.example,
		out_dir=args.out_dir,
		model=args.model,
		temperature=args.temperature,
	)
	print(f"Markdown 报告已生成：{out_path}")


if __name__ == "__main__":
	main()
