import httpx

from services.embedder_client import EmbedderClient, EmbedderClientError


def make_client(handler):
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return EmbedderClient("http://embedder.local/", client=http_client)


def test_embed_texts_posts_to_tei_embed_endpoint():
    def handler(request):
        assert request.method == "POST"
        assert str(request.url) == "http://embedder.local/embed"
        assert request.read() == b'{"inputs":["hello","world"]}'
        return httpx.Response(200, json=[[0.1, 0.2], [0.3, 0.4]])

    client = make_client(handler)

    assert client.embed_texts(["hello", "world"]) == [[0.1, 0.2], [0.3, 0.4]]


def test_embed_text_returns_single_embedding():
    client = make_client(lambda request: httpx.Response(200, json=[[1, 2, 3]]))

    assert client.embed_text("hello") == [1.0, 2.0, 3.0]


def test_embed_text_rejects_unexpected_embedding_count():
    client = make_client(lambda request: httpx.Response(200, json=[]))

    try:
        client.embed_text("hello")
    except EmbedderClientError as error:
        assert str(error) == "embedder returned unexpected embedding count"
        return

    raise AssertionError("unexpected embedding count should fail")


def test_embed_texts_rejects_http_error():
    client = make_client(lambda request: httpx.Response(503, json={"error": "down"}))

    try:
        client.embed_texts(["hello"])
    except EmbedderClientError as error:
        assert str(error) == "embedder request failed with status 503"
        return

    raise AssertionError("http error should fail")


def test_embed_texts_rejects_timeout():
    def handler(request):
        raise httpx.ReadTimeout("too slow", request=request)

    client = make_client(handler)

    try:
        client.embed_texts(["hello"])
    except EmbedderClientError as error:
        assert str(error) == "embedder request timed out"
        return

    raise AssertionError("timeout should fail")


def test_embed_texts_rejects_request_error():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    client = make_client(handler)

    try:
        client.embed_texts(["hello"])
    except EmbedderClientError as error:
        assert str(error) == "embedder request failed: connection refused"
        return

    raise AssertionError("request error should fail")


def test_embed_texts_rejects_invalid_response_shape():
    client = make_client(lambda request: httpx.Response(200, json={"embedding": [0.1]}))

    try:
        client.embed_texts(["hello"])
    except EmbedderClientError as error:
        assert str(error) == "embedder response must be a list"
        return

    raise AssertionError("invalid response shape should fail")
