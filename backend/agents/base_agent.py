from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatZhipuAI
from backend.config import AppConfig

class BaseAgent:
    def __init__(self, temperature=0.7):
        # 开发模式下跳过API密钥验证
        if AppConfig.DEV_MODE:
            print(f"🤖 开发模式: 初始化 {self.__class__.__name__} (跳过API验证)")
            self.llm = None
            return
            
        AppConfig.validate()
        print(f"🤖 初始化 Agent: {self.__class__.__name__} (Model: {AppConfig.CHAT_MODEL})")
        
        # 验证API密钥是否有效
        if AppConfig.ZHIPU_API_KEY:
            # 智谱AI API密钥已配置
            pass
        elif AppConfig.API_KEY == "自行填入" or not AppConfig.API_KEY:
            raise ValueError("❌ 请在.env文件中设置有效的OPENAI_API_KEY")
        
        # 根据配置选择大语言模型
        if AppConfig.ZHIPU_API_KEY:
            # 使用智谱AI大语言模型
            self.llm = ChatZhipuAI(
                model=AppConfig.ZHIPU_CHAT_MODEL,
                temperature=temperature,
                api_key=AppConfig.ZHIPU_API_KEY,
                max_tokens=None
            )
        else:
            # 使用ECNU OpenAI兼容接口
            self.llm = ChatOpenAI(
                model=AppConfig.CHAT_MODEL,
                temperature=temperature,
                openai_api_key=AppConfig.API_KEY,
                openai_api_base=AppConfig.API_BASE,
                max_tokens=None
            )