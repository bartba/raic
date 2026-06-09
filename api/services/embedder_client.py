from typing import Any, List, Optional

import httpx


class EmbedderClientError(RuntimeError):
    pass


class EmbedderClient:
    def __init__(
        self,
        base_url: str,
        client: Optional[httpx.Client] = None,
        timeout_ms: int = 800,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_ms / 1000.0
        self.client = client or httpx.Client(timeout=self.timeout_seconds)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        try:
            response = self.client.post(
                "{0}/embed".format(self.base_url),
                json={"inputs": texts},
            )
        except httpx.TimeoutException as error:
            raise EmbedderClientError("embedder request timed out") from error
        except httpx.RequestError as error:
            raise EmbedderClientError(
                "embedder request failed: {0}".format(error)
            ) from error

        if response.status_code >= 400:
            raise EmbedderClientError(
                "embedder request failed with status {0}".format(response.status_code)
            )

        try:
            data = response.json()
        except ValueError as error:
            raise EmbedderClientError("embedder response must be valid json") from error

        return _parse_embeddings(data)

    def embed_text(self, text: str) -> List[float]:
        embeddings = self.embed_texts([text])
        if len(embeddings) != 1:
            raise EmbedderClientError("embedder returned unexpected embedding count")
        return embeddings[0]


def _parse_embeddings(data: Any) -> List[List[float]]:
    if not isinstance(data, list):
        raise EmbedderClientError("embedder response must be a list")

    embeddings = []
    for item in data:
        if not isinstance(item, list):
            raise EmbedderClientError("embedding item must be a list")

        embedding = []
        for value in item:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise EmbedderClientError("embedding value must be a number")
            embedding.append(float(value))
        embeddings.append(embedding)

    return embeddings
