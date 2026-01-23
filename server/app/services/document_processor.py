"""
PatPat-Inconsistency-Hunter 文档处理模块
负责文档的预处理、分块和结构分析
"""

import re
import hashlib
import uuid
from typing import List, Optional, Tuple, Dict, Any

from ..config import settings
from ..models.schemas import DocumentInput, DocumentChunk
from ..utils.logger import logger


class DocumentProcessor:
    """
    文档处理器
    
    负责文档的预处理、结构分析和智能分块
    """
    
    def __init__(
        self,
        chunk_size: int = 2000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        """
        初始化文档处理器
        
        Args:
            chunk_size: 分块大小（字符数）
            chunk_overlap: 分块重叠大小
            min_chunk_size: 最小分块大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def process_document(
        self,
        document: DocumentInput,
    ) -> Tuple[List[DocumentChunk], Dict[str, Any]]:
        """
        处理文档，返回分块和文档元信息
        
        Args:
            document: 文档输入
        
        Returns:
            (分块列表, 文档元信息)
        """
        content = document.content
        
        # 预处理文档
        content = self._preprocess_content(content)
        
        # 分析文档结构
        structure = self._analyze_structure(content)
        
        # 智能分块
        chunks = self._create_chunks(content, structure)
        
        # 生成文档元信息
        metadata = {
            "title": document.title or self._extract_title(content),
            "content_hash": self._compute_hash(content),
            "content_length": len(content),
            "total_chunks": len(chunks),
            "structure": structure,
        }
        
        logger.info(f"文档处理完成: {metadata['title']}, {len(chunks)} 个分块")
        return chunks, metadata
    
    def _preprocess_content(self, content: str) -> str:
        """
        预处理文档内容
        
        Args:
            content: 原始文档内容
        
        Returns:
            预处理后的内容
        """
        # 统一换行符
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 移除多余的空白行（保留段落分隔）
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 移除行首尾空白
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(lines)
        
        # 移除特殊控制字符
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
        
        return content
    
    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """
        分析文档结构，识别章节
        
        Args:
            content: 文档内容
        
        Returns:
            文档结构信息
        """
        structure = {
            "chapters": [],
            "has_structure": False,
        }
        
        # 中文章节模式
        chapter_patterns = [
            # 第X章
            r'^第[一二三四五六七八九十百千\d]+章[\s:：]*(.*?)$',
            # 一、二、三、
            r'^[一二三四五六七八九十]+[、\.]\s*(.*?)$',
            # 1. 2. 3.
            r'^(\d+)[\.、]\s*(.*?)$',
            # 1 标题（纯数字开头）
            r'^(\d+)\s+(.+?)$',
        ]
        
        # 小节模式
        section_patterns = [
            # 第X节
            r'^第[一二三四五六七八九十百千\d]+节[\s:：]*(.*?)$',
            # X.X
            r'^(\d+\.\d+)\s*(.*?)$',
            # (一) (二) (三)
            r'^\([一二三四五六七八九十]+\)\s*(.*?)$',
            # (1) (2) (3)
            r'^\((\d+)\)\s*(.*?)$',
        ]
        
        lines = content.split('\n')
        current_chapter = None
        current_section = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是章节标题
            for pattern in chapter_patterns:
                match = re.match(pattern, line)
                if match:
                    chapter_title = match.group(1) if match.lastindex >= 1 else line
                    if match.lastindex >= 2:
                        chapter_title = match.group(2) or match.group(1)
                    
                    current_chapter = {
                        "id": len(structure["chapters"]) + 1,
                        "title": chapter_title.strip(),
                        "line_start": i,
                        "sections": [],
                    }
                    structure["chapters"].append(current_chapter)
                    structure["has_structure"] = True
                    break
            
            # 检查是否是小节标题
            if current_chapter:
                for pattern in section_patterns:
                    match = re.match(pattern, line)
                    if match:
                        section_title = match.group(1) if match.lastindex >= 1 else line
                        if match.lastindex >= 2:
                            section_title = match.group(2) or match.group(1)
                        
                        current_section = {
                            "id": len(current_chapter["sections"]) + 1,
                            "title": section_title.strip(),
                            "line_start": i,
                        }
                        current_chapter["sections"].append(current_section)
                        break
        
        # 计算每个章节的结束位置
        for i, chapter in enumerate(structure["chapters"]):
            if i + 1 < len(structure["chapters"]):
                chapter["line_end"] = structure["chapters"][i + 1]["line_start"] - 1
            else:
                chapter["line_end"] = len(lines) - 1
            
            # 计算小节的结束位置
            for j, section in enumerate(chapter["sections"]):
                if j + 1 < len(chapter["sections"]):
                    section["line_end"] = chapter["sections"][j + 1]["line_start"] - 1
                else:
                    section["line_end"] = chapter["line_end"]
        
        return structure
    
    def _create_chunks(
        self,
        content: str,
        structure: Dict[str, Any],
    ) -> List[DocumentChunk]:
        """
        创建文档分块
        
        Args:
            content: 文档内容
            structure: 文档结构信息
        
        Returns:
            分块列表
        """
        chunks = []
        lines = content.split('\n')
        
        if structure["has_structure"]:
            # 基于结构的分块
            chunks = self._create_structure_based_chunks(content, lines, structure)
        else:
            # 基于大小的分块
            chunks = self._create_size_based_chunks(content)
        
        return chunks
    
    def _create_structure_based_chunks(
        self,
        content: str,
        lines: List[str],
        structure: Dict[str, Any],
    ) -> List[DocumentChunk]:
        """
        基于文档结构创建分块
        
        Args:
            content: 文档内容
            lines: 文档行列表
            structure: 文档结构信息
        
        Returns:
            分块列表
        """
        chunks = []
        
        # 计算每行的字符位置
        line_positions = self._calculate_line_positions(content)
        
        for chapter in structure["chapters"]:
            chapter_title = chapter["title"]
            
            if chapter["sections"]:
                # 有小节的情况
                for section in chapter["sections"]:
                    section_content = '\n'.join(
                        lines[section["line_start"]:section["line_end"] + 1]
                    )
                    
                    if len(section_content) > self.chunk_size:
                        # 小节内容过长，需要进一步分块
                        sub_chunks = self._split_large_content(
                            section_content,
                            chapter_title,
                            section["title"],
                            line_positions[section["line_start"]][0],
                        )
                        chunks.extend(sub_chunks)
                    elif len(section_content) >= self.min_chunk_size:
                        chunk = DocumentChunk(
                            chunk_id=f"chunk_{uuid.uuid4().hex[:12]}",
                            content=section_content,
                            start_position=line_positions[section["line_start"]][0],
                            end_position=line_positions[section["line_end"]][1],
                            chapter=chapter_title,
                            section=section["title"],
                        )
                        chunks.append(chunk)
            else:
                # 没有小节的情况
                chapter_content = '\n'.join(
                    lines[chapter["line_start"]:chapter["line_end"] + 1]
                )
                
                if len(chapter_content) > self.chunk_size:
                    sub_chunks = self._split_large_content(
                        chapter_content,
                        chapter_title,
                        None,
                        line_positions[chapter["line_start"]][0],
                    )
                    chunks.extend(sub_chunks)
                elif len(chapter_content) >= self.min_chunk_size:
                    chunk = DocumentChunk(
                        chunk_id=f"chunk_{uuid.uuid4().hex[:12]}",
                        content=chapter_content,
                        start_position=line_positions[chapter["line_start"]][0],
                        end_position=line_positions[chapter["line_end"]][1],
                        chapter=chapter_title,
                        section=None,
                    )
                    chunks.append(chunk)
        
        # 处理章节之前的内容（如果有）
        if structure["chapters"]:
            first_chapter_start = structure["chapters"][0]["line_start"]
            if first_chapter_start > 0:
                preamble = '\n'.join(lines[:first_chapter_start])
                if len(preamble) >= self.min_chunk_size:
                    preamble_chunks = self._split_large_content(
                        preamble, "前言", None, 0
                    )
                    chunks = preamble_chunks + chunks
        
        return chunks
    
    def _create_size_based_chunks(self, content: str) -> List[DocumentChunk]:
        """
        基于大小创建分块（无结构时使用）
        
        Args:
            content: 文档内容
        
        Returns:
            分块列表
        """
        chunks = []
        paragraphs = content.split('\n\n')
        
        current_chunk = ""
        current_start = 0
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                if current_chunk:
                    current_chunk += '\n\n'
                current_chunk += para
            else:
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunk = DocumentChunk(
                        chunk_id=f"chunk_{uuid.uuid4().hex[:12]}",
                        content=current_chunk,
                        start_position=current_start,
                        end_position=current_start + len(current_chunk),
                        chapter=None,
                        section=None,
                    )
                    chunks.append(chunk)
                
                current_start = current_start + len(current_chunk) + 2
                current_chunk = para
        
        # 处理最后一个分块
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunk = DocumentChunk(
                chunk_id=f"chunk_{uuid.uuid4().hex[:12]}",
                content=current_chunk,
                start_position=current_start,
                end_position=current_start + len(current_chunk),
                chapter=None,
                section=None,
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_large_content(
        self,
        content: str,
        chapter: Optional[str],
        section: Optional[str],
        base_position: int,
    ) -> List[DocumentChunk]:
        """
        将大内容分割成多个分块
        
        Args:
            content: 内容
            chapter: 章节名称
            section: 小节名称
            base_position: 基础位置偏移
        
        Returns:
            分块列表
        """
        chunks = []
        
        # 按段落分割
        paragraphs = content.split('\n\n')
        current_chunk = ""
        current_start = base_position
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                if current_chunk:
                    current_chunk += '\n\n'
                current_chunk += para
            else:
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunk = DocumentChunk(
                        chunk_id=f"chunk_{uuid.uuid4().hex[:12]}",
                        content=current_chunk,
                        start_position=current_start,
                        end_position=current_start + len(current_chunk),
                        chapter=chapter,
                        section=section,
                    )
                    chunks.append(chunk)
                
                current_start = current_start + len(current_chunk) + 2
                current_chunk = para
        
        # 处理最后一部分
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunk = DocumentChunk(
                chunk_id=f"chunk_{uuid.uuid4().hex[:12]}",
                content=current_chunk,
                start_position=current_start,
                end_position=current_start + len(current_chunk),
                chapter=chapter,
                section=section,
            )
            chunks.append(chunk)
        
        return chunks
    
    def _calculate_line_positions(self, content: str) -> List[Tuple[int, int]]:
        """
        计算每行在原文中的位置
        
        Args:
            content: 文档内容
        
        Returns:
            每行的 (start, end) 位置列表
        """
        positions = []
        current_pos = 0
        
        for line in content.split('\n'):
            end_pos = current_pos + len(line)
            positions.append((current_pos, end_pos))
            current_pos = end_pos + 1  # +1 for newline
        
        return positions
    
    def _extract_title(self, content: str) -> str:
        """
        从文档内容中提取标题
        
        Args:
            content: 文档内容
        
        Returns:
            标题或默认值
        """
        lines = content.split('\n')
        for line in lines[:10]:  # 只检查前10行
            line = line.strip()
            if line and len(line) < 100:  # 标题通常不会太长
                return line
        return "未命名文档"
    
    def _compute_hash(self, content: str) -> str:
        """
        计算内容的哈希值
        
        Args:
            content: 文档内容
        
        Returns:
            SHA256哈希值
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def validate_document(self, document: DocumentInput) -> Tuple[bool, str]:
        """
        验证文档是否满足处理要求
        
        Args:
            document: 文档输入
        
        Returns:
            (是否有效, 错误消息)
        """
        content = document.content
        
        if not content or not content.strip():
            return False, "文档内容不能为空"
        
        if len(content) < settings.MIN_DOCUMENT_LENGTH:
            return False, f"文档长度不足，最少需要 {settings.MIN_DOCUMENT_LENGTH} 字符"
        
        if len(content) > settings.MAX_DOCUMENT_LENGTH:
            return False, f"文档过长，最多支持 {settings.MAX_DOCUMENT_LENGTH} 字符"
        
        return True, ""

