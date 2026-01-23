import re
import json
from typing import List, Dict, Any
from pypdf import PdfReader
from openai import OpenAI
import tiktoken
from models import Chunk

class DataProcessor:
    """处理各种输入格式的学习资料"""
    
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL
        )
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def process_input(self, input_data: str, input_type: str = "text") -> List[Chunk]:
        """处理不同类型的学习资料"""
        if input_type == "pdf":
            return self._process_pdf(input_data)
        elif input_type == "text":
            return self._process_text(input_data)
        else:
            raise ValueError(f"Unsupported input type: {input_type}")
    
    def _process_pdf(self, file_path: str) -> List[Chunk]:
        """处理PDF文件"""
        chunks = []
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        # 分块处理
                        page_chunks = self._chunk_text(
                            text, 
                            metadata={"source": file_path, "page": page_num + 1}
                        )
                        chunks.extend(page_chunks)
            
            return chunks
        except Exception as e:
            raise Exception(f"PDF processing failed: {str(e)}")
    
    def _process_text(self, text: str) -> List[Chunk]:
        """处理文本输入"""
        return self._chunk_text(text, metadata={"source": "direct_input"})
    
    def _chunk_text(self, text: str, metadata: Dict) -> List[Chunk]:
        """智能分块，保持语义完整性"""
        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        
        for para in paragraphs:
            if not para.strip():
                continue
            
            # 如果段落太长，进一步分割
            tokens = self.tokenizer.encode(para)
            if len(tokens) > 1000:  # 限制块大小
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = []
                current_tokens = 0
                
                for sentence in sentences:
                    sentence_tokens = len(self.tokenizer.encode(sentence))
                    if current_tokens + sentence_tokens > 1000:
                        if current_chunk:
                            chunks.append(Chunk(
                                text=' '.join(current_chunk),
                                metadata=metadata.copy()
                            ))
                        current_chunk = [sentence]
                        current_tokens = sentence_tokens
                    else:
                        current_chunk.append(sentence)
                        current_tokens += sentence_tokens
                
                if current_chunk:
                    chunks.append(Chunk(
                        text=' '.join(current_chunk),
                        metadata=metadata.copy()
                    ))
            else:
                chunks.append(Chunk(text=para, metadata=metadata.copy()))
        
        return chunks
    
    def extract_key_concepts(self, chunks: List[Chunk]) -> List[Dict]:
        """提取核心概念"""
        combined_text = "\n".join([chunk.text for chunk in chunks[:10]])  # 只取部分
        
        prompt = f"""请从以下学习资料中提取核心概念和知识点：
        
        {combined_text}
        
        请以JSON格式返回，包含以下字段：
        - concepts: 核心概念列表
        - key_points: 关键知识点列表
        - difficulty_level: 整体难度评估（easy/medium/hard）
        """
        
        response = self.client.chat.completions.create(
            model=self.config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)