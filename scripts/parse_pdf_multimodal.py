import os
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF
import pandas as pd
import camelot

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq

# ------------------------
# Config
# ------------------------
# 假设脚本在 rag/scripts/ 下，BASE_DIR 指向 rag/
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
OUT_JSONL = BASE_DIR / "data" / "parsed_docs.jsonl"
IMG_DIR = BASE_DIR / "data" / "extracted_images"

VLM_NAME = "Qwen/Qwen2-VL-2B-Instruct"


# ------------------------
# Utils
# ------------------------
def write_jsonl(records, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ------------------------
# VLM (保持不变)
# ------------------------
def load_vlm():
    if not torch.cuda.is_available():
        return None, None
    try:
        print(f"🔄 Loading VLM: {VLM_NAME}...")
        processor = AutoProcessor.from_pretrained(VLM_NAME, trust_remote_code=True, use_fast=False)
        model = AutoModelForVision2Seq.from_pretrained(VLM_NAME, torch_dtype=torch.float16, device_map="auto",
                                                       trust_remote_code=True)
        return processor, model
    except:
        return None, None


def vlm_caption(processor, model, image_path: Path) -> str:
    if not processor or not model: return ""
    try:
        image = Image.open(image_path).convert("RGB")
        instruction = "你是全能知识库助手。如果是代码图请提取逻辑；如果是架构图请描述流程；如果是图表请提取结论。"
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": instruction}]}]
        prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=prompt, images=image, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=512, do_sample=False)
        return processor.batch_decode(out, skip_special_tokens=True)[0].strip()
    except:
        return ""


# ------------------------
# PDF Extraction
# ------------------------
def extract_text_pymupdf(pdf_path: Path):
    try:
        doc = fitz.open(pdf_path)
        for page_idx in range(len(doc)):
            text = doc[page_idx].get_text("text").strip()
            if text:
                yield {
                    "type": "text",
                    "source": pdf_path.name,
                    "pdf_name": pdf_path.name,
                    "page": page_idx,
                    "content": f"【来源PDF】{pdf_path.name}\n{text}",
                    "meta": {"is_pdf": True}
                }
    except:
        pass


# ------------------------
# Markdown Processing (核心修复版)
# ------------------------
def process_markdown_file(md_path: Path, force_difficulty: str = "Unknown") -> List[Dict[str, Any]]:
    records = []
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. 获取基本信息
        folder_name = md_path.parent.name
        lines = content.split('\n')
        title = lines[0].strip().replace("# ", "") if lines else folder_name

        # 2. 构建增强文本
        full_text = f"""
【知识条目】 LeetCode / 算法笔记
【题目名称】 {title}
【题目难度】 {force_difficulty}
【来源路径】 {folder_name}/{md_path.name}
--------------------------------------------------
{content}
""".strip()

        # 3. 图片引用处理 (关键修复：忽略网络图片)
        img_matches = re.finditer(r'!\[(.*?)\]\((.*?)\)', content)
        for match in img_matches:
            alt, rel = match.groups()

            final_path = ""

            # === 修复 Start: 遇到网络图片直接保留，不拼本地路径 ===
            if rel.startswith(("http:", "https:")):
                final_path = rel
            else:
                # 只有本地图片才进行路径解析
                try:
                    abs_img = (md_path.parent / rel).resolve()
                    if str(abs_img).startswith(str(BASE_DIR)):
                        final_path = str(abs_img.relative_to(BASE_DIR))
                    else:
                        final_path = str(abs_img)
                except:
                    # 如果解析本地路径失败，跳过该图片
                    continue
            # === 修复 End ===

            records.append({
                "type": "figure",
                "source": md_path.name,
                "page": 0,
                "image_path": final_path,
                "content": f"【图片】{title}: {alt}",
                "meta": {"difficulty": force_difficulty}
            })

        # 4. 生成记录
        try:
            rel_path = str(md_path.relative_to(BASE_DIR))
        except:
            rel_path = str(md_path)

        records.append({
            "type": "text",
            "source": md_path.name,
            "pdf_name": md_path.name,
            "page": 0,
            "content": full_text,
            "meta": {
                "difficulty": force_difficulty,
                "title": title,
                "file_path": rel_path,
                "is_leetcode": True
            }
        })
        return records

    except Exception as e:
        print(f"❌ 解析失败: {md_path} - {e}")
        return []


# ------------------------
# Main Logic (精准扫描)
# ------------------------
def main():
    if not DOCS_DIR.exists():
        print(f"❌ 找不到 docs 目录: {DOCS_DIR}")
        return

    processor, model = load_vlm()
    records = []

    # 1. 扫描 PDF
    print("🔍 正在扫描 PDF...")
    for pdf in DOCS_DIR.rglob("*.pdf"):
        records.extend(list(extract_text_pymupdf(pdf)))

    # 2. 扫描 LeetCode (Easy/Mid/Hard)
    # 映射表：文件夹名 -> 难度标记
    target_dirs = {
        "easy": "Easy",
        "mid": "Medium",
        "midium": "Medium",  # 兼容你的 midium 拼写
        "medium": "Medium",
        "hard": "Hard"
    }

    print("\n🔍 正在扫描 LeetCode 题目目录...")

    for dir_name, difficulty in target_dirs.items():
        target_path = DOCS_DIR / dir_name
        if not target_path.exists():
            continue

        print(f"   📂 进入目录: {dir_name} (难度: {difficulty})")

        # 遍历该难度下的所有子文件夹
        sub_count = 0
        for sub_folder in target_path.iterdir():
            if sub_folder.is_dir():
                # 精准找 README.md
                readme_path = sub_folder / "README.md"
                if readme_path.exists():
                    new_recs = process_markdown_file(readme_path, force_difficulty=difficulty)
                    records.extend(new_recs)
                    sub_count += 1

        print(f"      -> 已解析 {sub_count} 题")

    # 3. 扫描人工文档 (Manual)
    manual_dir = DOCS_DIR / "manual"
    if manual_dir.exists():
        print(f"\n🔍 正在扫描人工文档 (manual)...")
        m_count = 0
        for md in manual_dir.rglob("*.md"):
            new_recs = process_markdown_file(md, force_difficulty="Manual")
            records.extend(new_recs)
            m_count += 1
        print(f"      -> 已解析 {m_count} 个文档")

    # 汇总
    print(f"\n✅ 扫描结束！总共生成 {len(records)} 条数据记录。")
    print(f"💾 写入文件: {OUT_JSONL}")
    write_jsonl(records, OUT_JSONL)
    print("🚀 请运行 python build_index_ollama.py 构建索引")


if __name__ == "__main__":
    main()
