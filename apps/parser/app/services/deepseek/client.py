import time
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import httpx

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger("deepseek_client")

class DeepSeekClient:
    """
    Асинхронный клиент для взаимодействия с DeepSeek API.
    Поддерживает таймауты, ретраи, структурированный JSON-вывод и проверку здоровья (ping).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 20.0
    ):
        self.api_key = (api_key or DEEPSEEK_API_KEY or "").strip()
        self.base_url = (base_url or DEEPSEEK_BASE_URL or "https://api.deepseek.com").strip().rstrip("/")
        self.model = (model or DEEPSEEK_MODEL or "deepseek-chat").strip()
        self.timeout = timeout

    def set_api_key(self, new_key: str):
        self.api_key = new_key.strip()

    def is_configured(self) -> bool:
        if not self.api_key:
            import os
            self.api_key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
        return bool(self.api_key and not self.api_key.startswith("sk-placeholder"))

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.5,
        max_tokens: int = 600,
        json_mode: bool = False,
        retries: int = 2
    ) -> str:
        """
        Отправляет запрос на генерацию ответа.
        Возвращает текстовый ответ модели.
        """
        if not self.is_configured():
            raise ValueError("DeepSeek API ключ не настроен. Задайте DEEPSEEK_API_KEY.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_error = None
        for attempt in range(1, retries + 2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "").strip()
                        return ""
                    elif response.status_code == 429:
                        logger.warning(f"DeepSeek Rate Limit (429), попытка {attempt}...")
                        last_error = f"DeepSeek rate limit 429: {response.text}"
                    else:
                        last_error = f"DeepSeek HTTP {response.status_code}: {response.text}"
                        logger.warning(f"Ошибка DeepSeek (попытка {attempt}): {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Сбой соединения с DeepSeek (попытка {attempt}): {e}")

        raise RuntimeError(f"Не удалось получить ответ от DeepSeek после {retries + 1} попыток: {last_error}")

    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 600
    ) -> Dict[str, Any]:
        """
        Гарантированно возвращает распарсенный JSON словарь из ответа модели.
        """
        content = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Очистка markdown блоков ```json ... ``` при необходимости
            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())

    async def ping(self) -> Tuple[bool, float, str]:
        """
        Проверка доступности DeepSeek API и замер задержки (latency в ms).
        """
        if not self.is_configured():
            return False, 0.0, "API ключ не настроен"

        start_time = time.perf_counter()
        try:
            # Легкий проверочный запрос
            test_messages = [{"role": "user", "content": "ping"}]
            await self.chat_completion(test_messages, max_tokens=5, retries=0)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return True, round(latency_ms, 1), "OK"
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return False, round(latency_ms, 1), str(e)


# Синглтон клиент
deepseek_client = DeepSeekClient()
