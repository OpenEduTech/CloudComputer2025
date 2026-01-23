import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover
    PdfReader = None  # type: ignore

_WHISPER_MODEL = None
_WHISPER_MODEL_NAME: Optional[str] = None

TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
PDF_EXTENSIONS = {".pdf"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def _ensure_pdf_support() -> None:
    if PdfReader is None:
        raise HTTPException(status_code=500, detail="缺少 PDF 支持，请在 API 环境中安装 pypdf 库。")


def _load_whisper_model() -> "object":
    global _WHISPER_MODEL
    global _WHISPER_MODEL_NAME
    try:
        import whisper  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500,
            detail="缺少 openai-whisper 依赖，无法转写录音文件。请在 API 镜像中安装 openai-whisper，并确保已安装 ffmpeg。",
        ) from exc

    model_name = os.getenv("WHISPER_MODEL", "small")
    if _WHISPER_MODEL is None or _WHISPER_MODEL_NAME != model_name:
        _WHISPER_MODEL = whisper.load_model(model_name)
        _WHISPER_MODEL_NAME = model_name
    return _WHISPER_MODEL


def _extract_pdf_text(data: bytes) -> str:
    _ensure_pdf_support()
    reader = PdfReader(BytesIO(data))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text.strip())
    return "\n".join(filter(None, pages)).strip()


def _extract_text_file(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("gbk", errors="ignore")


def _transcribe_audio(data: bytes, suffix: str) -> str:
    model = _load_whisper_model()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        result = model.transcribe(tmp_path, fp16=False)
        text = result.get("text", "").strip()
        return text
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _extension(filename: Optional[str]) -> str:
    if not filename:
        return ""
    return Path(filename).suffix.lower()


def guess_material_text(filename: Optional[str], raw: bytes) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="文件名缺失，无法判断类型")
    ext = _extension(filename)
    if not raw:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if ext in TEXT_EXTENSIONS:
        text = _extract_text_file(raw)
    elif ext in PDF_EXTENSIONS:
        text = _extract_pdf_text(raw)
    elif ext in AUDIO_EXTENSIONS:
        text = _transcribe_audio(raw, ext)
    else:
        raise HTTPException(status_code=400, detail=f"暂不支持的文件类型: {ext}")
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="未能从文件中提取有效文本")
    return cleaned
