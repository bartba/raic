import json
from typing import Optional

import httpx


class LLMClientError(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        api_key: Optional[str] = None,
        timeout_ms: int = 800,
        max_retries: int = 0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
        self.timeout_ms = timeout_ms
        self.timeout = httpx.Timeout(
            timeout=timeout_ms / 1000.0,
            connect=timeout_ms / 1000.0,
            read=timeout_ms / 1000.0,
            write=timeout_ms / 1000.0,
            pool=timeout_ms / 1000.0,
        )
        self.max_retries = max(0, max_retries)

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 2048,
            "stream": False,
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = self._post_with_retries(client, url, headers, payload)

        if response.status_code >= 400:
            raise LLMClientError(
                f"llm request failed with status {response.status_code}: {response.text[:200]}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as error:
            raise LLMClientError("llm response is not valid JSON") from error

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as error:
            raise LLMClientError("llm response missing expected fields") from error

        if not content or not isinstance(content, str):
            raise LLMClientError("llm response content is empty or invalid")

        return content

    def _post_with_retries(
        self,
        client: httpx.Client,
        url: str,
        headers: dict,
        payload: dict,
    ) -> httpx.Response:
        attempts = self.max_retries + 1

        for attempt in range(attempts):
            try:
                response = client.post(url, headers=headers, json=payload)
            except httpx.TimeoutException as error:
                if attempt < self.max_retries:
                    continue
                raise LLMClientError("llm request timed out") from error
            except httpx.RequestError as error:
                if attempt < self.max_retries:
                    continue
                raise LLMClientError(f"llm request failed: {error}") from error

            if response.status_code < 500 or attempt == self.max_retries:
                return response

        raise LLMClientError("llm request failed")
