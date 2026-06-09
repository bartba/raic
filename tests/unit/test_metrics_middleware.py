import anyio
from prometheus_client import CollectorRegistry, generate_latest
from starlette.datastructures import URL
from starlette.responses import Response

from middleware.metrics_mw import (
    configure_metrics,
    metrics_middleware,
    record_classify_decision,
    record_external_timeout,
)


class FakeState:
    pass


class FakeApp:
    def __init__(self):
        self.state = FakeState()

    def middleware(self, kind):
        def register(func):
            self.middleware_kind = kind
            self.middleware_func = func
            return func

        return register


class FakeRequest:
    method = "POST"

    def __init__(self, app, path="/v1/classify"):
        self.app = app
        self.url = URL("http://testserver{0}".format(path))


async def ok_response(request):
    return Response(status_code=200)


async def failing_response(request):
    raise RuntimeError("boom")


def metrics_text(registry):
    return generate_latest(registry).decode("utf-8")


def test_metrics_middleware_records_request_count_and_latency():
    app = FakeApp()
    configure_metrics(app, registry=CollectorRegistry())
    request = FakeRequest(app)

    response = anyio.run(metrics_middleware, request, ok_response)
    output = metrics_text(app.state.metrics_registry)

    assert response.status_code == 200
    assert 'raic_http_requests_total{method="POST",path="/v1/classify",status_code="200"} 1.0' in output
    assert 'raic_http_request_latency_seconds_count{method="POST",path="/v1/classify"} 1.0' in output


def test_metrics_middleware_records_failed_request():
    app = FakeApp()
    configure_metrics(app, registry=CollectorRegistry())
    request = FakeRequest(app)

    try:
        anyio.run(metrics_middleware, request, failing_response)
    except RuntimeError:
        pass
    else:
        raise AssertionError("middleware should re-raise downstream errors")

    output = metrics_text(app.state.metrics_registry)
    assert 'raic_http_requests_total{method="POST",path="/v1/classify",status_code="500"} 1.0' in output


def test_record_classify_decision_increments_counter():
    app = FakeApp()
    configure_metrics(app, registry=CollectorRegistry())
    request = FakeRequest(app)

    record_classify_decision(request, "confirm", "check_status")

    output = metrics_text(app.state.metrics_registry)
    assert 'raic_classify_decisions_total{decision="confirm",intent="check_status"} 1.0' in output


def test_record_external_timeout_increments_counter():
    app = FakeApp()
    configure_metrics(app, registry=CollectorRegistry())
    request = FakeRequest(app)

    record_external_timeout(request, "llm")

    output = metrics_text(app.state.metrics_registry)
    assert 'raic_external_timeouts_total{source="llm"} 1.0' in output
