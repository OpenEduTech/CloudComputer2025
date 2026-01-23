import os
import base64
import io
import time
from openai import OpenAI  # ✅ 保留你的 OCR 客户端
from pdf2image import convert_from_path
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

# 引入统一配置
from backend.config import AppConfig

class IngestionService:
    def __init__(self):
        print(f"👁️ 初始化多模态摄入服务...")
        
        # --- 1. OCR 模块初始化 (你的部分) ---
        if not AppConfig.API_KEY:
            print("⚠️ 未配置 OPENAI_API_KEY，OCR 功能已禁用")
            self.ocr_client = None
        else:
            self.ocr_client = OpenAI(
                api_key=AppConfig.API_KEY,
                base_url=AppConfig.API_BASE 
            )
            print(f"   - OCR 模型: {AppConfig.OCR_MODEL}")

        # --- 2. 语音模块初始化 (队友的部分 - 懒加载) ---
        self.asr_model = None 

    def process_pdf(self, file_path, use_ocr=False):
        """
        [你的逻辑] 处理PDF：支持强制 OCR
        """
        print(f"📄 开始处理 PDF: {os.path.basename(file_path)}")
        
        # 强制 OCR 逻辑
        if use_ocr:
            if self.ocr_client:
                print(f"🔥 用户强制启用 OCR，正在调用 {AppConfig.OCR_MODEL}...")
                return self._ocr_with_qwen_api(file_path)
            else:
                print("⚠️ 用户开启了 OCR 但 API Client 未初始化，回退到普通模式。")

        # 常规提取逻辑
        loader = PyPDFLoader(file_path)
        try:
            docs = loader.load()
            raw_text = "".join([d.page_content for d in docs if d.page_content])
            
            if len(raw_text.strip()) < 50:
                print("⚠️ 警告: 提取的文本极少。如果这是扫描件，请在侧边栏勾选 [启用视觉 OCR]。")
                
            return docs
        except Exception as e:
            print(f"❌ 常规 PDF 解析异常: {e}")
            return []

    def _ocr_with_qwen_api(self, file_path):
        """
        [你的逻辑] 使用 Qwen-VL-OCR 进行高精度识别
        """
        extracted_docs = []
        
        # 1. 检查依赖
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise ImportError("缺少 pdf2image 库。请运行 `pip install pdf2image`")

        # 2. 转图片
        print(f"🖼️ 正在将 PDF 转为图片流...")
        try:
            images = convert_from_path(file_path, dpi=150, fmt="jpeg")
        except Exception as e:
            if "poppler" in str(e).lower() or "page count" in str(e).lower():
                raise Exception(f"系统缺少 Poppler 工具。请检查 Dockerfile 是否安装了 poppler-utils。\n原始错误: {e}")
            raise e

        total_pages = len(images)
        print(f"   共 {total_pages} 页，开始逐页识别...")

        for i, img in enumerate(images):
            # 图片转 Base64
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            try:
                # 调用 Qwen-VL
                completion = self.ocr_client.chat.completions.create(
                    model=AppConfig.OCR_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}},
                                {"type": "text", "text": "请将图片中的文字完整提取出来。如果是表格，请还原为 Markdown 格式。保持段落结构。"}
                            ]
                        }
                    ]
                )
                page_content = completion.choices[0].message.content
                
            except Exception as api_err:
                raise Exception(f"API 调用失败 (第 {i+1} 页): {api_err}")

            if page_content:
                doc = Document(
                    page_content=page_content, 
                    metadata={"page": i+1, "source": file_path, "type": "ocr_qwen", "model": AppConfig.OCR_MODEL}
                )
                extracted_docs.append(doc)
            
            print(f"   ✅ 第 {i+1}/{total_pages} 页识别完成")

        return extracted_docs

    def process_audio(self, audio_file_path):
        """
        [进阶功能] 录音转写 (Speech-to-Text) - 使用阿里 FunASR (Paraformer)
        支持 wav, aiff, flac。自动尝试将 mp3 转换为 wav (需 pydub)。
        """
        import os
        import time
        target_path = audio_file_path
        converted_wav_path = None
        
        # 0. 如果是 MP3，尝试转换 (FunASR 推荐使用 16k采样率的 WAV)
        if audio_file_path.lower().endswith(".mp3"):
            try:
                print(f"🎵 检测到 MP3 文件: {audio_file_path}，正在转换为 WAV (16k Hz)...")
                from pydub import AudioSegment
                
                sound = AudioSegment.from_mp3(audio_file_path)
                # 重采样为 16000Hz 单声道，这对 ASR 模型最友好
                sound = sound.set_frame_rate(16000).set_channels(1)
                
                converted_wav_path = audio_file_path.replace(".mp3", ".wav")
                # 避免文件名冲突
                if os.path.exists(converted_wav_path):
                     converted_wav_path = audio_file_path.replace(".mp3", f"_{int(time.time())}.wav")
                     
                sound.export(converted_wav_path, format="wav")
                target_path = converted_wav_path
                print(f"✅ MP3 转换成功: {target_path}")
            except ImportError:
                print("❌ 缺少 pydub 库，无法处理 MP3。请运行: pip install pydub")
                return "（MP3转换失败：环境缺少 pydub 库）"
            except Exception as e:
                print(f"❌ MP3 转换异常 (可能缺少 ffmpeg): {e}")
                return f"（MP3转换失败：{e}）"

        try:
            # 1. 懒加载 FunASR 模型
            if self.asr_model is None:
                print("⏳ 正在首次加载 FunASR 模型 (Paraformer)... 请耐心等待模型下载...")
                from funasr import AutoModel
                # 使用阿里达摩院(ModelScope)的标准 Paraformer 模型
                self.asr_model = AutoModel(
                    model="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                    model_revision="v2.0.4",
                    vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
                    vad_model_revision="v2.0.4",
                    punc_model="iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
                    punc_model_revision="v2.0.4",
                    disable_update=True  # 避免每次检查更新
                )
                print("✅ FunASR 模型加载完成")

            # 2. 执行推理
            print(f"🎙️ 正在使用 FunASR 识别音频内容: {target_path} ...")
            # generate 返回结果通常是列表
            res = self.asr_model.generate(input=target_path)
            
            text = ""
            if res and isinstance(res, list) and len(res) > 0:
                text = res[0].get("text", "")
            
            print(f"✅ 音频转写完成 (长度: {len(text)})")
            return text

        except Exception as e:
            print(f"❌ 语音转写失败: {e}")
            import traceback
            traceback.print_exc()
            return f"（语音转写失败：{e}）"
        finally:
            # 清理临时转换的 WAV 文件
            if converted_wav_path and os.path.exists(converted_wav_path):
                try:
                    os.remove(converted_wav_path)
                    print(f"🧹 已清理临时文件: {converted_wav_path}")
                except:
                    pass