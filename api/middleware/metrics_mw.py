import time

from fastapi import Request, Response
from prometheus_client import CollectorRegistry, Counter, Histogram
from starlette.middleware.base import RequestResponseEndpoint


def create_metrics(registry=None):
    registry = registry or CollectorRegistry()
    return {
        "request_count": Counter(
            "raic_http_requests_total",
            "Total HTTP requests.",
            ["method", "path", "status_code"],
            registry=registry,
        ),
        "request_latency": Histogram(
            "raic_http_request_latency_seconds",
            "HTTP request latency in seconds.",
            ["method", "path"],
            registry=registry,
        ),
        "decision_count": Counter(
            "raic_classify_decisions_total",
            "Total classify decisions.",
            ["decision", "intent"],
            registry=registry,
        ),
        "timeout_count": Counter(
            "raic_external_timeouts_total",
            "Total external timeout failures.",
            ["source"],
            registry=registry,
        ),
    }


async def metrics_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    started_at = time.monotonic()
    metrics = getattr(request.app.state, "metrics", None)

    try:
        response = await call_next(request)
    except Exception:
        if metrics is not None:
            _observe_request(metrics, request, 500, started_at)
        raise

    if metrics is not None:
        _observe_request(metrics, request, response.status_code, started_at)
    return response


def configure_metrics(app, registry=None) -> None:
    app.state.metrics_registry = registry or CollectorRegistry()
    app.state.metrics = create_metrics(app.state.metrics_registry)
    app.middleware("http")(metrics_middleware)


def record_classify_decision(request: Request, decision: str, intent: str) -> None:
    metrics = getattr(request.app.state, "metrics", None)
    if metrics is not None:
        metrics["decision_count"].labels(decision=decision, intent=intent).inc()


def record_external_timeout(request: Request, source: str) -> None:
    metrics = getattr(request.app.state, "metrics", None)
    if metrics is not None:
        metrics["timeout_count"].labels(source=source).inc()


def _observe_request(metrics, request: Request, status_code: int, started_at: float) -> None:
    path = request.url.path
    method = request.method
    metrics["request_count"].labels(
        method=method,
        path=path,
        status_code=str(status_code),
    ).inc()
    metrics["request_latency"].labels(method=method, path=path).observe(
        max(0.0, time.monotonic() - started_at)
    )
