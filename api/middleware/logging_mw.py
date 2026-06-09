import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint


REQUEST_ID_HEADER = "x-request-id"


async def logging_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
    logger = getattr(request.app.state, "logger", structlog.get_logger("raic.request"))
    started_at = time.monotonic()

    try:
        response = await call_next(request)
    except Exception as error:
        logger.error(
            "request_failed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=500,
            latency_ms=_elapsed_ms(started_at),
            error=error.__class__.__name__,
        )
        raise

    response.headers[REQUEST_ID_HEADER] = request_id
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=_elapsed_ms(started_at),
    )
    return response


def configure_logging(app, logger=None) -> None:
    app.state.logger = logger or structlog.get_logger("raic.request")
    app.middleware("http")(logging_middleware)


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))
