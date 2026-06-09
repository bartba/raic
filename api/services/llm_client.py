from typing import Any, Optional


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
        chat_model: Optional[Any] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
        self.timeout_seconds = timeout_ms / 1000.0
        self.max_retries = max_retries
        self.chat_model = chat_model or self._build_chat_model()

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.chat_model.invoke(
                [
                    ("system", system_prompt),
                    ("human", user_prompt),
                ]
            )
        except TimeoutError as error:
            raise LLMClientError("llm request timed out") from error
        except Exception as error:
            raise LLMClientError("llm request failed: {0}".format(error)) from error

        return _extract_text_content(response)

    def _build_chat_model(self) -> Any:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as error:
            raise LLMClientError(
                "langchain-openai is required to use LLMClient without a chat_model"
            ) from error

        return ChatOpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "unused",
            model=self.model_name,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )


def _extract_text_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        if not content:
            raise LLMClientError("llm response content is empty")
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                text_parts.append(item["text"])

        text = "".join(text_parts)
        if text:
            return text

    raise LLMClientError("llm response content must be text")
