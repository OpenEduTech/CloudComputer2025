"""
导出服务
支持导出为Markdown和PDF格式
"""

from typing import Dict, List
from pathlib import Path
import logging
import re
import os

logger = logging.getLogger(__name__)

# reportlab 为可选依赖：没有它也应该允许服务启动（仅 PDF 导出不可用）
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    REPORTLAB_AVAILABLE = True
except Exception as e:
    REPORTLAB_AVAILABLE = False
    _REPORTLAB_IMPORT_ERROR = e


class ExportService:
    """
    导出服务类
    支持将扩展内容导出为Markdown和PDF格式
    """
    
    def __init__(self):
        """初始化导出服务"""
        # 如果 reportlab 不可用，只启用 Markdown 导出
        if REPORTLAB_AVAILABLE:
            self._register_chinese_fonts()
        else:
            self.chinese_font_name = "Helvetica"
            logger.warning(
                f"reportlab 未安装/不可用，PDF 导出将不可用: {str(_REPORTLAB_IMPORT_ERROR)}"
            )
        logger.info("导出服务初始化完成")
    
    def _register_chinese_fonts(self):
        """注册中文字体"""
        try:
            # 尝试注册常见的中文字体
            # 如果系统没有这些字体，会使用默认字体
            font_paths = [
                # Windows常见路径
                "C:/Windows/Fonts/simsun.ttc",  # 宋体
                "C:/Windows/Fonts/simhei.ttf",  # 黑体
                "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
                # macOS常见路径
                "/System/Library/Fonts/STSong.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
                # Linux常见路径
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
            
            chinese_font_name = "ChineseFont"
            registered = False
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        if font_path.endswith('.ttc'):
                            # TTC文件需要指定字体索引
                            pdfmetrics.registerFont(TTFont(chinese_font_name, font_path, subfontIndex=0))
                        else:
                            pdfmetrics.registerFont(TTFont(chinese_font_name, font_path))
                        registered = True
                        logger.info(f"中文字体注册成功: {font_path}")
                        break
                    except Exception as e:
                        logger.warning(f"字体注册失败 {font_path}: {str(e)}")
                        continue
            
            if not registered:
                logger.warning("未找到中文字体，PDF中文显示可能异常")
                # 使用DejaVu Sans作为备选（支持基本UTF-8）
                chinese_font_name = "Helvetica"
            
            self.chinese_font_name = chinese_font_name
            
        except Exception as e:
            logger.error(f"字体初始化失败: {str(e)}")
            self.chinese_font_name = "Helvetica"
    
    def export_to_markdown(self, ppt_data: Dict, expanded_data: Dict, page_number: int = None) -> str:
        """
        导出为Markdown格式
        
        Args:
            ppt_data: PPT原始数据
            expanded_data: 扩展后的数据
            page_number: 指定导出的页码，None表示导出全部
            
        Returns:
            Markdown格式的字符串
        """
        try:
            md_content = []
            
            md_content.append(f"# {ppt_data.get('metadata', {}).get('file_name', 'PPT扩展内容')}\n\n")
            
            slides_to_export = ppt_data.get('slides', [])
            
            if page_number is not None:
                slides_to_export = [s for s in slides_to_export if s.get('page_number') == page_number]
            
            for slide in slides_to_export:
                page_num = slide.get('page_number', 0)
                title = slide.get('title', f'第{page_num}页')
                
                md_content.append(f"## {title}\n\n")
                
                for text_box in slide.get('text_boxes', []):
                    text = text_box.get('text', '')
                    if text:
                        md_content.append(f"### {text}\n\n")
                        
                        slide_key = f"slide_{page_num}_box_{text_box.get('id', '')}"
                        expanded_content = expanded_data.get(slide_key, {})
                        
                        if expanded_content:
                            if expanded_content.get('background'):
                                md_content.append(f"**背景说明**\n\n{expanded_content['background']}\n\n")
                            
                            if expanded_content.get('principles'):
                                md_content.append(f"**原理阐述**\n\n{expanded_content['principles']}\n\n")
                            
                            if expanded_content.get('formulas'):
                                md_content.append(f"**公式推导**\n\n{expanded_content['formulas']}\n\n")
                            
                            if expanded_content.get('examples'):
                                md_content.append(f"**代码示例**\n\n```python\n{expanded_content['examples']}\n```\n\n")
                            
                            if expanded_content.get('summary'):
                                md_content.append(f"**要点总结**\n\n{expanded_content['summary']}\n\n")
                            
                            if expanded_content.get('references'):
                                md_content.append("**参考资料**\n\n")
                                for ref in expanded_content['references']:
                                    md_content.append(f"- [{ref.get('title', '')}]({ref.get('url', '')})\n")
                                md_content.append("\n")
                
                md_content.append("---\n\n")
            
            return ''.join(md_content)
            
        except Exception as e:
            logger.error(f"导出Markdown失败: {str(e)}")
            raise
    
    def export_to_pdf(self, markdown_content: str, output_path: str) -> str:
        """
        将Markdown转换为PDF
        
        Args:
            markdown_content: Markdown内容
            output_path: 输出文件路径
            
        Returns:
            PDF文件路径
        """
        try:
            if not REPORTLAB_AVAILABLE:
                raise ImportError(
                    "PDF 导出依赖 reportlab 未安装。请在当前环境安装 reportlab，或使用 Docker 运行。"
                )

            doc = SimpleDocTemplate(output_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            lines = markdown_content.split('\n')
            in_code_block = False
            code_lines = []
            
            for line in lines:
                if line.strip().startswith('```'):
                    if in_code_block:
                        in_code_block = False
                        code_text = '\n'.join(code_lines)
                        code_style = ParagraphStyle(
                            'Code',
                            parent=styles['Code'],
                            fontName='Courier',  # 代码使用Courier等宽字体
                            fontSize=9,
                            leading=12,
                            leftIndent=20,
                            backColor=colors.lightgrey,
                            borderPadding=10
                        )
                        # 转义HTML特殊字符
                        code_text = code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(code_text, code_style))
                        code_lines = []
                    else:
                        in_code_block = True
                        code_lines = []
                    continue
                
                if in_code_block:
                    code_lines.append(line)
                    continue
                
                if line.strip():
                    if line.startswith('# '):
                        h1_style = ParagraphStyle(
                            'CustomH1',
                            parent=styles['Heading1'],
                            fontName=self.chinese_font_name,
                            fontSize=18,
                            textColor='#2c3e50',
                            spaceAfter=12,
                            spaceBefore=12
                        )
                        text = line[2:].strip()
                        # 转义HTML特殊字符
                        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(text, h1_style))
                    elif line.startswith('## '):
                        h2_style = ParagraphStyle(
                            'CustomH2',
                            parent=styles['Heading2'],
                            fontName=self.chinese_font_name,
                            fontSize=14,
                            textColor='#34495e',
                            spaceAfter=10,
                            spaceBefore=10
                        )
                        text = line[3:].strip()
                        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(text, h2_style))
                    elif line.startswith('### '):
                        h3_style = ParagraphStyle(
                            'CustomH3',
                            parent=styles['Heading3'],
                            fontName=self.chinese_font_name,
                            fontSize=12,
                            textColor='#7f8c8d',
                            spaceAfter=8,
                            spaceBefore=8
                        )
                        text = line[4:].strip()
                        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(text, h3_style))
                    elif line.startswith('---'):
                        story.append(Spacer(1, 0.2 * inch))
                    elif line.startswith('**') and line.endswith('**'):
                        bold_style = ParagraphStyle(
                            'CustomBold',
                            parent=styles['Normal'],
                            fontName=self.chinese_font_name if self.chinese_font_name != 'Helvetica' else 'Helvetica-Bold',
                            fontSize=11
                        )
                        text = line[2:-2].strip()
                        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(f"<b>{text}</b>", bold_style))
                    elif line.startswith('- '):
                        bullet_style = ParagraphStyle(
                            'CustomBullet',
                            parent=styles['Normal'],
                            fontName=self.chinese_font_name,
                            leftIndent=20,
                            bulletIndent=10,
                            fontSize=10
                        )
                        text = line[2:].strip()
                        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(f"• {text}", bullet_style))
                    else:
                        normal_style = ParagraphStyle(
                            'CustomNormal',
                            parent=styles['Normal'],
                            fontName=self.chinese_font_name,
                            fontSize=10,
                            leading=14,
                            alignment=TA_LEFT
                        )
                        # 转义HTML特殊字符
                        escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(escaped_line, normal_style))
            
            doc.build(story)
            
            logger.info(f"PDF导出成功: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"导出PDF失败: {str(e)}")
            raise
    
    def save_markdown(self, markdown_content: str, output_path: str) -> str:
        """
        保存Markdown文件
        
        Args:
            markdown_content: Markdown内容
            output_path: 输出文件路径
            
        Returns:
            文件路径
        """
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Markdown文件保存成功: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"保存Markdown文件失败: {str(e)}")
            raise


export_service = ExportService()
