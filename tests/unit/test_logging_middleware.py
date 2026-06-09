import anyio
from starlette.datastructures import Headers, URL
from starlette.responses import Response

from middleware.logging_mw import REQUEST_ID_HEADER, configure_logging, logging_middleware


class FakeLogger:
    def __init__(self):
        self.events = []

    def info(self, event, **fields):
        self.events.append(("info", event, fields))

    def error(self, event, **fields):
        self.events.append(("error", event, fields))


class FakeState:
    pass


class FakeApp:
    def __init__(self, logger):
        self.state = FakeState()
        self.state.logger = logger


class FakeRequest:
    method = "POST"

    def __init__(self, path="/v1/classify", headers=None, logger=None):
        self.app = FakeApp(logger or FakeLogger())
        self.url = URL("http://testserver{0}".format(path))
        self.headers = Headers(headers or {})


async def ok_response(request):
    return Response(status_code=200)


async def failing_response(request):
    raise RuntimeError("boom")


def test_logging_middleware_logs_request_fields_and_sets_request_id():
    logger = FakeLogger()
    request = FakeRequest(
        headers={REQUEST_ID_HEADER: "request-1"},
        logger=logger,
    )

    response = anyio.run(logging_middleware, request, ok_response)

    assert response.headers[REQUEST_ID_HEADER] == "request-1"
    assert logger.events[0][0] == "info"
    assert logger.events[0][1] == "request_completed"
    fields = logger.events[0][2]
    assert fields["request_id"] == "request-1"
    assert fields["method"] == "POST"
    assert fields["path"] == "/v1/classify"
    assert fields["status_code"] == 200
    assert fields["latency_ms"] >= 0
    assert "utterance" not in fields


def test_logging_middleware_generates_request_id_when_missing():
    logger = FakeLogger()
    request = FakeRequest(logger=logger)

    response = anyio.run(logging_middleware, request, ok_response)

    assert response.headers[REQUEST_ID_HEADER]
    assert logger.events[0][2]["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_logging_middleware_logs_error_without_request_body():
    logger = FakeLogger()
    request = FakeRequest(logger=logger)

    try:
        anyio.run(logging_middleware, request, failing_response)
    except RuntimeError:
        pass
    else:
        raise AssertionError("middleware should re-raise downstream errors")

    assert logger.events[0][0] == "error"
    assert logger.events[0][1] == "request_failed"
    fields = logger.events[0][2]
    assert fields["status_code"] == 500
    assert fields["error"] == "RuntimeError"
    assert "utterance" not in fields


def test_configure_logging_registers_state_and_middleware():
    from fastapi import FastAPI

    logger = FakeLogger()
    app = FastAPI()

    configure_logging(app, logger=logger)

    assert app.state.logger is logger
    assert len(app.user_middleware) == 1
