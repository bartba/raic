import anyio
from fastapi import FastAPI
from starlette.datastructures import Headers, URL

from middleware.auth_mw import auth_middleware, configure_auth


class FakeState:
    pass


class FakeApp:
    def __init__(self, token=None):
        self.state = FakeState()
        self.state.api_auth_token = token
        self.state.auth_public_paths = {"/health", "/ready", "/metrics"}


class FakeRequest:
    def __init__(self, path, headers=None, token=None):
        self.app = FakeApp(token=token)
        self.url = URL("http://testserver{0}".format(path))
        self.headers = Headers(headers or {})


async def ok_response(request):
    return "ok"


def run_middleware(request):
    return anyio.run(auth_middleware, request, ok_response)


def test_auth_middleware_allows_request_when_token_is_not_configured():
    response = run_middleware(FakeRequest("/v1/classify"))

    assert response == "ok"


def test_auth_middleware_allows_public_paths_without_token_header():
    response = run_middleware(FakeRequest("/health", token="secret"))

    assert response == "ok"


def test_auth_middleware_rejects_missing_token():
    response = run_middleware(FakeRequest("/v1/classify", token="secret"))

    assert response.status_code == 401
    assert response.body == b'{"detail":"unauthorized"}'


def test_auth_middleware_rejects_wrong_token():
    response = run_middleware(
        FakeRequest(
            "/v1/classify",
            headers={"authorization": "Bearer wrong"},
            token="secret",
        )
    )

    assert response.status_code == 401


def test_auth_middleware_allows_valid_bearer_token():
    response = run_middleware(
        FakeRequest(
            "/v1/classify",
            headers={"authorization": "Bearer secret"},
            token="secret",
        )
    )

    assert response == "ok"


def test_configure_auth_registers_state_and_middleware():
    app = FastAPI()

    configure_auth(app, token="secret")

    assert app.state.api_auth_token == "secret"
    assert "/health" in app.state.auth_public_paths
    assert len(app.user_middleware) == 1
