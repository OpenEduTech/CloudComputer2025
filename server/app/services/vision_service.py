"""
PatPat-Inconsistency-Hunter 视觉模型服务
使用 InternVL 视觉大模型将图片/图表转换为文字描述
"""

import asyncio
import os
import re
import aiohttp
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor

from ..config import settings
from ..utils.logger import logger


class VisionService:
    """
    视觉模型服务
    
    负责将图片转换为文字描述，支持本地 InternVL 模型
    """
    
    def __init__(
        self,
        model_root: str = "./models",
        model_name: str = "InternVL3_5-4B-HF",
        max_concurrency: int = 2,
        use_local_model: bool = True,
    ):
        """
        初始化视觉服务
        
        Args:
            model_root: 模型根目录
            model_name: 模型名称
            max_concurrency: 最大并发处理数
            use_local_model: 是否使用本地模型
        """
        self._model_root = model_root
        self._model_name = model_name
        self._max_concurrency = max_concurrency
        self._use_local_model = use_local_model
        self._executor = ThreadPoolExecutor(max_workers=max_concurrency)
        self._model = None
        self._model_lock = asyncio.Lock()
        
    async def _ensure_model_loaded(self):
        """确保模型已加载（懒加载）"""
        if not self._use_local_model:
            return
            
        async with self._model_lock:
            if self._model is None:
                try:
                    # 在线程池中加载模型避免阻塞
                    loop = asyncio.get_event_loop()
                    self._model = await loop.run_in_executor(
                        self._executor,
                        self._load_model
                    )
                    logger.info(f"视觉模型 {self._model_name} 加载完成")
                except Exception as e:
                    logger.error(f"视觉模型加载失败: {e}")
                    self._use_local_model = False
                    raise
    
    def _load_model(self):
        """同步加载模型"""
        try:
            import torch
            import sys
            
            # 添加项目根目录到路径
            project_root = Path(__file__).parent.parent.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            from LocalInternVL import LocalInternVL
            
            # 确定模型路径
            model_path = Path(self._model_root) / self._model_name
            if not model_path.exists():
                # 尝试项目根目录
                model_path = project_root / self._model_root / self._model_name
            
            if not model_path.exists():
                raise FileNotFoundError(f"模型目录不存在: {model_path}")
            
            # 检测是否有 CUDA GPU 可用
            use_gpu = torch.cuda.is_available()
            logger.info(f"CUDA 可用: {use_gpu}, 设备数: {torch.cuda.device_count() if use_gpu else 0}")
            
            if use_gpu:
                # GPU 模式
                model = LocalInternVL(
                    model_root=str(model_path.parent),
                    model_name=model_path.name,
                    dtype=torch.bfloat16,
                    device_map="auto",
                    load_in_8bit=False,
                    use_flash_attn=True,
                )
            else:
                # CPU 模式（较慢但能运行）
                logger.warning("未检测到 GPU，将使用 CPU 模式运行视觉模型（速度较慢）")
                model = LocalInternVL(
                    model_root=str(model_path.parent),
                    model_name=model_path.name,
                    dtype=torch.float32,  # CPU 不支持 bfloat16
                    device_map=None,
                    device="cpu",
                    load_in_8bit=False,
                    use_flash_attn=False,  # CPU 不支持 flash attention
                )
            
            return model
            
        except ImportError as e:
            logger.warning(f"无法导入视觉模型依赖: {e}")
            raise
        except Exception as e:
            logger.error(f"加载视觉模型时出错: {e}")
            raise
    
    async def extract_image_description(
        self,
        image_path: str,
        context: str = "",
        max_words: int = 200,
    ) -> str:
        """
        从图片中提取文字描述
        
        Args:
            image_path: 图片路径
            context: 上下文信息（可选，帮助理解图片内容）
            max_words: 最大描述字数
            
        Returns:
            图片的文字描述
        """
        if not os.path.exists(image_path):
            logger.warning(f"图片文件不存在: {image_path}")
            return f"[图片: 文件不存在]"
        
        try:
            await self._ensure_model_loaded()
            
            if self._model is None:
                # 模型未加载成功，返回简单描述
                return self._get_fallback_description(image_path)
            
            loop = asyncio.get_event_loop()
            description = await loop.run_in_executor(
                self._executor,
                self._extract_sync,
                image_path,
                context,
                max_words,
            )
            
            return description
            
        except Exception as e:
            logger.error(f"图片描述提取失败 {image_path}: {e}")
            return self._get_fallback_description(image_path)
    
    def _extract_sync(
        self,
        image_path: str,
        context: str,
        max_words: int,
    ) -> str:
        """同步提取图片描述"""
        try:
            import torch
            
            # 加载图片
            pixel_values = self._model.load_image(image_path, max_num=6)
            
            # 构建提示词
            if context:
                prompt = f"""<image>
请详细描述这张图片的内容，包括：
1. 如果是图表，提取其中的所有数据、标签、标题
2. 如果是表格，提取表格结构和所有单元格内容
3. 如果是流程图或示意图，描述其结构和各部分含义
4. 如果是普通图片，描述图中的关键信息

上下文信息：{context}

请用中文描述，控制在{max_words}字以内，确保信息完整准确。"""
            else:
                prompt = f"""<image>
请详细描述这张图片的内容：
1. 如果是图表，提取所有数据、标签、标题、趋势
2. 如果是表格，提取完整的表格结构和内容
3. 如果是示意图，描述结构和关系
4. 关注图中的数字、日期、名称等关键信息

请用中文描述，控制在{max_words}字以内。"""
            
            # 调用模型
            response = self._model.chat(
                question=prompt,
                pixel_values=pixel_values,
                return_history=False,
            )
            
            # 处理返回值（可能是元组）
            if isinstance(response, tuple):
                description = response[0]
            else:
                description = response
            
            return description.strip()
            
        except Exception as e:
            logger.error(f"模型推理失败: {e}")
            return self._get_fallback_description(image_path)
    
    def _get_fallback_description(self, image_path: str) -> str:
        """获取备用描述"""
        filename = os.path.basename(image_path)
        return f"[图片: {filename}]"
    
    async def batch_extract_descriptions(
        self,
        images: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None,
    ) -> List[Dict[str, str]]:
        """
        批量提取图片描述
        
        Args:
            images: 图片信息列表，每项包含 image_id, image_path, context
            progress_callback: 进度回调
            
        Returns:
            描述结果列表，每项包含 image_id, description
        """
        if not self._use_local_model:
            logger.info("视觉模型未启用，返回默认描述")
            return [{
                "image_id": img.get("image_id", ""),
                "description": f"[图片: {img.get('context', '图片')}]",
                "source_path": img.get("image_path", ""),
            } for img in images]
        
        results = []
        total = len(images)
        
        logger.info(f"开始批量提取 {total} 张图片的描述...")
        
        # 使用信号量限制并发
        semaphore = asyncio.Semaphore(self._max_concurrency)
        
        async def process_single(img_info: Dict[str, Any], index: int) -> Dict[str, str]:
            async with semaphore:
                image_id = img_info.get("image_id", "")
                image_path = img_info.get("image_path", "")
                logger.info(f"处理图片 {index+1}/{total}: {image_id} ({image_path})")
                
                description = await self.extract_image_description(
                    image_path=image_path,
                    context=img_info.get("context", ""),
                )
                
                logger.info(f"图片 {image_id} 描述提取完成: {description[:50]}...")
                
                if progress_callback:
                    await progress_callback((index + 1) / total * 100)
                
                return {
                    "image_id": image_id,
                    "description": description,
                    "source_path": image_path,
                }
        
        tasks = [process_single(img, i) for i, img in enumerate(images)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤异常
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"处理图片 {images[i].get('image_id')} 失败: {result}", exc_info=True)
                valid_results.append({
                    "image_id": images[i].get("image_id", ""),
                    "description": self._get_fallback_description(images[i].get("image_path", "")),
                    "source_path": images[i].get("image_path", ""),
                })
            else:
                valid_results.append(result)
        
        logger.info(f"批量提取完成，成功处理 {len(valid_results)} 张图片")
        return valid_results
    
    async def close(self):
        """关闭服务，释放资源"""
        self._executor.shutdown(wait=False)
        if self._model is not None:
            # 清理模型
            self._model = None
            try:
                import torch
                torch.cuda.empty_cache()
            except:
                pass


# 全局视觉服务实例
_vision_service: Optional[VisionService] = None


def get_vision_service() -> VisionService:
    """获取视觉服务单例"""
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService(
            model_root=getattr(settings, 'VISION_MODEL_ROOT', './models'),
            model_name=getattr(settings, 'VISION_MODEL_NAME', 'InternVL3_5-4B-HF'),
            max_concurrency=2,
            use_local_model=getattr(settings, 'USE_VISION_MODEL', True),
        )
    return _vision_service


async def close_vision_service():
    """关闭视觉服务"""
    global _vision_service
    if _vision_service is not None:
        await _vision_service.close()
        _vision_service = None

