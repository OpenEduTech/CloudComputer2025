from backend.models.llm_graph_builder import BASE_URL, API_KEY, MODEL_ID
from volcenginesdkarkruntime import Ark
from backend.models.lib.ark_io import extract_text_from_ark_response, extract_token_detail

def llm_chat(message, history):
    if not message:
        return {"error": "empty message"}

    if not API_KEY or not MODEL_ID:
        return {"error": "missing VOLC_ARK_API_KEY or VOLC_ARK_MODEL", "reply": ""}

    # 组装上下文，将历史对话压缩为文本提示
    lines = []
    for item in history[-8:]:  # 仅保留最近 8 轮，避免提示过长
        role = item.get("role") or "user"
        text = item.get("text") or ""
        lines.append(f"{role}: {text}")
    lines.append(f"user: {message}")
    prompt_text = "\n".join(lines)

    client = Ark(base_url=BASE_URL, api_key=API_KEY)
    resp = client.responses.create(
        model=MODEL_ID,
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt_text}]}],
    )
    reply_text = extract_text_from_ark_response(resp)
    usage = extract_token_detail(resp)
    return reply_text, usage