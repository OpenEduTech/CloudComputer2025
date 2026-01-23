import os
import sys
import json
import ssl
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from PyPDF2 import PdfReader
from docx import Document
import whisper
import base64
import dashscope
import httpx  # 添加缺失的导入


# ---------------------- 安全加载配置 ----------------------
load_dotenv()  # 从 .env 加载环境变量

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
if not QWEN_API_KEY:
    raise ValueError(" 请在 .env 文件中设置 QWEN_API_KEY")

QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"

# Whisper 配置（保留完整音频识别配置）
WHISPER_CACHE_DIR = Path(os.environ.get("WHISPER_CACHE", Path.home() / ".cache/whisper"))
DEFAULT_WHISPER_MODEL = "small"
ssl._create_default_https_context = ssl._create_unverified_context

# 初始化Qwen客户端
client = OpenAI(
    api_key=QWEN_API_KEY,
    base_url=QWEN_BASE_URL
)


# ---------------------- 工具函数 ----------------------
def get_cross_platform_desktop_path() -> str:
    if sys.platform == "darwin":
        return os.path.expanduser("~/Desktop")
def validate_file_path(file_path: str) -> bool:
    supported = (".pdf", ".txt", ".docx", ".mp3", ".wav", ".m4a", ".png", ".jpg", ".jpeg", ".bmp")
    file_path = file_path.strip().strip("'\"")
    if os.path.exists(file_path) and file_path.lower().endswith(supported):
        return True
    print(f" 文件无效或格式不支持：{file_path}")
    return False

def select_files_via_cli() -> list:
    desktop = get_cross_platform_desktop_path()
    print(f"\n 当前桌面：{desktop}")
    input_str = input(" 请输入文件路径（支持 PDF/TXT/DOCX/音频，多个路径用空格分隔）：").strip()
    
    # 仅用空格分隔（自动过滤空字符串）
    paths = [p.strip() for p in input_str.split() if p.strip()]
    
    valid_files = []
    for path in paths:
        if validate_file_path(path):
            valid_files.append(path)
        else:
            print(f" 跳过无效文件：{path}")
    
    return valid_files

# ---------------------- 文件解析模块（核心修复+保留所有功能） ----------------------
def parse_pdf_raw(pdf_file_obj) -> str:
    """兼容文件路径和文件对象两种输入"""
    try:
        # 如果是文件路径字符串
        if isinstance(pdf_file_obj, str):
            with open(pdf_file_obj, "rb") as f:
                reader = PdfReader(f)
                return "\n".join(page.extract_text().strip() for page in reader.pages if page.extract_text())
        # 如果是文件对象
        else:
            reader = PdfReader(pdf_file_obj)
            return "\n".join(page.extract_text().strip() for page in reader.pages if page.extract_text())
    except Exception as e:
        return f"PDF解析失败：{str(e)}"

def parse_txt_raw(txt_file_obj) -> str:
    """核心修复：兼容文件路径和文件对象两种输入"""
    try:
        # 如果是文件路径字符串
        if isinstance(txt_file_obj, str):
            with open(txt_file_obj, "r", encoding="utf-8") as f:
                return f.read().strip()
        # 如果是文件对象
        else:
            return txt_file_obj.read().decode("utf-8").strip()
    except Exception as e:
        return f"TXT解析失败：{str(e)}"

def parse_docx_raw(docx_file_obj) -> str:
    """兼容文件路径和文件对象两种输入"""
    try:
        # 如果是文件路径字符串
        if isinstance(docx_file_obj, str):
            doc = Document(docx_file_obj)
            return "\n".join(para.text.strip() for para in doc.paragraphs if para.text.strip())
        # 如果是文件对象
        else:
            doc = Document(docx_file_obj)
            return "\n".join(para.text.strip() for para in doc.paragraphs if para.text.strip())
    except Exception as e:
        return f"DOCX解析失败：{str(e)}"

def parse_audio_raw(audio_file_obj) -> str:
    """完整保留音频识别功能：接收文件对象/路径，使用临时文件处理"""
    import tempfile
    try:
        temp_audio_path = ""
        # 如果是文件路径字符串
        if isinstance(audio_file_obj, str):
            temp_audio_path = audio_file_obj
        # 如果是文件对象
        else:
            # 创建临时文件保存音频内容
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                temp_audio.write(audio_file_obj.read())
                temp_audio_path = temp_audio.name
        
        print(" 正在加载 Whisper 模型（small）...")
        model = whisper.load_model(DEFAULT_WHISPER_MODEL, download_root=WHISPER_CACHE_DIR)
        print(" 开始语音识别...")
        result = model.transcribe(temp_audio_path, language="zh")
        
        # 如果是文件对象创建的临时文件，删除临时文件
        if not isinstance(audio_file_obj, str) and os.path.exists(temp_audio_path):
            os.unlink(temp_audio_path)
        
        return result["text"].strip()
    except Exception as e:
        return f"音频解析失败：{str(e)}"
    
