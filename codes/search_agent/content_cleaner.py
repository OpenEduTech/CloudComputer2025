import re
from .utils import get_logger

logger = get_logger(__name__)

def clean_content(content: str, llm=None) -> str:
    """清洗内容，去除无意义内容或字符，并将内容统一编码成汉字"""
    logger.info("清洗网页内容并统一编码为汉字")
    if not content or content.startswith("读取失败"):
        return content
    # 移除HTML标签
    content = re.sub(r'<[^>]+>', ' ', content)
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', content)
    noise_patterns = [
        r'cookie[s]?\s+政策', r'隐私政策', r'版权所有', r'Copyright © \d{4}', r'All Rights Reserved',
        r'网站地图', r'使用条款', r'关注我们', r'分享到', r'点击加载更多', r'返回顶部', r'广告', r'赞\d+', r'评论\d+',
        r'阅读\d+', r'\d+阅读', r'\d+评论', r'\d+赞', r'JavaScript is disabled', r'Please enable JavaScript',
        r'您的浏览器不支持.*?脚本', r'您的浏览器版本过低', r'联系我们', r'关于我们', r'加入我们', r'招聘信息', r'帮助中心',
        r'常见问题', r'免责声明', r'举报', r'反馈',
    ]
    for pattern in noise_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    content = re.sub(r'%PDF-\d+\.\d+.*?endobj', '', content, flags=re.DOTALL)
    content = re.sub(r'<>stream.*?endstream', '', content, flags=re.DOTALL)
    content = re.sub(r'[.。!！?？,，;；:：]{2,}', '.', content)
    content = re.sub(r'\d{10,}', '', content)
    content = re.sub(r'https?://\S+', '', content)
    content = re.sub(r'\S+@\S+\.\S+', '', content)
    content = re.sub(r'\n\s*\n', '\n\n', content)
    english_ratio = len(re.findall(r'[a-zA-Z]', content)) / (len(content) + 1)
    if english_ratio > 0.3 and llm is not None:
        try:
            template = """
            请将以下文本翻译成标准中文，确保所有内容都使用汉字表达：
            1. 将英文单词和短语翻译成对应的中文
            2. 将专业术语转换为中文常用表达
            3. 保持原文的意思和结构
            4. 确保翻译后的文本流畅自然
            {text}
            只返回翻译结果，不要有其他解释。
            """
            max_chunk_size = 2000
            translated_chunks = []
            for i in range(0, len(content), max_chunk_size):
                chunk = content[i:i+max_chunk_size]
                from langchain_core.prompts import PromptTemplate
                prompt = PromptTemplate(template=template, input_variables=["text"])
                chain = prompt | llm
                translated = chain.invoke({"text": chunk})
                translated_chunks.append(translated)
            content = "".join(translated_chunks)
            logger.info("内容已翻译为中文")
        except Exception as e:
            logger.warning(f"翻译内容失败: {e}，保留原始内容")
    if len(content.strip()) < 100:
        logger.warning("清洗后内容过少，可能过度清理")
        return content[:2000]
    logger.info("内容清洗和编码转换完成")
    return content.strip()