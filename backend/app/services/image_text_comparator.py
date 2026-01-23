"""
图文对比服务
对比文档描述与图片内容的一致性
"""
import json
import logging
from typing import Dict, Any, List, Optional

from .image_extractor import image_extractor
from .llm_client import llm_client
from .redis_client import redis_client

logger = logging.getLogger(__name__)

# 图文对比 Prompt
IMAGE_TEXT_COMPARISON = """图片描述（由 AI 提取）：
{image_description}

文档相关段落：
{document_text}

请作为一名专业的"图文一致性审核专家"进行分析。你的任务是判断**文档内容是否准确反映了图片的逻辑架构和核心信息**。

请遵循以下评审原则：
1. **区分"核心逻辑"与"视觉细节"**：
   - 如果图片与文档在**逻辑架构、数据流向、核心组件**上不一致，这是严重错误（矛盾点）。
   - 如果文档仅忽略了图片的**装饰性元素**（如具体的像素尺寸、线条颜色、非核心的布局位置），且这不影响对架构的理解，这属于"可以接受的简略"，**不应**视为严重缺失或矛盾。
2. **矛盾点判定**：仅当文档明确描述的内容与图片展示的内容直接冲突时（例如：图片是垂直分层，文档说是水平排列；图片是A指向B，文档说是B指向A），才标记为矛盾。
3. **遗漏元素判定**：仅列出那些对理解架构至关重要的遗漏信息（如核心模块缺失、关键步骤缺失）。无关紧要的视觉细节（如"未提及红色箭头"）除非造成理解歧义，否则不应列入。

请以 JSON 格式返回：
{{
    "is_consistent": true,  // 只要核心逻辑一致，即可为 true
    "consistency_score": 85, // 基于核心逻辑的一致性打分
    "missing_elements": ["文档未提及的关键核心组件"], // 仅包含关键信息
    "contradictions": ["逻辑或事实层面的严重冲突"], // 仅包含实质性冲突
    "suggestions": ["针对核心内容的改进建议"]
}}
"""


class ImageTextComparator:
    """图文对比服务"""
    
    def __init__(self):
        self.image_extractor = image_extractor
        self.llm_client = llm_client
        self.redis_client = redis_client
    
    async def compare_image_with_document(
        self,
        image_content: bytes,
        image_filename: str,
        document_id: str,
        relevant_sections: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        对比图片与文档的一致性
        
        Args:
            image_content: 图片二进制内容
            image_filename: 图片文件名
            document_id: 文档ID
            relevant_sections: 相关章节索引列表（None 表示所有章节）
        
        Returns:
            对比结果
        """
        # 1. 提取图片内容
        logger.info(f"开始提取图片内容: {image_filename}")
        image_info = await self.image_extractor.extract_from_image(
            image_content, image_filename
        )
        image_description = image_info['description']
        
        logger.info(f"图片内容提取完成，描述长度: {len(image_description)} 字符")
        
        # 2. 获取文档内容
        doc_data = self.redis_client.get_document_metadata(document_id)
        if not doc_data:
            raise ValueError(f"文档 {document_id} 不存在")
        
        sections = doc_data.get('sections', [])
        if not sections:
            raise ValueError(f"文档 {document_id} 没有章节内容")
        
        # 如果指定了相关章节，只对比这些章节
        if relevant_sections:
            sections = [sections[i] for i in relevant_sections if 0 <= i < len(sections)]
        
        if not sections:
            raise ValueError("没有找到有效的章节进行对比")
        
        logger.info(f"开始对比图片与文档: {document_id}, 共 {len(sections)} 个章节")
        
        # 3. 对比每个相关章节
        comparisons = []
        for idx, section in enumerate(sections):
            section_text = section.get('content', '')
            if not section_text or len(section_text.strip()) < 50:
                continue
            
            try:
                comparison_result = await self._compare_section_with_image(
                    section_text, image_description, section.get('title', '')
                )
                
                if comparison_result:
                    comparisons.append({
                        'section_title': section.get('title', ''),
                        'section_index': idx,
                        'section_content_preview': section_text[:200],
                        **comparison_result
                    })
            except Exception as e:
                logger.warning(f"章节 {idx} 对比失败: {str(e)}")
                continue
        
        logger.info(f"对比完成: 共 {len(comparisons)} 个章节完成对比")
        
        # 4. 汇总统计
        total_sections = len(comparisons)
        consistent_sections = sum(1 for c in comparisons if c.get('is_consistent', False))
        inconsistent_sections = total_sections - consistent_sections
        
        avg_score = 0
        if total_sections > 0:
            scores = [c.get('consistency_score', 0) for c in comparisons]
            avg_score = sum(scores) / len(scores) if scores else 0
        
        # 统计缺失元素和矛盾
        all_missing = []
        all_contradictions = []
        for c in comparisons:
            all_missing.extend(c.get('missing_elements', []))
            all_contradictions.extend(c.get('contradictions', []))
        
        return {
            'image_info': {
                'filename': image_filename,
                'description': image_description,
                'extracted_elements': image_info.get('extracted_elements', {}),
                'image_type': image_info.get('extracted_elements', {}).get('image_type', '未知')
            },
            'document_id': document_id,
            'document_filename': doc_data.get('filename', 'unknown'),
            'comparisons': comparisons,
            'statistics': {
                'total_sections_compared': total_sections,
                'consistent_sections': consistent_sections,
                'inconsistent_sections': inconsistent_sections,
                'average_consistency_score': round(avg_score, 2),
                'total_missing_elements': len(set(all_missing)),
                'total_contradictions': len(set(all_contradictions))
            }
        }
    
    async def _compare_section_with_image(
        self,
        section_text: str,
        image_description: str,
        section_title: str
    ) -> Optional[Dict[str, Any]]:
        """对比单个章节与图片"""
        prompt = IMAGE_TEXT_COMPARISON.format(
            image_description=image_description[:3000],  # 限制长度
            document_text=section_text[:2000]
        )
        
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的图文一致性分析专家。请准确判断文档描述是否与图片内容一致，并指出具体的遗漏或矛盾之处。必须返回有效的 JSON 格式。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = await self.llm_client.chat(messages, temperature=0.2, max_tokens=2048)
            
            # 解析 JSON 响应
            response = response.strip()
            
            # 移除可能的 markdown 代码块
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            # 尝试提取 JSON（可能包含在文本中）
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                response = response[start_idx:end_idx+1]
            
            result = json.loads(response)
            
            # 验证必需字段
            if 'is_consistent' not in result or 'consistency_score' not in result:
                logger.warning("LLM 返回结果缺少必需字段")
                return None
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析对比结果 JSON 失败: {e}, 原始响应: {response[:200]}")
            return None
        except Exception as e:
            logger.error(f"图文对比失败: {str(e)}")
            return None


# 全局实例
image_text_comparator = ImageTextComparator()

