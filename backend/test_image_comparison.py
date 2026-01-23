"""
图片对比功能测试脚本
使用方法：
1. 准备测试文件：architecture.png（或其它图片）、document.docx
   位置：项目根目录 (D:\VsCodeP\factguardian-main\)
2. 运行：python test_image_comparison.py
"""
import requests
import json
import os
import sys

BASE_URL = "http://localhost:8000"

def check_service():
    """检查服务是否运行"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def main():
    print("=" * 70)
    print("图片对比功能测试")
    print("=" * 70)
    
    # 检查服务
    if not check_service():
        print("\n[错误] 无法连接服务")
        print("  请确保服务已启动：docker-compose up -d")
        sys.exit(1)
    
    print("\n[OK] 服务连接正常")
    
    # 检查文件
    image_files = ['architecture.png', 'diagram.png', 'flowchart.png', 'system.png']
    image_file = None
    for img in image_files:
        if os.path.exists(img):
            image_file = img
            break
    
    current_dir = os.getcwd()
    
    if not image_file:
        print(f"\n[错误] 未找到图片文件")
        print(f"  当前目录: {current_dir}")
        print("\n  请准备以下文件之一（放在项目根目录）：")
        print("  - architecture.png")
        print("  - diagram.png")
        print("  - flowchart.png")
        print("  - system.png")
        print("  或其他 PNG/JPG 格式图片")
        sys.exit(1)
    
    if not os.path.exists('document.docx'):
        print(f"\n[错误] 未找到文档文件")
        print(f"  当前目录: {current_dir}")
        print("\n  请准备：document.docx（描述图片的文档）")
        sys.exit(1)
    
    print(f"\n[OK] 文件已找到：")
    print(f"  - {image_file}（图片）")
    print(f"  - document.docx（文档）")
    
    # 步骤 1：提取图片内容
    print("\n" + "-" * 70)
    print("步骤 1：提取图片内容")
    print("-" * 70)
    
    try:
        files = {'file': open(image_file, 'rb')}
        response = requests.post(f"{BASE_URL}/api/extract-from-image", files=files, timeout=120)
        response.raise_for_status()
        image_result = response.json()
        files['file'].close()
        
        print(f"[OK] 图片提取成功！")
        print(f"  文件名：{image_result['filename']}")
        print(f"  图片格式：{image_result['image_format']}")
        print(f"  图片尺寸：{image_result['image_size']}")
        print(f"  文件大小：{image_result['file_size_bytes'] / 1024:.2f} KB")
        print(f"  图片类型：{image_result['extracted_elements']['image_type']}")
        print(f"\n  图片描述预览：")
        print("-" * 70)
        desc = image_result['description']
        if len(desc) > 300:
            print(desc[:300] + "...")
        else:
            print(desc)
        
    except requests.exceptions.RequestException as e:
        print(f"[错误] 图片提取失败：{e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"  错误详情：{json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                print(f"  错误详情：{e.response.text}")
        sys.exit(1)
    
    # 步骤 2：上传文档
    print("\n" + "-" * 70)
    print("步骤 2：上传文档")
    print("-" * 70)
    
    try:
        files = {'file': open('document.docx', 'rb')}
        response = requests.post(f"{BASE_URL}/api/upload", files=files, timeout=60)
        response.raise_for_status()
        doc_result = response.json()
        files['file'].close()
        
        doc_id = doc_result['document_id']
        print(f"[OK] 文档上传成功！")
        print(f"  文档ID：{doc_id}")
        print(f"  文件名：{doc_result['filename']}")
        print(f"  章节数：{doc_result['section_count']}")
        print(f"  字数：{doc_result['word_count']}")
        
    except requests.exceptions.RequestException as e:
        print(f"[错误] 文档上传失败：{e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"  错误详情：{json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                print(f"  错误详情：{e.response.text}")
        sys.exit(1)
    
    # 步骤 3：图片-文本对比
    print("\n" + "-" * 70)
    print("步骤 3：执行图片-文本对比")
    print("-" * 70)
    
    try:
        files = {'file': open(image_file, 'rb')}
        data = {'document_id': doc_id}
        
        print(f"  对比中...")
        response = requests.post(
            f"{BASE_URL}/api/compare-image-text",
            files=files,
            data=data,
            timeout=300  # 5 分钟超时
        )
        response.raise_for_status()
        comparison_result = response.json()
        files['file'].close()

        print(f"[OK] 对比完成！")

        # 根据返回的 mode 判断处理类型
        mode = comparison_result.get('mode', 'unknown')
        print(f"  Mode: {mode}")

        if mode == 'extraction_only':
            # 纯图片提取模式
            print(f"\n  Image info:")
            print(f"    Filename: {comparison_result.get('filename', 'N/A')}")
            print(f"    Format: {comparison_result.get('image_format', 'N/A')}")
            print(f"    Size: {comparison_result.get('image_size', 'N/A')}")
            print(f"  Description preview:")
            desc = comparison_result.get('description', '')
            if len(desc) > 500:
                print(f"    {desc[:500]}...")
            else:
                print(f"    {desc}")
        elif mode == 'comparison':
            # 图片-文本对比模式
            print(f"\n统计信息：")
            stats = comparison_result.get('statistics', {})
            print(f"  对比章节数：{stats.get('total_sections_compared', 0)}")
            print(f"  一致章节数：{stats.get('consistent_sections', 0)}")
            print(f"  不一致章节数：{stats.get('inconsistent_sections', 0)}")
            print(f"  平均一致性分数：{stats.get('average_consistency_score', 'N/A')}")
            print(f"  缺失元素数：{stats.get('total_missing_elements', 0)}")
            print(f"  矛盾点数：{stats.get('total_contradictions', 0)}")

            # 显示图片信息
            image_info = comparison_result.get('image_info', {})
            print(f"\n图片信息：")
            print(f"  文件名：{image_info.get('filename', 'N/A')}")
            print(f"  图片类型：{image_info.get('image_type', 'N/A')}")

            # 显示每个章节的对比详情
            comparisons = comparison_result.get('comparisons', [])
            if comparisons:
                print(f"\n详细对比结果：")
                print("-" * 70)
                for idx, comparison in enumerate(comparisons, 1):
                    section_title = comparison.get('section_title', f'章节 #{idx}')
                    is_consistent = comparison.get('is_consistent', False)
                    consistency_score = comparison.get('consistency_score', 0)

                    status = "[一致]" if is_consistent else "[不一致]"
                    print(f"\n章节 #{idx}：{section_title}")
                    print(f"  状态：{status}")
                    print(f"  一致性分数：{consistency_score}")

                    # 显示缺失元素
                    missing = comparison.get('missing_elements', [])
                    if missing:
                        print(f"  缺失元素 ({len(missing)} 个)：")
                        for elem in missing[:5]:
                            print(f"    - {elem}")
                        if len(missing) > 5:
                            print(f"    ... 还有 {len(missing) - 5} 个")

                    # 显示矛盾点
                    contradictions = comparison.get('contradictions', [])
                    if contradictions:
                        print(f"  矛盾点 ({len(contradictions)} 个)：")
                        for contra in contradictions[:5]:
                            print(f"    - {contra}")
                        if len(contradictions) > 5:
                            print(f"    ... 还有 {len(contradictions) - 5} 个")

                    # 显示建议
                    suggestions = comparison.get('suggestions', [])
                    if suggestions:
                        print(f"  改进建议 ({len(suggestions)} 条)：")
                        for sugg in suggestions[:3]:
                            print(f"    - {sugg}")
        else:
            print(f"\n  未知模式：{mode}")
            print(f"  可用字段：{list(comparison_result.keys())}")
        
    except requests.exceptions.RequestException as e:
        print(f"[错误] 对比失败：{e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"  错误详情：{json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                print(f"  错误详情：{e.response.text}")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)

if __name__ == "__main__":
    main()
