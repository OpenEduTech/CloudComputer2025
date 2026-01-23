"""
文档解析器服务
支持 Word (.docx)、PDF (.pdf)、TXT (.txt)、Markdown (.md) 文件解析
"""
import re
from typing import List, Dict, Optional
from io import BytesIO

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


class DocumentParser:
    """文档解析器类"""
    
    def __init__(self):
        self.supported_extensions = {'docx', 'pdf', 'txt', 'md', 'markdown'}
    
    def parse(self, file_content: bytes, filename: str) -> Dict:
        """
        解析文档内容
        
        Args:
            file_content: 文件二进制内容
            filename: 文件名（用于判断文件类型）
        
        Returns:
            Dict包含:
                - text: 完整文本内容
                - sections: 分段后的文本列表
                - metadata: 文档元数据（章节信息等）
                - word_count: 字数统计
        """
        file_ext = self._get_file_extension(filename)
        
        if file_ext not in self.supported_extensions:
            raise ValueError(f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(self.supported_extensions)}")
        
        if file_ext == 'docx':
            return self._parse_docx(file_content)
        elif file_ext == 'pdf':
            return self._parse_pdf(file_content)
        elif file_ext == 'txt':
            return self._parse_txt(file_content)
        elif file_ext in ('md', 'markdown'):
            return self._parse_markdown(file_content)
        else:
            raise ValueError(f"未实现的解析器: {file_ext}")
    
    def _get_file_extension(self, filename: str) -> str:
        """获取文件扩展名（不带点）"""
        return filename.lower().split('.')[-1] if '.' in filename else ''
    
    def _parse_docx(self, file_content: bytes) -> Dict:
        """解析 Word 文档"""
        if Document is None:
            raise ImportError("python-docx 未安装")
        
        doc = Document(BytesIO(file_content))
        
        # 提取完整文本
        full_text = []
        sections = []
        current_section = []
        metadata = {
            'title': None,
            'author': None,
            'sections': []
        }
        
        # 提取文档属性
        if doc.core_properties.title:
            metadata['title'] = doc.core_properties.title
        if doc.core_properties.author:
            metadata['author'] = doc.core_properties.author
        
        # 解析段落
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            full_text.append(text)
            
            # 判断是否为章节标题（通常是大标题样式或特定格式）
            is_heading = self._is_heading(para, text)
            
            if is_heading and current_section:
                # 保存当前章节
                section_text = '\n'.join(current_section)
                if section_text:
                    sections.append({
                        'title': current_section[0] if current_section else '',
                        'content': section_text,
                        'word_count': len(section_text)
                    })
                current_section = []
            
            current_section.append(text)
            
            # 记录章节标题
            if is_heading:
                metadata['sections'].append(text)
        
        # 添加最后一个章节
        if current_section:
            section_text = '\n'.join(current_section)
            if section_text:
                sections.append({
                    'title': current_section[0] if current_section else '',
                    'content': section_text,
                    'word_count': len(section_text)
                })
        
        # 如果没有检测到章节，按段落分段
        if not sections:
            sections = self._split_by_paragraphs(full_text)
        
        full_text_str = '\n'.join(full_text)
        
        return {
            'text': full_text_str,
            'sections': sections,
            'metadata': metadata,
            'word_count': len(full_text_str),
            'file_type': 'docx'
        }
    
    def _parse_pdf(self, file_content: bytes) -> Dict:
        """解析 PDF 文档（优先使用 pdfplumber，回退到 PyPDF2）"""
        # 优先使用 pdfplumber（更好的文本提取）
        if pdfplumber is not None:
            return self._parse_pdf_with_pdfplumber(file_content)
        elif PyPDF2 is not None:
            return self._parse_pdf_with_pypdf2(file_content)
        else:
            raise ImportError("pdfplumber 或 PyPDF2 未安装")
    
    def _parse_pdf_with_pdfplumber(self, file_content: bytes) -> Dict:
        """使用 pdfplumber 解析 PDF"""
        full_text = []
        sections = []
        current_section = []
        metadata = {'sections': []}
        
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            metadata['page_count'] = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue
                
                # 按行分割
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    full_text.append(line)
                    
                    # 判断是否为章节标题（通常是大写、短行、特定格式）
                    is_heading = self._is_pdf_heading(line)
                    
                    if is_heading and current_section:
                        section_text = '\n'.join(current_section)
                        if section_text:
                            sections.append({
                                'title': current_section[0] if current_section else '',
                                'content': section_text,
                                'word_count': len(section_text)
                            })
                        current_section = []
                    
                    current_section.append(line)
                    
                    if is_heading:
                        metadata['sections'].append(line)
        
        # 添加最后一个章节
        if current_section:
            section_text = '\n'.join(current_section)
            if section_text:
                sections.append({
                    'title': current_section[0] if current_section else '',
                    'content': section_text,
                    'word_count': len(section_text)
                })
        
        # 如果没有检测到章节，按段落分段
        if not sections:
            sections = self._split_by_paragraphs(full_text)
        
        full_text_str = '\n'.join(full_text)
        
        return {
            'text': full_text_str,
            'sections': sections,
            'metadata': metadata,
            'word_count': len(full_text_str),
            'file_type': 'pdf'
        }
    
    def _parse_pdf_with_pypdf2(self, file_content: bytes) -> Dict:
        """使用 PyPDF2 解析 PDF（备用方案）"""
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
        
        full_text = []
        metadata = {
            'page_count': len(pdf_reader.pages),
            'sections': []
        }
        
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
        
        full_text_str = '\n'.join(full_text)
        
        # 按段落分段
        sections = self._split_by_paragraphs(full_text)
        
        return {
            'text': full_text_str,
            'sections': sections,
            'metadata': metadata,
            'word_count': len(full_text_str),
            'file_type': 'pdf'
        }
    
    def _parse_txt(self, file_content: bytes) -> Dict:
        """解析 TXT 文本文件"""
        try:
            text = file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = file_content.decode('gbk')
            except UnicodeDecodeError:
                text = file_content.decode('utf-8', errors='ignore')
        
        # 按行分割
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        full_text = '\n'.join(lines)
        
        # 分段处理
        sections = self._split_by_paragraphs(lines)
        
        metadata = {
            'sections': [section['title'] for section in sections if section.get('title')]
        }
        
        return {
            'text': full_text,
            'sections': sections,
            'metadata': metadata,
            'word_count': len(full_text),
            'file_type': 'txt'
        }
    
    def _is_heading(self, para, text: str) -> bool:
        """判断 Word 段落是否为标题"""
        # 检查样式名称
        if para.style.name.startswith('Heading') or para.style.name.startswith('标题'):
            return True
        
        # 检查格式（加粗、字号较大等）
        if para.runs:
            first_run = para.runs[0]
            if first_run.bold and len(text) < 100:
                return True
        
        # 检查文本模式（章节编号：第一章、1.1、一、等）
        heading_patterns = [
            r'^第[一二三四五六七八九十\d]+章',
            r'^第[一二三四五六七八九十\d]+节',
            r'^\d+\.\d+',  # 1.1, 2.3 等
            r'^[一二三四五六七八九十]+、',  # 一、二、等
            r'^[（(]\d+[）)]',  # (1) (2) 等
        ]
        
        for pattern in heading_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _is_pdf_heading(self, text: str) -> bool:
        """判断 PDF 文本行是否为标题"""
        # 检查章节编号模式
        heading_patterns = [
            r'^第[一二三四五六七八九十\d]+章',
            r'^第[一二三四五六七八九十\d]+节',
            r'^\d+\.\d+',
            r'^[一二三四五六七八九十]+、',
            r'^[（(]\d+[）)]',
        ]
        
        for pattern in heading_patterns:
            if re.match(pattern, text):
                return True
        
        # 短行且全大写可能是标题
        if len(text) < 50 and text.isupper() and len(text) > 3:
            return True
        
        return False
    
    def _split_by_paragraphs(self, lines: List[str], min_section_length: int = 200) -> List[Dict]:
        """
        按段落分段
        
        Args:
            lines: 文本行列表
            min_section_length: 最小章节长度（字符数）
        
        Returns:
            分段后的章节列表
        """
        sections = []
        current_section = []
        current_length = 0
        
        for line in lines:
            current_section.append(line)
            current_length += len(line)
            
            # 当达到最小长度时，创建一个新章节
            if current_length >= min_section_length:
                section_text = '\n'.join(current_section)
                sections.append({
                    'title': current_section[0][:50] if current_section else '',  # 使用第一行作为标题
                    'content': section_text,
                    'word_count': current_length
                })
                current_section = []
                current_length = 0
        
        # 添加最后一个章节
        if current_section:
            section_text = '\n'.join(current_section)
            sections.append({
                'title': current_section[0][:50] if current_section else '',
                'content': section_text,
                'word_count': current_length
            })
        
        return sections
    
    def _parse_markdown(self, file_content: bytes) -> Dict:
        """解析 Markdown 文件"""
        try:
            text = file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = file_content.decode('gbk')
            except UnicodeDecodeError:
                text = file_content.decode('utf-8', errors='ignore')
        
        lines = text.split('\n')
        
        full_text = []
        sections = []
        current_section = []
        current_title = None
        metadata = {'sections': []}
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_section:
                    current_section.append('')  # 保留空行用于段落分隔
                continue
            
            full_text.append(stripped)
            
            # 检测 Markdown 标题（# ## ### 等）
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                # 保存当前章节
                if current_section:
                    section_text = '\n'.join(current_section)
                    if section_text.strip():
                        sections.append({
                            'title': current_title or '',
                            'content': section_text,
                            'word_count': len(section_text),
                            'level': len(heading_match.group(1)) if heading_match else 0
                        })
                    current_section = []
                
                # 开始新章节
                current_title = heading_match.group(2)
                metadata['sections'].append({
                    'level': len(heading_match.group(1)),
                    'title': current_title
                })
                current_section.append(stripped)
            else:
                current_section.append(stripped)
        
        # 添加最后一个章节
        if current_section:
            section_text = '\n'.join(current_section)
            if section_text.strip():
                sections.append({
                    'title': current_title or current_section[0][:50] if current_section else '',
                    'content': section_text,
                    'word_count': len(section_text)
                })
        
        # 如果没有检测到章节，按段落分段
        if not sections:
            sections = self._split_by_paragraphs(full_text)
        
        full_text_str = '\n'.join(full_text)
        
        return {
            'text': full_text_str,
            'sections': sections,
            'metadata': metadata,
            'word_count': len(full_text_str),
            'file_type': 'markdown'
        }

