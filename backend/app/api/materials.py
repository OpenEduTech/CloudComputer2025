import os
import shutil
from pathlib import Path
from typing import Optional
from uuid import uuid4

from bson.errors import InvalidId
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.jobs.queue import queue
from app.services.material_service import create_material, get_material, list_materials, update_material_status

router = APIRouter()
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "storage/uploads"))
INGEST_JOB_TIMEOUT = int(os.getenv("INGEST_JOB_TIMEOUT", "1200"))


class MaterialCreateRequest(BaseModel):
    student_id: str = "demo_user"
    notebook_id: str
    title: str
    source_type: str = "text"
    material_type: str = "textbook"
    is_primary: bool = False
    file_url: Optional[str] = None
    text: Optional[str] = None


class MaterialCreateResponse(BaseModel):
    id: str
    status: str
    text_chunk_count: int
    job_id: Optional[str] = None


@router.post("/", response_model=MaterialCreateResponse)
def upload_material(payload: MaterialCreateRequest):
    if payload.source_type != "text" and not payload.file_url:
        raise HTTPException(status_code=400, detail="file_url is required for non-text materials")
    if payload.source_type == "text" and not payload.text:
        raise HTTPException(status_code=400, detail="text is required for text materials")

    data = payload.dict(exclude={"text"})
    result = create_material(data, text=payload.text)

    if payload.text:
        return result

    update_material_status(result["id"], "queued")
    job = queue.enqueue("tasks.ingest.ingest_material", result["id"], job_timeout=INGEST_JOB_TIMEOUT)
    result["status"] = "queued"
    result["job_id"] = job.id
    return result


@router.post("/upload", response_model=MaterialCreateResponse)
def upload_material_file(
    student_id: str = Form("demo_user"),
    notebook_id: str = Form(...),
    title: Optional[str] = Form(None),
    source_type: Optional[str] = Form(None),
    material_type: str = Form("textbook"),
    is_primary: bool = Form(False),
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="file is required")

    resolved_source = _resolve_source_type(file.filename, source_type)
    saved_path = _save_upload(file)
    material_title = title or Path(file.filename).stem

    payload = {
        "student_id": student_id,
        "notebook_id": notebook_id,
        "title": material_title,
        "source_type": resolved_source,
        "material_type": material_type,
        "is_primary": is_primary,
        "file_url": str(saved_path),
    }

    if resolved_source == "text":
        text = saved_path.read_text(encoding="utf-8", errors="ignore")
        return create_material(payload, text=text)

    result = create_material(payload)
    update_material_status(result["id"], "queued")
    job = queue.enqueue("tasks.ingest.ingest_material", result["id"], job_timeout=INGEST_JOB_TIMEOUT)
    result["status"] = "queued"
    result["job_id"] = job.id
    return result


@router.get("/{material_id}")
def get_material_detail(material_id: str):
    try:
        material = get_material(material_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="invalid material_id")
    if not material:
        raise HTTPException(status_code=404, detail="material not found")
    return material


@router.get("/")
def list_materials_by_notebook(notebook_id: str, student_id: str = "demo_user"):
    return list_materials(notebook_id, student_id=student_id)


def _resolve_source_type(filename: str, override: Optional[str]) -> str:
    if override:
        normalized = override.strip().lower()
        mapped = _SOURCE_TYPE_ALIAS.get(normalized)
        if not mapped:
            raise HTTPException(status_code=400, detail=f"unsupported source_type: {override}")
        return mapped
    ext = Path(filename).suffix.lower()
    mapped = _SOURCE_TYPE_ALIAS.get(ext)
    if not mapped:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {ext}")
    return mapped


def _save_upload(upload: UploadFile) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "").suffix.lower()
    filename = f"{uuid4().hex}{suffix}"
    dest = UPLOAD_DIR / filename
    with dest.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return dest.resolve()


_SOURCE_TYPE_ALIAS = {
    "pdf": "pdf",
    ".pdf": "pdf",
    "docx": "docx",
    ".docx": "docx",
    "text": "text",
    "txt": "text",
    ".txt": "text",
    "audio": "audio",
    "mp3": "audio",
    ".mp3": "audio",
    "wav": "audio",
    ".wav": "audio",
    "m4a": "audio",
    ".m4a": "audio",
    "ogg": "audio",
    ".ogg": "audio",
    "flac": "audio",
    ".flac": "audio",
}
