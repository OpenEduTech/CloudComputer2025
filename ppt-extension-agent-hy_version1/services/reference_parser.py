"""
参考文件解析服务
快速解析Word和PDF文件，提取文本内容（不使用LLM）
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import re

logger = logging.getLogger(__name__)


class ReferenceParser:
    """
    参考文件解析器
    支持Word和PDF格式，快速提取文本内容
    """
    
    def __init__(self):
        """初始化解析器"""
        self.supported_formats = ['.docx', '.doc', '.pdf']
        logger.info("参考文件解析器初始化完成")
    
    def parse_file(self, file_path: str) -> Dict:
        """
        解析参考文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            解析结果字典，包含：
            - filename: 文件名
            - file_type: 文件类型
            - content: 提取的文本内容
            - chunks: 文本块列表（用于相关性判断）
            - word_count: 字数统计
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            file_ext = file_path_obj.suffix.lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"不支持的文件格式: {file_ext}，仅支持 {', '.join(self.supported_formats)}")
            
            logger.info(f"开始解析文件: {file_path}")
            
            if file_ext == '.docx':
                content = self._parse_docx(file_path)
            elif file_ext == '.doc':
                # .doc格式需要特殊处理，这里先尝试用docx解析
                logger.warning(".doc格式可能无法正确解析，建议转换为.docx格式")
                content = self._parse_docx(file_path)
            elif file_ext == '.pdf':
                content = self._parse_pdf(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            
            # 清理文本
            content = self._clean_text(content)
            
            # 分割为文本块（用于相关性判断）
            chunks = self._split_into_chunks(content)
            
            result = {
                "filename": file_path_obj.name,
                "file_type": file_ext,
                "content": content,
                "chunks": chunks,
                "word_count": len(content)
            }
            
            logger.info(f"文件解析完成: {file_path}, 字数: {result['word_count']}")
            return result
            
        except Exception as e:
            logger.error(f"文件解析失败: {file_path}, 错误: {str(e)}")
            raise
    
    def _parse_docx(self, file_path: str) -> str:
        """
        解析Word文档（.docx格式）
        
        Args:
            file_path: 文件路径
            
        Returns:
            提取的文本内容
        """
        try:
            from docx import Document
            
            doc = Document(file_path)
            paragraphs = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)
            
            # 提取表格内容
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        if cell_text:
                            row_text.append(cell_text)
                    if row_text:
                        paragraphs.append(" | ".join(row_text))
            
            return "\n\n".join(paragraphs)
            
        except ImportError:
            logger.error("python-docx库未安装，请运行: pip install python-docx")
            raise ImportError("需要安装python-docx库: pip install python-docx")
        except Exception as e:
            logger.error(f"解析Word文档失败: {str(e)}")
            raise
    
    def _parse_pdf(self, file_path: str) -> str:
        """
        解析PDF文档
        
        Args:
            file_path: 文件路径
            
        Returns:
            提取的文本内容
        """
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(file_path)
            paragraphs = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    paragraphs.append(text.strip())
            
            doc.close()
            return "\n\n".join(paragraphs)
            
        except ImportError:
            logger.error("PyMuPDF库未安装，请运行: pip install PyMuPDF")
            raise ImportError("需要安装PyMuPDF库: pip install PyMuPDF")
        except Exception as e:
            logger.error(f"解析PDF文档失败: {str(e)}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本内容
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符（保留中文、英文、数字和基本标点）
        text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？；：、""''（）【】《》\n]', '', text)
        # 移除多余的换行
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def _split_into_chunks(self, text: str, chunk_size: int = 500) -> List[str]:
        """
        将文本分割为块（用于相关性判断）
        
        Args:
            text: 文本内容
            chunk_size: 每个块的大小（字符数）
            
        Returns:
            文本块列表
        """
        chunks = []
        sentences = re.split(r'[。！？\n]', text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence)
            
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def extract_keywords(self, text: str, max_keywords: int = 20) -> List[str]:
        """
        提取关键词（简单方法，不使用LLM）
        
        Args:
            text: 文本内容
            max_keywords: 最大关键词数量
            
        Returns:
            关键词列表
        """
        # 简单的关键词提取：去除停用词，统计词频
        # 中文停用词
        stopwords = {'的', '是', '在', '了', '和', '与', '或', '但', '而', '及', '等', '这', '那', '有', '为', '以', '从', '到', '对', '就', '也', '都', '还', '要', '会', '可以', '能', '应该', '可能', '如果', '因为', '所以', '虽然', '但是', '然而', '因此', '此外', '另外', '同时', '首先', '其次', '最后', '总之', '例如', '比如', '即', '也就是说', '换句话说', '实际上', '事实上', '一般来说', '通常', '一般', '通常', '一般', '通常'}
        
        # 提取中文词汇（2-4字）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        # 提取英文单词（3个字符以上）
        english_words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        
        # 统计词频
        word_freq = {}
        for word in chinese_words + english_words:
            word_lower = word.lower()
            if word_lower not in stopwords and len(word_lower) >= 2:
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
        
        # 按频率排序，返回前N个
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:max_keywords]]
        
        return keywords
    
    def is_relevant(self, reference_content: str, ppt_content: str, threshold: float = 0.3) -> bool:
        """
        判断参考文件内容是否与PPT内容相关（简单方法，不使用LLM）
        
        Args:
            reference_content: 参考文件内容
            ppt_content: PPT内容
            threshold: 相关性阈值（0-1之间）
            
        Returns:
            是否相关
        """
        try:
            # 提取关键词
            ref_keywords = set(self.extract_keywords(reference_content, max_keywords=30))
            ppt_keywords = set(self.extract_keywords(ppt_content, max_keywords=30))
            
            if not ref_keywords or not ppt_keywords:
                return False
            
            # 计算关键词重叠率
            intersection = ref_keywords & ppt_keywords
            union = ref_keywords | ppt_keywords
            
            if not union:
                return False
            
            similarity = len(intersection) / len(union)
            
            logger.info(f"参考文件相关性判断: 相似度={similarity:.2f}, 阈值={threshold}")
            
            return similarity >= threshold
            
        except Exception as e:
            logger.warning(f"相关性判断失败: {str(e)}，默认返回True")
            return True  # 如果判断失败，默认认为相关，让LLM决定
