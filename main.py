from layers.perception_layer import perception_layer, parse_file_raw, parse_multiple_files_raw
from layers.planning_layer import planning_layer
from layers.decision_layer import batch_grade_all_questions
from layers.memory_layer import record_mistakes
from layers.reflection_layer import reflection_layer
import os
import shlex
import traceback  # 新增：打印详细异常堆栈
import whisper    # 新增：备用音频解析逻辑（用于调试）


def debug_audio_parse(file_path):
    """
    调试用：手动解析音频文件，返回文本和详细日志
    """
    try:
        print("  [调试] 尝试手动解析音频文件...")
        # 强制指定Whisper缓存路径（适配Docker）
        os.environ['WHISPER_CACHE'] = '/app/.cache/whisper'
        model = whisper.load_model('small', download_root='/app/.cache/whisper')
        print("  [调试] Whisper small模型加载成功")
        
        # 解析音频
        result = model.transcribe(file_path, language='zh')
        text = result['text'].strip()
        print(f"  [调试] 音频解析结果（前200字符）：{text[:200]}")
        print(f"  [调试] 音频解析文本长度：{len(text)} 字符")
        return True, text
    except Exception as e:
        print(f"  [调试] 音频解析失败：{type(e).__name__}: {str(e)}")
        return False, ""


