from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[dict]:
    """
    将长文本切分为片段，返回标准化结构。
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [{"chunk_id": f"c{i+1}", "text": c} for i, c in enumerate(chunks) if c.strip()]
