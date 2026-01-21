import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# ❌ 删除本地模型引用: from langchain_huggingface import HuggingFaceEmbeddings
# ✅ 换回 OpenAI 兼容接口
from langchain_openai import OpenAIEmbeddings
# 智谱AI嵌入模型支持
from langchain_community.embeddings import ZhipuAIEmbeddings

# 引入摄入服务
from backend.ingestion_service import IngestionService
# 引入配置
from backend.config import AppConfig

class RAGService:
    def __init__(self):
        # 1. 验证配置
        AppConfig.validate()
        
        self.initialized = False
        
        # 2. 开发模式支持
        if AppConfig.DEV_MODE:
            print("🚧 开发模式: 跳过API密钥验证")
            self.embeddings = None
            self.vector_store = None
            self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
            self.ingestion = IngestionService()
            return
        
        # 3. 根据配置选择嵌入模型
        if AppConfig.ZHIPU_API_KEY:
            # 使用智谱AI嵌入模型
            print(f"🔄 连接智谱AI Embedding 模型: {AppConfig.ZHIPU_EMBEDDING_MODEL} ...")
            self.embeddings = ZhipuAIEmbeddings(
                model=AppConfig.ZHIPU_EMBEDDING_MODEL,
                api_key=AppConfig.ZHIPU_API_KEY,
                check_embedding_ctx_length=False
            )
        else:
            # 使用ECNU OpenAI兼容接口
            if AppConfig.API_KEY == "自行填入" or not AppConfig.API_KEY:
                raise ValueError("❌ 请在.env文件中设置有效的OPENAI_API_KEY")
            
            print(f"🔄 连接远程 Embedding 模型: {AppConfig.EMBEDDING_MODEL} ...")
            print(f"   API Base: {AppConfig.API_BASE}")
            
            self.embeddings = OpenAIEmbeddings(
                model=AppConfig.EMBEDDING_MODEL,      # ecnu-embedding-small
                openai_api_key=AppConfig.API_KEY,     # 你的 API Key
                openai_api_base=AppConfig.API_BASE,   # ECNU API 地址
                check_embedding_ctx_length=False      # 关键：关闭本地 token 检查，防止报错
            )
        
        self.vector_store = None
        
        # 初始化切分器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600, 
            chunk_overlap=100
        )
        
        # 初始化多模态摄入服务
        self.ingestion = IngestionService()

    def build_index(self, file_path, file_type="pdf", use_ocr=False):
        """
        构建知识库索引 (支持 PDF 和 Audio)
        """
        docs = []
        
        # A. 根据类型调用摄入服务
        if file_type == "pdf":
            print(f"📄 开始解析 PDF: {file_path} (OCR={use_ocr})")
            docs = self.ingestion.process_pdf(file_path, use_ocr=use_ocr)
            
        elif file_type == "audio":
            print(f"🔊 开始解析录音: {file_path}")
            text = self.ingestion.process_audio(file_path)
            if text:
                docs = [Document(page_content=text, metadata={"source": file_path, "type": "audio"})]

        # B. 数据清洗
        valid_docs = [d for d in docs if d.page_content and d.page_content.strip()]
        
        if not valid_docs:
            print("⚠️ 未提取到有效文本，跳过索引构建。")
            return 0
            
        # C. 文本切分
        splits = self.text_splitter.split_documents(valid_docs)
        print(f"✂️ 文本切分完成，共 {len(splits)} 个片段。")
        
        if not splits:
            return 0

        # D. 开发模式下跳过实际的向量索引构建
        if AppConfig.DEV_MODE:
            print("🚧 开发模式: 跳过向量索引构建")
            self.initialized = True
            return len(splits)

        # E. 向量化并建立索引 (远程 API)
        try:
            print(f"🚀 正在调用 API 构建向量索引...")
            texts = [doc.page_content for doc in splits]
            metadatas = [doc.metadata for doc in splits]

            from langchain_community.embeddings.zhipuai import ZhipuAIEmbeddings
            if isinstance(self.embeddings, ZhipuAIEmbeddings):
                batch_size = 64
            else:
                batch_size = 25

            all_embeddings = []
            total_batches = (len(texts) + batch_size - 1) // batch_size

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                print(f"   处理批次 {i // batch_size + 1}/{total_batches} ({len(batch)}个片段)...")
                embeddings_batch = self.embeddings.embed_documents(batch)
                all_embeddings.extend(embeddings_batch)

            self.vector_store = FAISS.from_embeddings(
                list(zip(texts, all_embeddings)),
                self.embeddings,
                metadatas=metadatas
            )
            
            print("✅ 索引构建成功！")
            return len(splits)
        except Exception as e:
            print(f"❌ 向量化失败 (请检查 API Key 或 网络): {e}")
            # 抛出异常以便前端捕获
            raise e

    def retrieve_relevant_content(self, query, k=3):
        """
        根据 Query 检索相关背景知识
        """
        # 开发模式下返回模拟的检索结果
        if AppConfig.DEV_MODE:
            return f"[开发模式] 为查询 '{query}' 检索到的相关内容"
        
        if not self.vector_store:
            return ""
        
        try:
            # 相似度搜索 (也会调用 API 将 query 向量化)
            docs = self.vector_store.similarity_search(query, k=k)
            context = "\n\n".join([d.page_content for d in docs])
            return context
        except Exception as e:
            print(f"❌ 检索失败: {e}")
            return ""
