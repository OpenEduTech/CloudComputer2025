import os
import json
import numpy as np
from typing import Dict
from dotenv import load_dotenv
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
from sentence_transformers import SentenceTransformer
from openai import AsyncOpenAI

load_dotenv()

# 如果没有设置，默认使用 huggingface 镜像
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

class RAGEngine:
    def __init__(self):
        self.base_dir = "./lightrag_workdir"
        os.makedirs(self.base_dir, exist_ok=True)
        self.rag_instances: Dict[str, LightRAG] = {}
        
        self.api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.llm_model = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # Embedding 模型加载
        model_path = os.getenv("EMBEDDING_MODEL", "./bge-large-zh-v1.5")
        try:
            if os.path.exists(model_path) and os.path.exists(os.path.join(model_path, "config.json")):
                self.embedding_model = SentenceTransformer(model_path, device='cpu')
            else:
                print(f"Loading embedding model from HF: BAAI/bge-large-zh-v1.5")
                self.embedding_model = SentenceTransformer('BAAI/bge-large-zh-v1.5', device='cpu')
        except Exception as e:
            print(f"Warning: Embedding load failed ({e}), using fallback.")
            self.embedding_model = SentenceTransformer('BAAI/bge-large-zh-v1.5', device='cpu')
    
    def get_rag_instance(self, concept: str) -> LightRAG:
        if concept not in self.rag_instances:
            working_dir = os.path.join(self.base_dir, concept)
            os.makedirs(working_dir, exist_ok=True)
            self.rag_instances[concept] = LightRAG(
                working_dir=working_dir,
                llm_model_func=self._llm_wrapper,
                embedding_func=EmbeddingFunc(
                    embedding_dim=1024,
                    max_token_size=512,
                    func=self._embedding_wrapper
                )
            )
        return self.rag_instances[concept]
    
    async def query(self, concept: str, question: str, param: QueryParam = None) -> str:
        if param is None:
            param = QueryParam(mode="hybrid")
        
        rag = self.get_rag_instance(concept)
        #  显式初始化存储
        await rag.initialize_storages()
        
        return await rag.aquery(question, param=param)

    async def _llm_wrapper(self, prompt, system_prompt=None, history_messages=[], **kwargs):
        """LLM 调用封装：包含 Prompt 注入和参数过滤"""
        
        # 1. 清理 LightRAG 传入的特殊参数
        kwargs.pop("hashing_kv", None)
        kwargs.pop("keyword_extraction", None)
        
        # 2. 过滤掉 OpenAI API 不支持的参数
        allowed_params = {
            "temperature", "top_p", "n", "stream", "stop", 
            "max_tokens", "presence_penalty", "frequency_penalty",
            "logit_bias", "user", "response_format", "seed",
            "tools", "tool_choice", "functions", "function_call"
        }
        kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}
    
        # 3. 注入你的核心 Prompt (实体提取规则 & 中文强制)
        instruction = """
        【重要：实体提取控制与过滤规则】
        你是一个严谨的科学知识图谱构建者。请在提取实体时遵守以下标准：

        **保留（白名单）**：
        1. **核心概念**：如 "熵"、"热力学第二定律"、"耗散结构"。
        2. **关键人物**：如 "香农"、"薛定谔"、"玻尔兹曼"。
        3. **专有名词**：如 "最大熵原理"、"公式 S=k*lnW"。
        
        **丢弃（黑名单 - 绝对不要提取）**：
        1. **时间/日期**：不要提取 "1948年"、"20世纪"、"今天" 这样的时间词。
        2. **数量/度量**：不要提取 "一个"、"大量"、"均值" 这样的泛指数量词。
        3. **通用动词/形容词**：不要提取 "增加"、"减少"、"复杂的"、"美丽的" 这种非名词性实体。
        4. **文档元数据**：不要提取 "论文"、"书"、"章节" 这种载体词，除非是专有名词（如《生命是什么》）。
        
        ---------------------
        【必须遵守的规则】
        1. 忽略上文所有的英文示例 (Examples)。
        2. **必须使用简体中文**输出所有内容。
        3. 将英文术语翻译为中文（如 "Entropy" -> "熵"）。
        4. 保持 JSON 格式正确。
        ---------------------
        """
        # 将指令附加到 Prompt 后
        prompt = prompt + instruction
        
        # 4. 创建 Client (复用 __init__ 中初始化的配置)
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(history_messages)
        messages.append({"role": "user", "content": prompt})
        
        # 5. 发起请求
        response = await client.chat.completions.create(
            model=self.llm_model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
    
    async def _embedding_wrapper(self, texts: list) -> np.ndarray:
        return self.embedding_model.encode(texts, normalize_embeddings=True)
    
    async def build_graph(self, concept: str, documents: list) -> tuple[str, dict]:
        rag = self.get_rag_instance(concept)
        working_dir = os.path.join(self.base_dir, concept)
        
        # 初始化存储
        await rag.initialize_storages()
        
        print(f"Inserting {len(documents)} docs for '{concept}'...")
        for doc in documents:
            text = f"[DOC_ID: {doc['doc_id']}]\n[领域: {doc['domain']}]\n{doc['content']}"
            await rag.ainsert(text)
            
        return working_dir, self._build_chunk_mapping(working_dir, documents)
    
    def _build_chunk_mapping(self, working_dir: str, documents: list) -> dict:
        chunk_json_path = os.path.join(working_dir, "kv_store_text_chunks.json")
        if not os.path.exists(chunk_json_path): return {}
        
        try:
            with open(chunk_json_path, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
        except Exception:
            return {}
            
        doc_map = {d['doc_id']: d['domain'] for d in documents}
        mapping = {}
        for cid, cdata in chunks.items():
            content = cdata.get('content', '')
            found = set()
            for did in doc_map:
                if f"[DOC_ID: {did}]" in content: found.add(did)
            if not found:
                 for doc in documents:
                    clean = content.replace('[DOC_ID:', '').replace('[领域:', '')
                    if clean[:50] in doc['content']: 
                        found.add(doc['doc_id']); break
            
            if found:
                mapping[cid] = {
                    'doc_ids': list(found), 
                    'domains': list(set(doc_map[d] for d in found))
                }
        return mapping

rag_engine = RAGEngine()