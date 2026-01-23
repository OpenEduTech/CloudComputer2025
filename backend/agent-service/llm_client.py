# llm_client.py
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


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
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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

        for attempt in range(1, max(1, self.max_retries) + 1):
            try:
                resp = self._session.post(
                    url,
                    headers=self._headers,
                    json=payload,
                    timeout=self.timeout,
                )
                last_status = resp.status_code
                last_text = resp.text or ""
                resp.raise_for_status()
                return resp.json()

            except Exception as e:
                last_exc = e
                # Decide retry
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status is None:
                    status = last_status
                if not self._should_retry(status, e):
                    # Non-transient error: fail fast with details
                    body = (last_text[:800] + "…") if len(last_text) > 800 else last_text
                    raise RuntimeError(f"LLM HTTP error (status={status}): {body}") from e

                # Backoff (cap it)
                sleep_s = min(8.0, 1.2 * attempt)
                time.sleep(sleep_s)

        body = (last_text[:800] + "…") if len(last_text) > 800 else last_text
        raise RuntimeError(
            f"LLM request failed after {self.max_retries} retries. "
            f"last_status={last_status}, last_error={last_exc}, body={body}"
        )

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

        # ✅ Some providers support response_format, some don't.
        # We'll try it first, and if server rejects, fall back without it.
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            data = self._post(url, payload)
        except RuntimeError as e:
            # Fallback: if json_mode caused schema error, retry once without response_format
            if json_mode and ("response_format" in str(e) or "json_object" in str(e) or "schema" in str(e)):
                payload.pop("response_format", None)
                data = self._post(url, payload)
            else:
                raise

        # Robust extraction
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Unexpected LLM response shape: {data}") from e
