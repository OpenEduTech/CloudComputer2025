import os
import tempfile
from typing import Tuple
from urllib.parse import urlparse

import requests
from fastapi import UploadFile, HTTPException

SUPPORTED_EXTS = {".pptx", ".pdf"}


def ensure_supported_ext(filename: str) -> str:
    _, ext = os.path.splitext(filename.lower())
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(status_code=400, detail="仅支持 .pptx/.pdf 文件")
    return ext


def download_to_temp(url: str) -> Tuple[str, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="仅支持 http/https 链接")

    resp = requests.get(url, timeout=15, allow_redirects=True)
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="下载失败，状态码 %s" % resp.status_code)

    filename = os.path.basename(parsed.path) or "remote_file"
    content_type = (resp.headers.get("Content-Type") or "").split(";")[0].lower()
    type_ext_map = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    }

    ext = os.path.splitext(filename.lower())[1]
    if ext not in SUPPORTED_EXTS:
        guessed = type_ext_map.get(content_type)
        if guessed:
            ext = guessed
            if not filename.lower().endswith(ext):
                filename = f"{filename}{ext}"
        else:
            raise HTTPException(status_code=400, detail="链接文件类型不支持，仅允许 .pptx/.pdf")

    ensure_supported_ext(filename)
    fd, path = tempfile.mkstemp(suffix=ext)
    with os.fdopen(fd, "wb") as f:
        f.write(resp.content)
    return path, filename


async def save_upload_to_temp(file: UploadFile) -> Tuple[str, str]:
    filename = file.filename
    ext = ensure_supported_ext(filename)
    fd, path = tempfile.mkstemp(suffix=ext)
    with os.fdopen(fd, "wb") as f:
        f.write(await file.read())
    return path, filename
