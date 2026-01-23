"""
配置文件管理
适配 config.json 结构
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class LLMConfig:
    """LLM 配置"""
    api_key: str = ""
    model: str = "gpt-3.5-turbo"
    base_url: Optional[str] = None
    temperature: float = 0.7
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果 api_key 为空，尝试从环境变量获取
        if not self.api_key:
            self.api_key = os.getenv('OPENAI_API_KEY', '')
        
        # 如果 base_url 为空，尝试从环境变量获取
        if not self.base_url:
            self.base_url = os.getenv('OPENAI_BASE_URL', None)

@dataclass
class RetrievalConfig:
    """检索配置"""
    preferred_sources: list = None
    max_results: int = 3
    local_rag_priority: bool = True
    
    def __post_init__(self):
        if self.preferred_sources is None:
            self.preferred_sources = ["arxiv", "wikipedia"]

@dataclass
class ExpansionConfig:
    """扩展配置"""
    max_revisions: int = 2
    min_gap_priority: int = 3
    temperature: float = 0.7

@dataclass
class StreamingConfig:
    """流式配置"""
    enabled: bool = True
    chunk_size: int = 50

@dataclass
class KnowledgeBaseConfig:
    """知识库配置"""
    path: str = "./knowledge_base"
    chunk_size: int = 1000
    chunk_overlap: int = 200

class ConfigManager:
    """配置管理器"""
    
    _instance = None
    _config_data = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载配置文件"""
        config_paths = [
            Path(__file__).parent.parent / "config.json",
            Path(__file__).parent / "config.json",
            Path.cwd() / "config.json",
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        self._config_data = json.load(f)
                    print(f"📁 配置文件加载成功: {config_path}")
                    break
                except Exception as e:
                    print(f"❌ 读取配置文件失败: {e}")
        
        if self._config_data is None:
            print("⚠️  未找到配置文件，使用默认配置")
            self._config_data = {}
    
    def get_llm_config(self) -> LLMConfig:
        """获取 LLM 配置"""
        llm_data = self._config_data.get('llm', {})
        
        # 设置环境变量
        if 'api_key' in llm_data:
            os.environ['OPENAI_API_KEY'] = llm_data['api_key']
        if 'base_url' in llm_data:
            os.environ['OPENAI_BASE_URL'] = llm_data['base_url']
        
        return LLMConfig(
            api_key=llm_data.get('api_key', ''),
            model=llm_data.get('model', 'gpt-3.5-turbo'),
            base_url=llm_data.get('base_url'),
            temperature=self._config_data.get('expansion', {}).get('temperature', 0.7)
        )
    
    def get_retrieval_config(self) -> RetrievalConfig:
        """获取检索配置"""
        retrieval_data = self._config_data.get('retrieval', {})
        return RetrievalConfig(
            preferred_sources=retrieval_data.get('preferred_sources', ["arxiv", "wikipedia"]),
            max_results=retrieval_data.get('max_results', 3),
            local_rag_priority=retrieval_data.get('local_rag_priority', True)
        )
    
    def get_expansion_config(self) -> ExpansionConfig:
        """获取扩展配置"""
        expansion_data = self._config_data.get('expansion', {})
        return ExpansionConfig(
            max_revisions=expansion_data.get('max_revisions', 2),
            min_gap_priority=expansion_data.get('min_gap_priority', 3),
            temperature=expansion_data.get('temperature', 0.7)
        )
    
    def get_streaming_config(self) -> StreamingConfig:
        """获取流式配置"""
        streaming_data = self._config_data.get('streaming', {})
        return StreamingConfig(
            enabled=streaming_data.get('enabled', True),
            chunk_size=streaming_data.get('chunk_size', 50)
        )
    
    def get_knowledge_base_config(self) -> KnowledgeBaseConfig:
        """获取知识库配置"""
        kb_data = self._config_data.get('knowledge_base', {})
        return KnowledgeBaseConfig(
            path=kb_data.get('path', "./knowledge_base"),
            chunk_size=kb_data.get('chunk_size', 1000),
            chunk_overlap=kb_data.get('chunk_overlap', 200)
        )

# 全局配置实例
config_manager = ConfigManager()

# 快捷访问函数
def get_llm_config() -> LLMConfig:
    """获取 LLM 配置"""
    return config_manager.get_llm_config()

def get_retrieval_config() -> RetrievalConfig:
    """获取检索配置"""
    return config_manager.get_retrieval_config()

def get_expansion_config() -> ExpansionConfig:
    """获取扩展配置"""
    return config_manager.get_expansion_config()

# 使用示例
if __name__ == "__main__":
    llm_config = get_llm_config()
    print(f"LLM 配置:")
    print(f"  API Key: {llm_config.api_key[:10]}..." if llm_config.api_key else "  API Key: 未设置")
    print(f"  模型: {llm_config.model}")
    print(f"  Base URL: {llm_config.base_url}")
    print(f"  温度: {llm_config.temperature}")
    
    # 检查环境变量是否已设置
    print(f"\n环境变量检查:")
    print(f"  OPENAI_API_KEY: {'已设置' if os.getenv('OPENAI_API_KEY') else '未设置'}")
    print(f"  OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL', '未设置')}")