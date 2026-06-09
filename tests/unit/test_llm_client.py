from services.llm_client import LLMClient, LLMClientError


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeChatModel:
    def __init__(self, response):
        self.response = response
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return self.response


class FailingChatModel:
    def invoke(self, messages):
        raise RuntimeError("server error")


class TimeoutChatModel:
    def invoke(self, messages):
        raise TimeoutError("too slow")


def test_generate_json_invokes_langchain_chat_model_with_prompts():
    chat_model = FakeChatModel(
        FakeResponse('{"intent":"check_status","slots":{},"confidence_score":0.9}')
    )
    client = LLMClient(
        base_url="http://llm.local/v1/",
        model_name="Qwen3.5-35B-A3B",
        chat_model=chat_model,
    )

    result = client.generate_json("system prompt", "user prompt")

    assert result == '{"intent":"check_status","slots":{},"confidence_score":0.9}'
    assert chat_model.messages == [
        ("system", "system prompt"),
        ("human", "user prompt"),
    ]
    assert client.base_url == "http://llm.local/v1"


def test_generate_json_extracts_text_content_blocks():
    chat_model = FakeChatModel(
        FakeResponse(
            [
                {"type": "text", "text": '{"intent":"check_status",'},
                {"type": "text", "text": '"slots":{},"confidence_score":0.9}'},
            ]
        )
    )
    client = LLMClient(
        base_url="http://llm.local/v1",
        model_name="Qwen3.5-35B-A3B",
        chat_model=chat_model,
    )

    assert (
        client.generate_json("system prompt", "user prompt")
        == '{"intent":"check_status","slots":{},"confidence_score":0.9}'
    )


def test_generate_json_rejects_empty_content():
    client = LLMClient(
        base_url="http://llm.local/v1",
        model_name="Qwen3.5-35B-A3B",
        chat_model=FakeChatModel(FakeResponse("")),
    )

    try:
        client.generate_json("system prompt", "user prompt")
    except LLMClientError as error:
        assert str(error) == "llm response content is empty"
        return

    raise AssertionError("empty llm response should fail")


def test_generate_json_wraps_model_error():
    client = LLMClient(
        base_url="http://llm.local/v1",
        model_name="Qwen3.5-35B-A3B",
        chat_model=FailingChatModel(),
    )

    try:
        client.generate_json("system prompt", "user prompt")
    except LLMClientError as error:
        assert str(error) == "llm request failed: server error"
        return

    raise AssertionError("llm model error should fail")


def test_generate_json_wraps_timeout_error():
    client = LLMClient(
        base_url="http://llm.local/v1",
        model_name="Qwen3.5-35B-A3B",
        chat_model=TimeoutChatModel(),
    )

    try:
        client.generate_json("system prompt", "user prompt")
    except LLMClientError as error:
        assert str(error) == "llm request timed out"
        return

    raise AssertionError("llm timeout should fail")
