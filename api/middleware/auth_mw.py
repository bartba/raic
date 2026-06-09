from typing import Iterable

from fastapi import Request, Response, status
from starlette.middleware.base import RequestResponseEndpoint


PUBLIC_PATHS = {"/health", "/ready", "/metrics"}


async def auth_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    token = getattr(request.app.state, "api_auth_token", None)
    public_paths = getattr(request.app.state, "auth_public_paths", PUBLIC_PATHS)
    if not token or request.url.path in public_paths:
        return await call_next(request)

    authorization = request.headers.get("authorization")
    if authorization != "Bearer {0}".format(token):
        return Response(
            content='{"detail":"unauthorized"}',
            status_code=status.HTTP_401_UNAUTHORIZED,
            media_type="application/json",
        )

    return await call_next(request)


def configure_auth(app, token=None, public_paths: Iterable[str] = PUBLIC_PATHS) -> None:
    app.state.api_auth_token = token
    app.state.auth_public_paths = set(public_paths)
    app.middleware("http")(auth_middleware)
