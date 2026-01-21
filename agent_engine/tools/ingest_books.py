import os
import glob
import shutil
import tempfile
import traceback
import concurrent.futures
from typing import List, Dict
from tqdm import tqdm

# Ebook processing
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import mobi

# LangChain & Chroma
import chromadb
from chromadb.utils import embedding_functions
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import settings
from tools.ecnu_embedding import ECNUEmbeddingFunction
from tools.ecnu_llm import ECNULLM

import hashlib

class BookIngester:
    def __init__(self):
        # 初始化 ChromaDB 客户端
        print(f"Connecting to ChromaDB at {settings.CHROMA_SERVER_HOST}:{settings.CHROMA_SERVER_PORT}...")
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_SERVER_HOST,
            port=settings.CHROMA_SERVER_PORT
        )
        
        # 初始化 Embedding 函数
        if "ecnu" in settings.EMBEDDING_MODEL:
            print(f"Using ECNU Embedding: {settings.EMBEDDING_MODEL}")
            self.embedding_fn = ECNUEmbeddingFunction()
        else:
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL
            )
        
        # 初始化 LLM (用于关键词提取)
        # 切换到 ecnu-turbo (300 RPM)
        # self.llm = ECNULLM(model="ecnu-turbo", rpm_limit=280)
        
        # 读取 Prompt
        self.keyword_prompt = ""
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompt", "keyword_extract.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.keyword_prompt = f.read()
        else:
            print(f"Warning: Prompt file not found at {prompt_path}")
            self.keyword_prompt = "请从以下文本中提取核心实体，以JSON格式输出：{\"entities\": [\"实体1\", \"实体2\"]}"

        # 缓存 Collection 对象，避免重复获取
        self.collections = {}
        
        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=300,
            separators=["\n\n", "\n", "。", "！", "？", ".", " ", ""]
        )

    def _get_safe_collection_name(self, name: str) -> str:
        """
        生成合法的 Collection Name (ChromaDB 限制: 3-63 chars, alphanumeric, dashes, underscores)
        这里使用 MD5 哈希来确保安全，同时保留原名的映射关系以便查询（如果需要）
        """
        # 简单处理：如果全是英文且符合规范，直接用；否则 Hash
        # 为了统一，这里对中文目录统一使用 Hash 前缀 + 简单标识
        hash_object = hashlib.md5(name.encode())
        hash_hex = hash_object.hexdigest()
        return f"cat_{hash_hex}"

    def get_collection(self, category_name: str):
        """根据一级目录名获取或创建 Collection"""
        safe_name = self._get_safe_collection_name(category_name)
        
        if safe_name not in self.collections:
            print(f"Getting collection for category '{category_name}' (ID: {safe_name})...")
            # 将真实的中文名存入 Collection 的 metadata，方便辨认
            self.collections[safe_name] = self.client.get_or_create_collection(
                name=safe_name,
                embedding_function=self.embedding_fn,
                metadata={"real_name": category_name}
            )
        return self.collections[safe_name]

    def clean_html(self, html_content):
        """使用 BeautifulSoup 清洗 HTML 标签"""
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text()

    def process_epub(self, file_path) -> str:
        """解析 EPUB 文件提取文本"""
        try:
            book = epub.read_epub(file_path)
            full_text = []
            
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content = item.get_content().decode('utf-8', 'ignore')
                    text = self.clean_html(content)
                    if text.strip():
                        full_text.append(text)
            
            return "\n".join(full_text)
        except Exception as e:
            print(f"Error processing EPUB {file_path}: {e}")
            return ""

    def process_mobi(self, file_path) -> str:
        """解析 MOBI 文件提取文本"""
        tmp_dir = tempfile.mkdtemp()
        try:
            temp_file, filepath = mobi.extract(file_path)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    return self.clean_html(content)
            return ""
        except Exception as e:
            print(f"Error processing MOBI {file_path}: {e}")
            return ""
        finally:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def process_chunk_keywords(self, chunk, chunk_index, total):
        """处理单个 Chunk 的关键词提取 (用于并发)"""
        # print(f"Extracting keywords for chunk {chunk_index+1}/{total}...")
        # keywords = self.llm.extract_keywords(chunk, self.keyword_prompt)
        keywords = []
        return chunk_index, keywords

    def ingest_file(self, file_path, category_name, sub_category_name):
        """处理单个文件并入库"""
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        
        # 获取对应的 Collection
        collection = self.get_collection(category_name)
        
        content = ""
        if ext == '.epub':
            content = self.process_epub(file_path)
        elif ext == '.mobi':
            content = self.process_mobi(file_path)
        else:
            print(f"Skipping unsupported file type: {ext}")
            return

        if not content:
            print(f"No content extracted from {filename}")
            return

        # 分块
        chunks = self.text_splitter.split_text(content)
        print(f"Split into {len(chunks)} chunks.")
        
        if not chunks:
            return

        # --- 步骤1: 并发提取关键词 ---
        chunk_keywords_map = {} # index -> keywords list
        
        # 使用 ThreadPoolExecutor 并发调用 LLM
        # ecnu-turbo 支持 300 RPM，我们可以适当增加并发数
        # max_workers = 10 
        # print(f"Extracting keywords with {max_workers} threads...")
        
        # with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        #     # 提交所有任务
        #     future_to_chunk = {
        #         executor.submit(self.process_chunk_keywords, chunk, i, len(chunks)): i 
        #         for i, chunk in enumerate(chunks)
        #     }
        #     
        #     # 使用 tqdm 显示进度
        #     for future in tqdm(concurrent.futures.as_completed(future_to_chunk), total=len(chunks), desc="LLM Extraction"):
        #         try:
        #             idx, keywords = future.result()
        #             chunk_keywords_map[idx] = keywords
        #         except Exception as e:
        #             print(f"Chunk processing generated an exception: {e}")
        #             chunk_keywords_map[future_to_chunk[future]] = []

        # --- 步骤2: 批量入库 ---
        ids = []
        documents = []
        metadatas = []
        documents_for_embedding = []
        
        batch_size = 50
        
        print("Ingesting into ChromaDB...")
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filename}_{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            
            # 获取提取到的关键词
            keywords_list = chunk_keywords_map.get(i, [])
            # 转为字符串存储，方便查看，也可以逗号分隔用于后续过滤
            keywords_str = ", ".join(keywords_list)
            
            metadatas.append({
                "source": filename,
                "type": "book",
                "chunk_index": i,
                "keywords": keywords_str,
                "category": category_name,      # 一级学科
                "sub_category": sub_category_name # 二级学科
            })
            
            contextualized_text = f"《{filename}》\n{chunk}"
            documents_for_embedding.append(contextualized_text)
            
            if len(ids) >= batch_size:
                embeddings = self.embedding_fn(documents_for_embedding)
                collection.add(
                    ids=ids, 
                    documents=documents, 
                    embeddings=embeddings, 
                    metadatas=metadatas
                )
                ids = []
                documents = []
                metadatas = []
                documents_for_embedding = []
                print(".", end="", flush=True)
        
        if ids:
            embeddings = self.embedding_fn(documents_for_embedding)
            collection.add(
                ids=ids, 
                documents=documents, 
                embeddings=embeddings, 
                metadatas=metadatas
            )
        
        print(f"\nFinished ingesting {filename}")

    def scan_and_ingest(self, data_dir):
        """扫描目录并处理所有书籍"""
        print(f"Scanning directory: {data_dir}")
        
        # 遍历逻辑更新：需要解析层级结构
        # 假设结构: data_dir / Category / SubCategory / Book.epub
        
        files_to_process = [] # (path, category, sub_category)
        
        for root, dirs, filenames in os.walk(data_dir):
            for filename in filenames:
                if filename.lower().endswith(('.epub', '.mobi')):
                    file_path = os.path.join(root, filename)
                    
                    # 计算相对路径
                    rel_path = os.path.relpath(file_path, data_dir)
                    parts = rel_path.split(os.sep)
                    
                    # 默认值
                    category = "Unknown"
                    sub_category = "Unknown"
                    
                    if len(parts) >= 3:
                        # data/Category/SubCategory/Book.epub
                        category = parts[0]
                        sub_category = parts[1]
                    elif len(parts) == 2:
                        # data/Category/Book.epub (没有二级)
                        category = parts[0]
                    
                    files_to_process.append((file_path, category, sub_category))
        
        print(f"Found {len(files_to_process)} books.")
        
        for file_path, cat, sub_cat in tqdm(files_to_process, desc="Ingesting Books"):
            try:
                print(f"\nProcessing [{cat} -> {sub_cat}]: {os.path.basename(file_path)}")
                self.ingest_file(file_path, cat, sub_cat)
            except Exception as e:
                print(f"Failed to ingest {file_path}: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    possible_paths = [
        "/app/data",
        "data",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    ]
    
    data_dir = None
    for p in possible_paths:
        if os.path.exists(p):
            data_dir = p
            break
            
    if data_dir:
        ingester = BookIngester()
        ingester.scan_and_ingest(data_dir)
    else:
        print("Data directory not found!")
