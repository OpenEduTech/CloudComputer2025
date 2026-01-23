from pathlib import Path
import pandas as pd
import torch

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


DOCS_DIR = Path("docs")
OUT_DIR = Path("kg")
MODEL_NAME = "Babelscape/rebel-large"


def load_docs():
    docs = []
    for p in DOCS_DIR.rglob("*"):
        if p.is_dir():
            continue
        suffix = p.suffix.lower()
        try:
            if suffix == ".pdf":
                docs.extend(PyPDFLoader(str(p)).load())
            elif suffix in [".docx"]:
                docs.extend(Docx2txtLoader(str(p)).load())
            elif suffix in [".txt", ".md"]:
                docs.extend(TextLoader(str(p), encoding="utf-8").load())
        except Exception as e:
            print(f"[WARN] Failed to load {p}: {e}")
    return docs


def parse_rebel_output(text: str):
    """
    REBEL 生成的序列通常包含 <triplet> <subj> ... <obj> ... 这样的标记。
    这里做一个简单解析器：尽量抽出 (subj, rel, obj)。
    """
    triplets = []
    # 清理
    text = text.replace("<s>", "").replace("</s>", "").strip()
    tokens = text.split()

    subj, rel, obj = None, None, None
    mode = None

    def flush():
        nonlocal subj, rel, obj
        if subj and rel and obj:
            triplets.append((subj.strip(), rel.strip(), obj.strip()))
        subj = rel = obj = None

    for t in tokens:
        if t == "<triplet>":
            flush()
            mode = "subj"
            continue
        if t == "<subj>":
            mode = "subj"
            continue
        if t == "<obj>":
            mode = "obj"
            continue

        # REL 通常在 subj 和 obj 之间（REBEL格式有时是 subj rel obj）
        # 这里用启发式：subj段结束后，先收集到 rel，直到 <obj>
        if mode == "subj":
            subj = (subj + " " + t) if subj else t
        elif mode == "obj":
            obj = (obj + " " + t) if obj else t
        else:
            rel = (rel + " " + t) if rel else t

    flush()
    return triplets


def main():
    if not DOCS_DIR.exists():
        raise RuntimeError("docs/ not found.")

    raw_docs = load_docs()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\n\n", "\n", "。", "！", "？", ".", " ", ""],
    )
    chunks = splitter.split_documents(raw_docs)
    print(f"Docs={len(raw_docs)} Chunks={len(chunks)}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    model.to(device)

    rows = []
    for idx, d in enumerate(chunks):
        text = d.page_content.strip()
        if len(text) < 50:
            continue

        inp = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        inp = {k: v.to(device) for k, v in inp.items()}

        with torch.no_grad():
            gen = model.generate(
                **inp,
                max_new_tokens=256,
                num_beams=3,
            )
        out = tokenizer.decode(gen[0], skip_special_tokens=False)
        triplets = parse_rebel_output(out)

        src = d.metadata.get("source", "")
        page = d.metadata.get("page", "")

        for s, r, o in triplets:
            rows.append(
                {"subject": s, "relation": r, "object": o, "source": src, "page": page, "chunk_id": idx}
            )

        if (idx + 1) % 50 == 0:
            print(f"Processed {idx+1}/{len(chunks)} chunks... triples so far={len(rows)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows).drop_duplicates()
    out_csv = OUT_DIR / "triples_rebel.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Saved triples: {len(df)} -> {out_csv}")


if __name__ == "__main__":
    main()