def parse_image_with_qwen_vl(image_file_obj) -> str:
    """兼容文件路径和文件对象两种输入"""
    try:
        image_b64 = ""
        # 如果是文件路径字符串
        if isinstance(image_file_obj, str):
            with open(image_file_obj, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
        # 如果是文件对象
        else:
            image_b64 = base64.b64encode(image_file_obj.read()).decode("utf-8")
        
        # 构造多模态消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": f"data:image/png;base64,{image_b64}"},
                    {"text": "请准确提取图中的所有文字内容，不要解释或总结，直接输出原文。"}
                ]
            }
        ]

        response = dashscope.MultiModalConversation.call(
            api_key=QWEN_API_KEY,  # 复用已有的 QWEN_API_KEY
            model='qwen-vl-plus',
            messages=messages
        )

        if response.status_code == 200:
            return response.output.choices[0].message.content[0]["text"].strip()
        else:
            return f"Qwen-VL 调用失败：{response.code}"
            
    except Exception as e:
        return f"图像解析异常：{str(e)}"

def parse_file_raw(file_obj, filename: str = None) -> str:
    """
    完整保留：支持文件对象和文件路径两种输入，兼容所有格式
    Args:
        file_obj: 文件路径字符串 或 文件对象
        filename: 文件名（用于文件对象判断类型）
    """
    # 如果传入的是路径字符串，兼容原有逻辑
    if isinstance(file_obj, str):
        ext = file_obj.lower()
        if ext.endswith(".pdf"):
            return parse_pdf_raw(file_obj)
        elif ext.endswith(".txt"):
            return parse_txt_raw(file_obj)
        elif ext.endswith(".docx"):
            return parse_docx_raw(file_obj)
        elif ext.endswith((".mp3", ".wav", ".m4a")):
            return parse_audio_raw(file_obj)
        elif ext.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff")):
            return parse_image_with_qwen_vl(file_obj)
        else:
            return "不支持的文件格式"
    
    # 处理文件对象
    if not filename:
        return "无法识别文件类型：未提供文件名"
    
    ext = filename.lower()
    file_obj.seek(0)  # 重置指针到开头
    if ext.endswith(".pdf"):
        return parse_pdf_raw(file_obj)
    elif ext.endswith(".txt"):
        return parse_txt_raw(file_obj)
    elif ext.endswith(".docx"):
        return parse_docx_raw(file_obj)
    elif ext.endswith((".mp3", ".wav", ".m4a")):
        return parse_audio_raw(file_obj)
    elif ext.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff")):
        return parse_image_with_qwen_vl(file_obj)
    else:
        return "不支持的文件格式"

# ---------------------- Qwen API 调用 ----------------------
def call_qwen_api(prompt: str, system_prompt: str) -> str:
    try:
        completion = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1200,
            stream=False
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[错误] Qwen API 调用失败：{e}")
        return ""

# ---------------------- 意图对齐 ----------------------
def intent_alignment(raw_text: str) -> tuple:
    prompt = f"""
请严格按以下格式回复，仅返回三行内容：
1或0
判断理由（100字内）
补充建议（100字内）

文本内容：{raw_text[:800]}
判断标准：
1. Flag=1：包含机器学习/统计知识点（如回归、分类、假设检验等），内容连贯；
2. Flag=0：无有效知识点、乱码、过短或无关。
"""
    response = call_qwen_api(prompt, "你是一个严谨的学术内容审核员。")
    if not response:
        return 0, "API调用失败", "请重试或检查网络"

    lines = response.strip().split("\n")
    flag = int(lines[0]) if lines and lines[0] in ["0", "1"] else 0
    reason = lines[1] if len(lines) > 1 else "未知"
    suggestion = lines[2] if len(lines) > 2 else "无"
    return flag, reason, suggestion

# ---------------------- 考点提取（Qwen） ----------------------
def extract_exam_points_qwen(raw_text: str) -> str:
    prompt = f"""
请从以下文本中提取所有与机器学习或统计学相关的明确知识点，严格按以下规则输出：

原文：{raw_text[:10000]}

要求：
1. 仅提取原文中明确提及的概念、定义、公式、假设、性质、步骤、条件、应用场景等；
2. 每条考点独立一行，以“- ”开头，内容简洁（≤25字）；
3. 禁止编造、总结、推断或添加原文未出现的内容；
4. 不要任何标题、分类（如“必须掌握”）、说明或额外文字；
5. 若无有效考点，返回空字符串。

示例正确格式：
- 主成分回归结合PCA与线性回归
- 多重共线性导致参数估计方差增大
- t检验要求样本来自正态总体
"""
    return call_qwen_api(prompt, "你是严谨的学术助教，只输出原文明确出现的考点，每条以“- ”开头，无任何其他内容。")

