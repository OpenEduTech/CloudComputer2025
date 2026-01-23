# -*- coding: utf-8 -*-
import requests
import json
import time
import os
import sys

BASE_URL = "http://127.0.0.1:8000"

# ANSI 颜色代码（Windows 终端支持）
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_header(text):
    """打印加粗的标题"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

def print_step(step_num, text):
    """打印步骤信息"""
    print(f"{Colors.BOLD}{Colors.BLUE}[步骤 {step_num}] {text}{Colors.RESET}")

def print_success(text):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    """打印错误信息"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def test_image_extraction(file_path):
    print_header(f"FactGuardian 图片内容提取测试")
    print(f"测试文件: {Colors.CYAN}{file_path}{Colors.RESET}\n")

    if not os.path.exists(file_path):
        print_error(f"文件不存在: {file_path}")
        return

    print_step(1, "提取图片内容")
    try:
        files = {'file': (os.path.basename(file_path), open(file_path, 'rb'))}
        response = requests.post(f"{BASE_URL}/api/extract-from-image", files=files, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            print_success("图片内容提取成功！")
            desc = result.get('description', '')
            analysis = result.get('analysis', '')
            print(f"  说明: {desc[:200]}..." if len(desc) > 200 else f"  说明: {desc}")
            print(f"  详细分析: {analysis[:200]}..." if len(analysis) > 200 else f"  详细分析: {analysis}")
        else:
            print_error(f"图片提取失败: {response.text}")
    except Exception as e:
        print_error(f"图片提取测试出错: {str(e)}")

def test_text_pipeline(file_path):
    print_header(f"FactGuardian 文档自动化测试")
    print(f"测试文件: {Colors.CYAN}{file_path}{Colors.RESET}\n")
    
    # 1. 检查文件是否存在
    if not os.path.exists(file_path):
        print_error(f"文件不存在: {file_path}")
        return

    # 2. 上传文档
    print_step(1, "上传文档")
    files = {'file': (os.path.basename(file_path), open(file_path, 'rb'), 'text/plain')}
    response = requests.post(f"{BASE_URL}/api/upload", files=files)
    if response.status_code != 200:
        print_error(f"上传失败: {response.text}")
        return
    
    data = response.json()
    doc_id = data.get("document_id")
    print_success(f"文档上传成功！文档ID: {Colors.BOLD}{doc_id}{Colors.RESET}")
    
    # 3. 提取事实
    print_step(2, "提取关键事实")
    response = requests.post(f"{BASE_URL}/api/documents/{doc_id}/extract-facts")
    if response.status_code != 200:
        print_error(f"事实提取失败: {response.text}")
        return
    facts_data = response.json()
    total_facts = facts_data.get('total_facts', 0)
    print_success(f"成功提取 {Colors.BOLD}{total_facts}{Colors.RESET} 条事实")
    
    # 显示提取的事实列表
    if total_facts > 0:
        print(f"\n{Colors.BOLD}提取的事实列表:{Colors.RESET}")
        facts_list = facts_data.get('facts', [])
        for i, fact in enumerate(facts_list, 1):
            fact_type = fact.get('type', '未知')
            content = fact.get('content', '')
            print(f"  {i}. [{fact_type}] {content}")

    # 4. 验证事实
    print_step(3, "溯源验证（联网查证）")
    response = requests.post(f"{BASE_URL}/api/documents/{doc_id}/verify-facts?only_errors=true")
    
    if response.status_code != 200:
        print_error(f"验证失败: {response.text}")
        return

    verify_data = response.json()
    results = verify_data.get("verifications", [])
    statistics = verify_data.get("statistics", {})
    print_success(f"验证完成！")
    
    # 5. 生成详细报告
    print_header("事实验证报告")
    
    #显示统计摘要
    print(f"  {Colors.GREEN}✓ 验证通过: {statistics.get('supported', 0)}{Colors.RESET}")
    print(f"  {Colors.RED}✗ 验证失败: {statistics.get('unsupported', 0)}{Colors.RESET}")
    print(f"  {Colors.YELLOW}⊙ 跳过验证: {statistics.get('skipped', 0)}{Colors.RESET} (内部数据)")
    
    # 只显示验证失败的事实
    if len(results) > 0:
        print(f"{Colors.BOLD}发现 {len(results)} 条需要修正的事实：{Colors.RESET}\n")
        
        for idx, res in enumerate(results, 1):
            confidence = res.get('confidence_level', 'Unknown')
            original_fact = res.get('original_fact', {})
            content = original_fact.get('content', '')
            fact_type = original_fact.get('type', '未知')
            fact_index = res.get('fact_index', idx)
            
            # 置信度颜色
            if confidence == "High":
                conf_color = Colors.RED
            elif confidence == "Medium":
                conf_color = Colors.YELLOW
            else:
                conf_color = Colors.RED
            
            print(f"{Colors.BOLD}【错误 {idx}】原事实 #{fact_index}{Colors.RESET}")
            print(f"  类型: {fact_type}")
            print(f"  内容: {content}")
            print(f"  状态: {Colors.RED}✗ 错误{Colors.RESET}")
            print(f"  置信度: {conf_color}{confidence}{Colors.RESET}")
            
            correction = res.get('correction', 'N/A')
            assessment = res.get('assessment', '')
            
            if correction and correction != 'N/A' and correction.strip():
                print(f"  {Colors.YELLOW}建议修正:{Colors.RESET} {correction}")
            print(f"  {Colors.YELLOW}原因分析:{Colors.RESET} {assessment}")
            print()
    else:
        print(f"{Colors.GREEN}所有可验证事实均通过验证！{Colors.RESET}\n")
    
    # 6. 内部冲突检测
    print_step(4, "内部冲突检测（不依赖搜索）")
    conflict_resp = requests.post(f"{BASE_URL}/api/detect-conflicts/{doc_id}")
    if conflict_resp.status_code != 200:
        print_error(f"冲突检测失败: {conflict_resp.text}")
        return

    conflict_data = conflict_resp.json()
    conflicts = conflict_data.get("conflicts", [])
    repetitions = conflict_data.get("repetitions", [])
    conflicts_found = conflict_data.get("conflicts_found", len(conflicts))
    print_success(f"冲突检测完成！发现 {conflicts_found} 个冲突，{len(repetitions)} 个重复片段\n")

    print_header("冲突检测报告")
    if not conflicts:
        print(f"  {Colors.GREEN}未发现内部冲突{Colors.RESET}\n")
    else:
        for idx, c in enumerate(conflicts, 1):
            severity = c.get("severity", "中")
            conflict_type = c.get("conflict_type", "未知")
            explanation = c.get("explanation", "")
            fact_a = c.get("fact_a", {})
            fact_b = c.get("fact_b", {})

            sev_color = Colors.YELLOW if severity == "中" else (Colors.RED if severity == "高" else Colors.GREEN)

            print(f"{Colors.BOLD}【冲突 {idx}】{Colors.RESET}")
            print(f"  冲突类型: {conflict_type}")
            print(f"  严重程度: {sev_color}{severity}{Colors.RESET}")
            print(f"  说明: {explanation}")
            print(f"  事实A: [{fact_a.get('type', '未知')}] {fact_a.get('content', '')}")
            print(f"    位置: {fact_a.get('location', '')}")
            print(f"  事实B: [{fact_b.get('type', '未知')}] {fact_b.get('content', '')}")
            print(f"    位置: {fact_b.get('location', '')}\n")
            
    # 7. 重复内容检测 (独立模块)
    print_step(5, "重复核心内容检测")
    if not repetitions:
        print(f"  {Colors.GREEN}未发现高频重复核心内容{Colors.RESET}\n")
    else:
        for idx, rep in enumerate(repetitions, 1):
            # 重复内容结构在 conflict_detector.py 中被定义为了冲突格式 (fact_a=source, fact_b=stats)
            # 我们需要适配这个格式进行展示，或者后端直接传回原始结构。
            # 查看后端代码，_detect_repetitions 返回的是冲突对象格式
            
            content = rep.get("fact_a", {}).get("content", "")
            count_info = rep.get("fact_b", {}).get("content", "")
            explanation = rep.get("explanation", "")
            
            print(f"{Colors.BOLD}【重复片段 {idx}】{Colors.RESET}")
            print(f"  {Colors.YELLOW}核心文本:{Colors.RESET} {content}")
            print(f"  {Colors.RED}统计信息:{Colors.RESET} {count_info}")
            print(f"  详细说明: {explanation}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_auto.py <文件名> [模式]")
        print("模式: none(默认), image-compare(图文对比), ref-compare(参考对比)")
        sys.exit(1)

    target_file = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "auto"
        
    ext = os.path.splitext(target_file)[1].lower()
    
    if mode == "image-compare":
        # 必须同时提供文本和图片，这里假设第二个参数是图片
        if len(sys.argv) < 4:
             print("错误: 图文对比模式需要提供第二个参数（图片路径）")
             print("用法: python test_auto.py <文档路径> image-compare <图片路径>")
        else:
            image_path = sys.argv[3]
            from test_auto import test_text_pipeline # 确保能调用
            # 这里我们需要稍微修改一下逻辑，不仅仅是运行 pipeline，还要在中间插手
            print_header(f"FactGuardian 图文一致性对比测试")
            target_doc_id = None
            
            # 1. 先上传文档拿到 ID
            print_step(1, "上传文档")
            if not os.path.exists(target_file):
                 print_error(f"文档不存在: {target_file}")
                 sys.exit(1)
            files = {'file': (os.path.basename(target_file), open(target_file, 'rb'), 'text/plain')}
            response = requests.post(f"{BASE_URL}/api/upload", files=files)
            if response.status_code == 200:
                target_doc_id = response.json().get("document_id")
                print_success(f"文档上传成功！ID: {target_doc_id}")
            else:
                 print_error(f"文档上传失败: {response.text}")
                 sys.exit(1)

            # 2. 执行对比
            print_step(2, "图文一致性对比")
            if os.path.exists(image_path):
                try:
                    files = {'file': open(image_path, 'rb')}
                    data = {'document_id': target_doc_id}
                    print(f"正在对比图片 {image_path} 与文档...")
                    response = requests.post(f"{BASE_URL}/api/compare-image-text", files=files, data=data, timeout=300)
                    if response.status_code == 200:
                       result = response.json()
                       print_success("图文对比成功！")
                       stats = result.get('statistics', {})
                       print(f"  一致章节数: {stats.get('consistent_sections', 0)}")
                       print(f"  不一致章节数: {stats.get('inconsistent_sections', 0)}")
                       print(f"  平均一致性分数: {stats.get('average_consistency_score', 'N/A')}")
                       
                       # 显示详细结果
                       details = result.get('comparison_results', [])
                       for det in details:
                           sect = det.get('section_title', '未知章节')
                           score = det.get('consistency_score', 0)
                           issues = det.get('inconsistencies', [])
                           print(f"\n  [章节] {sect} (一致性: {score}%)")
                           if issues:
                               for issue in issues:
                                   print(f"    - {issue}")
                    else:
                        print_warning(f"图文对比请求失败: {response.text}")
                except Exception as e:
                    print_error(f"图文对比测试出错: {str(e)}")
            else:
                 print_error(f"图片不存在: {image_path}")

    elif mode == "ref-compare":
         # 参考文档对比模式
         if len(sys.argv) < 4:
             print("错误: 参考对比模式需要提供第二个参数（参考文档路径）")
             print("用法: python test_auto.py <主文档路径> ref-compare <参考文档路径>")
         else:
             ref_path = sys.argv[3]
             print_header(f"FactGuardian 参考文档对比测试")
             
             if not os.path.exists(target_file) or not os.path.exists(ref_path):
                 print_error("主文档或参考文档不存在")
                 sys.exit(1)

             try:
                print_step(1, "多文档上传")
                files = [
                    ('main_doc', (os.path.basename(target_file), open(target_file, 'rb'), 'text/plain')),
                    ('ref_docs', (os.path.basename(ref_path), open(ref_path, 'rb'), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')) # 简单起见假设 docx
                ]
                # 注意：如果 ref_docs 是 txt，mimetype 要改
                
                response = requests.post(f"{BASE_URL}/api/upload-multiple", files=files)
                if response.status_code == 200:
                    upload_data = response.json()
                    main_id = upload_data['main_document_id']
                    ref_ids = upload_data['reference_document_ids']
                    print_success(f"上传成功 (主ID: {main_id}, 参考数: {len(ref_ids)})")
                    
                    print_step(2, "执行对比")
                    comp_data = {
                        "main_doc_id": main_id,
                        "ref_doc_ids": ref_ids,
                        "similarity_threshold": 0.3
                    }
                    response = requests.post(f"{BASE_URL}/api/compare-references", json=comp_data, timeout=300)
                    if response.status_code == 200:
                        comp_result = response.json()
                        print_success("对比完成！")
                        stats = comp_result.get('statistics', {})
                        print(f"  总对比次数: {stats.get('total_comparisons', 0)}")
                        print(f"  相似章节数: {stats.get('similar_sections_found', 0)}")
                        
                        comparisons = comp_result.get('comparisons', [])
                        if comparisons:
                            print(f"\n{Colors.BOLD}详细对比结果:{Colors.RESET}")
                            for comp in comparisons:
                                sim_score = comp.get('similarity_score', 0)
                                if sim_score > 0: # 只显示有相似度的
                                    print(f"  - (相似度 {sim_score}%) {comp.get('similarity_type', '未知')}")
                                    print(f"    主文档段落: {comp.get('main_text', '')[:50]}...")
                                    print(f"    参考文档段落: {comp.get('reference_text', '')[:50]}...")
                    else:
                        print_warning(f"对比请求失败: {response.text}")
                else:
                    print_warning(f"上传失败: {response.text}")
             except Exception as e:
                 print_error(f"测试出错: {str(e)}")

    elif ext in ['.png', '.jpg', '.jpeg', '.webp']:
        test_image_extraction(target_file)
    else:
        test_text_pipeline(target_file)
