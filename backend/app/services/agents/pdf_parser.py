import asyncio
import os
from app.services.llm_factory import LLMFactory

class PDFParserAgent:
    def __init__(self):
        self.client = LLMFactory.get_zhipu_client()

    async def parse_pdf(self, file_path: str) -> str:
        """
        解析PDF文件并返回内容
        使用智谱AI的file_parser，失败时降级到pypdf
        """
        try:
            # Run the parsing in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, self._call_parser, file_path)
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
