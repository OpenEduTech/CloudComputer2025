"""
导出服务：将AI分析结果导出为Markdown格式
"""
from typing import Dict, List, Optional, Any


class ExportService:
    """导出服务"""
    
    def export_summary_markdown(
        self,
        doc_info: Dict[str, Any],
        global_analysis: Optional[Dict[str, Any]] = None,
        page_count: int = 0,
        analyzed_pages: int = 0
    ) -> str:
        """
        导出分析摘要为Markdown格式
        
        Args:
            doc_info: 文档信息字典，包含 file_name, file_type, created_at, updated_at
            global_analysis: 全局分析结果
            page_count: 文档总页数
            analyzed_pages: 已分析页数
            
        Returns:
            Markdown格式的字符串
        """
        lines = []
        
        lines.append(f"# {doc_info.get('file_name', '未知文档')} - AI分析摘要")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        lines.append("## 📄 文档信息")
        lines.append("")
        lines.append(f"- **文件名**: {doc_info.get('file_name', '未知')}")
        lines.append(f"- **文件类型**: {doc_info.get('file_type', 'unknown')}")
        lines.append(f"- **总页数**: {page_count}")
        lines.append(f"- **已分析页数**: {analyzed_pages}")
        if doc_info.get('created_at'):
            lines.append(f"- **创建时间**: {doc_info['created_at']}")
        if doc_info.get('updated_at'):
            lines.append(f"- **更新时间**: {doc_info['updated_at']}")
        lines.append("")
        
        if global_analysis:
            lines.append("## 📚 全局分析摘要")
            lines.append("")
            
            # 主题
            main_topic = global_analysis.get('main_topic', '未知')
            if main_topic and main_topic != '未知':
                lines.append(f"### 核心主题")
                lines.append("")
                lines.append(f"{main_topic}")
                lines.append("")
            
            # 知识流程
            knowledge_flow = global_analysis.get('knowledge_flow', '')
            if knowledge_flow:
                lines.append(f"### 知识逻辑流程")
                lines.append("")
                lines.append(f"{knowledge_flow}")
                lines.append("")
            
            # 章节结构
            chapters = global_analysis.get('chapters', [])
            if chapters:
                lines.append("### 章节结构")
                lines.append("")
                for i, chapter in enumerate(chapters, 1):
                    title = chapter.get('title', f'章节{i}')
                    pages = chapter.get('pages', [])
                    key_concepts = chapter.get('key_concepts', [])
                    
                    lines.append(f"#### {i}. {title}")
                    if pages:
                        lines.append(f"- **页码**: {', '.join(map(str, pages))}")
                    if key_concepts:
                        lines.append(f"- **核心概念**: {', '.join(key_concepts)}")
                    lines.append("")
            
            # 知识点单元统计
            knowledge_units = global_analysis.get('knowledge_units', [])
            if knowledge_units:
                lines.append("### 知识点单元统计")
                lines.append("")
                lines.append(f"共识别出 **{len(knowledge_units)}** 个知识点单元：")
                lines.append("")
                for unit in knowledge_units:
                    title = unit.get('title', '未知知识点')
                    pages = unit.get('pages', [])
                    core_concepts = unit.get('core_concepts', [])
                    
                    lines.append(f"- **{title}**")
                    if pages:
                        lines.append(f"  - 涉及页面: {', '.join(map(str, pages))}")
                    if core_concepts:
                        lines.append(f"  - 核心概念: {', '.join(core_concepts)}")
                    lines.append("")
        else:
            lines.append("## ⚠️ 全局分析")
            lines.append("")
            lines.append("该文档尚未进行全局分析。")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("*本文档由 PPTAS AI 分析系统自动生成*")
        
        return "\n".join(lines)
    
    def export_to_markdown(
        self,
        doc_info: Dict[str, Any],
        global_analysis: Optional[Dict[str, Any]] = None,
        page_analyses: Optional[Dict[int, Dict[str, Any]]] = None,
        include_global: bool = True,
        include_pages: bool = True,
        page_range: Optional[List[int]] = None
    ) -> str:
        """
        导出完整分析内容为Markdown格式
        
        Args:
            doc_info: 文档信息字典
            global_analysis: 全局分析结果
            page_analyses: 页面分析结果字典，key为page_id，value为分析数据
            include_global: 是否包含全局分析
            include_pages: 是否包含页面分析
            page_range: 页面范围（None表示全部）
            
        Returns:
            Markdown格式的字符串
        """
        lines = []
    
        lines.append(f"# {doc_info.get('file_name', '未知文档')} - AI分析补充内容")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        lines.append("## 📄 文档信息")
        lines.append("")
        lines.append(f"- **文件名**: {doc_info.get('file_name', '未知')}")
        lines.append(f"- **文件类型**: {doc_info.get('file_type', 'unknown')}")
        if doc_info.get('created_at'):
            lines.append(f"- **创建时间**: {doc_info['created_at']}")
        if doc_info.get('updated_at'):
            lines.append(f"- **更新时间**: {doc_info['updated_at']}")
        if page_range:
            lines.append(f"- **导出页面范围**: {', '.join(map(str, sorted(page_range)))}")
        lines.append("")
        
        # 全局分析
        if include_global and global_analysis:
            lines.append("## 📚 全局分析")
            lines.append("")
            
            main_topic = global_analysis.get('main_topic', '未知')
            if main_topic and main_topic != '未知':
                lines.append(f"### 核心主题")
                lines.append("")
                lines.append(f"**{main_topic}**")
                lines.append("")
            
            knowledge_flow = global_analysis.get('knowledge_flow', '')
            if knowledge_flow:
                lines.append(f"### 知识逻辑流程")
                lines.append("")
                lines.append(f"{knowledge_flow}")
                lines.append("")

            chapters = global_analysis.get('chapters', [])
            if chapters:
                lines.append("### 章节结构")
                lines.append("")
                for i, chapter in enumerate(chapters, 1):
                    title = chapter.get('title', f'章节{i}')
                    pages = chapter.get('pages', [])
                    key_concepts = chapter.get('key_concepts', [])
                    
                    lines.append(f"#### {i}. {title}")
                    if pages:
                        lines.append(f"- **页码**: {', '.join(map(str, pages))}")
                    if key_concepts:
                        lines.append(f"- **核心概念**: {', '.join(key_concepts)}")
                    lines.append("")

            knowledge_units = global_analysis.get('knowledge_units', [])
            if knowledge_units:
                lines.append("### 知识点单元")
                lines.append("")
                for unit in knowledge_units:
                    title = unit.get('title', '未知知识点')
                    pages = unit.get('pages', [])
                    core_concepts = unit.get('core_concepts', [])
                    
                    lines.append(f"#### {title}")
                    if pages:
                        lines.append(f"- **涉及页面**: {', '.join(map(str, pages))}")
                    if core_concepts:
                        lines.append(f"- **核心概念**: {', '.join(core_concepts)}")
                    lines.append("")
            
            lines.append("---")
            lines.append("")
        
        # 页面分析
        if include_pages and page_analyses:
            lines.append("## 📑 页面详细分析")
            lines.append("")

            sorted_pages = sorted(page_analyses.keys())
            
            for page_id in sorted_pages:
                analysis = page_analyses[page_id]
                lines.append(f"### 第 {page_id} 页")
                lines.append("")

                knowledge_clusters = analysis.get('knowledge_clusters', [])
                if knowledge_clusters:
                    lines.append("#### 🔍 难点概念识别")
                    lines.append("")
                    for cluster in knowledge_clusters:
                        concept = cluster.get('concept', '未知概念')
                        explanation = cluster.get('explanation', '')
                        lines.append(f"- **{concept}**")
                        if explanation:
                            lines.append(f"  {explanation}")
                        lines.append("")
 
                structure_notes = analysis.get('structure_notes', '')
                if structure_notes:
                    lines.append("#### 📐 结构理解")
                    lines.append("")
                    lines.append(structure_notes)
                    lines.append("")
   
                gaps = analysis.get('gaps', [])
                if gaps:
                    lines.append("#### ⚠️ 知识缺口")
                    lines.append("")
                    for gap in gaps:
                        gap_type = gap.get('type', '未知类型')
                        description = gap.get('description', '')
                        lines.append(f"- **{gap_type}**: {description}")
                    lines.append("")
                
                understanding_notes = analysis.get('understanding_notes', '')
                if understanding_notes:
                    lines.append("#### 📝 理解笔记")
                    lines.append("")
                    lines.append(understanding_notes)
                    lines.append("")

                deep_analysis = analysis.get('deep_analysis', '')
                if deep_analysis:
                    lines.append("#### 🧠 深度分析")
                    lines.append("")
                    lines.append(deep_analysis)
                    lines.append("")
                
                lines.append("---")
                lines.append("")
        
        lines.append("*本文档由 PPTAS AI 分析系统自动生成*")
        
        return "\n".join(lines)