# ---------------------- 轻量本地校验 ----------------------
def light_verify(points: str) -> tuple:
    lines = points.strip().split("\n")
    valid_points = [line for line in lines if line.strip().startswith("- ") and len(line.strip()) > 2]
    
    if len(valid_points) >= 1:
        return True, f"共提取 {len(valid_points)} 个考点"
    else:
        return False, "未提取到有效考点（需至少1条以“- ”开头的内容）"

# ---------------------- 结构化 JSON 输出 ----------------------
def format_as_json(exam_points: str, filename: str, reason: str, verify_note: str) -> dict:
    lines = exam_points.strip().split("\n")
    all_points = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            content = stripped[2:].strip()
            if content:
                all_points.append(content)
    
    return {
        "metadata": {
            "filename": filename,
            "intent_reason": reason,
            "verify_note": verify_note
        },
        "exam_points": {
            "all_points": all_points
        }
    }

# ---------------------- 核心流程 ----------------------
def perception_layer(input_data, is_file_object: bool = False) -> tuple:
    """
    完整保留：支持文件对象和文件路径两种输入
    Args:
        input_data: 文件路径字符串 或 文件对象
        is_file_object: 是否为文件对象（True=文件对象，False=文件路径）
    """
    if is_file_object:
        # 处理FastAPI上传的文件对象
        file_obj = input_data
        filename = getattr(file_obj, 'name', 'unknown_file')
        raw_text = parse_file_raw(file_obj, filename)
    else:
        # 兼容原有文件路径逻辑
        file_path = input_data
        raw_text = parse_file_raw(file_path)
        filename = os.path.basename(file_path)

    if "解析失败" in raw_text or "不支持" in raw_text:
        return False, raw_text, {}

    print(f"\n[调试] 文本长度：{len(raw_text)} 字符")
    print(f"[预览] {raw_text[:200]}...")

    flag, reason, _ = intent_alignment(raw_text)
    if flag != 1:
        print(f"  {reason}")
        # 移除交互式输入（适配API调用场景）
        print(" 意图对齐未通过，但仍继续提取考点...")

    # 提取（跳过旧的 validate_and_correct_qwen，因其依赖分类结构）
    exam_points = extract_exam_points_qwen(raw_text)
    final_points = exam_points

    # 轻量校验
    verify_ok, verify_note = light_verify(final_points)

    # 生成结构化 JSON
    result_json = format_as_json(final_points, filename, reason, verify_note)

    return verify_ok, json.dumps(result_json, ensure_ascii=False, indent=2), result_json


def parse_multiple_files_raw(file_paths: list) -> str:
    """
    完整保留多文件解析功能：支持 PDF/DOCX/TXT/图片/音频混合格式，返回合并后的完整文本
    跳过不存在或解析失败的文件。
    """
    all_texts = []
    for i, path in enumerate(file_paths):
        if not os.path.exists(path):
            print(f"⚠️  文件不存在，跳过：{path}")
            continue
        print(f"[感知层] 正在解析文件 {i+1}/{len(file_paths)}: {os.path.basename(path)}")
        text = parse_file_raw(path)
        if "解析失败" in text or "不支持" in text:
            print(f"⚠️  {text}，跳过该文件")
        else:
            all_texts.append(text)
    
    # 合并所有成功解析的文本，用两个换行分隔
    return "\n\n".join(all_texts)

# ---------------------- 主函数 ----------------------
def main():
    print("=" * 60)
    print(" 感知层 ")
    print("=" * 60)

    files = select_files_via_cli()
    if not files:
        print(" 未选择有效文件")
        return

    for i, file in enumerate(files, 1):
        print("-" * 80)
        print(f" 处理第 {i} 个文件：{file}")
        success, result_str, result_json = perception_layer(file)
        print(result_str)
        print(f"\n{' 成功' if success else ' 失败'}")

    print("\n" + "=" * 60)
    print(" 所有文件处理完成！")


# ---------------------- 新增：从纯文本提取考点 ----------------------
def extract_exam_points_from_text(text: str) -> dict:
    """
    完整保留：从原始文本直接提取考点（不涉及文件解析）
    
    Args:
        text (str): 原始教材/笔记文本
        
    Returns:
        dict: {"all_points": [考点1, 考点2, ...]}
    """
    if not text or not text.strip():
        return {"all_points": []}
    
    # 1. 意图对齐（可选，但建议保留）
    flag, reason, _ = intent_alignment(text)
    if flag != 1:
        # 即使意图不符，也尝试提取（避免过度过滤）
        print(f"[感知层] 文本意图可能不符：{reason}，但仍尝试提取考点...")
    
    # 2. 核心考点提取
    exam_points_str = extract_exam_points_qwen(text)
    
    # 3. 轻量校验 & 结构化
    verify_ok, verify_note = light_verify(exam_points_str)
    
    # 4. 转换为列表
    lines = exam_points_str.strip().split("\n")
    all_points = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            content = stripped[2:].strip()
            if content:
                all_points.append(content)
    
    return {
        "all_points": all_points
    }


if __name__ == "__main__":
    main()