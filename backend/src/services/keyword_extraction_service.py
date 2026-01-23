"""关键词提取服务"""

import re
from typing import List, Dict, Any, Optional
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json

from ..agents.base import LLMConfig


class KeywordExtractionService:
    """从PPT内容中提取有意义的中文名词短语"""
    
    def __init__(self, llm_config: LLMConfig):
        self.llm = llm_config.create_llm(temperature=0.5)
        self.llm_config = llm_config
    
    def extract_keywords(self, content: str, title: str = "", num_keywords: int = 5, raw_points: List[dict] = None) -> List[str]:
        """从内容中提取关键词
        
        Args:
            content: 页面内容
            title: 页面标题
            num_keywords: 要提取的关键词数量
            raw_points: 原始数据点列表
        
        Returns:
            关键词列表
        """
        # 如果 content 为空，尝试从 raw_points 构建内容
        if not content or not content.strip():
            if raw_points and len(raw_points) > 0:
                # 从raw_points中提取所有文本
                points_text = []
                for point in raw_points:
                    if isinstance(point, dict):
                        if point.get('type') == 'text' and point.get('text'):
                            points_text.append(point.get('text', ''))
                        elif point.get('type') == 'table' and point.get('data'):
                            table_rows = point.get('data', [])
                            for row in table_rows:
                                if isinstance(row, list):
                                    points_text.extend([str(cell) for cell in row if cell])
                    else:
                        points_text.append(str(point))
                
                if points_text:
                    content = "页面内容：" + " | ".join(points_text[:10]) 
                    print(f"   📝 从raw_points构建内容: {content[:100]}")
            
            # 如果还是没有content，用标题
            if not content or not content.strip():
                if title and title.strip() and title != "1":  
                    content = f"页面标题: {title}"
                else:
                    return []
        
        max_content_length = 2000
        content = content[:max_content_length]
        
        template = """你是一个内容关键词提取专家。从PPT页面的实际内容中提取最重要的概念和信息。

页面标题: {title}

页面内容:
{content}

提取任务：
1. 阅读页面的实际内容（通常是结构化的信息点）
2. 提取{num_keywords}个最重要的**有实际意义的名词短语**
3. 提取指导：
   - ⭐ 直接从内容中提取**具体的概念、主题、人名、技术名称、产品名**等
   - ⭐ 例如：如果页面讲"新兴技术与数据安全"，提取"新兴技术"、"数据安全"
   - ⭐ 例如：如果页面有讲师名字，直接提取讲师名字
   - ⭐ 例如：如果有列表，提取**列表项的核心概念**，而不是"列表"本身
   - ⭐ 提取的应该是用户**真正关心的主题和内容**
   - ⭐ 避免提取那些**格式或标签**（如"讲次"、"邮箱"、"标题"等修饰词）
4. 每个关键词长度不少于2个字符
5. 避免纯英文、纯数字或纯符号
6. 关键词应该来自页面内容，不应该是形式描述

返回格式：JSON数组，例如:
["新兴技术", "数据安全", "高巾捷"]

严格要求: 只返回JSON数组。提取的每个关键词都是页面讨论的**实际主题和内容**。"""
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "title": title or "未知",
                "content": content,
                "num_keywords": num_keywords
            })
            
            response_text = response.content.strip()
            print(f"📝 LLM原始响应: {response_text[:100]}")
            
            # 提取JSON数组
            keywords = self._parse_keywords_response(response_text, num_keywords)
            
            print(f"🔍 解析后关键词: {keywords}")
            
            # 验证和清理关键词
            validated_keywords = self._validate_keywords(keywords)
            
            print(f"✅ 验证后关键词: {validated_keywords}")
            
            # 如果验证后没有关键词，返回原始解析的关键词（宽松模式）
            if not validated_keywords and keywords:
                print(f"⚠️  验证过于严格，使用原始关键词")
                validated_keywords = keywords[:num_keywords]
            
            # 确保返回指定数量的关键词
            return validated_keywords[:num_keywords]
            
        except Exception as e:
            print(f"❌ 关键词提取失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_keywords_response(self, response_text: str, num_keywords: int) -> List[str]:
        """从LLM响应中解析关键词"""
        try:
            # 尝试直接解析JSON
            if "[" in response_text and "]" in response_text:
                # 提取JSON数组部分
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                json_str = response_text[start:end]
                print(f"  📦 提取JSON: {json_str}")
                keywords = json.loads(json_str)
                
                if isinstance(keywords, list):
                    result = [str(k).strip() for k in keywords if k]
                    print(f"  ✅ JSON解析成功: {len(result)}个关键词")
                    return result
        except json.JSONDecodeError as e:
            print(f"  ⚠️ JSON解析失败: {e}")
        except Exception as e:
            print(f"  ⚠️ JSON提取异常: {e}")
        
        # 如果JSON解析失败，尝试行分割
        print(f"  🔄 尝试行分割解析...")
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        keywords = []
        for line in lines:
            # 移除列表标记 (- 或数字.)
            line = re.sub(r'^[-\d.]\s*', '', line).strip()
            # 移除引号
            line = line.strip('"\'')
            # 移除括号内的内容
            line = re.sub(r'\([^)]*\)', '', line).strip()
            if line and len(line) >= 2:
                keywords.append(line)
        
        print(f"  ✅ 行分割解析成功: {len(keywords)}个关键词")
        return keywords
    
    def _validate_keywords(self, keywords: List[str]) -> List[str]:
        """验证关键词，确保符合要求"""
        validated = []
        
        # 格式标签和修饰词黑名单 - 只过滤那些格式化标记，不过滤实际内容
        form_labels = {
            '讲次', '讲', '第', '标题', '说明', '备注', '邮箱', '网址', '电话',
            '作者', '出版', '来源', '链接', '参考', '附注', '脚注', '注释',
            '附件', '图片', '图表', '视频', '音频', '资源'
        }
        
        for keyword in keywords:
            if not keyword:
                continue
            
            keyword = keyword.strip()
            
            # 检查长度（至少2个字符）
            if len(keyword) < 2:
                continue
            
            # 检查是否为格式标签词汇（严格限定）
            if keyword in form_labels:
                print(f"  ❌ 过滤格式标签: {keyword}")
                continue
            
            # 检查是否为纯英文（严格模式）
            if self._is_pure_english(keyword):
                print(f"  ❌ 过滤纯英文: {keyword}")
                continue
            
            # 检查是否为纯数字
            if self._is_pure_number(keyword):
                print(f"  ❌ 过滤纯数字: {keyword}")
                continue
            
            # 检查是否为纯符号
            if self._is_pure_symbol(keyword):
                print(f"  ❌ 过滤纯符号: {keyword}")
                continue
            
            # 至少要包含一个中文字符（不强制，如果没有可能是英文短语和中文混合）
            has_chinese = self._has_chinese_char(keyword)
            if not has_chinese:
                # 允许包含数字和符号的组合，但严格过滤纯英文
                # 例如允许 "CNN网络" "2D打印" 但不允许 "CNN" "animation"
                pure_alpha_count = sum(1 for c in keyword if c.isalpha())
                total_count = len(keyword.replace(' ', ''))
                
                # 如果超过80%是字母，则认为是纯英文，过滤掉
                if total_count > 0 and pure_alpha_count > total_count * 0.8:
                    print(f"  ❌ 过滤纯英文词组: {keyword}")
                    continue
            
            print(f"  ✅ 保留关键词: {keyword}")
            validated.append(keyword)
        
        return validated
    
    @staticmethod
    def _is_pure_english(text: str) -> bool:
        """检查是否为纯英文"""
        return all(c.isascii() and c.isalpha() for c in text.replace(' ', '').replace('-', '').replace('_', ''))
    
    @staticmethod
    def _is_pure_number(text: str) -> bool:
        """检查是否为纯数字"""
        return all(c.isdigit() or c in '.,- ' for c in text)
    
    @staticmethod
    def _is_pure_symbol(text: str) -> bool:
        """检查是否为纯符号"""
        symbols = set('!@#$%^&*()[]{},.;:?/<>\\|~`\'"')
        return all(c in symbols or c.isspace() for c in text)
    
    @staticmethod
    def _has_chinese_char(text: str) -> bool:
        """检查是否包含中文字符"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符范围
                return True
        return False
    
    def extract_keywords_from_clusters(self, knowledge_clusters: List[Dict]) -> List[str]:
        """从知识聚类中提取关键词
        
        Args:
            knowledge_clusters: 知识聚类列表（通常来自AI分析）
        
        Returns:
            关键词列表
        """
        keywords = []
        
        for cluster in knowledge_clusters[:5]:  # 最多取前5个
            if isinstance(cluster, dict):
                concept = cluster.get("concept", "")
            else:
                concept = str(cluster)
            
            if concept and len(concept) >= 3:
                concept = concept.strip()
                if self._has_chinese_char(concept):
                    keywords.append(concept)
        
        return keywords
