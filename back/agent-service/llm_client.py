# llm_client.py
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
import json
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class LLMClient:
    """
    OpenAI-compatible chat completions client.
    Default targets SiliconFlow: https://api.siliconflow.cn/v1

    Key improvements vs your version:
    - load_dotenv() so .env works out of the box
    - safer retry policy (only retry on transient errors)
    - json_mode has graceful fallback (provider may not support response_format)
    - clearer error messages (status code + truncated body)
    """

    def __init__(self) -> None:
        # ✅ allow .env
        load_dotenv()

        self.api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3.2").strip()

        self.timeout = int(os.getenv("LLM_TIMEOUT", "300"))
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))

        # Optional: if provider supports it, can reduce randomness further
        self.default_temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set. Please set it in .env or export it.")

        self._session = requests.Session()
        # 确保会话使用UTF-8编码
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json; charset=utf-8",
        })
        # 保存headers引用用于日志
        self._headers = self._session.headers

        # 创建适配器，暂时禁用SSL验证（如果有证书问题）
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=3
        )
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)

        # 暂时禁用SSL验证（生产环境应该启用）
        self._session.verify = False

    def _should_retry(self, status_code: Optional[int], exc: Optional[BaseException]) -> bool:
        # Network/timeout -> retry
        if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
            return True
        # HTTP transient: 408/429/5xx
        if status_code in (408, 429, 500, 502, 503, 504):
            return True
        return False

    def _post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        last_exc: Optional[BaseException] = None
        last_status: Optional[int] = None
        last_text: str = ""

        json_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')

        for attempt in range(1, max(1, self.max_retries) + 1):
            try:
                resp = self._session.post(url, headers=self._headers, data=json_data, timeout=self.timeout)
                last_status = resp.status_code
                resp.encoding = 'utf-8'
                last_text = resp.text or ""

                logger.info(f"HTTP响应状态: {last_status}, 响应长度: {len(last_text)}")

                try:
                    resp.raise_for_status()
                except requests.exceptions.HTTPError as http_err:
                    logger.error(f"HTTP错误: {http_err}, body: {last_text[:300]}")
                    raise RuntimeError(f"LLM HTTP error (status={last_status}): {last_text[:500]}") from http_err

                # 尝试解析 JSON
                try:
                    return resp.json()
                except json.JSONDecodeError:
                    # 试图清洗控制字符后再解析
                    import re
                    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', last_text)
                    try:
                        return json.loads(cleaned)
                    except json.JSONDecodeError:
                        logger.warning("LLM 返回的 JSON 无法解析，返回原始文本供上层处理")
                        # 将无法解析的 body 放在错误里
                        raise RuntimeError(f"LLM JSON解析失败: {last_text[:1000]}")

            except Exception as e:
                last_exc = e
                status = getattr(getattr(e, "response", None), "status_code", None) or last_status
                logger.error(f"LLM请求失败 - 尝试: {attempt}, 状态码: {status}, 异常: {type(e).__name__}: {e}")
                logger.error(f"请求URL: {url}")
                logger.error(f"请求头: {self._headers}")
                logger.error(f"请求数据长度: {len(json_data)}")
                logger.error(f"响应文本长度: {len(last_text)}")
                logger.error(f"响应文本前200字符: {repr(last_text[:200])}")

                if not self._should_retry(status, e) or attempt == self.max_retries:
                    body = (last_text[:800] + "…") if len(last_text) > 800 else last_text
                    raise RuntimeError(f"LLM request failed after {attempt} attempts. last_status={status}, body={body}") from e

                # 指数退避
                time.sleep(min(8.0, 1.2 * attempt))

        raise RuntimeError("LLM request failed: exhausted retries")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """
        messages: [{"role":"system","content":"..."}, {"role":"user","content":"..."}]
        returns: assistant message content (str)
        """
        url = f"{self.base_url}/chat/completions"
        temp = self.default_temperature if temperature is None else float(temperature)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
        }
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)

        # 暂时移除response_format参数，因为可能导致兼容性问题
        # if json_mode:
        #     payload["response_format"] = {"type": "json_object"}

        try:
            data = self._post(url, payload)
        except RuntimeError as e:
            # 如果是response_format相关错误，可以重试
            if json_mode and ("response_format" in str(e) or "json_object" in str(e) or "schema" in str(e)):
                logger.warning("response_format参数可能不受支持，重试中...")
                # payload.pop("response_format", None)
                data = self._post(url, payload)
            else:
                raise

        # Robust extraction
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Unexpected LLM response shape: {data}") from e
