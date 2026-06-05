from pydantic import ValidationError

from config import Settings


def test_settings_load_required_env(monkeypatch):
    monkeypatch.setenv("LLM_API_URL", "http://llm.local")
    monkeypatch.setenv("API_AUTH_TOKEN", "secret-token")

    settings = Settings()

    assert settings.llm_api_url == "http://llm.local"
    assert settings.api_auth_token == "secret-token"
    assert settings.policy_mode == "confirm_all"
    assert settings.faiss_top_k == 10


def test_settings_allow_missing_api_auth_token(monkeypatch):
    monkeypatch.setenv("LLM_API_URL", "http://llm.local")
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)

    settings = Settings()

    assert settings.llm_api_url == "http://llm.local"
    assert settings.api_auth_token is None


def test_settings_require_llm_url(monkeypatch):
    monkeypatch.delenv("LLM_API_URL", raising=False)
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)

    try:
        Settings()
    except ValidationError as error:
        missing_fields = {item["loc"][0] for item in error.errors()}
    else:
        raise AssertionError("Settings should require LLM_API_URL")

    assert "LLM_API_URL" in missing_fields
