import requests
import tempfile
from .utils import get_logger

logger = get_logger(__name__)

def read_webpage(url: str) -> str:
    """读取网页内容，支持HTML和PDF格式"""
    logger.info(f"读取内容: {url}")
    try:
        if url.lower().endswith('.pdf') or 'application/pdf' in url.lower():
            logger.info(f"检测到PDF文件: {url}")
            return read_pdf(url)
        else:
            from langchain_community.document_loaders import WebBaseLoader
            loader = WebBaseLoader(url)
            docs = loader.load()
            return docs[0].page_content
    except Exception as e:
        logger.error(f"读取内容失败: {e}")
        return f"读取失败: {str(e)}"

def read_pdf(url: str) -> str:
    logger.info(f"开始下载和解析PDF: {url}")
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
            temp_file.flush()
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(temp_path)
        documents = loader.load()
        text_content = "\n\n".join([doc.page_content for doc in documents])
        import os
        try:
            os.unlink(temp_path)
            logger.info(f"已删除临时文件: {temp_path}")
        except Exception as e:
            logger.warning(f"删除临时文件失败: {e}")
        logger.info(f"PDF解析完成，内容长度: {len(text_content)} 字符")
        return text_content
    except Exception as e:
        logger.error(f"PDF处理失败: {e}")
        return f"PDF处理失败: {str(e)}"