"""
PatPat-Inconsistency-Hunter LangGraph 分析引擎
使用 LangGraph 实现更高效的 Agent 工作流
"""

import asyncio
import uuid
import time
import os
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List, TypedDict, Annotated, Literal
from collections import Counter
from operator import add

from ..config import settings
from ..models.schemas import (
    DocumentInput,
    DocumentChunk,
    AnalysisTask,
    AnalysisResult,
    TaskStatus,
    ConflictReport,
    FactWithSource,
    ConflictPair,
    ConflictType,
    VerificationResult,
)
from ..utils.logger import logger
from .document_processor import DocumentProcessor
from .document_editor import RichTextContent  # 在顶部导入，避免运行时导入错误
from .fact_extractor import FactExtractor
from .conflict_detector import ConflictDetector
from .fact_verifier import FactVerifier
from .vision_service import get_vision_service
from .llm_client import DeepSeekClient, get_llm_client


# ==================== 状态定义 ====================

class ImageInfo(TypedDict):
    """图片信息"""
    image_id: str
    image_path: str
    description: str
    position: tuple  # (start, end)


class AnalysisState(TypedDict):
    """分析状态 - LangGraph 工作流的状态"""
    # 输入
    document: DocumentInput
    task_id: str
    skip_verification: bool
    content_json: Optional[Dict[str, Any]]  # 富文本JSON内容
    
    # 中间状态
    chunks: List[DocumentChunk]
    images: List[ImageInfo]
    facts: List[FactWithSource]
    candidate_pairs: List[tuple]  # 候选冲突对
    conflicts: List[ConflictPair]
    conflict_reports: List[ConflictReport]
    
    # 元信息
    metadata: Dict[str, Any]
    current_step: str
    progress: float
    error: Optional[str]
    
    # 输出
    result: Optional[AnalysisResult]


