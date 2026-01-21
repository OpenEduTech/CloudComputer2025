import json
import time
import threading
import requests
from config import settings

class ECNULLM:
    def __init__(self, model="ecnu-plus", rpm_limit=100):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_API_BASE
        self.model = model
        
        # 速率限制配置
        self.rpm_limit = rpm_limit
        self.interval = 60.0 / self.rpm_limit # 每次请求的最小间隔时间 (秒)
        self.last_request_time = 0
        self.lock = threading.Lock() # 线程锁，确保多线程下的速率控制
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY is not set.")

    def _wait_for_rate_limit(self):
        """简单的阻塞式限流"""
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.interval:
                sleep_time = self.interval - elapsed
                time.sleep(sleep_time)
            self.last_request_time = time.time()

    def chat(self, messages, temperature=0.1):
        """
        调用 ChatECNU Chat API (带限流)
        """
        self._wait_for_rate_limit() # 在发起请求前等待
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error calling ECNU LLM: {e}")
            return None

    def extract_keywords(self, text: str, prompt_template: str) -> list:
        """
        使用指定 Prompt 提取关键词
        """
        messages = [
            {"role": "system", "content": prompt_template},
            {"role": "user", "content": text}
        ]
        
        result = self.chat(messages)
        if not result:
            return []
            
        # 解析 JSON
        try:
            # 清理可能的 Markdown 代码块标记
            cleaned_result = result.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_result)
            return data.get("entities", [])
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from LLM response: {result[:100]}...")
            return []
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return []
