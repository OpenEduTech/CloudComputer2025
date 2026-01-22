from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any

import chromadb

from core.ppt_parser import Slide, parse_ppt


# 使用 PersistentClient 持久化到项目目录下的 chroma_db/
_client = chromadb.PersistentClient(path=str(Path(__file__).resolve().parent / "chroma_db"))


def get_slides_collection(name: str = "ppt_slides"):
    """获取（或创建）用于存储 PPT 切片的 Chroma collection。

    默认 collection 名为 ppt_slides，可根据需要扩展多课程/多项目。
    """

    return _client.get_or_create_collection(name)


def slide_to_document(slide: Slide) -> str:
    """将单个 Slide 转换为可供向量化的文本表示。"""

    lines: List[str] = []
    if slide.title:
        lines.append(slide.title)
    if slide.bullets:
        lines.extend(slide.bullets)
    if slide.notes:
        lines.append(slide.notes)
    return "\n".join(lines)


def index_slides(slides: List[Slide], ppt_id: str, collection_name: str = "ppt_slides") -> None:
    """将一组 Slide 写入 Chroma 向量库。

    - ppt_id: 用于标记属于同一 PPT 的切片。
    - 每个 slide 将生成一个唯一 id: f"{ppt_id}-{slide.index}"。
    """

    collection = get_slides_collection(collection_name)

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for slide in slides:
        sid = f"{ppt_id}-{slide.index}"
        ids.append(sid)
        documents.append(slide_to_document(slide))
        metadatas.append(
            {
                "ppt_id": ppt_id,
                "slide_index": slide.index,
                "title": slide.title,
            }
        )

    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)


def index_ppt_file(ppt_path: str | Path, ppt_id: str, collection_name: str = "ppt_slides") -> List[Slide]:
    """从 PPT 文件解析 Slide，并写入 Chroma，返回解析得到的 Slide 列表。"""

    slides = parse_ppt(ppt_path)
    index_slides(slides, ppt_id=ppt_id, collection_name=collection_name)
    return slides


def query_similar_slides(
    query_text: str,
    n_results: int = 5,
    collection_name: str = "ppt_slides",
) -> Dict[str, Any]:
    """基于语义相似度，在Chroma 向量库中检索相关的幻灯片。

    返回值为 Chroma 的原始 query 结果字典，其中包含 ids、distances、metadatas 等字段。
    上层可以根据 metadatas 中的 ppt_id、slide_index 做进一步渲染。
    """

    collection = get_slides_collection(collection_name)
    results = collection.query(query_texts=[query_text], n_results=n_results)
    return results