class LangGraphAnalysisEngine:
    """
    基于 LangGraph 的分析引擎
    
    使用图结构工作流实现更灵活的分析流程，支持：
    1. 并行处理 - 图片分析和文本分块并行
    2. 条件分支 - 根据内容特征选择不同处理路径
    3. 循环优化 - 反馈循环改进检测结果
    """
    
    def __init__(
        self,
        llm_client: Optional[DeepSeekClient] = None,
        max_concurrency: int = 5,
    ):
        """初始化分析引擎"""
        self._client = llm_client or get_llm_client()
        self._max_concurrency = max_concurrency
        
        # 初始化处理模块
        self._document_processor = DocumentProcessor(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        self._fact_extractor = FactExtractor(
            llm_client=self._client,
            max_concurrency=max_concurrency,
        )
        self._conflict_detector = ConflictDetector(
            llm_client=self._client,
            max_concurrency=max_concurrency,
        )
        self._fact_verifier = FactVerifier(
            llm_client=self._client,
            max_concurrency=max_concurrency,
        )
        
        # 任务状态存储
        self._tasks: Dict[str, AnalysisTask] = {}
        
        # 进度回调
        self._progress_callbacks: Dict[str, Callable] = {}
    
    # ==================== 工作流节点 ====================
    
    async def _node_validate_document(
        self, 
        state: AnalysisState
    ) -> Dict[str, Any]:
        """节点: 验证文档"""
        document = state["document"]
        
        is_valid, error_msg = self._document_processor.validate_document(document)
        if not is_valid:
            return {"error": error_msg}
        
        return {"current_step": "文档验证通过", "progress": 5}
    
    async def _node_process_document(
        self,
        state: AnalysisState
    ) -> Dict[str, Any]:
        """节点: 处理文档结构"""
        document = state["document"]
        content_json = state.get("content_json")
        
        # 如果有 content_json，使用它来提取带图片占位符的文本
        if content_json:
            try:
                plain_text_with_images = RichTextContent.to_plain_text(content_json, include_image_placeholders=True)
                logger.info(f"从 content_json 提取文本，包含图片占位符，长度: {len(plain_text_with_images)}")
                # 检查是否有图片占位符
                image_placeholder_count = plain_text_with_images.count("[IMAGE:")
                logger.info(f"检测到 {image_placeholder_count} 个图片占位符")
                
                # 创建新的 DocumentInput，使用带占位符的内容
                document = DocumentInput(
                    title=document.title,
                    content=plain_text_with_images,
                    metadata=document.metadata,
                )
            except Exception as e:
                logger.warning(f"从 content_json 提取文本失败: {e}，使用原始内容")
        
        # 处理文档，获取分块
        chunks, metadata = self._document_processor.process_document(document)
        
        if not chunks:
            return {"error": "文档分块失败，无法提取有效内容"}
        
        logger.info(f"文档处理完成: {len(chunks)} 个分块")
        
        return {
            "chunks": chunks,
            "metadata": metadata,
            "current_step": "文档处理完成",
            "progress": 10,
        }
    
    async def _node_extract_images(
        self,
        state: AnalysisState
    ) -> Dict[str, Any]:
        """节点: 提取并处理图片"""
        try:
            logger.info("=" * 50)
            logger.info("🖼️ [图片提取节点] 开始执行 _node_extract_images")
            
            content_json = state.get("content_json")
            logger.info(f"🔍 content_json 是否存在: {content_json is not None}")
            if content_json:
                logger.info(f"📦 content_json 类型: {type(content_json)}")
                if isinstance(content_json, dict):
                    logger.info(f"📦 content_json keys: {list(content_json.keys())}")
            
            images = []
            
            # 从 content_json 中提取图片信息
            if content_json:
                logger.info(f"📄 content_json 类型: {type(content_json)}, 内容预览: {str(content_json)[:200]}")
                # RichTextContent 已在文件顶部导入
                images_info = RichTextContent.extract_images(content_json)
                logger.info(f"📸 从 content_json 中提取到 {len(images_info)} 张图片信息")
                
                for img_info in images_info:
                    image_id = img_info.get("imageId")
                    src = img_info.get("src")
                    alt_text = img_info.get("alt") or "图片"
                    
                    logger.info(f"  图片信息: imageId={image_id}, src={src}, alt={alt_text}")
                    
                    if not image_id:
                        logger.warning(f"  跳过无效图片（缺少 imageId）: {img_info}")
                        continue
                    
                    # 构建图片路径
                    logger.info(f"  构建图片路径: src={src}, image_id={image_id}")
                    image_path = self._get_image_path_from_src(src, image_id)
                    logger.info(f"  图片路径: {image_path}, 文件存在: {os.path.exists(image_path) if image_path else False}")
                    if image_path and not os.path.exists(image_path):
                        logger.warning(f"  ⚠️ 图片文件不存在: {image_path}")
                    
                    images.append({
                        "image_id": image_id,
                        "image_path": image_path,
                        "alt_text": alt_text,
                        "position": (0, 0),  # 位置信息在JSON中不直接可用
                        "description": "",
                    })
            
            # 如果没有 content_json，尝试从纯文本中查找（向后兼容）
            if not images:
                logger.info("📝 content_json 中没有图片，尝试从纯文本中查找...")
                document = state["document"]
                content = document.content
                
                # 从文档内容中查找图片引用
                # 格式: [IMAGE:image_id:alt_text] 或 [IMAGE:alt_text]
                import re
                image_pattern = r'\[IMAGE:([^\]:]+)(?::([^\]]+))?\]'
                matches = list(re.finditer(image_pattern, content))
                logger.info(f"📝 从纯文本中找到 {len(matches)} 个图片占位符")
                
                for match in matches:
                    image_id = match.group(1)
                    alt_text = match.group(2) or "图片"
                    position = (match.start(), match.end())
                    
                    # 构建图片路径
                    image_path = self._get_image_path(image_id)
                    
                    images.append({
                        "image_id": image_id,
                        "image_path": image_path,
                        "alt_text": alt_text,
                        "position": position,
                        "description": "",
                    })
            
            logger.info(f"🖼️ 总共找到 {len(images)} 张图片需要处理")
            
            if not images:
                logger.info("ℹ️ 没有找到图片，跳过图片处理")
                return {
                    "images": [],
                    "current_step": "图片处理完成 (0 张)",
                    "progress": 12,
                }
            
            if images:
                logger.info(f"🔄 开始处理 {len(images)} 张图片...")
                # 使用视觉模型提取图片描述
                try:
                    logger.info(f"🔧 检查视觉模型配置: USE_VISION_MODEL={settings.USE_VISION_MODEL}")
                    if not settings.USE_VISION_MODEL:
                        logger.info("⚠️ 视觉模型未启用，跳过图片描述提取")
                        for img in images:
                            img["description"] = f"[图片: {img['alt_text']}]"
                    else:
                        vision_service = get_vision_service()
                        logger.info(f"✅ 视觉模型服务已获取，开始提取描述...")
                        descriptions = await vision_service.batch_extract_descriptions(
                            images=[{
                                "image_id": img["image_id"],
                                "image_path": img["image_path"],
                                "context": img["alt_text"],
                            } for img in images]
                        )
                        
                        # 更新图片描述
                        desc_map = {d["image_id"]: d["description"] for d in descriptions}
                        for img in images:
                            img["description"] = desc_map.get(img["image_id"], f"[图片: {img['alt_text']}]")
                        
                        # 保存图片描述到 PostgreSQL
                        await self._save_image_descriptions_to_db(images)
                        
                        logger.info(f"✅ 成功提取了 {len(images)} 张图片的描述并保存到数据库")
                except Exception as e:
                    logger.error(f"❌ 图片描述提取失败: {e}", exc_info=True)
                    for img in images:
                        img["description"] = f"[图片: {img['alt_text']}]"
            
            return {
                "images": images,
                "current_step": f"图片处理完成 ({len(images)} 张)",
                "progress": 12,
            }
        except Exception as e:
            logger.error(f"❌ _node_extract_images 执行异常: {e}", exc_info=True)
            return {
                "images": [],
                "current_step": "图片处理失败（异常）",
                "progress": 12,
            }
    
    def _get_image_path(self, image_id: str) -> str:
        """根据 image_id 获取图片文件路径"""
        import os
        from pathlib import Path
        from .document_editor import UPLOAD_DIR
        
        # 使用配置的 UPLOAD_DIR
        uploads_dir = UPLOAD_DIR if UPLOAD_DIR else Path("uploads/images")
        uploads_dir = Path(uploads_dir) if not isinstance(uploads_dir, Path) else uploads_dir
        
        # 尝试多种路径格式
        possible_paths = [
            uploads_dir / image_id,
            uploads_dir / f"{image_id}.png",
            uploads_dir / f"{image_id}.jpg",
            uploads_dir / f"{image_id}.jpeg",
        ]
        
        # 检查日期格式的路径 (2026/01/18/img_xxx.png)
        if image_id.startswith("img_"):
            # 尝试最近的日期目录
            from datetime import datetime, timedelta
            for days_ago in range(7):
                date = datetime.now() - timedelta(days=days_ago)
                date_path = date.strftime("%Y/%m/%d")
                for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
                    path = uploads_dir / date_path / f"{image_id}{ext}"
                    if path.exists():
                        return str(path.absolute())
        
        for path in possible_paths:
            if path.exists():
                return str(path.absolute())
        
        # 返回第一个可能的路径（即使不存在，用于后续处理）
        return str(possible_paths[0].absolute()) if possible_paths else ""
    
    def _get_image_path_from_src(self, src: str, image_id: str) -> str:
        """从 src URL 获取图片文件路径"""
        import os
        from pathlib import Path
        from .document_editor import UPLOAD_DIR
        
        logger.debug(f"🔍 [路径解析] src={src}, image_id={image_id}, UPLOAD_DIR={UPLOAD_DIR}")
        
        if not src:
            logger.debug(f"🔍 [路径解析] src 为空，使用默认方法")
            return self._get_image_path(image_id)
        
        # 如果 src 是相对路径，如 /api/uploads/images/2026/01/21/img_xxx.jpg
        if src.startswith("/api/uploads/"):
            # 转换为实际文件路径
            # /api/uploads/images/2026/01/21/img_xxx.jpg -> 2026/01/21/img_xxx.jpg
            relative_path = src.replace("/api/uploads/images/", "")
            logger.debug(f"🔍 [路径解析] 相对路径: {relative_path}")
            
            # 使用 UPLOAD_DIR
            uploads_dir = UPLOAD_DIR if UPLOAD_DIR else Path("uploads/images")
            uploads_dir = Path(uploads_dir) if not isinstance(uploads_dir, Path) else uploads_dir
            logger.debug(f"🔍 [路径解析] uploads_dir: {uploads_dir}")
            
            full_path = uploads_dir / relative_path
            logger.debug(f"🔍 [路径解析] 完整路径: {full_path}, 存在: {full_path.exists()}")
            if full_path.exists():
                return str(full_path.absolute())
            
            # 如果不存在，尝试不带扩展名
            path_without_ext = full_path.parent / full_path.stem
            logger.debug(f"🔍 [路径解析] 尝试无扩展名: {path_without_ext}, 存在: {path_without_ext.exists()}")
            if path_without_ext.exists():
                return str(path_without_ext.absolute())
        
        # 如果 src 是绝对路径
        if os.path.isabs(src) and os.path.exists(src):
            logger.debug(f"🔍 [路径解析] src 是绝对路径且存在: {src}")
            return src
        
        # 回退到默认方法
        logger.debug(f"🔍 [路径解析] 回退到默认方法")
        return self._get_image_path(image_id)
    
    async def _save_image_descriptions_to_db(self, images: List[Dict[str, Any]]):
        """
        将图片描述保存到 PostgreSQL 数据库
        
        Args:
            images: 图片信息列表，包含 image_id, image_path, description, alt_text
        """
        try:
            from ..utils.db_session import async_session_maker
            from ..models.database import DocumentImage
            from sqlalchemy import select, update
            from datetime import datetime
            
            async with async_session_maker() as db:
                for img in images:
                    image_id = img.get("image_id", "")
                    description = img.get("description", "")
                    
                    if not image_id or not description:
                        continue
                    
                    # 检查是否已存在
                    result = await db.execute(
                        select(DocumentImage).where(DocumentImage.image_id == image_id)
                    )
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        # 更新描述
                        await db.execute(
                            update(DocumentImage)
                            .where(DocumentImage.image_id == image_id)
                            .values(
                                description=description,
                                description_extracted_at=datetime.now(),
                            )
                        )
                    else:
                        # 创建新记录
                        new_image = DocumentImage(
                            image_id=image_id,
                            file_name=f"{image_id}.png",
                            file_path=img.get("image_path", ""),
                            file_url=f"/api/images/{image_id}",
                            file_size=0,
                            mime_type="image/png",
                            description=description,
                            description_extracted_at=datetime.now(),
                            alt_text=img.get("alt_text", ""),
                        )
                        db.add(new_image)
                
                await db.commit()
                logger.info(f"已将 {len(images)} 张图片描述保存到 PostgreSQL")
                
        except Exception as e:
            logger.error(f"保存图片描述到 PostgreSQL 失败: {e}")
    
    async def _node_enhance_content_with_images(
        self,
        state: AnalysisState
    ) -> Dict[str, Any]:
        """节点: 用图片描述增强文档内容"""
        chunks = state.get("chunks", [])
        images = state.get("images", [])
        
        logger.info(f"🔄 [增强内容] 开始处理，chunks={len(chunks)}, images={len(images)}")
        
        if not images:
            logger.info("🔄 [增强内容] 无图片，跳过增强")
            return {"progress": 14}
        
        # 创建图片描述映射
        image_desc_map = {}
        for img in images:
            image_desc_map[img["image_id"]] = {
                "description": img["description"],
                "position": img["position"],
            }
        logger.info(f"🔄 [增强内容] 图片描述映射: {list(image_desc_map.keys())}")
        
        # 在每个分块中替换图片占位符为描述
        import re
        enhanced_chunks = []
        total_replacements = 0
        
        for chunk in chunks:
            content = chunk.content
            
            # 先统计有多少占位符
            placeholders = re.findall(r'\[IMAGE:([^\]:]+)(?::([^\]]+))?\]', content)
            logger.info(f"🔄 [增强内容] 分块 {chunk.chunk_id} 中发现 {len(placeholders)} 个图片占位符")
            
            # 替换图片占位符
            replacement_count = [0]  # 用列表来在闭包中修改
            def replace_image(match):
                image_id = match.group(1)
                alt_text = match.group(2) or "图片"
                if image_id in image_desc_map:
                    desc = image_desc_map[image_id]["description"]
                    replacement_count[0] += 1
                    logger.info(f"✅ 替换图片 {image_id}: {desc[:50]}...")
                    # 保留 image_id 以便后续提取事实时能关联到具体图片
                    return f"\n[图片内容开始: {image_id}: {alt_text}]\n{desc}\n[图片内容结束]\n"
                else:
                    logger.warning(f"⚠️ 图片 {image_id} 不在映射中，可用的: {list(image_desc_map.keys())}")
                return match.group(0)
            
            enhanced_content = re.sub(
                r'\[IMAGE:([^\]:]+)(?::([^\]]+))?\]',
                replace_image,
                content
            )
            total_replacements += replacement_count[0]
            
            # 创建增强后的分块
            enhanced_chunk = DocumentChunk(
                chunk_id=chunk.chunk_id,
                content=enhanced_content,
                start_position=chunk.start_position,
                end_position=chunk.end_position,
                chapter=chunk.chapter,
                section=chunk.section,
            )
            enhanced_chunks.append(enhanced_chunk)
        
        logger.info(f"✅ [增强内容] 完成，共替换 {total_replacements} 个图片占位符")
        
        return {
            "chunks": enhanced_chunks,
            "current_step": "图片描述已嵌入文档",
            "progress": 15,
        }
    
    async def _node_extract_facts(
        self,
        state: AnalysisState,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """节点: 提取事实"""
        chunks = state.get("chunks", [])
        images = state.get("images", [])
        
        if not chunks:
            return {"facts": [], "progress": 50}
        
        async def update_progress(p: float):
            progress = 15 + p * 0.35
            if progress_callback:
                await progress_callback(progress, f"提取事实 ({p:.0f}%)")
        
        # 提取并过滤事实
        facts = await self._fact_extractor.extract_and_filter(
            chunks=chunks,
            extraction_progress_callback=update_progress,
        )
        
        # 为从图片中提取的事实添加标记
        if images:
            image_positions = {img["image_id"]: img for img in images}
            import re
            for fact in facts:
                # 检查事实来源是否包含图片内容
                if "[图片内容开始:" in fact.source_text or "[图片:" in fact.source_text or "[IMAGE:" in fact.source_text:
                    # 标记为图片来源事实
                    fact.fact_type = f"image_{fact.fact_type}"
                    fact.is_image_source = True
                    
                    # 从 source_text 中提取图片ID
                    # 方法1: 匹配 [IMAGE:image_id:alt] 或 [IMAGE:image_id]
                    image_id_match = re.search(r'\[IMAGE:([^\]:]+)', fact.source_text)
                    if image_id_match:
                        image_id = image_id_match.group(1)
                        fact.image_id = image_id
                        if image_id in image_positions:
                            fact.image_description = image_positions[image_id].get("description")
                        logger.info(f"✅ 从 [IMAGE:] 提取图片ID: {fact.fact_id} -> {image_id}")
                    else:
                        # 方法2: 匹配 [图片内容开始: image_id: alt_text] (新格式，保留了image_id)
                        img_content_match = re.search(r'\[图片内容开始:\s*([^:\]]+)(?::\s*[^\]]+)?\]', fact.source_text)
                        if img_content_match:
                            potential_id = img_content_match.group(1).strip()
                            # 检查是否是有效的 image_id (以 img_ 开头或在 images 列表中)
                            if potential_id.startswith('img_') or potential_id in image_positions:
                                fact.image_id = potential_id
                                if potential_id in image_positions:
                                    fact.image_description = image_positions[potential_id].get("description")
                                logger.info(f"✅ 从 [图片内容开始:] 提取图片ID: {fact.fact_id} -> {potential_id}")
                            else:
                                # potential_id 可能是 alt_text，尝试通过 alt 匹配
                                for img_info in images:
                                    img_alt = img_info.get("alt", "")
                                    if img_alt and (img_alt == potential_id or potential_id in img_alt or img_alt in potential_id):
                                        fact.image_id = img_info["image_id"]
                                        fact.image_description = img_info.get("description")
                                        logger.info(f"✅ 通过 alt 匹配图片ID: {fact.fact_id} -> {img_info['image_id']}")
                                        break
                        else:
                            # 方法3: 回退到旧逻辑，通过 alt_text 匹配
                            for img_info in images:
                                img_alt = img_info.get("alt", "")
                                if img_alt and img_alt in fact.source_text:
                                    fact.image_id = img_info["image_id"]
                                    fact.image_description = img_info.get("description")
                                    logger.info(f"✅ 通过 source_text 内容匹配图片ID: {fact.fact_id} -> {img_info['image_id']}")
                                    break
                    
                    logger.info(f"📸 标记图片来源事实: {fact.fact_id}, image_id: {fact.image_id}, is_image_source: {fact.is_image_source}")
        
        logger.info(f"提取到 {len(facts)} 个事实")
        
        return {
            "facts": facts,
            "current_step": "事实提取完成",
            "progress": 50,
        }
    
    async def _node_generate_candidate_pairs(
        self,
        state: AnalysisState
    ) -> Dict[str, Any]:
        """节点: 生成候选冲突对 (优化后的预筛选)"""
        facts = state.get("facts", [])
        
        if len(facts) < 2:
            return {"candidate_pairs": [], "progress": 55}
        
        # 使用改进的候选对生成策略
        candidate_pairs = await self._generate_smart_candidates(facts)
        
        logger.info(f"生成 {len(candidate_pairs)} 个候选冲突对")
        
        return {
            "candidate_pairs": candidate_pairs,
            "current_step": f"候选对筛选完成 ({len(candidate_pairs)} 对)",
            "progress": 55,
        }
    
    async def _generate_smart_candidates(
        self,
        facts: List[FactWithSource]
    ) -> List[tuple]:
        """
        智能生成候选冲突对
        
        使用多种策略减少需要检测的对数：
        1. 类型相似性 - 同类型事实更可能冲突
        2. 实体重叠 - 提及相同实体的事实
        3. 主题聚类 - 关于同一主题的事实
        """
        from itertools import combinations
        import re
        
        candidate_pairs = []
        seen = set()
        
        # 策略1: 同类型事实配对
        type_groups: Dict[str, List[FactWithSource]] = {}
        for fact in facts:
            base_type = fact.fact_type.replace("image_", "")  # 去除图片前缀
            if base_type not in type_groups:
                type_groups[base_type] = []
            type_groups[base_type].append(fact)
        
        for fact_type, type_facts in type_groups.items():
            if len(type_facts) >= 2:
                for pair in combinations(type_facts, 2):
                    pair_key = tuple(sorted([pair[0].fact_id, pair[1].fact_id]))
                    if pair_key not in seen:
                        seen.add(pair_key)
                        candidate_pairs.append(pair)
        
        # 策略2: 实体重叠配对
        def extract_entities(text: str) -> set:
            """提取实体（数字、日期、名称等）"""
            entities = set()
            # 数字
            entities.update(re.findall(r'\d+(?:\.\d+)?(?:%|万|亿|元)?', text))
            # 中文名称（2-4字）
            entities.update(re.findall(r'[\u4e00-\u9fa5]{2,4}(?:公司|集团|大学|项目|系统)?', text))
            # 英文单词
            entities.update(w.lower() for w in re.findall(r'\b[A-Za-z]+\b', text) if len(w) > 2)
            return entities
        
        fact_entities = [(fact, extract_entities(fact.content)) for fact in facts]
        
        for i, (fact_a, entities_a) in enumerate(fact_entities):
            for j, (fact_b, entities_b) in enumerate(fact_entities[i+1:], i+1):
                pair_key = tuple(sorted([fact_a.fact_id, fact_b.fact_id]))
                if pair_key in seen:
                    continue
                
                # 计算实体重叠
                overlap = len(entities_a & entities_b)
                if overlap >= 1:  # 至少有1个共同实体
                    seen.add(pair_key)
                    candidate_pairs.append((fact_a, fact_b))
        
        # 策略3: 图片事实与文本事实配对
        image_facts = [f for f in facts if f.fact_type.startswith("image_")]
        text_facts = [f for f in facts if not f.fact_type.startswith("image_")]
        
        for img_fact in image_facts:
            img_entities = extract_entities(img_fact.content)
            for txt_fact in text_facts:
                pair_key = tuple(sorted([img_fact.fact_id, txt_fact.fact_id]))
                if pair_key in seen:
                    continue
                
                txt_entities = extract_entities(txt_fact.content)
                if len(img_entities & txt_entities) >= 1:
                    seen.add(pair_key)
                    candidate_pairs.append((img_fact, txt_fact))
        
        return candidate_pairs
    
    async def _node_detect_conflicts(
        self,
        state: AnalysisState,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """节点: 检测冲突"""
        candidate_pairs = state.get("candidate_pairs", [])
        facts = state.get("facts", [])
        
        if not candidate_pairs:
            return {"conflicts": [], "progress": 75}
        
        async def update_progress(p: float):
            progress = 55 + p * 0.20
            if progress_callback:
                await progress_callback(progress, f"检测冲突 ({p:.0f}%)")
        
        # 直接使用候选对进行冲突检测
        conflicts = await self._conflict_detector._detect_conflicts_in_pairs(
            pairs=candidate_pairs,
            progress_callback=update_progress,
        )
        
        # 去重和排序
        conflicts = self._conflict_detector._merge_conflicts(conflicts)
        
        logger.info(f"检测到 {len(conflicts)} 个冲突")
        
        return {
            "conflicts": conflicts,
            "current_step": "冲突检测完成",
            "progress": 75,
        }
    
    async def _node_verify_conflicts(
        self,
        state: AnalysisState,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """节点: 验证冲突"""
        conflicts = state.get("conflicts", [])
        document = state["document"]
        skip_verification = state.get("skip_verification", False)
        
        if not conflicts or skip_verification:
            conflict_reports = [
                ConflictReport(conflict=c, verification=None)
                for c in conflicts
            ]
            return {"conflict_reports": conflict_reports, "progress": 95}
        
        async def update_progress(p: float):
            progress = 75 + p * 0.20
            if progress_callback:
                await progress_callback(progress, f"验证冲突 ({p:.0f}%)")
        
        conflict_reports = await self._fact_verifier.verify_conflicts(
            conflicts=conflicts,
            document_content=document.content,
            progress_callback=update_progress,
        )
        
        logger.info(f"冲突验证完成，{len(conflict_reports)} 个报告")
        
        return {
            "conflict_reports": conflict_reports,
            "current_step": "冲突验证完成",
            "progress": 95,
        }
    
    async def _node_generate_result(
        self,
        state: AnalysisState
    ) -> Dict[str, Any]:
        """节点: 生成分析结果"""
        task_id = state["task_id"]
        document = state["document"]
        metadata = state.get("metadata", {})
        chunks = state.get("chunks", [])
        facts = state.get("facts", [])
        conflict_reports = state.get("conflict_reports", [])
        
        # 统计冲突类型分布
        conflict_type_distribution = dict(Counter(
            cr.conflict.conflict_type.value for cr in conflict_reports
        ))
        
        # 统计严重程度分布
        severity_distribution = {
            "critical": sum(1 for cr in conflict_reports if cr.conflict.severity >= 0.9),
            "high": sum(1 for cr in conflict_reports if 0.6 <= cr.conflict.severity < 0.9),
            "medium": sum(1 for cr in conflict_reports if 0.3 <= cr.conflict.severity < 0.6),
            "low": sum(1 for cr in conflict_reports if cr.conflict.severity < 0.3),
        }
        
        verified_count = sum(
            1 for cr in conflict_reports 
            if cr.verification and cr.verification.is_verified
        )
        
        result = AnalysisResult(
            task_id=task_id,
            document_title=metadata.get("title"),
            document_length=metadata.get("content_length", len(document.content)),
            total_chunks=len(chunks),
            total_facts=len(facts),
            total_conflicts=len(conflict_reports),
            verified_conflicts=verified_count,
            facts=facts,
            conflicts=conflict_reports,
            analysis_time=0,  # 将在外层计算
            conflict_type_distribution=conflict_type_distribution,
            severity_distribution=severity_distribution,
        )
        
        return {
            "result": result,
            "current_step": "分析完成",
            "progress": 100,
        }
    
    # ==================== 主入口 ====================
    
    async def analyze_document(
        self,
        document: DocumentInput,
        task_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
        skip_verification: bool = False,
        content_json: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        执行完整的文档分析流程
        
        使用 LangGraph 风格的工作流执行分析
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        
        # 创建任务
        task = AnalysisTask(
            task_id=task_id,
            status=TaskStatus.PENDING,
            progress=0.0,
            current_step="初始化",
        )
        self._tasks[task_id] = task
        
        async def update_progress(progress: float, step: str):
            task.progress = progress
            task.current_step = step
            task.updated_at = datetime.now()
            if progress_callback:
                await progress_callback(task_id, progress, step)
        
        # 初始化状态
        state: AnalysisState = {
            "document": document,
            "task_id": task_id,
            "skip_verification": skip_verification,
            "content_json": content_json,
            "chunks": [],
            "images": [],
            "facts": [],
            "candidate_pairs": [],
            "conflicts": [],
            "conflict_reports": [],
            "metadata": {},
            "current_step": "初始化",
            "progress": 0,
            "error": None,
            "result": None,
        }
        
        try:
            # ===== 工作流执行 =====
            
            # 步骤1: 验证文档
            result = await self._node_validate_document(state)
            if result.get("error"):
                raise ValueError(result["error"])
            state.update(result)
            await update_progress(state["progress"], state["current_step"])
            
            # 步骤2 & 3: 并行处理 - 文档分块 + 图片提取
            task.status = TaskStatus.EXTRACTING
            logger.info(f"📋 准备并行处理：文档分块 + 图片提取，content_json={state.get('content_json') is not None}")
            
            try:
                process_result, image_result = await asyncio.gather(
                    self._node_process_document(state),
                    self._node_extract_images(state),
                    return_exceptions=True,  # 即使有异常也继续
                )
                
                # 检查是否有异常
                if isinstance(process_result, Exception):
                    logger.error(f"❌ 文档处理异常: {process_result}", exc_info=process_result)
                    raise process_result
                if isinstance(image_result, Exception):
                    logger.error(f"❌ 图片提取异常: {image_result}", exc_info=image_result)
                    # 图片提取失败不影响整体流程，使用空结果
                    image_result = {"images": [], "current_step": "图片处理失败", "progress": 12}
                
                if process_result.get("error"):
                    raise ValueError(process_result["error"])
                
                logger.info(f"✅ 并行处理完成：文档={process_result.get('current_step')}, 图片={image_result.get('current_step')}")
                
                state.update(process_result)
                state.update(image_result)
                await update_progress(state["progress"], "文档和图片处理完成")
            except Exception as e:
                logger.error(f"❌ 并行处理异常: {e}", exc_info=True)
                # 即使图片处理失败，也继续执行
                if "image_result" not in locals() or isinstance(image_result, Exception):
                    logger.warning("⚠️ 图片处理失败，使用空结果继续")
                    state.update({"images": [], "current_step": "图片处理失败", "progress": 12})
                raise
            
            # 步骤4: 用图片描述增强内容
            enhance_result = await self._node_enhance_content_with_images(state)
            state.update(enhance_result)
            
            # 步骤5: 提取事实
            facts_result = await self._node_extract_facts(
                state, 
                progress_callback=update_progress
            )
            state.update(facts_result)
            
            if not state["facts"]:
                logger.warning("未提取到任何事实")
                return self._create_empty_result(
                    task_id, document, state["metadata"], time.time() - start_time
                )
            
            # 步骤6: 生成候选对
            task.status = TaskStatus.DETECTING
            candidate_result = await self._node_generate_candidate_pairs(state)
            state.update(candidate_result)
            await update_progress(state["progress"], state["current_step"])
            
            # 步骤7: 检测冲突
            conflict_result = await self._node_detect_conflicts(
                state,
                progress_callback=update_progress
            )
            state.update(conflict_result)
            
            # 步骤8: 验证冲突
            if state["conflicts"] and not skip_verification:
                task.status = TaskStatus.VERIFYING
                verify_result = await self._node_verify_conflicts(
                    state,
                    progress_callback=update_progress
                )
                state.update(verify_result)
            else:
                state["conflict_reports"] = [
                    ConflictReport(conflict=c, verification=None)
                    for c in state["conflicts"]
                ]
            
            # 步骤9: 生成结果
            final_result = await self._node_generate_result(state)
            state.update(final_result)
            
            # 计算分析时间
            analysis_time = time.time() - start_time
            result = state["result"]
            result.analysis_time = analysis_time
            
            # 更新任务状态
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            task.current_step = "完成"
            await update_progress(100, "分析完成")
            
            logger.info(
                f"文档分析完成: {result.total_facts} 个事实, "
                f"{result.total_conflicts} 个冲突, "
                f"耗时 {analysis_time:.2f}秒"
            )
            
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.current_step = "失败"
            logger.error(f"文档分析失败: {e}")
            raise
    
    def _create_empty_result(
        self,
        task_id: str,
        document: DocumentInput,
        metadata: Dict[str, Any],
        analysis_time: float,
    ) -> AnalysisResult:
        """创建空结果"""
        return AnalysisResult(
            task_id=task_id,
            document_title=metadata.get("title"),
            document_length=len(document.content),
            total_chunks=metadata.get("total_chunks", 0),
            total_facts=0,
            total_conflicts=0,
            verified_conflicts=0,
            facts=[],
            conflicts=[],
            analysis_time=analysis_time,
            conflict_type_distribution={},
            severity_distribution={},
        )
    
    def get_task(self, task_id: str) -> Optional[AnalysisTask]:
        """获取任务状态"""
        return self._tasks.get(task_id)
    
    def list_tasks(self) -> List[AnalysisTask]:
        """列出所有任务"""
        return list(self._tasks.values())
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.EXTRACTING, 
                                     TaskStatus.DETECTING, TaskStatus.VERIFYING]:
            task.status = TaskStatus.FAILED
            task.error_message = "用户取消"
            return True
        return False


# 创建全局分析引擎实例
_langgraph_engine_instance: Optional[LangGraphAnalysisEngine] = None


def get_langgraph_engine() -> LangGraphAnalysisEngine:
    """获取 LangGraph 分析引擎单例"""
    global _langgraph_engine_instance
    if _langgraph_engine_instance is None:
        _langgraph_engine_instance = LangGraphAnalysisEngine()
    return _langgraph_engine_instance

