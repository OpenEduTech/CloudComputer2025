import asyncio
import os
from app.services.llm_factory import LLMFactory
from typing import Tuple

class PDFParserAgent:
    def __init__(self):
        self.client = LLMFactory.get_zhipu_client()
        self.llm = LLMFactory.get_deepseek_llm()

    async def _verify_parsed_content(self, content: str, file_path: str) -> Tuple[bool, str]:
        """
        验证解析的内容是否有效，避免乱码或解析失败
        返回: (是否通过验证, 问题描述)
        """
        # 基本检查
        if not content or len(content.strip()) < 50:
            return False, "解析内容过短，可能解析失败"
        
        # 检查乱码比例
        total_chars = len(content)
        chinese_chars = sum(1 for c in content if '\u4e00' <= c <= '\u9fff')
        english_chars = sum(1 for c in content if c.isalpha() and ord(c) < 128)
        digit_chars = sum(1 for c in content if c.isdigit())
        valid_chars = chinese_chars + english_chars + digit_chars
        
        valid_ratio = valid_chars / total_chars if total_chars > 0 else 0
        
        if valid_ratio < 0.5:
            return False, f"有效字符比例过低（{valid_ratio:.1%}），可能存在大量乱码"
        
        # 使用 LLM 进行语义检查（采样前500字符）
        sample = content[:500]
        verification_prompt = f"""你是一位文档质量检查员，请判断以下文本是否是有效的学习材料内容。

文本样本：
{sample}

请判断：
1. 文本是否可读，没有大量乱码？
2. 文本是否包含有意义的学习内容（而不是纯符号、页码等）？
3. 文本是否适合用于生成学习测验？

返回JSON格式：
{{
  "is_valid": true/false,
  "reason": "简要说明内容质量好 或 指出具体问题"
}}

只返回JSON，不要其他文字。"""

        try:
            response = await self.llm.ainvoke(verification_prompt)
            content_str = response.content.strip()
            
            # Extract JSON
            if "```json" in content_str:
                content_str = content_str.split("```json")[1].split("```")[0].strip()
            elif "```" in content_str:
                content_str = content_str.split("```")[1].split("```")[0].strip()
            
            import json
            result = json.loads(content_str)
            return result.get("is_valid", True), result.get("reason", "未知原因")
        except Exception as e:
            print(f"⚠️  验证解析内容时出错: {e}")
            # 如果验证失败，基于基本检查结果
            if valid_ratio >= 0.7:
                return True, f"基本检查通过（有效字符比例: {valid_ratio:.1%}）"
            else:
                return False, f"有效字符比例较低（{valid_ratio:.1%}）"

    async def parse_pdf(self, file_path: str) -> str:
        """
        解析PDF文件并返回内容
        使用智谱AI的file_parser，失败时降级到pypdf
        """
        try:
            # Run the parsing in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, self._call_parser, file_path)
            
            # Check layer: 验证解析内容质量
            print("🔍 验证PDF解析内容质量...")
            is_valid, reason = await self._verify_parsed_content(content, file_path)
            
            if is_valid:
                print(f"  ✓ 内容验证通过: {reason}")
            else:
                print(f"  ⚠️  内容验证失败: {reason}")
                print(f"  ⚠️  建议检查PDF文件或尝试其他解析方法")
            
            return content
        except Exception as e:
            print(f"Error parsing PDF: {e}")
            raise
    
    def _call_parser(self, file_path: str) -> str:
        """
        使用智谱AI file_parser解析PDF，失败时降级到pypdf
        """
        # Try ZhipuAI first (按照doc.md的官方示例)
        try:
            print(f"正在使用智谱AI解析PDF: {file_path}")
            with open(file_path, 'rb') as f:
                response = self.client.file_parser.create_sync(
                    file=f,
                    file_type="pdf",
                    tool_type="prime-sync",
                )
            print(f"智谱AI解析成功，内容长度: {len(response.content)}")
            return response.content
        except Exception as e:
            print(f"智谱AI解析失败: {e}. 降级到pypdf...")
        
        # Fallback to pypdf
        try:
            import pypdf
            print(f"正在使用pypdf解析PDF: {file_path}")
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            print(f"pypdf解析成功，内容长度: {len(text)}")
            return text
        except Exception as e:
            raise Exception(f"所有解析方法都失败了。pypdf错误: {e}")

pdf_parser_agent = PDFParserAgent()
