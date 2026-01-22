import json
import time
import threading
import requests
from config import settings

class KimiLLM:
    def __init__(self, model="kimi-k2-turbo-preview", rpm_limit=3):
        self.api_key = settings.KIMI_API_KEY
        self.base_url = settings.KIMI_API_BASE
        self.model = model
        
        # 速率限制配置 (Kimi 免费版通常有并发限制，这里设置保守值)
        self.rpm_limit = rpm_limit
        self.interval = 60.0 / self.rpm_limit 
        self.last_request_time = 0
        self.lock = threading.Lock()
        
        if not self.api_key:
            print("Warning: KIMI_API_KEY is not set.")

    def _wait_for_rate_limit(self):
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.interval:
                sleep_time = self.interval - elapsed
                time.sleep(sleep_time)
            self.last_request_time = time.time()

    def chat(self, messages, temperature=0.3):
        """
        调用 Kimi (Moonshot AI) Chat API
        """
        if not self.api_key:
            return None
            
        self._wait_for_rate_limit()
        
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
        
        # Configure requests with retry strategy
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        retry = Retry(
            total=3, 
            backoff_factor=1, 
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        try:
            # Increase timeout significantly as LLM inference can be slow
            response = session.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error calling Kimi LLM: {e}")
            return None
