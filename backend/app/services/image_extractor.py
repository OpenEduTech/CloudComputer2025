"""
图片内容提取服务
支持使用 Claude Vision / GPT-4V / 豆包 提取图片中的文本和结构信息
"""
import os
import re
import base64
import logging
from typing import Dict, Any, Optional, List
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger(__name__)

# 图片提取 Prompt
IMAGE_EXTRACTION_PROMPT = """请详细描述这张图片的内容，包括：

1. **图片类型**：架构图/流程图/数据图表/示意图/其他
2. **主要元素和组件**：列出所有可见的元素、组件、模块
3. **元素之间的关系**：描述元素之间的连接、依赖、数据流等关系
4. **文字标注**：提取图片中的所有文字标注和说明
5. **整体结构**：描述图片的整体布局和结构层次
6. **关键信息**：提取关键数据、指标、流程步骤等

请用结构化的方式描述，便于后续与文档文本进行对比。"""


class ImageExtractor:
    """图片内容提取服务"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.doubao_api_key = os.getenv("DOUBAO_API_KEY")
        self.doubao_endpoint = os.getenv("DOUBAO_ENDPOINT", "https://ark.cn-beijing.volces.com/api/v3")
        
        # 优先级：豆包 > Claude > OpenAI
        if self.doubao_api_key:
            self.provider = "doubao"
            logger.info("使用豆包 Vision API")
        elif self.anthropic_api_key:
            self.provider = "claude"
            logger.info("使用 Claude Vision API")
        elif self.openai_api_key:
            self.provider = "openai"
            logger.info("使用 OpenAI Vision API")
        else:
            self.provider = None
            logger.warning("未配置 Vision API Key，图片提取功能将不可用")
    
    def is_available(self) -> bool:
        """检查图片提取服务是否可用"""
        return bool(self.doubao_api_key or self.anthropic_api_key or self.openai_api_key)
    
    async def extract_from_image(
        self,
        image_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        从图片中提取内容描述
        
        Args:
            image_content: 图片二进制内容
            filename: 文件名
        
        Returns:
            提取的图片描述信息
        """
        if not self.is_available():
            raise ValueError("未配置 Vision API Key (OPENAI_API_KEY / ANTHROPIC_API_KEY / DOUBAO_API_KEY)")
        
        if Image is None:
            raise ImportError("Pillow 未安装，请运行: pip install Pillow")
        
        try:
            # 验证图片格式
            image = Image.open(BytesIO(image_content))
            image_format = image.format
            image_size = image.size
            
            # 检查图片大小（Vision API 通常限制 < 20MB）
            if len(image_content) > 20 * 1024 * 1024:
                raise ValueError(f"图片文件过大 ({len(image_content) / 1024 / 1024:.2f}MB)，请压缩到 20MB 以下")
            
            # 转换为 base64
            image_base64 = base64.b64encode(image_content).decode('utf-8')
            
            # 确定图片 MIME 类型
            mime_type = self._get_mime_type(image_format, filename)
            
            # 根据提供商调用不同的 API
            if self.provider == "doubao":
                description = await self._extract_with_doubao(image_base64, mime_type)
            elif self.provider == "claude":
                description = await self._extract_with_claude(image_base64, mime_type)
            elif self.provider == "openai":
                description = await self._extract_with_openai(image_base64, mime_type)
            else:
                raise ValueError("未配置任何 Vision API")
            
            # 清洗描述，去除多余的前置语和 Markdown 头标记
            description = self._sanitize_description(description)
            # 解析结构化元素
            extracted_elements = self._parse_elements(description)
            
            return {
                "success": True,
                "filename": filename,
                "image_format": image_format,
                "image_size": image_size,
                "file_size_bytes": len(image_content),
                "description": description,
                "extracted_elements": extracted_elements
            }
        except Exception as e:
            logger.error(f"图片提取失败: {str(e)}")
            raise
    
    def _get_mime_type(self, image_format: str, filename: str) -> str:
        """获取图片 MIME 类型"""
        format_map = {
            'PNG': 'image/png',
            'JPEG': 'image/jpeg',
            'JPG': 'image/jpeg',
            'GIF': 'image/gif',
            'WEBP': 'image/webp'
        }
        
        if image_format in format_map:
            return format_map[image_format]
        
        # 从文件名推断
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if ext == 'png':
            return 'image/png'
        elif ext in ['jpg', 'jpeg']:
            return 'image/jpeg'
        elif ext == 'gif':
            return 'image/gif'
        else:
            return 'image/png'  # 默认
    
    async def _extract_with_claude(self, image_base64: str, mime_type: str) -> str:
        """使用 Claude Vision API 提取"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            
            message = client.messages.create(
                model="claude-3-opus-20240229",  # 或 claude-3-sonnet-20240229
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": IMAGE_EXTRACTION_PROMPT
                            }
                        ]
                    }
                ]
            )
            
            return message.content[0].text
        except ImportError:
            raise ImportError("anthropic 库未安装，请运行: pip install anthropic")
        except Exception as e:
            logger.error(f"Claude Vision API 调用失败: {str(e)}")
            raise
    
    async def _extract_with_openai(self, image_base64: str, mime_type: str) -> str:
        """使用 OpenAI GPT-4V 提取"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": IMAGE_EXTRACTION_PROMPT
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096
            )
            
            return response.choices[0].message.content
        except ImportError:
            raise ImportError("openai 库未安装，请运行: pip install openai")
        except Exception as e:
            logger.error(f"OpenAI Vision API 调用失败: {str(e)}")
            raise
    
    async def _extract_with_doubao(self, image_base64: str, mime_type: str) -> str:
        """使用豆包 Vision API 提取"""
        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {self.doubao_api_key}",
                "Content-Type": "application/json"
            }

            # 豆包使用火山引擎 API 格式
            payload = {
                "model": "doubao-seed-1-8-251228",
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_image",
                                "image_url": f"data:{mime_type};base64,{image_base64}"
                            },
                            {
                                "type": "input_text",
                                "text": IMAGE_EXTRACTION_PROMPT
                            }
                        ]
                    }
                ]
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.doubao_endpoint + "/responses",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

                data = response.json()
                logger.info(f"豆包 API 原始响应: {data}")

                # 豆包返回格式处理 - 尝试多种可能格式
                try:
                    # 格式1: 新版推理格式 (包含 reasoning 和 message)
                    # 结构: [{"type": "reasoning", ...}, {"type": "message", "content": [...]}]
                    if isinstance(data, list):
                        # 尝试在新版推理格式中提取文字
                        text = self._extract_text_from_doubao_content(data)
                        if text:
                            return text
                        return ""

                    # 格式2: output.choices[0].message.content (旧版格式)
                    if "output" in data and "choices" in data["output"]:
                        message_content = data["output"]["choices"][0]["message"].get("content")
                        text = self._extract_text_from_doubao_content(message_content)
                        if text:
                            return text
                        return "" if not isinstance(message_content, str) else message_content
                    # 格式3: output.text
                    elif "output" in data and "text" in data["output"]:
                        return data["output"]["text"]
                    # 格式4: 直接返回 content 字段
                    elif "content" in data:
                        text = self._extract_text_from_doubao_content(data["content"])
                        if text:
                            return text
                        return "" if not isinstance(data["content"], str) else data["content"]
                    # 格式5: 直接返回 output
                    elif "output" in data:
                        output_data = data["output"]
                        text = self._extract_text_from_doubao_content(output_data)
                        if text:
                            return text
                        if isinstance(output_data, dict) and "content" in output_data:
                            return output_data["content"] if isinstance(output_data["content"], str) else ""
                        return "" if not isinstance(output_data, str) else output_data
                    # 格式6: 未知格式，返回空字符串而不是原始结构
                    else:
                        return ""
                except Exception as parse_error:
                    logger.error(f"解析豆包响应失败: {parse_error}, 响应数据: {data}")
                    return ""

        except ImportError:
            raise ImportError("httpx 库未安装，请运行: pip install httpx")
        except Exception as e:
            logger.error(f"豆包 Vision API 调用失败: {str(e)}")
            raise

    def _extract_text_from_doubao_content(self, content) -> str:
        """从豆包多层 content/reasoning 结构中递归抽取文本，避免直接输出结构体。"""
        texts: List[str] = []

        def walk(node):
            if node is None:
                return
            if isinstance(node, str):
                stripped = node.strip()
                if stripped:
                    texts.append(stripped)
                return
            if isinstance(node, list):
                for item in node:
                    walk(item)
                return
            if isinstance(node, dict):
                # 常见字段: text / content / summary
                if isinstance(node.get("text"), str):
                    t = node.get("text", "").strip()
                    if t:
                        texts.append(t)
                if "summary" in node:
                    walk(node["summary"])
                if "content" in node:
                    walk(node["content"])
                return

        walk(content)
        return "\n".join(texts).strip()

    def _extract_text_from_nested_list(self, data) -> str:
        """兼容旧的递归提取函数，内部复用统一的解析逻辑。"""
        return self._extract_text_from_doubao_content(data)

    def _sanitize_description(self, description: str) -> str:
        """去除模型返回中的提示性前缀语句与 Markdown 头标记，只保留结论性内容。"""
        lines = description.splitlines()
        cleaned: List[str] = []
        for line in lines:
            raw = line.strip()
            if not raw:
                continue
            # 过滤常见的自述/任务说明句子
            if re.search(r"(我现在要|按照用户要求|按照要求|现在整理|现在检查)", raw):
                continue
            # 去掉 Markdown 标题前缀 #
            raw = raw.lstrip("#").strip()
            cleaned.append(raw)
        result = "\n".join(cleaned).strip()
        return result if result else description.strip()
    
    def _parse_elements(self, description: str) -> Dict[str, Any]:
        """
        从描述中解析结构化元素
        这是一个简单实现，可以后续用 LLM 优化
        """
        elements = {
            "components": [],
            "relationships": [],
            "labels": [],
            "image_type": "未知"
        }
        
        # 简单的关键词提取
        description_lower = description.lower()
        
        # 判断图片类型
        if "架构" in description or "architecture" in description_lower:
            elements["image_type"] = "架构图"
        elif "流程" in description or "flow" in description_lower:
            elements["image_type"] = "流程图"
        elif "数据" in description or "chart" in description_lower or "graph" in description_lower:
            elements["image_type"] = "数据图表"
        elif "示意" in description or "diagram" in description_lower:
            elements["image_type"] = "示意图"
        
        # 这里可以添加更复杂的解析逻辑
        # 或者调用 LLM 进行结构化提取
        
        return elements


# 全局实例
image_extractor = ImageExtractor()