def main():
    print("=" * 60)
    print("智能出题与评分系统 v2.4（调试增强版）")
    print("  感知层 → 规划层 → 决策层 → 记忆层（错题追踪）")
    print("=" * 60)
    user_id = input("请输入您的学号/ID（用于错题追踪）：").strip() or "anonymous"

    # --- 感知层 ---
    file_path = input("\n请输入教材文件路径：").strip().strip("\"'")
    if not os.path.exists(file_path):
        print("❌ 文件不存在")
        print(f"  [调试] 检查路径：{file_path}")
        print(f"  [调试] 容器内当前目录：{os.getcwd()}")
        print(f"  [调试] 容器内/app/data目录文件：{os.listdir('/app/data') if os.path.exists('/app/data') else '不存在'}")
        return

    print("\n[1/4] 运行感知层...")
    # 新增：捕获感知层的所有异常，并打印详细信息
    try:
        success, _, result_json = perception_layer(file_path)
    except Exception as e:
        print(f"❌ 感知层执行抛出异常：{type(e).__name__}: {str(e)}")
        print(f"❌ 异常堆栈：\n{traceback.format_exc()}")
        
        # 针对音频文件，尝试手动解析（调试）
        if file_path.lower().endswith(('.mp3', '.wav', '.flac', '.m4a')):
            print("\n📌 检测到音频文件，尝试手动解析...")
            audio_success, audio_text = debug_audio_parse(file_path)
            if audio_success and audio_text:
                print("⚠️  手动解析音频成功，但感知层内部逻辑失败！")
                print("   请检查perception_layer.py中音频处理后的考点提取逻辑")
            else:
                print("❌ 手动解析音频也失败，确认音频文件/Whisper模型是否正常")
        return

    # 新增：感知层返回结果的详细调试日志
    print(f"  [调试] 感知层success：{success}")
    print(f"  [调试] 感知层result_json：{result_json if isinstance(result_json, dict) else '非字典类型'}")
    
    # 调整判断逻辑：更宽松，且打印具体原因
    exam_points = result_json.get("exam_points", {}) if isinstance(result_json, dict) else {}
    all_points = exam_points.get("all_points", [])
    if not success:
        print("❌ 感知层失败：perception_layer返回success=False")
        return
    if not all_points:
        print("❌ 感知层失败：未提取到任何考点（all_points为空）")
        # 针对音频文件，补充提示
        if file_path.lower().endswith(('.mp3', '.wav', '.flac', '.m4a')):
            print("📌 可能原因：")
            print("   1. 音频解析后的文本无有效考点关键词")
            print("   2. 感知层的考点提取逻辑未适配音频文本格式")
            print("   3. 意图对齐阈值过高（可放宽perception_layer中的判断）")
        return

    print(f"✅ 感知层成功：提取到 {len(all_points)} 个考点")
    raw_text = parse_file_raw(file_path)
    print(f"  [调试] 原始文本长度：{len(raw_text)} 字符")

    # --- 规划层 ---
    print("\n[2/4] 运行规划层...")
    try:
        planning_result = planning_layer(all_points, raw_text, interactive=True)
    except Exception as e:
        print(f"❌ 规划层执行失败：{type(e).__name__}: {str(e)}")
        print(f"❌ 异常堆栈：\n{traceback.format_exc()}")
        return
    
    if not planning_result:
        print("❌ 规划层返回空结果")
        return

    print("\n" + "="*60)
    print("✅ 题目生成完成（无答案）")
    print("="*60)
    print(planning_result["questions_raw"])

    # 修正：保存路径适配Docker（保存到/app/generated，对应宿主机./generated）
    save_path = "/app/generated/generated_questions.txt" if os.path.exists("/app/generated") else "generated_questions.txt"
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(planning_result["questions_raw"])
        print(f"📝 题目已保存至 {save_path}")
    except Exception as e:
        print(f"⚠️  题目保存失败：{e}")
        print("   仍继续后续流程...")

    # --- 决策层：多文件作答 ---
    print("\n[3/4] 请提交作答文件（支持 PDF/DOCX/TXT/图片，可多文件）")
    print("❗ 重要提示：")
    print("   - 请在作答中明确标注题号（如：题目1：...）")
    print("   - 多文件请用空格分隔路径，带空格的路径请加英文引号")
    print("   - Docker环境下路径需以/app/data开头（对应宿主机./data）")
    answer_input = input("作答文件路径：").strip()

    answer_file_paths = shlex.split(answer_input) if answer_input else []
    if not answer_file_paths:
        print("❌ 未提供作答文件")
        return

    # 验证作答文件是否存在
    valid_answer_paths = []
    for path in answer_file_paths:
        if os.path.exists(path):
            valid_answer_paths.append(path)
        else:
            print(f"⚠️  作答文件不存在：{path}，已跳过")
    
    if not valid_answer_paths:
        print("❌ 无有效作答文件")
        return

    print(f"[4/4] 正在解析 {len(valid_answer_paths)} 个作答文件...")
    try:
        full_answer_text = parse_multiple_files_raw(valid_answer_paths)
    except Exception as e:
        print(f"❌ 作答文件解析失败：{type(e).__name__}: {str(e)}")
        print(f"❌ 异常堆栈：\n{traceback.format_exc()}")
        return

    if not full_answer_text.strip():
        print("❌ 所有作答文件解析失败或内容为空")
        print(f"  [调试] 解析后的文本：{full_answer_text}")
        return

    # 批改
    try:
        grading_report = batch_grade_all_questions(
            structured_questions=planning_result["structured_questions"],
            full_answer_text=full_answer_text
        )
    except Exception as e:
        print(f"❌ 批改失败：{type(e).__name__}: {str(e)}")
        print(f"❌ 异常堆栈：\n{traceback.format_exc()}")
        return

    # 检查批改是否成功
    if "error" in grading_report:
        print(f"❌ 批改失败：{grading_report['error']}")
        return

    # ✅ 关键：先确认成功，再调用记忆层
    try:
        record_result = record_mistakes(
            user_id=user_id,
            grading_results=grading_report["results"],
            structured_questions=planning_result["structured_questions"]
        )
        print(f"✅ 记忆层：{record_result['status']}，记录 {record_result['mistake_count']} 道错题")
    except Exception as e:
        print(f"⚠️  记忆层执行警告：{e}")
        print("   仍继续输出评分报告...")

    # 输出报告
    print("\n" + "="*60)
    print("🎯 最终评分汇总")
    print("="*60)
    total_score = grading_report["total_score"]
    max_total = grading_report["max_total"]
    for item in grading_report["results"]:
        print(f"题目{item['question_index']}: {item['score']}/{item['max_score']} 分 | {item['feedback']}")
    print(f"\n总分：{total_score} / {max_total}")
    
    # 反思层
    try:
        reflection = reflection_layer(user_id)
        print("\n" + "="*60)
        print("🧠 个性化学习建议（基于历史错题）")
        print("="*60)
        print(reflection["remedial_report"])
    except Exception as e:
        print(f"⚠️  反思层执行警告：{e}")
    
    print(f"\n💡 您的错题已记录（ID: {user_id}），可用于后续个性化复习建议。")


if __name__ == "__main__":
    # 全局异常捕获：防止程序崩溃
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断程序执行")
    except Exception as e:
        print(f"\n❌ 程序意外崩溃：{type(e).__name__}: {str(e)}")
        print(f"❌ 完整异常堆栈：\n{traceback.format_exc()}")