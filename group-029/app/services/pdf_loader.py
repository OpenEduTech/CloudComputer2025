from pdfminer.high_level import extract_text


def load_pdf_text(file_path: str) -> str:
    """
    读取 PDF 文本内容并返回字符串。
    """
    # 这里先使用 pdfminer.six 做基础抽取，后续可替换为 PyMuPDF
    return extract_text(file_path)
