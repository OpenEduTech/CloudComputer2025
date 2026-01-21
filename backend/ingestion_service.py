import os
import base64
import speech_recognition as sr
from pdf2image import convert_from_path
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

# 引入统一配置
from backend.config import AppConfig

class IngestionService:
    def __init__(self):
        # 初始化用于视觉识别的大模型
        # 这里使用 AppConfig 中的配置，确保能够调用到支持视觉的模型（如 gpt-4o 或 ecnu-plus 兼容接口）
        print(f"👁️ 初始化视觉服务 (Model: {AppConfig.CHAT_MODEL})...")
        self.vision_llm = ChatOpenAI(
            model=AppConfig.CHAT_MODEL, 
            openai_api_key=AppConfig.API_KEY,
            openai_api_base=AppConfig.API_BASE,
            max_tokens=2000,
            temperature=0.2 # 识别文字不需要太高的创造性
        )

    def process_pdf(self, file_path, use_ocr=False):
        """
        处理PDF：优先尝试直接提取文本，如果文本极少且开启OCR，则调用视觉模型
        """
        # 1. 尝试常规 PyPDFLoader 提取
        loader = PyPDFLoader(file_path)
        try:
            docs = loader.load()
            # 拼接所有页面的文本，检查长度
            text_content = "\n".join([d.page_content for d in docs])
        except Exception as e:
            print(f"⚠️ 常规PDF解析失败: {e}")
            text_content = ""
            docs = []

        # 2. 智能判断：如果提取内容太少（<50字符）且用户开启了 OCR
        # 这通常意味着上传的是扫描件（纯图片PDF）
        if len(text_content.strip()) < 50 and use_ocr:
            print("⚠️ 检测到扫描件或空文本，尝试调用视觉模型进行 OCR...")
            return self._ocr_pdf_with_vision_model(file_path)
        
        return docs

    def _ocr_pdf_with_vision_model(self, file_path):
        """
        [进阶功能] 将PDF转图片，发送给 LLM Vision API 提取文字
        注意：需要系统安装 Poppler 工具支持 pdf2image
        """
        try:
            # 将 PDF 转为图片 (为了演示效率，默认只处理前3页，避免Token爆炸)
            # first_page=1, last_page=3
            images = convert_from_path(file_path, first_page=1, last_page=3)
            extracted_docs = []
            
            print(f"🖼️ PDF已转为 {len(images)} 张图片，开始视觉识别...")

            for i, img in enumerate(images):
                # 图片转 base64
                import io
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                # 构造 Vision 请求
                msg = HumanMessage(content=[
                    {"type": "text", "text": "请将这张图片中的文字完整提取出来，保持段落结构，不要遗漏任何细节。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
                ])
                
                response = self.vision_llm.invoke([msg])
                
                # 将识别结果包装成 Document 对象
                doc = Document(
                    page_content=response.content, 
                    metadata={"page": i+1, "source": file_path, "type": "ocr_vision"}
                )
                extracted_docs.append(doc)
            
            return extracted_docs
            
        except ImportError:
            print("❌ 缺少 pdf2image 依赖或 Poppler 工具，无法进行图片OCR。")
            return []
        except Exception as e:
            print(f"❌ OCR 失败: {e}")
            return []

    def process_audio(self, audio_file_path):
        """
        [进阶功能] 录音转写 (Speech-to-Text)
        """
        r = sr.Recognizer()
        try:
            print("🎙️ 正在处理音频文件...")
            # 支持 wav, aiff, flac
            with sr.AudioFile(audio_file_path) as source:
                audio_data = r.record(source)
                
                # 尝试使用 Google Web API (注意：国内网络可能需要代理)
                # 如果是离线环境，可以改用 r.recognize_sphinx(audio_data) 需要额外安装 pocketsphinx
                text = r.recognize_google(audio_data, language="zh-CN")
                print("✅ 音频转写完成")
                return text
        except Exception as e:
            print(f"❌ 语音转写失败: {e}")
            return "（语音转写失败，请检查网络或音频格式）"