import pytest
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ppt_parser import PPTParser

@pytest.fixture
def ppt_parser():
    return PPTParser()

@pytest.fixture
def test_data_dir():
    """获取测试数据目录路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "test_data")

def test_parser_initialization(ppt_parser):
    """测试解析器初始化"""
    assert ppt_parser is not None
    assert hasattr(ppt_parser, 'executor')

def test_extract_toc():
    """测试目录提取"""
    from app.ppt_parser import PPTParser
    parser = PPTParser()
    
    # 模拟页面数据
    pages = [
        {"page_num": 1, "title": "INTRODUCTION"},
        {"page_num": 2, "title": "1.1 Background"},
        {"page_num": 3, "title": "Related Work"},
    ]
    
    toc = parser._extract_toc(pages)
    assert len(toc) == 3
    assert toc[0]["page"] == 1
    assert toc[0]["title"] == "INTRODUCTION"
    assert toc[0]["level"] == 1  # 大写标题应该是level 1

def test_determine_title_level():
    """测试标题层级判断"""
    from app.ppt_parser import PPTParser
    parser = PPTParser()
    
    assert parser._determine_title_level("INTRODUCTION") == 1
    assert parser._determine_title_level("1.1 Background") == 2
    assert parser._determine_title_level("Regular Title") == 3