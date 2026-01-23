from __future__ import annotations

import hashlib
import secrets
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import requests
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.ppt_parser import Slide, parse_ppt
from core.vector_store import index_ppt_file, query_similar_slides
from core.llm_agent import AgentConfig, expand_slide_with_tools

import markdown

try: 
    from weasyprint import HTML  
except Exception:  
    HTML = None  


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
FRONTEND_DIR = BASE_DIR / "frontend"


app = FastAPI(title="PPT Agent Backend", version="0.1.0")
app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")


# 简单的内存存储：ppt_id -> List[Slide]
PPT_SLIDES: Dict[str, List[Slide]] = {}

USERS: Dict[str, str] = {}
TOKENS: Dict[str, str] = {}


class SlideOut(BaseModel):
    index: int
    title: str
    bullets: List[str]
    notes: Optional[str] = None


class UploadResponse(BaseModel):
    ppt_id: str
    filename: str
    num_slides: int


class SearchHit(BaseModel):
    ppt_id: str
    slide_index: int
    title: str
    score: float
    snippet: str


class ExpandResponse(BaseModel):
    ppt_id: str
    slide_index: int
    title: str
    expanded_markdown: str


class NoteExportRequest(BaseModel):
    markdown: str
    filename: Optional[str] = None


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    username: str
    token: str


class UploadUrlRequest(BaseModel):
    url: str


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_current_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="登录信息无效")
    token = authorization[len("Bearer ") :].strip()
    username = TOKENS.get(token)
    if not username:
        raise HTTPException(status_code=401, detail="登录已过期")
    return username


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/ui/index.html")


@app.post("/auth/register")
async def register(req: AuthRequest) -> Dict[str, str]:
    username = (req.username or "").strip()
    password = req.password or ""

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名或密码不能为空")
    if len(username) < 4 or len(username) > 32:
        raise HTTPException(status_code=400, detail="用户名长度需为 4-32")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    if username in USERS:
        raise HTTPException(status_code=400, detail="用户名已存在")

    USERS[username] = _hash_password(password)
    return {"status": "ok"}


@app.post("/auth/login", response_model=AuthResponse)
async def login(req: AuthRequest) -> AuthResponse:
    username = (req.username or "").strip()
    password = req.password or ""

    pwd_hash = USERS.get(username)
    if not pwd_hash:
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if pwd_hash != _hash_password(password):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    token = secrets.token_hex(24)
    TOKENS[token] = username
    return AuthResponse(username=username, token=token)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """后端健康检查接口。"""

    return {"status": "ok"}


@app.post("/upload", response_model=UploadResponse)
async def upload_ppt(
    file: UploadFile = File(...),
    _: str = Depends(get_current_user),
) -> UploadResponse:
    """上传 PPT 文件，解析并写入向量库。

    返回生成的 ppt_id 以及解析到的页数。
    """

    if not file.filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="仅支持 .pptx 文件")

    ppt_id = uuid4().hex
    dest_path = UPLOAD_DIR / f"{ppt_id}.pptx"

    content = await file.read()
    dest_path.write_bytes(content)

    # 解析 PPT 并写入向量库
    slides = parse_ppt(dest_path)
    PPT_SLIDES[ppt_id] = slides
    index_ppt_file(dest_path, ppt_id=ppt_id)

    return UploadResponse(ppt_id=ppt_id, filename=file.filename, num_slides=len(slides))


@app.post("/upload_url", response_model=UploadResponse)
async def upload_ppt_by_url(
    req: UploadUrlRequest,
    _: str = Depends(get_current_user),
) -> UploadResponse:
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url 不能为空")

    if "github.com/" in url and "/blob/" in url:
        try:
            prefix, rest = url.split("github.com/", 1)
            owner_repo, path_part = rest.split("/blob/", 1)
            url = f"https://raw.githubusercontent.com/{owner_repo}/{path_part}"
        except Exception:
            pass

    if not url.lower().split("?")[0].endswith(".pptx"):
        raise HTTPException(status_code=400, detail="仅支持 .pptx 文件 URL")

    ppt_id = uuid4().hex
    dest_path = UPLOAD_DIR / f"{ppt_id}.pptx"

    max_bytes = 50 * 1024 * 1024
    total = 0
    try:
        resp = requests.get(url, stream=True, timeout=20)
        resp.raise_for_status()
        head_checked = False
        with dest_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                if not head_checked:
                    head_checked = True
                    if not chunk.startswith(b"PK"):
                        raise HTTPException(status_code=400, detail="URL 不是可直接下载的 .pptx 文件，请使用文件直链（例如 GitHub raw 链接或在链接后追加 ?raw=1）")
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=400, detail="文件过大，最大 50MB")
                f.write(chunk)
    except HTTPException:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise
    except Exception:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="URL 下载失败")

    try:
        slides = parse_ppt(dest_path)
    except Exception:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="下载的内容无法解析为 PPTX，请确认 URL 为可直接下载的 .pptx 文件")
    PPT_SLIDES[ppt_id] = slides
    index_ppt_file(dest_path, ppt_id=ppt_id)
    return UploadResponse(ppt_id=ppt_id, filename=dest_path.name, num_slides=len(slides))


