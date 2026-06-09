from types import SimpleNamespace

from main import create_app


def test_create_app_configures_auth_token_from_explicit_argument():
    app = create_app(api_auth_token="secret")

    assert app.state.api_auth_token == "secret"


def test_create_app_configures_auth_token_from_settings():
    settings = SimpleNamespace(api_auth_token="from-settings")

    app = create_app(settings=settings)

    assert app.state.api_auth_token == "from-settings"
