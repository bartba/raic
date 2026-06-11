import json
from unittest.mock import Mock, patch

import httpx

from services.llm_client import LLMClient, LLMClientError


def test_generate_json_sends_correct_http_payload():
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"intent":"test","slots":{},"confidence_score":0.9}'}}]
    }

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        client = LLMClient(
            base_url="http://llm.local/v1",
            model_name="test-model",
            timeout_ms=1000,
        )
        result = client.generate_json("system", "user")

        assert result == '{"intent":"test","slots":{},"confidence_score":0.9}'
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://llm.local/v1/chat/completions"
        assert call_args[1]["json"]["model"] == "test-model"
        assert call_args[1]["json"]["stream"] is False
        assert len(call_args[1]["json"]["messages"]) == 2
        assert call_args[1]["json"]["messages"][0]["role"] == "system"
        assert call_args[1]["json"]["messages"][0]["content"] == "system"
        assert call_args[1]["json"]["messages"][1]["role"] == "user"
        assert call_args[1]["json"]["messages"][1]["content"] == "user"


def test_generate_json_sets_auth_header():
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"intent":"test","slots":{},"confidence_score":0.9}'}}]
    }

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        client = LLMClient(
            base_url="http://llm.local/v1",
            model_name="test-model",
            api_key="test-token",
        )
        client.generate_json("system", "user")

        assert mock_post.call_args[1]["headers"]["Authorization"] == "Bearer test-token"
        assert mock_post.call_args[1]["headers"]["Content-Type"] == "application/json"


def test_generate_json_applies_timeout():
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"intent":"test","slots":{},"confidence_score":0.9}'}}]
    }

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        client = LLMClient(base_url="http://llm.local/v1", model_name="test", timeout_ms=800)
        client.generate_json("system", "user")

        # Verify timeout was used
        assert client.timeout_ms == 800
        assert client.timeout.connect == 0.8
        assert client.timeout.read == 0.8
        # Verify post was called
        assert mock_post.called


def test_generate_json_handles_timeout_exception():
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("timed out")):
        client = LLMClient(base_url="http://llm.local/v1", model_name="test", timeout_ms=800)

        try:
            client.generate_json("system", "user")
            assert False, "should raise LLMClientError"
        except LLMClientError as e:
            assert "timed out" in str(e).lower()


def test_generate_json_handles_request_error():
    with patch("httpx.Client.post", side_effect=httpx.ConnectError("connection failed")):
        client = LLMClient(base_url="http://llm.local/v1", model_name="test", timeout_ms=800)

        try:
            client.generate_json("system", "user")
            assert False, "should raise LLMClientError"
        except LLMClientError as e:
            assert "connection failed" in str(e)


def test_generate_json_retries_timeout_then_returns_success():
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"intent":"test","slots":{},"confidence_score":0.9}'}}]
    }

    with patch(
        "httpx.Client.post",
        side_effect=[httpx.TimeoutException("timed out"), mock_response],
    ) as mock_post:
        client = LLMClient(
            base_url="http://llm.local/v1",
            model_name="test",
            timeout_ms=800,
            max_retries=1,
        )

        result = client.generate_json("system", "user")

        assert result == '{"intent":"test","slots":{},"confidence_score":0.9}'
        assert mock_post.call_count == 2


def test_generate_json_retries_server_error_then_returns_success():
    server_error = Mock(spec=httpx.Response)
    server_error.status_code = 503
    server_error.text = "Service Unavailable"

    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"intent":"test","slots":{},"confidence_score":0.9}'}}]
    }

    with patch(
        "httpx.Client.post",
        side_effect=[server_error, mock_response],
    ) as mock_post:
        client = LLMClient(
            base_url="http://llm.local/v1",
            model_name="test",
            timeout_ms=800,
            max_retries=1,
        )

        result = client.generate_json("system", "user")

        assert result == '{"intent":"test","slots":{},"confidence_score":0.9}'
        assert mock_post.call_count == 2


def test_generate_json_does_not_retry_client_error_status():
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        client = LLMClient(
            base_url="http://llm.local/v1",
            model_name="test",
            timeout_ms=800,
            max_retries=3,
        )

        try:
            client.generate_json("system", "user")
            assert False, "should raise LLMClientError"
        except LLMClientError as e:
            assert "401" in str(e)
            assert mock_post.call_count == 1


def test_generate_json_handles_http_error_status():
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    with patch("httpx.Client.post", return_value=mock_response):
        client = LLMClient(base_url="http://llm.local/v1", model_name="test", timeout_ms=800)

        try:
            client.generate_json("system", "user")
            assert False, "should raise LLMClientError"
        except LLMClientError as e:
            assert "401" in str(e)


def test_generate_json_handles_invalid_json():
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.side_effect = json.JSONDecodeError("expecting value", "response", 0)

    with patch("httpx.Client.post", return_value=mock_response):
        client = LLMClient(base_url="http://llm.local/v1", model_name="test", timeout_ms=800)

        try:
            client.generate_json("system", "user")
            assert False, "should raise LLMClientError"
        except LLMClientError as e:
            assert "valid json" in str(e).lower()


def test_generate_json_handles_missing_fields():
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": []}

    with patch("httpx.Client.post", return_value=mock_response):
        client = LLMClient(base_url="http://llm.local/v1", model_name="test", timeout_ms=800)

        try:
            client.generate_json("system", "user")
            assert False, "should raise LLMClientError"
        except LLMClientError as e:
            assert "missing expected fields" in str(e).lower()


def test_generate_json_handles_empty_content():
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": ""}}]}

    with patch("httpx.Client.post", return_value=mock_response):
        client = LLMClient(base_url="http://llm.local/v1", model_name="test", timeout_ms=800)

        try:
            client.generate_json("system", "user")
            assert False, "should raise LLMClientError"
        except LLMClientError as e:
            assert "empty" in str(e).lower()
