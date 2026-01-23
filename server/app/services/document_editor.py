"""
PatPat-Inconsistency-Hunter 统一文档编辑服务
管理文档内容（文字、表格、图片、格式）
支持富文本编辑、实时协作、导出等功能
"""

import os
import uuid
import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from ..utils.logger import logger
from ..utils.redis_client import get_redis_client


# ==================== 常量定义 ====================

# 上传目录：优先使用绝对路径，如果不存在则使用相对路径
_upload_dir_candidates = [
    Path("/app/uploads/images"),  # Docker 容器中的路径
    Path("uploads/images"),  # 相对路径
    Path("./uploads/images"),  # 当前目录
]
UPLOAD_DIR = None
for candidate in _upload_dir_candidates:
    if candidate.exists():
        UPLOAD_DIR = candidate
        break
if UPLOAD_DIR is None:
    # 如果都不存在，使用第一个作为默认值
    UPLOAD_DIR = _upload_dir_candidates[0]
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

# Redis键前缀
REDIS_DOC_CONTENT = "patpat:doc_content:"
REDIS_DOC_LOCK = "patpat:doc_lock:"
REDIS_DETECTION_LOCK = "patpat:detection_lock:"


# ==================== 文档内容格式 ====================

class RichTextContent:
    """
    富文本内容管理
    
    支持的内容格式：
    - TipTap JSON格式（推荐）
    - Quill Delta格式
    - HTML格式
    - 纯文本格式
    """
    
    @staticmethod
    def create_empty() -> Dict[str, Any]:
        """创建空白富文本内容"""
        return {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": []
                }
            ]
        }
    
    @staticmethod
    def from_plain_text(text: str) -> Dict[str, Any]:
        """从纯文本创建富文本内容"""
        paragraphs = text.split('\n')
        content = []
        
        for para in paragraphs:
            if para.strip():
                content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": para}]
                })
            else:
                content.append({"type": "paragraph", "content": []})
        
        return {
            "type": "doc",
            "content": content if content else [{"type": "paragraph", "content": []}]
        }
    
    @staticmethod
    def to_plain_text(content_json: Dict[str, Any], include_image_placeholders: bool = True) -> str:
        """
        从富文本提取纯文本
        
        Args:
            content_json: 富文本JSON
            include_image_placeholders: 是否包含图片占位符（用于后续视觉模型处理）
        """
        if not content_json or "content" not in content_json:
            return ""
        
        def extract_text(node: Dict) -> str:
            node_type = node.get("type", "")
            
            if node_type == "text":
                return node.get("text", "")
            
            # 图片节点 - 添加占位符
            if node_type == "image":
                if include_image_placeholders:
                    attrs = node.get("attrs", {})
                    image_id = attrs.get("imageId") or attrs.get("data-image-id") or ""
                    alt = attrs.get("alt", "图片")
                    if image_id:
                        return f"\n[IMAGE:{image_id}:{alt}]\n"
                    else:
                        # 没有image_id时，使用src的hash作为标识
                        src = attrs.get("src", "")
                        if src:
                            src_hash = hashlib.md5(src.encode()).hexdigest()[:8]
                            return f"\n[IMAGE:{src_hash}:{alt}]\n"
                return ""
            
            result = []
            for child in node.get("content", []):
                result.append(extract_text(child))
            
            # 段落之间添加换行
            if node_type in ("paragraph", "heading"):
                return "".join(result) + "\n"
            
            return "".join(result)
        
        return extract_text(content_json).strip()
    
    @staticmethod
    def extract_images(content_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从富文本内容中提取所有图片信息
        
        Returns:
            图片信息列表，包含 src, alt, imageId 等
        """
        if not content_json or "content" not in content_json:
            return []
        
        images = []
        position = [0]  # 使用列表来避免 nonlocal 与参数冲突
        
        def find_images(node: Dict):
            node_type = node.get("type", "")
            
            if node_type == "image":
                attrs = node.get("attrs", {})
                images.append({
                    "src": attrs.get("src", ""),
                    "alt": attrs.get("alt", ""),
                    "imageId": attrs.get("imageId") or attrs.get("data-image-id"),
                    "position": position[0],
                })
                return
            
            for child in node.get("content", []):
                if child.get("type") == "text":
                    position[0] += len(child.get("text", ""))
                find_images(child)
        
        find_images(content_json)
        return images
    
    @staticmethod
    def replace_image_placeholder(text: str, image_id: str, replacement: str) -> str:
        """
        替换图片占位符为实际文字（视觉模型处理后）
        
        Args:
            text: 包含图片占位符的文本
            image_id: 图片ID
            replacement: 替换文字（视觉模型生成的描述）
        
        Returns:
            替换后的文本
        """
        import re
        pattern = rf"\[IMAGE:{re.escape(image_id)}:[^\]]*\]"
        return re.sub(pattern, replacement, text)
    
    @staticmethod
    def to_html(content_json: Dict[str, Any]) -> str:
        """从富文本生成HTML，支持完整格式"""
        import html as html_module
        
        if not content_json or "content" not in content_json:
            return ""
        
        def render_node(node: Dict) -> str:
            if not node:
                return ""
            node_type = node.get("type") or ""
            content = node.get("content") or []
            marks = node.get("marks") or []
            
            # 文本节点
            if node_type == "text":
                raw_text = node.get("text") or ""
                text = html_module.escape(raw_text)
                # 应用样式标记（按正确顺序包裹）
                for mark in marks or []:
                    mark_type = mark.get("type", "") if mark else ""
                    if mark_type == "bold":
                        text = f"<strong>{text}</strong>"
                    elif mark_type == "italic":
                        text = f"<em>{text}</em>"
                    elif mark_type == "underline":
                        text = f"<u>{text}</u>"
                    elif mark_type == "strike":
                        text = f"<s>{text}</s>"
                    elif mark_type == "code":
                        text = f"<code class=\"inline-code\">{text}</code>"
                    elif mark_type == "highlight":
                        attrs = mark.get("attrs") or {}
                        color = attrs.get("color") or "#ffeb3b"
                        text = f'<mark style="background-color: {color}">{text}</mark>'
                    elif mark_type == "subscript":
                        text = f"<sub>{text}</sub>"
                    elif mark_type == "superscript":
                        text = f"<sup>{text}</sup>"
                    elif mark_type == "textStyle":
                        style_parts = []
                        attrs = mark.get("attrs") or {}
                        if attrs.get("color"):
                            style_parts.append(f"color: {attrs['color']}")
                        if attrs.get("backgroundColor"):
                            style_parts.append(f"background-color: {attrs['backgroundColor']}")
                        if attrs.get("fontSize"):
                            style_parts.append(f"font-size: {attrs['fontSize']}")
                        if attrs.get("fontFamily"):
                            style_parts.append(f"font-family: {attrs['fontFamily']}")
                        if style_parts:
                            text = f'<span style="{"; ".join(style_parts)}">{text}</span>'
                    elif mark_type == "link":
                        attrs = mark.get("attrs") or {}
                        href = html_module.escape(attrs.get("href") or "#")
                        target = attrs.get("target") or "_blank"
                        text = f'<a href="{href}" target="{target}" rel="noopener noreferrer">{text}</a>'
                return text
            
            # 其他节点
            children_html = "".join(render_node(child) for child in content)
            
            if node_type == "paragraph":
                # 处理段落对齐
                attrs = node.get("attrs") or {}
                text_align = attrs.get("textAlign")
                if text_align:
                    return f'<p style="text-align: {text_align}">{children_html}</p>'
                return f"<p>{children_html}</p>"
            elif node_type == "heading":
                attrs = node.get("attrs") or {}
                level = attrs.get("level") or 1
                text_align = attrs.get("textAlign")
                if text_align:
                    return f'<h{level} style="text-align: {text_align}">{children_html}</h{level}>'
                return f"<h{level}>{children_html}</h{level}>"
            elif node_type == "bulletList":
                return f"<ul>{children_html}</ul>"
            elif node_type == "orderedList":
                attrs = node.get("attrs") or {}
                start = attrs.get("start") or 1
                if start != 1:
                    return f'<ol start="{start}">{children_html}</ol>'
                return f"<ol>{children_html}</ol>"
            elif node_type == "listItem":
                return f"<li>{children_html}</li>"
            elif node_type == "taskList":
                return f'<ul class="task-list">{children_html}</ul>'
            elif node_type == "taskItem":
                attrs = node.get("attrs") or {}
                checked = attrs.get("checked", False)
                checkbox = '<input type="checkbox" disabled checked />' if checked else '<input type="checkbox" disabled />'
                return f'<li class="task-item">{checkbox}{children_html}</li>'
            elif node_type == "blockquote":
                return f"<blockquote>{children_html}</blockquote>"
            elif node_type == "codeBlock":
                attrs = node.get("attrs") or {}
                language = attrs.get("language") or ""
                lang_class = f' class="language-{language}"' if language else ""
                return f"<pre><code{lang_class}>{children_html}</code></pre>"
            elif node_type == "image":
                attrs = node.get("attrs", {}) or {}
                src = html_module.escape(attrs.get("src") or "")
                alt = html_module.escape(attrs.get("alt") or "")
                title = attrs.get("title") or ""
                if title:
                    title = html_module.escape(title)
                image_id = attrs.get("data-image-id") or attrs.get("imageId") or ""
                width = attrs.get("width")
                height = attrs.get("height")
                
                style_parts = []
                if width:
                    style_parts.append(f"width: {width}px" if isinstance(width, int) else f"width: {width}")
                if height:
                    style_parts.append(f"height: {height}px" if isinstance(height, int) else f"height: {height}")
                
                style_attr = f' style="{"; ".join(style_parts)}"' if style_parts else ""
                title_attr = f' title="{title}"' if title else ""
                data_id = f' data-image-id="{image_id}"' if image_id else ""
                
                return f'<img src="{src}" alt="{alt}"{title_attr}{data_id}{style_attr} class="document-image" />'
            elif node_type == "table":
                return f'<table class="document-table">{children_html}</table>'
            elif node_type == "tableRow":
                return f"<tr>{children_html}</tr>"
            elif node_type == "tableCell":
                attrs = node.get("attrs") or {}
                colspan = attrs.get("colspan") or 1
                rowspan = attrs.get("rowspan") or 1
                attrs_str = ""
                if colspan and colspan > 1:
                    attrs_str += f' colspan="{colspan}"'
                if rowspan and rowspan > 1:
                    attrs_str += f' rowspan="{rowspan}"'
                return f"<td{attrs_str}>{children_html}</td>"
            elif node_type == "tableHeader":
                attrs = node.get("attrs") or {}
                colspan = attrs.get("colspan") or 1
                rowspan = attrs.get("rowspan") or 1
                attrs_str = ""
                if colspan and colspan > 1:
                    attrs_str += f' colspan="{colspan}"'
                if rowspan and rowspan > 1:
                    attrs_str += f' rowspan="{rowspan}"'
                return f"<th{attrs_str}>{children_html}</th>"
            elif node_type == "horizontalRule":
                return "<hr />"
            elif node_type == "hardBreak":
                return "<br />"
            elif node_type == "doc":
                return children_html
            else:
                return children_html
        
        return render_node(content_json)
    
    @staticmethod
    def word_count(content_json: Dict[str, Any]) -> int:
        """统计字数"""
        text = RichTextContent.to_plain_text(content_json)
        # 中文按字符数，英文按单词数
        import re
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return chinese_chars + english_words


# ==================== 文档编辑服务 ====================

class DocumentEditorService:
    """
    统一文档编辑服务
    
    功能：
    - 管理文档内容（编辑时用Redis，保存时落PostgreSQL）
    - 图片上传和管理
    - 格式转换（JSON/HTML/PDF/Markdown）
    - 检测锁管理
    """
    
    def __init__(self):
        self._redis = None
        # 确保上传目录存在
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    async def _get_redis(self):
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    # ==================== 文档内容管理 ====================
    
    async def get_editing_content(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        获取正在编辑的文档内容（从Redis）
        
        Args:
            document_id: 文档ID或房间ID
        
        Returns:
            富文本内容JSON或None
        """
        redis = await self._get_redis()
        key = f"{REDIS_DOC_CONTENT}{document_id}"
        data = await redis.client.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def save_editing_content(
        self,
        document_id: str,
        content_json: Dict[str, Any],
        user_id: str,
        expire: int = 86400,  # 24小时
    ):
        """
        保存编辑中的文档内容（到Redis）
        
        Args:
            document_id: 文档ID或房间ID
            content_json: 富文本内容JSON
            user_id: 编辑用户ID
            expire: 过期时间（秒）
        """
        redis = await self._get_redis()
        key = f"{REDIS_DOC_CONTENT}{document_id}"
        
        data = {
            "content": content_json,
            "last_editor": user_id,
            "updated_at": datetime.now().isoformat(),
        }
        
        await redis.client.set(key, json.dumps(data, ensure_ascii=False), ex=expire)
    
    async def clear_editing_content(self, document_id: str):
        """清除编辑缓存"""
        redis = await self._get_redis()
        key = f"{REDIS_DOC_CONTENT}{document_id}"
        await redis.client.delete(key)
    
    # ==================== 图片管理 ====================
    
    async def upload_image(
        self,
        file_content: bytes,
        file_name: str,
        mime_type: str,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        room_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        上传图片
        
        Args:
            file_content: 文件内容
            file_name: 原始文件名
            mime_type: MIME类型
            user_id: 上传用户ID
            document_id: 关联文档ID
            room_id: 关联房间ID
        
        Returns:
            图片信息字典
        """
        # 验证文件类型
        if mime_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError(f"不支持的图片类型: {mime_type}")
        
        # 验证文件大小
        if len(file_content) > MAX_IMAGE_SIZE:
            raise ValueError(f"图片大小超过限制: {MAX_IMAGE_SIZE / 1024 / 1024}MB")
        
        # 生成唯一文件名
        image_id = f"img_{uuid.uuid4().hex[:12]}"
        ext = file_name.split('.')[-1] if '.' in file_name else 'png'
        new_file_name = f"{image_id}.{ext}"
        
        # 按日期组织目录
        date_dir = datetime.now().strftime("%Y/%m/%d")
        save_dir = UPLOAD_DIR / date_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        file_path = save_dir / new_file_name
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # 生成访问URL
        file_url = f"/api/uploads/images/{date_dir}/{new_file_name}"
        
        # 获取图片尺寸（可选）
        width, height = None, None
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(file_content))
            width, height = img.size
        except:
            pass
        
        logger.info(f"图片上传成功: {image_id}, 用户: {user_id}")
        
        return {
            "image_id": image_id,
            "file_name": file_name,
            "file_path": str(file_path),
            "file_url": file_url,
            "file_size": len(file_content),
            "mime_type": mime_type,
            "width": width,
            "height": height,
            "document_id": document_id,
            "room_id": room_id,
            "user_id": user_id,
        }
    
    def delete_image(self, file_path: str) -> bool:
        """删除图片文件"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
        except Exception as e:
            logger.error(f"删除图片失败: {e}")
        return False
    
    def get_image_absolute_path(self, file_url: str) -> Optional[str]:
        """
        将图片URL转换为绝对路径（用于导出PDF/DOCX）
        
        Args:
            file_url: 图片访问URL（如 /api/uploads/images/2024/01/01/xxx.png）
        
        Returns:
            文件的绝对路径或None
        """
        if not file_url:
            return None
        
        # 移除URL前缀，获取相对路径
        if file_url.startswith("/api/uploads/"):
            # /api/uploads/images/2024/01/01/xxx.png -> uploads/images/2024/01/01/xxx.png
            relative_path = file_url.replace("/api/uploads/", "")
            if not relative_path.startswith("uploads/"):
                relative_path = "uploads/" + relative_path
        elif file_url.startswith("/uploads/"):
            # /uploads/images/... -> uploads/images/...
            relative_path = file_url.lstrip("/")
        elif file_url.startswith("/static/"):
            relative_path = file_url.replace("/static/", "app/static/")
        elif file_url.startswith("uploads/"):
            # 已经是相对路径
            relative_path = file_url
        else:
            return None
        
        # 尝试多种路径可能性
        possible_paths = []
        
        # 路径1: 直接使用相对路径
        path1 = Path(relative_path)
        if path1.exists():
            possible_paths.append(path1.absolute())
        
        # 路径2: 相对于UPLOAD_DIR
        if "images/" in relative_path:
            img_part = relative_path.split("images/", 1)[1]
            path2 = UPLOAD_DIR / "images" / img_part
        else:
            path2 = UPLOAD_DIR / relative_path.lstrip("uploads/")
        if path2.exists():
            possible_paths.append(path2.absolute())
        
        # 路径3: 如果relative_path已经是完整路径，尝试直接使用
        if relative_path.startswith("uploads/"):
            path3 = Path(relative_path)
            if path3.exists():
                possible_paths.append(path3.absolute())
        
        # 返回第一个存在的路径
        if possible_paths:
            abs_path = str(possible_paths[0])
            logger.debug(f"找到图片路径: {abs_path} (原始URL: {file_url})")
            return abs_path
        
        logger.warning(f"无法找到图片路径: {file_url}, relative_path: {relative_path}, UPLOAD_DIR: {UPLOAD_DIR}")
        return None
    
    def convert_images_to_base64(self, content_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        将富文本中的图片URL转换为base64（用于导出）
        
        Args:
            content_json: 富文本JSON
        
        Returns:
            转换后的富文本JSON
        """
        import copy
        import base64
        
        result = copy.deepcopy(content_json)
        
        def process_node(node: Dict):
            if node.get("type") == "image":
                attrs = node.get("attrs", {})
                src = attrs.get("src", "")
                
                # 如果已经是base64，跳过
                if src.startswith("data:"):
                    return
                
                # 尝试获取文件路径并转换
                abs_path = self.get_image_absolute_path(src)
                if abs_path:
                    try:
                        with open(abs_path, "rb") as f:
                            data = f.read()
                        
                        # 获取MIME类型
                        ext = abs_path.split(".")[-1].lower()
                        mime_map = {
                            "jpg": "image/jpeg",
                            "jpeg": "image/jpeg",
                            "png": "image/png",
                            "gif": "image/gif",
                            "webp": "image/webp",
                        }
                        mime = mime_map.get(ext, "image/png")
                        
                        # 转换为base64
                        b64 = base64.b64encode(data).decode()
                        attrs["src"] = f"data:{mime};base64,{b64}"
                    except Exception as e:
                        logger.warning(f"图片转换base64失败: {e}")
            
            # 递归处理子节点
            for child in node.get("content", []):
                process_node(child)
        
        process_node(result)
        return result
    
    # ==================== 检测锁管理 ====================
    
    async def acquire_detection_lock(
        self,
        target_type: str,
        target_id: str,
        task_id: str,
        duration: int = 600,  # 10分钟
    ) -> bool:
        """
        获取检测锁
        
        Args:
            target_type: 目标类型（document/room）
            target_id: 目标ID
            task_id: 任务ID
            duration: 锁定时长（秒）
        
        Returns:
            是否成功获取锁
        """
        redis = await self._get_redis()
        key = f"{REDIS_DETECTION_LOCK}{target_type}:{target_id}"
        
        # 尝试获取锁（使用SET NX）
        result = await redis.client.set(
            key,
            json.dumps({
                "task_id": task_id,
                "locked_at": datetime.now().isoformat(),
            }),
            nx=True,
            ex=duration,
        )
        
        if result:
            logger.info(f"获取检测锁成功: {target_type}:{target_id}, 任务: {task_id}")
        
        return result is not None
    
    async def release_detection_lock(
        self,
        target_type: str,
        target_id: str,
        task_id: str,
    ) -> bool:
        """
        释放检测锁
        
        Args:
            target_type: 目标类型
            target_id: 目标ID
            task_id: 任务ID（只有持有者才能释放）
        
        Returns:
            是否成功释放
        """
        redis = await self._get_redis()
        key = f"{REDIS_DETECTION_LOCK}{target_type}:{target_id}"
        
        # 检查是否是持有者
        data = await redis.client.get(key)
        if data:
            lock_info = json.loads(data)
            if lock_info.get("task_id") == task_id:
                await redis.client.delete(key)
                logger.info(f"释放检测锁: {target_type}:{target_id}")
                return True
        
        return False
    
    async def check_detection_lock(
        self,
        target_type: str,
        target_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        检查检测锁状态
        
        Returns:
            锁信息或None（未锁定）
        """
        redis = await self._get_redis()
        key = f"{REDIS_DETECTION_LOCK}{target_type}:{target_id}"
        
        data = await redis.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    # ==================== 文件解析（导入） ====================
    
    async def parse_document_file(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        解析文档文件（PDF、DOCX、MD、TXT），提取格式和图片，转换为 TipTap JSON
        
        Args:
            file_content: 文件内容（字节）
            filename: 文件名
            mime_type: MIME 类型
            user_id: 用户ID（用于上传图片）
        
        Returns:
            包含 content, content_json, title 的字典
        """
        import os
        from pathlib import Path
        
        filename_lower = filename.lower()
        title = Path(filename).stem  # 使用文件名（不含扩展名）作为标题
        
        # 处理 TXT 文件
        if filename_lower.endswith('.txt') or mime_type == 'text/plain':
            text = file_content.decode('utf-8', errors='ignore')
            content_json = RichTextContent.from_plain_text(text)
            return {
                "content": text,
                "content_json": content_json,
                "title": title,
            }
        
        # 处理 Markdown 文件
        elif filename_lower.endswith('.md') or filename_lower.endswith('.markdown') or mime_type == 'text/markdown':
            text = file_content.decode('utf-8', errors='ignore')
            # 使用异步方法解析 Markdown（支持图片下载上传）
            content_json = await self.parse_markdown_to_tiptap_async(text, user_id)
            return {
                "content": RichTextContent.to_plain_text(content_json),
                "content_json": content_json,
                "title": title,
            }
        
        # 处理 DOCX 文件
        elif filename_lower.endswith('.docx') or mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            try:
                from docx import Document as DocxDocument
                import io
                
                docx_doc = DocxDocument(io.BytesIO(file_content))
                
                # 提取标题（从第一个标题或文件名）
                if docx_doc.paragraphs and docx_doc.paragraphs[0].style.name.startswith('Heading'):
                    title = docx_doc.paragraphs[0].text.strip()
                
                content_json = await self.parse_docx_to_tiptap(docx_doc, user_id)
                content = RichTextContent.to_plain_text(content_json)
                
                return {
                    "content": content,
                    "content_json": content_json,
                    "title": title,
                }
            except ImportError:
                raise ValueError("python-docx 未安装，无法解析 DOCX 文件")
            except Exception as e:
                logger.error(f"DOCX解析失败: {e}")
                raise ValueError(f"DOCX解析失败: {str(e)}")
        
        # 处理 PDF 文件（使用 PyMuPDF 或 pdfplumber，优先使用 PyMuPDF）
        elif filename_lower.endswith('.pdf') or mime_type == 'application/pdf':
            try:
                import io
                
                # 优先尝试使用 PyMuPDF (fitz)，它支持格式和图片提取
                try:
                    import fitz  # PyMuPDF
                    
                    pdf_doc = fitz.open(stream=file_content, filetype="pdf")
                    logger.info(f"开始解析PDF: {len(pdf_doc)}页")
                    
                    text_parts = []
                    content_nodes = []
                    extracted_images = []  # 存储提取的图片信息
                    
                    # 创建一个列表来存储每个页面的图片信息（按顺序）
                    page_images_list = []  # [{page_num, image_bytes, ext, xref}]
                    
                    # 首先提取所有页面的图片（不获取位置信息，因为get_image_rects可能很慢）
                    total_images = 0
                    for page_num, page in enumerate(pdf_doc):
                        try:
                            image_list = page.get_images()
                            logger.debug(f"页面{page_num}发现{len(image_list)}张图片")
                            
                            for img_idx, img_item in enumerate(image_list):
                                try:
                                    xref = img_item[0]  # xref 是第一个元素
                                    base_image = pdf_doc.extract_image(xref)
                                    img_bytes = base_image.get("image")
                                    img_ext = base_image.get("ext", "png")
                                    
                                    if img_bytes and isinstance(img_bytes, bytes):
                                        page_images_list.append({
                                            "page_num": page_num,
                                            "image": img_bytes,
                                            "ext": img_ext,
                                            "xref": xref,
                                            "img_idx": img_idx
                                        })
                                        total_images += 1
                                        logger.debug(f"提取PDF页面{page_num}图片{img_idx}: xref={xref}, ext={img_ext}, size={len(img_bytes)}字节")
                                except Exception as e:
                                    logger.warning(f"提取PDF页面{page_num}图片{img_idx}失败: {e}")
                        except Exception as e:
                            logger.warning(f"处理PDF页面{page_num}失败: {e}")
                    
                    logger.info(f"PDF共提取到{total_images}张图片")
                    
                    # 按页面排序图片
                    page_images_list.sort(key=lambda x: (x["page_num"], x["img_idx"]))
                    
                    # 提取文本和格式，处理文本块，并在适当位置插入图片
                    current_image_idx = 0  # 当前处理的图片索引
                    
                    logger.info("开始提取PDF文本和格式")
                    
                    for page_num, page in enumerate(pdf_doc):
                        logger.info(f"处理PDF页面{page_num}/{len(pdf_doc)-1}")
                        try:
                            # 提取文本和格式（这个操作可能很慢）
                            logger.debug(f"开始提取页面{page_num}的文本...")
                            blocks = page.get_text("dict")  # 获取带格式的文本
                            num_blocks = len(blocks.get('blocks', [])) if blocks else 0
                            logger.info(f"页面{page_num}提取完成: {num_blocks}个块")
                        
                            # 收集页面的所有块（文本和图片），按位置排序
                            page_items = []
                            
                            for block in blocks.get("blocks", []):
                                block_bbox = block.get("bbox", [0, 0, 0, 0])  # [x0, y0, x1, y1]
                                block_y = block_bbox[1] if block_bbox else 0  # y0 是顶部位置
                                
                                if "lines" in block:  # 文本块
                                    page_items.append({
                                        "type": "text",
                                        "block": block,
                                        "y": block_y
                                    })
                                elif block.get("type") == 1:  # 图片块（PyMuPDF 中 type 1 表示图片）
                                    page_items.append({
                                        "type": "image",
                                        "block": block,
                                        "y": block_y
                                    })
                        
                            logger.debug(f"页面{page_num}收集到{len(page_items)}个项（文本/图片块）")
                            
                            # 按 y 坐标排序（从上到下）
                            page_items.sort(key=lambda x: x["y"])
                            
                            # 处理排序后的块
                            item_count = 0
                            for item in page_items:
                                item_count += 1
                                
                                if item["type"] == "text":
                                    block = item["block"]
                                    para_text = ""
                                    para_runs = []
                                    
                                    for line in block["lines"]:
                                        for span in line["spans"]:
                                            text = span.get("text", "").strip()
                                            if not text:
                                                continue
                                            
                                            para_text += text + " "
                                            
                                            # 构建带格式的文本节点
                                            marks = []
                                            font_flags = span.get("flags", 0)
                                            font_name = span.get("font", "").lower() if span.get("font") else ""
                                            
                                            # PyMuPDF 字体标志位（flags 是一个整数）：
                                            # 位 4 (16): bold (粗体)
                                            # 位 0 (1): italic (斜体)
                                            
                                            # 检查粗体：通过标志位或字体名称
                                            if (font_flags & 16) or "bold" in font_name or "black" in font_name:
                                                marks.append({"type": "bold"})
                                            
                                            # 检查斜体：通过标志位或字体名称  
                                            if (font_flags & 1) or "italic" in font_name or "oblique" in font_name:
                                                marks.append({"type": "italic"})
                                            
                                            run_node = {"type": "text", "text": text}
                                            if marks:
                                                run_node["marks"] = marks
                                            para_runs.append(run_node)
                                        
                                        para_text += "\n"
                                    
                                    if para_runs:
                                        content_nodes.append({
                                            "type": "paragraph",
                                            "content": para_runs
                                        })
                                        text_parts.append(para_text.strip())
                                
                                elif item["type"] == "image":
                                    # 处理图片：从预提取的图片列表中获取
                                    if current_image_idx < len(page_images_list):
                                        img_info = page_images_list[current_image_idx]
                                        
                                        # 确保图片在当前页面
                                        if img_info["page_num"] == page_num:
                                            try:
                                                img_bytes = img_info["image"]
                                                img_ext = img_info["ext"]
                                                
                                                if img_bytes and isinstance(img_bytes, bytes):
                                                    # 确定 MIME 类型
                                                    mime_type_map = {
                                                        "png": "image/png",
                                                        "jpg": "image/jpeg",
                                                        "jpeg": "image/jpeg",
                                                        "gif": "image/gif",
                                                        "webp": "image/webp",
                                                    }
                                                    mime_type = mime_type_map.get(img_ext.lower(), "image/png")
                                                    
                                                    logger.debug(f"开始上传PDF图片 {current_image_idx+1}/{total_images}: 页面{page_num}")
                                                    img_upload_info = await self.upload_image(
                                                        file_content=img_bytes,
                                                        file_name=f"pdf_image_{page_num}_{len(extracted_images)}.{img_ext}",
                                                        mime_type=mime_type,
                                                        user_id=user_id,
                                                    )
                                                    extracted_images.append(img_upload_info)
                                                    
                                                    # 添加到内容中
                                                    content_nodes.append({
                                                        "type": "image",
                                                        "attrs": {
                                                            "src": img_upload_info["file_url"],
                                                            "alt": f"图片 {len(extracted_images)}",
                                                            "imageId": img_upload_info.get("image_id", ""),
                                                        }
                                                    })
                                                    
                                                    current_image_idx += 1
                                                    logger.info(f"成功上传并添加PDF页面{page_num}的图片 {current_image_idx}/{total_images}: {len(img_bytes)}字节")
                                            except Exception as img_err:
                                                logger.warning(f"处理PDF图片失败: {img_err}")
                                                import traceback
                                                logger.debug(f"PDF图片处理错误详情: {traceback.format_exc()}")
                                
                                # 处理完当前item，继续下一个
                            
                            logger.debug(f"页面{page_num}处理完成: {len(page_items)}个项目，添加到{len(content_nodes)}个内容节点")
                        except Exception as page_err:
                            logger.error(f"处理PDF页面{page_num}时出错: {page_err}")
                            import traceback
                            logger.error(f"页面{page_num}错误详情: {traceback.format_exc()}")
                            # 即使出错也继续处理下一页
                            continue
                    
                    logger.info(f"PDF文本提取完成，共{len(content_nodes)}个内容节点")
                    
                    # 处理剩余的图片（如果还有未处理的图片）
                    remaining_count = len(page_images_list) - current_image_idx
                    if remaining_count > 0:
                        logger.info(f"开始处理剩余{remaining_count}张PDF图片（共{len(page_images_list)}张，已处理{current_image_idx}张）")
                    
                    while current_image_idx < len(page_images_list):
                        img_info = page_images_list[current_image_idx]
                        try:
                            img_bytes = img_info["image"]
                            img_ext = img_info["ext"]
                            
                            if img_bytes and isinstance(img_bytes, bytes):
                                mime_type_map = {
                                    "png": "image/png",
                                    "jpg": "image/jpeg",
                                    "jpeg": "image/jpeg",
                                    "gif": "image/gif",
                                    "webp": "image/webp",
                                }
                                mime_type = mime_type_map.get(img_ext.lower(), "image/png")
                                
                                logger.debug(f"开始上传剩余PDF图片 {current_image_idx+1}/{total_images}: 页面{img_info['page_num']}")
                                img_upload_info = await self.upload_image(
                                    file_content=img_bytes,
                                    file_name=f"pdf_image_{img_info['page_num']}_{len(extracted_images)}.{img_ext}",
                                    mime_type=mime_type,
                                    user_id=user_id,
                                )
                                extracted_images.append(img_upload_info)
                                
                                content_nodes.append({
                                    "type": "image",
                                    "attrs": {
                                        "src": img_upload_info["file_url"],
                                        "alt": f"图片 {len(extracted_images)}",
                                        "imageId": img_upload_info.get("image_id", ""),
                                    }
                                })
                                
                                current_image_idx += 1
                                logger.info(f"添加剩余PDF图片 {current_image_idx}/{total_images}: 页面{img_info['page_num']}")
                        except Exception as e:
                            logger.warning(f"添加剩余PDF图片失败: {e}")
                            current_image_idx += 1
                    
                    pdf_doc.close()
                    
                    logger.info(f"PDF解析完成: 共{len(content_nodes)}个内容节点，{len(extracted_images)}张图片")
                    
                    text = "\n\n".join(text_parts).strip()
                    
                    # 构建 content_json
                    if content_nodes:
                        content_json = {
                            "type": "doc",
                            "content": content_nodes
                        }
                    else:
                        content_json = RichTextContent.from_plain_text(text)
                    
                    logger.info(f"准备返回PDF解析结果: content_json包含{len(content_json.get('content', []))}个节点")
                    
                    result = {
                        "content": text,
                        "content_json": content_json,
                        "title": title,
                        "extracted_images": extracted_images,  # 返回提取的图片信息
                    }
                    
                    logger.info(f"PDF解析结果已准备好，准备返回")
                    return result
                    
                except ImportError:
                    # 降级使用 pdfplumber（比 PyPDF2 更好）
                    try:
                        import pdfplumber
                        
                        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                            text_parts = []
                            for page in pdf.pages:
                                page_text = page.extract_text()
                                if page_text:
                                    text_parts.append(page_text)
                            
                            text = "\n\n".join(text_parts).strip()
                            content_json = RichTextContent.from_plain_text(text)
                            
                            # pdfplumber 也可以提取表格等，但格式信息有限
                            return {
                                "content": text,
                                "content_json": content_json,
                                "title": title,
                            }
                    except ImportError:
                        # 最后降级使用 PyPDF2
                        from PyPDF2 import PdfReader
                        
                        pdf_reader = PdfReader(io.BytesIO(file_content))
                        text_parts = []
                        for page in pdf_reader.pages:
                            text_parts.append(page.extract_text())
                        text = "\n\n".join(text_parts)
                        content_json = RichTextContent.from_plain_text(text)
                        
                        return {
                            "content": text,
                            "content_json": content_json,
                            "title": title,
                        }
                        
            except Exception as e:
                logger.error(f"PDF解析失败: {e}")
                raise ValueError(f"PDF解析失败: {str(e)}")
        
        else:
            raise ValueError(f"不支持的文件格式: {filename}")
    
    async def parse_markdown_to_tiptap_async(self, markdown_text: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        异步将 Markdown 文本解析为 TipTap JSON 格式（支持图片下载上传）
        
        支持：
        - 标题 (# ## ###)
        - 加粗 (**text**)
        - 斜体 (*text*)
        - 删除线 (~~text~~)
        - 代码 (`code`)
        - 链接 ([text](url))
        - 图片 (![alt](url)) - 自动下载并上传到服务器
        - 列表 (- item, 1. item)
        - 引用 (> text)
        - 表格
        - 分割线 (---)
        """
        import re
        import aiohttp
        import asyncio
        
        lines = markdown_text.split('\n')
        content = []
        i = 0
        
        # 图片下载缓存
        downloaded_images = {}
        
        async def download_and_upload_image(url: str, alt: str = "") -> Optional[Dict[str, Any]]:
            """下载网络图片并上传到服务器"""
            if url in downloaded_images:
                return downloaded_images[url]
            
            # 如果是本地路径或已上传的URL，直接返回
            if url.startswith("/api/uploads") or url.startswith("data:"):
                return {"src": url, "alt": alt}
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            content_type = response.headers.get('content-type', 'image/png')
                            # 确保是图片类型
                            if not content_type.startswith('image/'):
                                logger.warning(f"非图片类型: {content_type}, URL: {url}")
                                return {"src": url, "alt": alt}
                            
                            img_data = await response.read()
                            
                            # 获取文件扩展名
                            ext_map = {
                                'image/jpeg': 'jpg',
                                'image/png': 'png',
                                'image/gif': 'gif',
                                'image/webp': 'webp',
                            }
                            ext = ext_map.get(content_type, 'png')
                            
                            # 上传图片
                            img_info = await self.upload_image(
                                file_content=img_data,
                                file_name=f"md_image_{len(downloaded_images)}.{ext}",
                                mime_type=content_type,
                                user_id=user_id,
                            )
                            
                            result = {
                                "src": img_info["file_url"],
                                "alt": alt,
                                "imageId": img_info.get("image_id", ""),
                            }
                            downloaded_images[url] = result
                            logger.info(f"成功下载并上传Markdown图片: {url} -> {img_info['file_url']}")
                            return result
            except asyncio.TimeoutError:
                logger.warning(f"下载图片超时: {url}")
            except Exception as e:
                logger.warning(f"下载Markdown图片失败: {url}, 错误: {e}")
            
            return {"src": url, "alt": alt}
        
        async def parse_inline_with_images(text: str) -> List[Dict[str, Any]]:
            """解析行内格式，包含图片下载"""
            parts = []
            last_pos = 0
            
            # 图片 ![alt](url)
            for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', text):
                if match.start() > last_pos:
                    parts.extend(self._parse_text_formatting(text[last_pos:match.start()]))
                
                alt = match.group(1)
                url = match.group(2)
                
                # 下载并上传图片
                img_result = await download_and_upload_image(url, alt)
                if img_result:
                    parts.append({
                        "type": "image",
                        "attrs": img_result
                    })
                
                last_pos = match.end()
            
            if last_pos < len(text):
                parts.extend(self._parse_text_formatting(text[last_pos:]))
            
            return parts if parts else [{"type": "text", "text": text}]
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            if not stripped:
                content.append({"type": "paragraph", "content": []})
                i += 1
                continue
            
            # 分割线
            if re.match(r'^[-*_]{3,}$', stripped):
                content.append({"type": "horizontalRule"})
                i += 1
                continue
            
            # 标题
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2)
                # 处理标题中的格式
                heading_content = await parse_inline_with_images(text)
                content.append({
                    "type": "heading",
                    "attrs": {"level": level},
                    "content": heading_content
                })
                i += 1
                continue
            
            # 引用（支持多行）
            if stripped.startswith('> '):
                quote_lines = []
                while i < len(lines) and lines[i].strip().startswith('> '):
                    quote_lines.append(lines[i].strip()[2:])
                    i += 1
                quote_text = '\n'.join(quote_lines)
                quote_content = await parse_inline_with_images(quote_text)
                content.append({
                    "type": "blockquote",
                    "content": [{
                        "type": "paragraph",
                        "content": quote_content
                    }]
                })
                continue
            
            # 表格检测
            if '|' in stripped and i + 1 < len(lines) and re.match(r'^[\|\s\-:]+$', lines[i + 1].strip()):
                # 解析表格头
                header_cells = [cell.strip() for cell in stripped.split('|') if cell.strip()]
                i += 2  # 跳过分隔行
                
                table_rows = []
                # 表头行
                header_row = {
                    "type": "tableRow",
                    "content": [
                        {
                            "type": "tableHeader",
                            "content": [{"type": "paragraph", "content": [{"type": "text", "text": cell}]}]
                        }
                        for cell in header_cells
                    ]
                }
                table_rows.append(header_row)
                
                # 表格内容行
                while i < len(lines) and '|' in lines[i]:
                    row_cells = [cell.strip() for cell in lines[i].split('|') if cell.strip()]
                    # 补齐或截断列数
                    while len(row_cells) < len(header_cells):
                        row_cells.append("")
                    row_cells = row_cells[:len(header_cells)]
                    
                    table_rows.append({
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableCell",
                                "content": [{"type": "paragraph", "content": await parse_inline_with_images(cell)}]
                            }
                            for cell in row_cells
                        ]
                    })
                    i += 1
                
                content.append({
                    "type": "table",
                    "content": table_rows
                })
                continue
            
            # 无序列表
            if stripped.startswith('- ') or stripped.startswith('* '):
                list_items = []
                while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                    item_text = lines[i].strip()[2:]
                    item_content = await parse_inline_with_images(item_text)
                    list_items.append({
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": item_content
                        }]
                    })
                    i += 1
                if list_items:
                    content.append({
                        "type": "bulletList",
                        "content": list_items
                    })
                continue
            
            # 有序列表
            ordered_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
            if ordered_match:
                list_items = []
                while i < len(lines):
                    match = re.match(r'^(\d+)\.\s+(.+)$', lines[i].strip())
                    if match:
                        item_text = match.group(2)
                        item_content = await parse_inline_with_images(item_text)
                        list_items.append({
                            "type": "listItem",
                            "content": [{
                                "type": "paragraph",
                                "content": item_content
                            }]
                        })
                        i += 1
                    else:
                        break
                if list_items:
                    content.append({
                        "type": "orderedList",
                        "content": list_items
                    })
                continue
            
            # 代码块
            if stripped.startswith('```'):
                lang = stripped[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    i += 1  # 跳过结束的 ```
                code_text = '\n'.join(code_lines)
                content.append({
                    "type": "codeBlock",
                    "attrs": {"language": lang or ""},
                    "content": [{"type": "text", "text": code_text}]
                })
                continue
            
            # 普通段落
            para_content = await parse_inline_with_images(line)
            content.append({
                "type": "paragraph",
                "content": para_content
            })
            i += 1
        
        return {
            "type": "doc",
            "content": content if content else [{"type": "paragraph", "content": []}]
        }
    
    def parse_markdown_to_tiptap(self, markdown_text: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        同步将 Markdown 文本解析为 TipTap JSON 格式（不下载图片，保留原始URL）
        
        支持：
        - 标题 (# ## ###)
        - 加粗 (**text**)
        - 斜体 (*text*)
        - 删除线 (~~text~~)
        - 代码 (`code`)
        - 链接 ([text](url))
        - 图片 (![alt](url))
        - 列表 (- item, 1. item)
        - 引用 (> text)
        - 表格
        - 分割线 (---)
        """
        import re
        
        lines = markdown_text.split('\n')
        content = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            if not stripped:
                content.append({"type": "paragraph", "content": []})
                i += 1
                continue
            
            # 分割线
            if re.match(r'^[-*_]{3,}$', stripped):
                content.append({"type": "horizontalRule"})
                i += 1
                continue
            
            # 标题
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2)
                content.append({
                    "type": "heading",
                    "attrs": {"level": level},
                    "content": self._parse_inline_formatting(text)
                })
                i += 1
                continue
            
            # 引用（支持多行）
            if stripped.startswith('> '):
                quote_lines = []
                while i < len(lines) and lines[i].strip().startswith('> '):
                    quote_lines.append(lines[i].strip()[2:])
                    i += 1
                quote_text = '\n'.join(quote_lines)
                content.append({
                    "type": "blockquote",
                    "content": [{
                        "type": "paragraph",
                        "content": self._parse_inline_formatting(quote_text)
                    }]
                })
                continue
            
            # 表格检测
            if '|' in stripped and i + 1 < len(lines) and re.match(r'^[\|\s\-:]+$', lines[i + 1].strip()):
                # 解析表格头
                header_cells = [cell.strip() for cell in stripped.split('|') if cell.strip()]
                i += 2  # 跳过分隔行
                
                table_rows = []
                # 表头行
                header_row = {
                    "type": "tableRow",
                    "content": [
                        {
                            "type": "tableHeader",
                            "content": [{"type": "paragraph", "content": [{"type": "text", "text": cell}]}]
                        }
                        for cell in header_cells
                    ]
                }
                table_rows.append(header_row)
                
                # 表格内容行
                while i < len(lines) and '|' in lines[i]:
                    row_cells = [cell.strip() for cell in lines[i].split('|') if cell.strip()]
                    while len(row_cells) < len(header_cells):
                        row_cells.append("")
                    row_cells = row_cells[:len(header_cells)]
                    
                    table_rows.append({
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableCell",
                                "content": [{"type": "paragraph", "content": self._parse_inline_formatting(cell)}]
                            }
                            for cell in row_cells
                        ]
                    })
                    i += 1
                
                content.append({
                    "type": "table",
                    "content": table_rows
                })
                continue
            
            # 无序列表
            if stripped.startswith('- ') or stripped.startswith('* '):
                list_items = []
                while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                    item_text = lines[i].strip()[2:]
                    list_items.append({
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": self._parse_inline_formatting(item_text)
                        }]
                    })
                    i += 1
                if list_items:
                    content.append({
                        "type": "bulletList",
                        "content": list_items
                    })
                continue
            
            # 有序列表
            ordered_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
            if ordered_match:
                list_items = []
                while i < len(lines):
                    match = re.match(r'^(\d+)\.\s+(.+)$', lines[i].strip())
                    if match:
                        item_text = match.group(2)
                        list_items.append({
                            "type": "listItem",
                            "content": [{
                                "type": "paragraph",
                                "content": self._parse_inline_formatting(item_text)
                            }]
                        })
                        i += 1
                    else:
                        break
                if list_items:
                    content.append({
                        "type": "orderedList",
                        "content": list_items
                    })
                continue
            
            # 代码块
            if stripped.startswith('```'):
                lang = stripped[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    i += 1  # 跳过结束的 ```
                code_text = '\n'.join(code_lines)
                content.append({
                    "type": "codeBlock",
                    "attrs": {"language": lang or ""},
                    "content": [{"type": "text", "text": code_text}]
                })
                continue
            
            # 普通段落
            para_content = self._parse_inline_formatting(line)
            content.append({
                "type": "paragraph",
                "content": para_content
            })
            i += 1
        
        return {
            "type": "doc",
            "content": content if content else [{"type": "paragraph", "content": []}]
        }
    
    def _parse_inline_formatting(self, text: str) -> List[Dict[str, Any]]:
        """解析行内格式（加粗、斜体、代码、链接、图片）"""
        import re
        
        # 简化的解析（不支持嵌套）
        parts = []
        last_pos = 0
        
        # 图片 ![alt](url)
        for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', text):
            if match.start() > last_pos:
                parts.extend(self._parse_text_formatting(text[last_pos:match.start()]))
            parts.append({
                "type": "image",
                "attrs": {
                    "src": match.group(2),
                    "alt": match.group(1),
                }
            })
            last_pos = match.end()
        
        if last_pos < len(text):
            parts.extend(self._parse_text_formatting(text[last_pos:]))
        
        return parts if parts else [{"type": "text", "text": text}]
    
    def _parse_text_formatting(self, text: str) -> List[Dict[str, Any]]:
        """解析文本格式（代码、删除线、加粗、斜体、链接、高亮）"""
        import re
        
        # 处理高亮 ==text==
        if '==' in text:
            parts = []
            last_pos = 0
            for match in re.finditer(r'==([^=]+)==', text):
                if match.start() > last_pos:
                    parts.extend(self._parse_code(text[last_pos:match.start()]))
                parts.append({
                    "type": "text",
                    "text": match.group(1),
                    "marks": [{"type": "highlight"}]
                })
                last_pos = match.end()
            if last_pos < len(text):
                parts.extend(self._parse_code(text[last_pos:]))
            return parts
        
        return self._parse_code(text)
    
    def _parse_code(self, text: str) -> List[Dict[str, Any]]:
        """解析行内代码"""
        import re
        
        # 处理代码 `code`
        if '`' in text:
            parts = []
            last_pos = 0
            for match in re.finditer(r'`([^`]+)`', text):
                if match.start() > last_pos:
                    parts.extend(self._parse_bold_italic(text[last_pos:match.start()]))
                parts.append({
                    "type": "text",
                    "text": match.group(1),
                    "marks": [{"type": "code"}]
                })
                last_pos = match.end()
            if last_pos < len(text):
                parts.extend(self._parse_bold_italic(text[last_pos:]))
            return parts
        
        return self._parse_bold_italic(text)
    
    def _parse_bold_italic(self, text: str) -> List[Dict[str, Any]]:
        """解析加粗、斜体和删除线"""
        import re
        
        # 先处理删除线 ~~text~~
        if '~~' in text:
            parts = []
            last_pos = 0
            for match in re.finditer(r'~~([^~]+)~~', text):
                if match.start() > last_pos:
                    parts.extend(self._parse_bold(text[last_pos:match.start()]))
                parts.append({
                    "type": "text",
                    "text": match.group(1),
                    "marks": [{"type": "strike"}]
                })
                last_pos = match.end()
            if last_pos < len(text):
                parts.extend(self._parse_bold(text[last_pos:]))
            return parts
        
        return self._parse_bold(text)
    
    def _parse_bold(self, text: str) -> List[Dict[str, Any]]:
        """解析加粗"""
        import re
        
        # 加粗 **text**
        if '**' in text:
            parts = []
            last_pos = 0
            for match in re.finditer(r'\*\*([^*]+)\*\*', text):
                if match.start() > last_pos:
                    parts.extend(self._parse_italic(text[last_pos:match.start()]))
                parts.append({
                    "type": "text",
                    "text": match.group(1),
                    "marks": [{"type": "bold"}]
                })
                last_pos = match.end()
            if last_pos < len(text):
                parts.extend(self._parse_italic(text[last_pos:]))
            return parts
        
        return self._parse_italic(text)
    
    def _parse_italic(self, text: str) -> List[Dict[str, Any]]:
        """解析斜体"""
        import re
        
        # 斜体 *text*（不在代码块中）
        if '*' in text:
            parts = []
            last_pos = 0
            for match in re.finditer(r'(?<!\*)\*([^*]+)\*(?!\*)', text):
                if match.start() > last_pos:
                    parts.extend(self._parse_link(text[last_pos:match.start()]))
                parts.append({
                    "type": "text",
                    "text": match.group(1),
                    "marks": [{"type": "italic"}]
                })
                last_pos = match.end()
            if last_pos < len(text):
                parts.extend(self._parse_link(text[last_pos:]))
            return parts
        
        return self._parse_link(text)
    
    def _parse_link(self, text: str) -> List[Dict[str, Any]]:
        """解析链接"""
        import re
        
        # 链接 [text](url)
        if '[' in text and '](' in text:
            parts = []
            last_pos = 0
            for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', text):
                if match.start() > last_pos:
                    parts.append({"type": "text", "text": text[last_pos:match.start()]})
                parts.append({
                    "type": "text",
                    "text": match.group(1),
                    "marks": [{"type": "link", "attrs": {"href": match.group(2)}}]
                })
                last_pos = match.end()
            if last_pos < len(text):
                parts.append({"type": "text", "text": text[last_pos:]})
            return parts
        
        return [{"type": "text", "text": text}] if text else []
    
    async def parse_docx_to_tiptap(self, docx_doc, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        将 DOCX 文档解析为 TipTap JSON 格式
        
        支持：
        - 标题（不同级别）
        - 段落
        - 加粗、斜体、下划线
        - 列表（有序、无序）
        - 图片
        - 表格
        """
        content = []
        
        def parse_paragraph_runs(para):
            """解析段落中的文本运行（带格式）"""
            runs_content = []
            for run in para.runs:
                marks = []
                if run.bold:
                    marks.append({"type": "bold"})
                if run.italic:
                    marks.append({"type": "italic"})
                if run.underline:
                    marks.append({"type": "underline"})
                
                text = run.text
                if text:
                    run_node = {"type": "text", "text": text}
                    if marks:
                        run_node["marks"] = marks
                    runs_content.append(run_node)
            
            return runs_content if runs_content else []
        
        # 导入必要的模块（用于图片提取）
        from docx.oxml.ns import qn
        
        # 处理段落和图片（按照文档原始顺序）
        for element in docx_doc.element.body:
            if element.tag.endswith('p'):  # 段落
                # 查找对应的段落对象
                for para in docx_doc.paragraphs:
                    if para._element == element:
                        para_text = para.text.strip()
                        
                        # 先检查段落中是否有图片
                        has_images = False
                        paragraph_images = []
                        
                        for run in para.runs:
                            if run._element.xpath('.//a:blip'):
                                has_images = True
                                try:
                                    # 获取图片的 relationship ID
                                    blip = run._element.xpath('.//a:blip')[0]
                                    rId = blip.get(qn('r:embed'))
                                    if not rId:
                                        rId = blip.get(qn('r:link'))
                                    
                                    if rId:
                                        # 从文档的 relationships 中获取图片数据
                                        image_part = docx_doc.part.related_parts[rId]
                                        image_bytes = image_part.blob
                                        
                                        # 推断图片格式
                                        img_ext = 'png'
                                        if hasattr(image_part, 'content_type'):
                                            ct = image_part.content_type
                                            if 'jpeg' in ct or 'jpg' in ct:
                                                img_ext = 'jpg'
                                            elif 'png' in ct:
                                                img_ext = 'png'
                                            elif 'gif' in ct:
                                                img_ext = 'gif'
                                            elif 'webp' in ct:
                                                img_ext = 'webp'
                                        
                                        # 上传图片
                                        mime_type_map = {
                                            'jpg': 'image/jpeg',
                                            'jpeg': 'image/jpeg',
                                            'png': 'image/png',
                                            'gif': 'image/gif',
                                            'webp': 'image/webp',
                                        }
                                        mime_type = mime_type_map.get(img_ext, 'image/png')
                                        
                                        img_info = await self.upload_image(
                                            file_content=image_bytes,
                                            file_name=f"docx_image_{len([n for n in content if n.get('type') == 'image'])}.{img_ext}",
                                            mime_type=mime_type,
                                            user_id=user_id or 0,
                                        )
                                        
                                        paragraph_images.append({
                                            "type": "image",
                                            "attrs": {
                                                "src": img_info["file_url"],
                                                "alt": f"图片 {len([n for n in content if n.get('type') == 'image']) + 1}",
                                                "imageId": img_info.get("image_id", ""),
                                            }
                                        })
                                except Exception as e:
                                    logger.warning(f"提取段落中的图片失败: {e}")
                        
                        # 如果段落有文本，添加段落或标题
                        if para_text:
                            # 检查是否是标题
                            style_name = para.style.name
                            if style_name.startswith('Heading'):
                                try:
                                    level = int(style_name.replace('Heading', '').strip() or '1')
                                    level = max(1, min(6, level))  # 限制在 1-6
                                except:
                                    level = 1
                                
                                content.append({
                                    "type": "heading",
                                    "attrs": {"level": level},
                                    "content": parse_paragraph_runs(para) or [{"type": "text", "text": para_text}]
                                })
                            else:
                                content.append({
                                    "type": "paragraph",
                                    "content": parse_paragraph_runs(para) or [{"type": "text", "text": para_text}]
                                })
                        elif not has_images:
                            # 空段落且没有图片，添加空段落
                            content.append({"type": "paragraph", "content": []})
                        
                        # 将图片添加到段落后（保持文档原始顺序）
                        for img_node in paragraph_images:
                            content.append(img_node)
                        
                        break
            
            elif element.tag.endswith('tbl'):  # 表格
                # 完整实现表格解析
                # 查找对应的表格对象
                for table in docx_doc.tables:
                    if table._element == element:
                        # 解析表格
                        table_rows = []
                        is_first_row = True
                        
                        for row in table.rows:
                            row_cells = []
                            
                            for cell in row.cells:
                                # 解析单元格内容（可能包含段落、图片等）
                                cell_content = []
                                
                                # 处理单元格中的段落
                                for para in cell.paragraphs:
                                    para_text = para.text.strip()
                                    if para_text:
                                        # 检查段落格式
                                        runs_content = parse_paragraph_runs(para)
                                        if runs_content:
                                            cell_content.append({
                                                "type": "paragraph",
                                                "content": runs_content
                                            })
                                        else:
                                            cell_content.append({
                                                "type": "paragraph",
                                                "content": [{"type": "text", "text": para_text}]
                                            })
                                    
                                    # 检查段落中的图片
                                    for run in para.runs:
                                        if run._element.xpath('.//a:blip'):
                                            try:
                                                from docx.oxml.ns import qn
                                                blip = run._element.xpath('.//a:blip')[0]
                                                rId = blip.get(qn('r:embed')) or blip.get(qn('r:link'))
                                                
                                                if rId:
                                                    image_part = docx_doc.part.related_parts[rId]
                                                    image_bytes = image_part.blob
                                                    
                                                    # 推断图片格式
                                                    img_ext = 'png'
                                                    if hasattr(image_part, 'content_type'):
                                                        ct = image_part.content_type
                                                        if 'jpeg' in ct or 'jpg' in ct:
                                                            img_ext = 'jpg'
                                                        elif 'png' in ct:
                                                            img_ext = 'png'
                                                        elif 'gif' in ct:
                                                            img_ext = 'gif'
                                                        elif 'webp' in ct:
                                                            img_ext = 'webp'
                                                    
                                                    # 上传图片
                                                    mime_type_map = {
                                                        'jpg': 'image/jpeg',
                                                        'jpeg': 'image/jpeg',
                                                        'png': 'image/png',
                                                        'gif': 'image/gif',
                                                        'webp': 'image/webp',
                                                    }
                                                    mime_type = mime_type_map.get(img_ext, 'image/png')
                                                    
                                                    img_info = await self.upload_image(
                                                        file_content=image_bytes,
                                                        file_name=f"docx_table_cell_image_{len([n for n in content if n.get('type') == 'table'])}_r{len(table_rows)}_c{len(row_cells)}.{img_ext}",
                                                        mime_type=mime_type,
                                                        user_id=user_id or 0,
                                                    )
                                                    
                                                    cell_content.append({
                                                        "type": "image",
                                                        "attrs": {
                                                            "src": img_info["file_url"],
                                                            "alt": f"表格图片",
                                                            "imageId": img_info.get("image_id", ""),
                                                        }
                                                    })
                                            except Exception as e:
                                                logger.warning(f"提取表格单元格中的图片失败: {e}")
                                
                                # 如果单元格为空，添加一个空段落
                                if not cell_content:
                                    cell_content.append({
                                        "type": "paragraph",
                                        "content": []
                                    })
                                
                                # 判断是否是表头（通常第一行是表头）
                                if is_first_row:
                                    row_cells.append({
                                        "type": "tableHeader",
                                        "content": cell_content
                                    })
                                else:
                                    row_cells.append({
                                        "type": "tableCell",
                                        "content": cell_content
                                    })
                            
                            table_rows.append({
                                "type": "tableRow",
                                "content": row_cells
                            })
                            
                            is_first_row = False
                        
                        # 创建表格节点
                        if table_rows:
                            content.append({
                                "type": "table",
                                "content": table_rows
                            })
                        break
        
        return {
            "type": "doc",
            "content": content if content else [{"type": "paragraph", "content": []}]
        }
    
    # ==================== 格式转换（导出） ====================
    
    def convert_to_markdown(self, content_json: Dict[str, Any]) -> str:
        """将富文本转换为Markdown，保留完整格式"""
        if not content_json or "content" not in content_json:
            return ""
        
        def render_node(node: Dict, depth: int = 0, in_table: bool = False) -> str:
            node_type = node.get("type", "")
            content = node.get("content", [])
            marks = node.get("marks", [])
            
            if node_type == "text":
                text = node.get("text", "")
                # 按正确顺序应用标记
                for mark in marks:
                    mark_type = mark.get("type", "")
                    if mark_type == "bold":
                        text = f"**{text}**"
                    elif mark_type == "italic":
                        text = f"*{text}*"
                    elif mark_type == "strike":
                        text = f"~~{text}~~"
                    elif mark_type == "code":
                        text = f"`{text}`"
                    elif mark_type == "highlight":
                        text = f"=={text}=="
                    elif mark_type == "underline":
                        # Markdown 原生不支持下划线，使用 HTML
                        text = f"<u>{text}</u>"
                    elif mark_type == "subscript":
                        text = f"<sub>{text}</sub>"
                    elif mark_type == "superscript":
                        text = f"<sup>{text}</sup>"
                    elif mark_type == "link":
                        href = mark.get("attrs", {}).get("href", "#")
                        text = f"[{text}]({href})"
                return text
            
            children_md = "".join(render_node(child, depth, in_table) for child in content)
            
            if node_type == "paragraph":
                if in_table:
                    return children_md
                return f"{children_md}\n\n"
            elif node_type == "heading":
                level = node.get("attrs", {}).get("level", 1)
                return f"{'#' * level} {children_md}\n\n"
            elif node_type == "bulletList":
                items = []
                for child in content:
                    item_text = render_node(child, depth + 1).strip()
                    items.append(f"{'  ' * depth}- {item_text}")
                return "\n".join(items) + "\n\n"
            elif node_type == "orderedList":
                items = []
                start = node.get("attrs", {}).get("start", 1)
                for i, child in enumerate(content, start):
                    item_text = render_node(child, depth + 1).strip()
                    items.append(f"{'  ' * depth}{i}. {item_text}")
                return "\n".join(items) + "\n\n"
            elif node_type == "taskList":
                items = []
                for child in content:
                    checked = child.get("attrs", {}).get("checked", False)
                    checkbox = "[x]" if checked else "[ ]"
                    item_content = render_node(child, depth + 1).strip()
                    items.append(f"{'  ' * depth}- {checkbox} {item_content}")
                return "\n".join(items) + "\n\n"
            elif node_type == "taskItem":
                return children_md
            elif node_type == "listItem":
                return children_md
            elif node_type == "blockquote":
                lines = children_md.strip().split('\n')
                quoted_lines = []
                for line in lines:
                    if line.strip():
                        quoted_lines.append(f"> {line}")
                    else:
                        quoted_lines.append(">")
                return "\n".join(quoted_lines) + "\n\n"
            elif node_type == "codeBlock":
                lang = node.get("attrs", {}).get("language", "")
                return f"```{lang}\n{children_md}\n```\n\n"
            elif node_type == "image":
                attrs = node.get("attrs", {})
                src = attrs.get("src", "")
                alt = attrs.get("alt", "")
                title = attrs.get("title", "")
                image_id = attrs.get("data-image-id") or attrs.get("imageId") or ""
                
                # 构建图片标记
                if title:
                    img_md = f'![{alt}]({src} "{title}")'
                else:
                    img_md = f"![{alt}]({src})"
                
                # 在Markdown中保留图片ID作为注释（用于后续处理）
                if image_id:
                    return f"{img_md}\n<!-- image-id: {image_id} -->\n\n"
                return f"{img_md}\n\n"
            elif node_type == "table":
                # 渲染表格
                rows = content
                if not rows:
                    return ""
                
                table_lines = []
                for row_idx, row in enumerate(rows):
                    row_cells = row.get("content", [])
                    cell_texts = []
                    for cell in row_cells:
                        cell_content = render_node(cell, depth, in_table=True).strip()
                        # 转义表格分隔符
                        cell_content = cell_content.replace("|", "\\|")
                        cell_texts.append(cell_content)
                    table_lines.append("| " + " | ".join(cell_texts) + " |")
                    
                    # 在第一行后添加分隔行
                    if row_idx == 0:
                        separator = "| " + " | ".join(["---"] * len(cell_texts)) + " |"
                        table_lines.append(separator)
                
                return "\n".join(table_lines) + "\n\n"
            elif node_type == "tableRow":
                return children_md
            elif node_type == "tableCell" or node_type == "tableHeader":
                return children_md
            elif node_type == "horizontalRule":
                return "---\n\n"
            elif node_type == "hardBreak":
                return "  \n"  # Markdown 硬换行
            elif node_type == "doc":
                return children_md
            else:
                return children_md
        
        return render_node(content_json).strip()
    
    async def convert_to_pdf(self, content_json: Dict[str, Any], title: str = "") -> bytes:
        """
        将富文本转换为PDF
        
        需要安装: pip install weasyprint
        
        特性：
        - 完整中文支持（多种中文字体后备）
        - 保留所有格式（加粗、斜体、下划线等）
        - 支持图片嵌入（自动转换为base64）
        - 支持表格、列表、代码块等
        - A4页面布局，专业排版
        """
        try:
            from weasyprint import HTML
            import html as html_escape
            
            # 将图片转换为base64以嵌入PDF
            content_with_images = self.convert_images_to_base64(content_json)
            html_content = RichTextContent.to_html(content_with_images)
            
            # 转义标题中的HTML特殊字符
            escaped_title = html_escape.escape(title) if title else ""
            
            # 构建完整HTML文档（确保UTF-8编码和中文字体支持）
            full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>{escaped_title or 'Document'}</title>
    <style>
        /* 页面设置 */
        @page {{
            size: A4;
            margin: 2.5cm 2cm;
            
            @bottom-center {{
                content: counter(page) " / " counter(pages);
                font-size: 10pt;
                color: #666;
            }}
        }}
        
        @page:first {{
            margin-top: 3cm;
        }}
        
        /* 中文字体优先级配置 */
        @font-face {{
            font-family: "CJK";
            src: local("WenQuanYi Zen Hei"), 
                 local("WenQuanYi Micro Hei"), 
                 local("Noto Sans CJK SC"),
                 local("Noto Sans SC"),
                 local("Source Han Sans SC"),
                 local("Microsoft YaHei"),
                 local("SimHei"),
                 local("PingFang SC"),
                 local("Hiragino Sans GB");
        }}
        
        /* 基础样式 */
        html {{
            font-size: 12pt;
        }}
        
        body {{
            font-family: "CJK", "WenQuanYi Zen Hei", "WenQuanYi Micro Hei", "Noto Sans CJK SC", "Microsoft YaHei", "SimHei", "PingFang SC", Arial, sans-serif;
            line-height: 1.8;
            color: #1a1a1a;
            text-align: justify;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        
        /* 标题样式 */
        h1, h2, h3, h4, h5, h6 {{
            font-family: "CJK", "WenQuanYi Zen Hei", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
            color: #111;
            margin-top: 1.5em;
            margin-bottom: 0.8em;
            font-weight: 700;
            line-height: 1.4;
            page-break-after: avoid;
        }}
        
        h1 {{ 
            font-size: 2em; 
            border-bottom: 2px solid #333;
            padding-bottom: 0.3em;
            margin-top: 0;
        }}
        h2 {{ font-size: 1.6em; border-bottom: 1px solid #ddd; padding-bottom: 0.2em; }}
        h3 {{ font-size: 1.3em; }}
        h4 {{ font-size: 1.1em; }}
        h5, h6 {{ font-size: 1em; }}
        
        /* 段落样式 */
        p {{
            margin: 0.8em 0;
            text-indent: 0;
        }}
        
        /* 列表样式 */
        ul, ol {{
            margin: 0.8em 0;
            padding-left: 2em;
        }}
        
        li {{
            margin: 0.3em 0;
            line-height: 1.6;
        }}
        
        /* 代码样式 */
        code {{
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Courier New", "Consolas", monospace;
            font-size: 0.9em;
            color: #c7254e;
        }}
        
        pre {{
            background: #f8f8f8;
            padding: 1em;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
            overflow-x: auto;
            font-family: "Courier New", "Consolas", monospace;
            font-size: 0.85em;
            line-height: 1.5;
            page-break-inside: avoid;
        }}
        
        pre code {{
            background: none;
            padding: 0;
            color: inherit;
        }}
        
        /* 引用样式 */
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 1em 0;
            padding: 0.5em 1em;
            background: #f9f9f9;
            color: #555;
            font-style: italic;
            page-break-inside: avoid;
        }}
        
        /* 表格样式 */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
            page-break-inside: avoid;
        }}
        
        th, td {{
            border: 1px solid #ccc;
            padding: 10px 12px;
            text-align: left;
            vertical-align: top;
        }}
        
        th {{
            background: #f0f0f0;
            font-weight: 700;
            color: #333;
        }}
        
        tr:nth-child(even) td {{
            background: #fafafa;
        }}
        
        /* 图片样式 */
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em auto;
            page-break-inside: avoid;
        }}
        
        /* 文本格式 */
        strong, b {{
            font-weight: 700 !important;
        }}
        
        em, i {{
            font-style: italic !important;
        }}
        
        u {{
            text-decoration: underline !important;
        }}
        
        s, strike, del {{
            text-decoration: line-through !important;
            color: #888;
        }}
        
        /* 链接样式 */
        a {{
            color: #2563eb;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        /* 分隔线 */
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 2em 0;
        }}
        
        /* 高亮样式 */
        mark {{
            background: #ffeb3b;
            padding: 0 2px;
        }}
        
        /* 避免孤行和寡行 */
        p, li {{
            orphans: 2;
            widows: 2;
        }}
    </style>
</head>
<body>
    {f'<h1 style="text-align: center; border-bottom: none;">{escaped_title}</h1>' if title else ''}
    {html_content}
</body>
</html>"""
            
            # 使用HTML类创建文档并生成PDF
            html_doc = HTML(string=full_html, base_url=".")
            pdf_bytes = html_doc.write_pdf()
            return pdf_bytes
            
        except ImportError:
            logger.warning("weasyprint未安装，无法生成PDF")
            raise ValueError("PDF生成功能需要安装weasyprint库")
        except Exception as e:
            logger.error(f"生成PDF失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def convert_to_docx(self, content_json: Dict[str, Any], title: str = "") -> bytes:
        """
        将富文本转换为DOCX
        
        需要安装: pip install python-docx
        """
        try:
            from docx import Document as DocxDocument
            from docx.shared import Inches, Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            import io
            
            doc = DocxDocument()
            
            # 添加标题
            if title:
                doc.add_heading(title, 0)
            
            def process_node(node: Dict):
                node_type = node.get("type", "")
                
                if node_type == "paragraph":
                    para = doc.add_paragraph()
                    for child in node.get("content", []):
                        add_run(para, child)
                
                elif node_type == "heading":
                    level = node.get("attrs", {}).get("level", 1)
                    text = RichTextContent.to_plain_text(node, include_image_placeholders=False).strip()
                    doc.add_heading(text, level)
                
                elif node_type == "bulletList":
                    for item in node.get("content", []):
                        para = doc.add_paragraph(style='List Bullet')
                        for child in item.get("content", []):
                            if child.get("type") == "paragraph":
                                for c in child.get("content", []):
                                    add_run(para, c)
                
                elif node_type == "orderedList":
                    for item in node.get("content", []):
                        para = doc.add_paragraph(style='List Number')
                        for child in item.get("content", []):
                            if child.get("type") == "paragraph":
                                for c in child.get("content", []):
                                    add_run(para, c)
                
                elif node_type == "blockquote":
                    text = RichTextContent.to_plain_text(node, include_image_placeholders=False).strip()
                    para = doc.add_paragraph(text)
                    para.style = 'Intense Quote'
                
                elif node_type == "table":
                    # 处理表格
                    table_rows = node.get("content", [])
                    if table_rows:
                        # 确定列数（取第一行的列数）
                        first_row = table_rows[0] if table_rows else None
                        if first_row:
                            num_cols = len(first_row.get("content", []))
                            if num_cols > 0:
                                # 创建表格
                                table = doc.add_table(rows=len(table_rows), cols=num_cols)
                                table.style = 'Light Grid Accent 1'  # 使用预定义样式
                                
                                # 填充表格数据
                                for row_idx, row_node in enumerate(table_rows):
                                    row_cells = row_node.get("content", [])
                                    for col_idx, cell_node in enumerate(row_cells):
                                        if col_idx < num_cols:
                                            cell = table.rows[row_idx].cells[col_idx]
                                            
                                            # 清空单元格默认内容
                                            cell.text = ""
                                            
                                            # 处理单元格内容（可能是 tableHeader 或 tableCell）
                                            cell_content = cell_node.get("content", [])
                                            for content_node in cell_content:
                                                if content_node.get("type") == "paragraph":
                                                    # 添加段落
                                                    para = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
                                                    for child in content_node.get("content", []):
                                                        add_run(para, child)
                                                elif content_node.get("type") == "image":
                                                    # 处理单元格中的图片
                                                    attrs = content_node.get("attrs", {})
                                                    src = attrs.get("src", "")
                                                    
                                                    abs_path = self.get_image_absolute_path(src)
                                                    if abs_path and Path(abs_path).exists():
                                                        try:
                                                            cell.add_paragraph().add_run().add_picture(abs_path, width=Inches(2))
                                                        except Exception as e:
                                                            logger.warning(f"在表格单元格中添加图片失败: {e}")
                                                    elif src.startswith("data:"):
                                                        try:
                                                            import base64
                                                            header, data = src.split(",", 1)
                                                            img_data = base64.b64decode(data)
                                                            img_stream = io.BytesIO(img_data)
                                                            cell.add_paragraph().add_run().add_picture(img_stream, width=Inches(2))
                                                        except Exception as e:
                                                            logger.warning(f"在表格单元格中添加base64图片失败: {e}")
                                            
                                            # 如果是表头，设置单元格格式
                                            if cell_node.get("type") == "tableHeader":
                                                # 设置表头样式（加粗）
                                                for para in cell.paragraphs:
                                                    for run in para.runs:
                                                        run.bold = True
                
                elif node_type == "image":
                    attrs = node.get("attrs", {})
                    src = attrs.get("src", "")
                    
                    image_added = False
                    
                    # 方法1: 尝试从文件路径加载
                    abs_path = self.get_image_absolute_path(src)
                    if abs_path and Path(abs_path).exists():
                        try:
                            doc.add_picture(abs_path, width=Inches(5))
                            image_added = True
                            logger.debug(f"成功从文件路径添加图片到DOCX: {abs_path}")
                        except Exception as e:
                            logger.warning(f"从文件路径添加图片到DOCX失败: {e}, 路径: {abs_path}")
                    
                    # 方法2: 如果是base64图片
                    if not image_added and src.startswith("data:"):
                        try:
                            import base64
                            header, data = src.split(",", 1)
                            img_data = base64.b64decode(data)
                            img_stream = io.BytesIO(img_data)
                            doc.add_picture(img_stream, width=Inches(5))
                            image_added = True
                            logger.debug("成功从base64添加图片到DOCX")
                        except Exception as e:
                            logger.warning(f"添加base64图片到DOCX失败: {e}")
                    
                    # 方法3: 如果路径存在但无法直接加载，尝试读取文件并转换为base64
                    if not image_added and abs_path and Path(abs_path).exists():
                        try:
                            with open(abs_path, "rb") as f:
                                img_data = f.read()
                            img_stream = io.BytesIO(img_data)
                            doc.add_picture(img_stream, width=Inches(5))
                            image_added = True
                            logger.debug(f"成功通过读取文件添加图片到DOCX: {abs_path}")
                        except Exception as e:
                            logger.warning(f"通过读取文件添加图片到DOCX失败: {e}, 路径: {abs_path}")
                    
                    # 如果所有方法都失败，添加占位符
                    if not image_added:
                        logger.warning(f"无法添加图片到DOCX，src: {src}, abs_path: {abs_path}")
                        doc.add_paragraph(f"[图片: {attrs.get('alt', '未命名图片')}]")
                
                elif node_type == "doc":
                    for child in node.get("content", []):
                        process_node(child)
            
            def add_run(paragraph, node: Dict):
                if node.get("type") != "text":
                    return
                
                text = node.get("text", "")
                run = paragraph.add_run(text)
                
                # 导入颜色支持
                from docx.shared import RGBColor
                
                # 应用样式
                for mark in node.get("marks", []):
                    mark_type = mark.get("type", "")
                    if mark_type == "bold":
                        run.bold = True
                    elif mark_type == "italic":
                        run.italic = True
                    elif mark_type == "underline":
                        run.underline = True
                    elif mark_type == "strike":
                        run.font.strike = True
                    elif mark_type == "code":
                        # 代码样式：使用等宽字体和灰色背景效果（背景色需要更复杂的处理）
                        run.font.name = "Consolas"
                        run.font.size = Pt(10)
                    elif mark_type == "textStyle":
                        # 处理文本样式（颜色、字体大小、字体）
                        attrs = mark.get("attrs", {})
                        
                        # 字体颜色
                        if attrs.get("color"):
                            color_hex = attrs["color"].lstrip("#")
                            if len(color_hex) == 6:
                                try:
                                    r = int(color_hex[0:2], 16)
                                    g = int(color_hex[2:4], 16)
                                    b = int(color_hex[4:6], 16)
                                    run.font.color.rgb = RGBColor(r, g, b)
                                except ValueError:
                                    pass
                        
                        # 字体大小
                        if attrs.get("fontSize"):
                            try:
                                size_str = attrs["fontSize"].replace("px", "").replace("pt", "")
                                size = int(float(size_str))
                                run.font.size = Pt(size)
                            except (ValueError, TypeError):
                                pass
                        
                        # 字体
                        if attrs.get("fontFamily"):
                            run.font.name = attrs["fontFamily"]
                    elif mark_type == "highlight":
                        # 高亮样式（需要特殊处理，DOCX 不直接支持背景色）
                        from docx.enum.text import WD_COLOR_INDEX
                        try:
                            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
                        except Exception:
                            pass
                    elif mark_type == "link":
                        # 链接样式（设置下划线和蓝色）
                        run.underline = True
                        run.font.color.rgb = RGBColor(0x25, 0x63, 0xeb)
            
            process_node(content_json)
            
            # 保存到字节流
            buffer = io.BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            return buffer.read()
            
        except ImportError:
            logger.warning("python-docx未安装，无法生成DOCX")
            raise ValueError("DOCX生成功能需要安装python-docx库")
        except Exception as e:
            logger.error(f"生成DOCX失败: {e}")
            raise


# ==================== 全局实例 ====================

_document_editor: Optional[DocumentEditorService] = None


def get_document_editor() -> DocumentEditorService:
    """获取文档编辑服务单例"""
    global _document_editor
    if _document_editor is None:
        _document_editor = DocumentEditorService()
    return _document_editor