@app.get("/slides", response_model=List[SlideOut])
async def list_slides(
    ppt_id: str = Query(..., description="上传返回的 PPT 标识"),
    _: str = Depends(get_current_user),
) -> List[SlideOut]:
    """列出某个 PPT 的所有页面结构。"""

    slides = PPT_SLIDES.get(ppt_id)
    if slides is None:
        raise HTTPException(status_code=404, detail="ppt_id 未找到，请先上传 PPT")

    return [
        SlideOut(index=s.index, title=s.title, bullets=s.bullets, notes=s.notes)
        for s in slides
    ]


@app.get("/search", response_model=List[SearchHit])
async def search_slides(
    ppt_id: str = Query(..., description="目标 PPT 标识"),
    q: str = Query(..., description="查询语句，如某个知识点关键词"),
    top_k: int = Query(5, ge=1, le=20, description="返回的最大结果数"),
    _: str = Depends(get_current_user),
) -> List[SearchHit]:
    """在指定 PPT 内进行语义检索，返回最相关的若干页面。"""

    if not q.strip():
        raise HTTPException(status_code=400, detail="查询语句不能为空")

    raw = query_similar_slides(q, n_results=top_k * 3)
    ids_batch = raw.get("ids", [[]])[0]
    metas_batch = raw.get("metadatas", [[]])[0]
    docs_batch = raw.get("documents", [[]])[0]
    dists_batch = raw.get("distances", [[]])[0]

    hits: List[SearchHit] = []
    for sid, meta, doc, dist in zip(ids_batch, metas_batch, docs_batch, dists_batch):
        if not isinstance(meta, dict):
            continue
        if meta.get("ppt_id") != ppt_id:
            continue
        hits.append(
            SearchHit(
                ppt_id=ppt_id,
                slide_index=int(meta.get("slide_index", 0)),
                title=str(meta.get("title", "")),
                score=float(dist),
                snippet=doc[:300],
            )
        )
        if len(hits) >= top_k:
            break

    return hits


@app.get("/expand", response_model=ExpandResponse)
async def expand_slide(
    ppt_id: str = Query(..., description="目标 PPT 标识"),
    slide_index: int = Query(..., ge=1, description="要扩展的页面索引（从 1 开始）"),
    use_wikipedia: bool = Query(True, description="是否启用外部知识"),
    _: str = Depends(get_current_user),
) -> ExpandResponse:
    """为指定 PPT 的某一页生成扩展讲解（调用 Agent + Checklayer）。"""

    slides = PPT_SLIDES.get(ppt_id)
    if slides is None:
        raise HTTPException(status_code=404, detail="ppt_id 未找到，请先上传 PPT")

    slide_map = {s.index: s for s in slides}
    slide = slide_map.get(slide_index)
    if slide is None:
        raise HTTPException(status_code=404, detail="指定的 slide_index 不存在")

    cfg = AgentConfig(use_wikipedia=use_wikipedia, top_k_slides=5, top_k_wiki=3)
    expanded = expand_slide_with_tools(slide, config=cfg, ppt_id=ppt_id)

    return ExpandResponse(
        ppt_id=ppt_id,
        slide_index=slide.index,
        title=slide.title,
        expanded_markdown=expanded,
    )


@app.post("/export_note_pdf")
async def export_note_pdf(payload: NoteExportRequest) -> Response:
    """根据前端传入的 Markdown 文本导出为 PDF 文件。

    前端可以在“复制”按钮旁边增加“导出 PDF”按钮：
    - 将当前笔记的 markdown 文本放入 `markdown` 字段
    - 可选提供 `filename` 字段自定义下载文件名
    返回值为 application/pdf 的二进制流，带 Content-Disposition 便于浏览器直接下载。
    """

    if HTML is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "当前环境未完整安装 WeasyPrint 所需的系统依赖，"
                "可在 Docker / 服务器环境中启用 PDF 导出，"
                "本地调试时请先忽略该功能。"
            ),
        )

    if not payload.markdown.strip():
        raise HTTPException(status_code=400, detail="markdown 内容不能为空")

    html_body = markdown.markdown(payload.markdown, output_format="html5")
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Note Export</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif; line-height: 1.6; padding: 24px; }}
    h1, h2, h3, h4, h5, h6 {{ margin-top: 1.2em; margin-bottom: 0.6em; }}
    p {{ margin: 0.4em 0; }}
    code, pre {{ font-family: SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; background: #f5f5f5; }}
    pre {{ padding: 12px; overflow-x: auto; }}
    ul, ol {{ margin-left: 1.5em; }}
  </style>
</head>
<body>
{html_body}
</body>
</html>
"""

    pdf_bytes = HTML(string=full_html, base_url=str(BASE_DIR)).write_pdf()

    filename = payload.filename or "note.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
        },
    )
