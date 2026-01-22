from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.knowledge_service import build_tree

router = APIRouter()


@router.get("/tree")
def get_knowledge_tree(
    material_id: str = Query(...),
    student_id: str = Query("demo_user"),
    notebook_id: Optional[str] = Query(None),
):
    if not material_id:
        raise HTTPException(status_code=400, detail="material_id is required")
    tree = build_tree(material_id=material_id, student_id=student_id, notebook_id=notebook_id)
    return {"material_id": material_id, "tree": tree}
