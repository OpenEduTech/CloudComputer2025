"""
图片识别服务
使用OCR和视觉模型识别图片内容
"""

from typing import Dict, Optional
from pathlib import Path
import logging
import base64
from PIL import Image
import io

logger = logging.getLogger(__name__)


class ImageRecognizer:
    """
    图片识别服务
    支持OCR文字识别和视觉模型内容识别
    """
    
    def __init__(self, use_ocr: bool = True, use_vision_model: bool = True):
        """
        初始化图片识别器
        
        Args:
            use_ocr: 是否使用OCR识别文字
            use_vision_model: 是否使用视觉模型识别内容
        """
        self.use_ocr = use_ocr
        self.use_vision_model = use_vision_model
        
        # 尝试初始化OCR
        self.ocr_available = False
        if use_ocr:
            try:
                import pytesseract
                from PIL import Image
                self.ocr_available = True
                logger.info("OCR功能已启用（pytesseract）")
            except ImportError:
                try:
                    import easyocr
                    self.easyocr_reader = easyocr.Reader(['ch_sim', 'en'])
                    self.ocr_available = True
                    self.ocr_type = "easyocr"
                    logger.info("OCR功能已启用（easyocr）")
                except ImportError:
                    logger.warning("OCR库未安装，将跳过OCR识别。请安装pytesseract或easyocr")
                    self.ocr_available = False
        
        logger.info("图片识别服务初始化完成")
    
    def recognize_image(self, image_path: str, page_number: int = None) -> Dict:
        """
        识别图片内容
        
        Args:
            image_path: 图片文件路径
            page_number: 页码（用于上下文）
            
        Returns:
            识别结果字典，包含：
            - text: OCR识别的文字
            - description: 图片内容描述
            - confidence: 识别置信度
        """
        result = {
            "text": "",
            "description": "",
            "confidence": 0.0
        }
        
        if not Path(image_path).exists():
            logger.warning(f"图片文件不存在: {image_path}")
            return result
        
        try:
            # OCR文字识别
            if self.use_ocr and self.ocr_available:
                ocr_result = self._ocr_recognize(image_path)
                result["text"] = ocr_result.get("text", "")
                result["confidence"] = ocr_result.get("confidence", 0.0)
            
            # 视觉模型识别（如果启用）
            if self.use_vision_model:
                vision_result = self._vision_recognize(image_path, page_number)
                result["description"] = vision_result.get("description", "")
                # 如果OCR未识别到文字，使用视觉模型的描述
                if not result["text"] and result["description"]:
                    result["text"] = result["description"]
            
            logger.info(f"图片识别完成: {image_path}")
            return result
            
        except Exception as e:
            logger.error(f"图片识别失败: {str(e)}")
            return result
    
    def _ocr_recognize(self, image_path: str) -> Dict:
        """
        使用OCR识别图片中的文字
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            OCR识别结果
        """
        try:
            if hasattr(self, 'ocr_type') and self.ocr_type == "easyocr":
                return self._easyocr_recognize(image_path)
            else:
                return self._pytesseract_recognize(image_path)
        except Exception as e:
            logger.error(f"OCR识别失败: {str(e)}")
            return {"text": "", "confidence": 0.0}
    
    def _pytesseract_recognize(self, image_path: str) -> Dict:
        """使用pytesseract进行OCR识别"""
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(image_path)
            
            # 识别中文和英文
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            
            # 获取置信度（需要安装tesseract）
            try:
                data = pytesseract.image_to_data(image, lang='chi_sim+eng', output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
            except:
                avg_confidence = 0.8  # 默认置信度
            
            return {
                "text": text.strip(),
                "confidence": avg_confidence
            }
        except ImportError:
            logger.warning("pytesseract未安装，跳过OCR识别")
            return {"text": "", "confidence": 0.0}
    
    def _easyocr_recognize(self, image_path: str) -> Dict:
        """使用easyocr进行OCR识别"""
        try:
            results = self.easyocr_reader.readtext(image_path)
            
            # 合并所有识别的文字
            texts = []
            confidences = []
            for (bbox, text, confidence) in results:
                texts.append(text)
                confidences.append(confidence)
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                "text": "\n".join(texts),
                "confidence": avg_confidence
            }
        except Exception as e:
            logger.error(f"EasyOCR识别失败: {str(e)}")
            return {"text": "", "confidence": 0.0}
    
    def _vision_recognize(self, image_path: str, page_number: int = None) -> Dict:
        """
        使用视觉模型识别图片内容
        
        Args:
            image_path: 图片文件路径
            page_number: 页码
            
        Returns:
            视觉识别结果
        """
        try:
            from utils.llm_factory import create_llm
            from langchain_core.messages import HumanMessage
            
            # 读取图片并转换为base64
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 确定图片格式
            img_format = Path(image_path).suffix[1:].lower() or "png"
            image_url = f"data:image/{img_format};base64,{image_base64}"
            
            # 创建支持视觉的LLM（如果API支持）
            # 注意：当前使用的DeepSeek-V3.2-Exp可能不支持视觉，这里使用文本描述的方式
            # 如果API支持视觉，可以使用以下代码：
            # llm = create_llm()
            # messages = [
            #     HumanMessage(
            #         content=[
            #             {"type": "text", "text": f"请描述这张图片的内容。这是PPT第{page_number}页的图片。"},
            #             {"type": "image_url", "image_url": {"url": image_url}}
            #         ]
            #     )
            # ]
            # response = llm.invoke(messages)
            # description = response.content
            
            # 由于当前API可能不支持视觉，使用OCR结果生成描述
            if self.ocr_available:
                ocr_result = self._ocr_recognize(image_path)
                text = ocr_result.get("text", "")
                if text:
                    # 使用LLM基于OCR文字生成描述
                    from utils.prompts import get_image_description_prompt
                    from utils.llm_factory import create_llm
                    
                    prompt = get_image_description_prompt(text, page_number)
                    llm = create_llm()
                    response = llm.invoke(prompt)
                    description = response.content
                else:
                    description = "图片中未识别到文字内容"
            else:
                description = "图片内容识别功能需要OCR或视觉模型支持"
            
            return {
                "description": description
            }
            
        except Exception as e:
            logger.error(f"视觉模型识别失败: {str(e)}")
            # 如果视觉模型不可用，尝试使用OCR结果
            if self.ocr_available:
                ocr_result = self._ocr_recognize(image_path)
                return {
                    "description": ocr_result.get("text", "无法识别图片内容")
                }
            return {"description": "图片识别功能不可用"}
    
    def batch_recognize(self, image_paths: list, page_numbers: list = None) -> list:
        """
        批量识别图片
        
        Args:
            image_paths: 图片路径列表
            page_numbers: 页码列表（可选）
            
        Returns:
            识别结果列表
        """
        results = []
        for idx, image_path in enumerate(image_paths):
            page_num = page_numbers[idx] if page_numbers and idx < len(page_numbers) else None
            result = self.recognize_image(image_path, page_num)
            results.append(result)
        return results


# 创建全局实例
image_recognizer = ImageRecognizer()
