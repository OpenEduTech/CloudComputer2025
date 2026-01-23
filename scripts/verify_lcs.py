# scripts/verify_lcs.py
import requests
import json

url = "http://localhost:8001/ask"
payload = {
    "question": "请详细讲解最长公共子序列(LCS)的定义和算法实现，最好有代码示例。"
}

print(f"Testing RAG endpoint: {url}...")
try:
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        print("\n✅ RAG Response Received!")
        print("-" * 50)
        print(data["answer"])
        print("-" * 50)

        # 验证是否包含图片链接
        if "seq1.png" in data["answer"] or "seq1.png" in str(data.get("context")):
            print("✅ 成功检索到图片 seq1.png！")
        else:
            print("⚠️ 警告：回答中未发现图片引用，请检查检索相关度。")

        # 验证是否包含特定文本
        if "暴力枚举复杂度高达" in str(data.get("context")):
            print("✅ 成功检索到 manual/LCS_Solution.md 的核心内容！")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Connection Failed: {e}")
